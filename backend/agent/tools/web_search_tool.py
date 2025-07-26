from tavily import AsyncTavilyClient
import httpx
from dotenv import load_dotenv
from agentpress.tool import Tool, ToolResult, openapi_schema, xml_schema
from utils.config import config
from sandbox.tool_base import SandboxToolsBase
from agentpress.thread_manager import ThreadManager
import json
import os
import datetime
import asyncio
import logging

# TODO: add subpages, etc... in filters as sometimes its necessary 

class SandboxWebSearchTool(SandboxToolsBase):
    """Tool for performing web searches using Tavily API and web scraping using Firecrawl."""

    def __init__(self, project_id: str, thread_manager: ThreadManager):
        super().__init__(project_id, thread_manager)
        # Load environment variables
        load_dotenv()
        # Use API keys from config
        self.tavily_api_key = config.TAVILY_API_KEY
        self.firecrawl_api_key = config.FIRECRAWL_API_KEY
        self.firecrawl_url = config.FIRECRAWL_URL
        
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY not found in configuration")
        if not self.firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in configuration")

        # Tavily asynchronous search client
        self.tavily_client = AsyncTavilyClient(api_key=self.tavily_api_key)

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web using the Tavily API to find relevant and up-to-date information. Now returns up to 50 results by default for more comprehensive coverage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to execute"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of search results to return (1-50, default 50 for comprehensive coverage)",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 50
                    }
                },
                "required": ["query"]
            }
        }
    })
    @xml_schema(
        tag_name="web-search",
        mappings=[
            {"param_name": "query", "node_type": "attribute", "path": "."},
            {"param_name": "num_results", "node_type": "attribute", "path": "."}
        ],
        example='''
        <function_calls>
        <invoke name="web_search">
        <parameter name="query">what is Kortix AI and what are they building?</parameter>
        <parameter name="num_results">20</parameter>
        </invoke>
        </function_calls>
        
        <!-- Another search example -->
        <function_calls>
        <invoke name="web_search">
        <parameter name="query">latest AI research on transformer models</parameter>
        <parameter name="num_results">20</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def web_search(
        self, 
        query: str,
        num_results: int = 50  # Increased from 20 to 50 for better coverage
    ) -> ToolResult:
        """
        Search the web using the Tavily API to find relevant and up-to-date information.
        Now defaults to 50 results for more comprehensive research capability.
        """
        try:
            # Ensure we have a valid query
            if not query or not isinstance(query, str):
                return self.fail_response("A valid search query is required.")
            
            # Normalize num_results - now defaults to 50 for better coverage
            if num_results is None:
                num_results = 50
            elif isinstance(num_results, int):
                num_results = max(1, min(num_results, 50))
            elif isinstance(num_results, str):
                try:
                    num_results = max(1, min(int(num_results), 50))
                except ValueError:
                    num_results = 50
            else:
                num_results = 50

            # Execute the search with Tavily - enhanced for comprehensive results
            logging.info(f"Executing ENHANCED web search for query: '{query}' with {num_results} results")
            search_response = await self.tavily_client.search(
                query=query,
                max_results=num_results,
                include_images=True,
                include_answer="advanced",
                search_depth="advanced",  # Use advanced search for better quality
                include_domains=None,     # Don't restrict domains for comprehensive results
                exclude_domains=None,     # Don't exclude domains
            )
            
            # Check if we have actual results or an answer
            results = search_response.get('results', [])
            answer = search_response.get('answer', '')
            
            # Return the complete Tavily response with enhanced metadata
            # This includes the query, answer, results, images and more
            search_response['search_metadata'] = {
                'query': query,
                'requested_results': num_results,
                'actual_results': len(results),
                'has_answer': bool(answer and answer.strip()),
                'enhanced_search': True,
                'search_depth': 'advanced'
            }
            
            logging.info(f"ENHANCED search completed for '{query}': {len(results)} results, answer: {bool(answer)}")
            
            # Consider search successful if we have either results OR an answer
            if len(results) > 0 or (answer and answer.strip()):
                return ToolResult(
                    success=True,
                    output=json.dumps(search_response, ensure_ascii=False)
                )
            else:
                # No results or answer found
                logging.warning(f"No search results or answer found for query: '{query}'")
                return ToolResult(
                    success=False,
                    output=json.dumps(search_response, ensure_ascii=False)
                )
        
        except Exception as e:
            error_message = str(e)
            logging.error(f"Error performing enhanced web search for '{query}': {error_message}")
            simplified_message = f"Error performing web search: {error_message[:200]}"
            if len(error_message) > 200:
                simplified_message += "..."
            return self.fail_response(simplified_message)

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "comprehensive_search",
            "description": "Perform comprehensive multi-query search for complex research topics. Automatically generates and executes multiple related search queries to ensure complete coverage of the topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "main_query": {
                        "type": "string",
                        "description": "The primary search query or topic to research comprehensively"
                    },
                    "additional_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional additional search queries to expand coverage (will auto-generate if not provided)",
                        "default": []
                    },
                    "max_results_per_query": {
                        "type": "integer",
                        "description": "Maximum results per individual search (default 25)",
                        "minimum": 5,
                        "maximum": 50,
                        "default": 25
                    }
                },
                "required": ["main_query"]
            }
        }
    })
    async def comprehensive_search(
        self,
        main_query: str,
        additional_queries: list = None,
        max_results_per_query: int = 25
    ) -> ToolResult:
        """
        Perform comprehensive multi-query search for thorough topic coverage.
        Automatically generates multiple search variations and aggregates results.
        """
        try:
            if not main_query or not isinstance(main_query, str):
                return self.fail_response("A valid main search query is required.")

            # Auto-generate additional search queries if not provided
            if not additional_queries:
                additional_queries = []
                
                # Generate query variations for comprehensive coverage
                base_terms = main_query.lower().split()
                
                # Add specific variations based on common research patterns
                if any(term in main_query.lower() for term in ['subnet', 'network', 'protocol']):
                    additional_queries.extend([
                        f"{main_query} list complete",
                        f"{main_query} all active",
                        f"{main_query} comprehensive guide",
                        f"{main_query} official documentation"
                    ])
                elif any(term in main_query.lower() for term in ['vs', 'versus', 'compare']):
                    additional_queries.extend([
                        f"{main_query} differences",
                        f"{main_query} comparison table",
                        f"{main_query} detailed analysis"
                    ])
                else:
                    additional_queries.extend([
                        f"{main_query} complete list",
                        f"{main_query} comprehensive overview",
                        f"{main_query} detailed information",
                        f'"{main_query}" exact match'
                    ])

            # Limit additional queries to prevent excessive API calls
            additional_queries = additional_queries[:4]
            all_queries = [main_query] + additional_queries

            logging.info(f"Starting comprehensive search with {len(all_queries)} queries: {all_queries}")

            # Execute all searches concurrently for better performance
            search_tasks = []
            for query in all_queries:
                task = self.tavily_client.search(
                    query=query,
                    max_results=max_results_per_query,
                    include_images=True,
                    include_answer="advanced",
                    search_depth="advanced"
                )
                search_tasks.append(task)

            # Wait for all searches to complete
            import asyncio
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            # Aggregate and deduplicate results
            all_results = []
            all_answers = []
            seen_urls = set()
            total_results = 0

            for i, result in enumerate(search_results):
                if isinstance(result, Exception):
                    logging.warning(f"Search failed for query '{all_queries[i]}': {result}")
                    continue

                query_results = result.get('results', [])
                query_answer = result.get('answer', '')

                if query_answer and query_answer.strip():
                    all_answers.append({
                        'query': all_queries[i],
                        'answer': query_answer
                    })

                # Deduplicate results by URL
                for res in query_results:
                    url = res.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        res['source_query'] = all_queries[i]
                        all_results.append(res)
                        total_results += 1

            # Sort results by relevance (Tavily provides this inherently)
            # Keep the order from Tavily but add metadata
            comprehensive_response = {
                'query': main_query,
                'search_type': 'comprehensive_multi_query',
                'queries_executed': all_queries,
                'total_unique_results': total_results,
                'results': all_results,
                'consolidated_answers': all_answers,
                'search_metadata': {
                    'main_query': main_query,
                    'additional_queries': additional_queries,
                    'total_queries_executed': len(all_queries),
                    'max_results_per_query': max_results_per_query,
                    'total_unique_results': total_results,
                    'deduplication_applied': True,
                    'search_depth': 'advanced',
                    'comprehensive_search': True
                }
            }

            logging.info(f"Comprehensive search completed: {len(all_queries)} queries, {total_results} unique results")

            if total_results > 0 or all_answers:
                return ToolResult(
                    success=True,
                    output=json.dumps(comprehensive_response, ensure_ascii=False)
                )
            else:
                logging.warning(f"No results found in comprehensive search for: '{main_query}'")
                return ToolResult(
                    success=False,
                    output=json.dumps(comprehensive_response, ensure_ascii=False)
                )

        except Exception as e:
            error_message = str(e)
            logging.error(f"Error in comprehensive search for '{main_query}': {error_message}")
            simplified_message = f"Error performing comprehensive search: {error_message[:200]}"
            if len(error_message) > 200:
                simplified_message += "..."
            return self.fail_response(simplified_message)

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "scrape_webpage",
            "description": "Extract full text content from multiple webpages in a single operation. IMPORTANT: You should ALWAYS collect multiple relevant URLs from web-search results and scrape them all in a single call for efficiency. This tool saves time by processing multiple pages simultaneously rather than one at a time. The extracted text includes the main content of each page without HTML markup.",
            "parameters": {
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "string",
                        "description": "Multiple URLs to scrape, separated by commas. You should ALWAYS include several URLs when possible for efficiency. Example: 'https://example.com/page1,https://example.com/page2,https://example.com/page3'"
                    }
                },
                "required": ["urls"]
            }
        }
    })
    @xml_schema(
        tag_name="scrape-webpage",
        mappings=[
            {"param_name": "urls", "node_type": "attribute", "path": "."}
        ],
        example='''
        <function_calls>
        <invoke name="scrape_webpage">
        <parameter name="urls">https://www.bignoodle.ai/,https://github.com/bignoodle-ai/biggie</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def scrape_webpage(
        self,
        urls: str
    ) -> ToolResult:
        """
        Retrieve the complete text content of multiple webpages in a single efficient operation.
        
        ALWAYS collect multiple relevant URLs from search results and scrape them all at once
        rather than making separate calls for each URL. This is much more efficient.
        
        Parameters:
        - urls: Multiple URLs to scrape, separated by commas
        """
        try:
            logging.info(f"Starting to scrape webpages: {urls}")
            
            # Ensure sandbox is initialized
            await self._ensure_sandbox()
            
            # Parse the URLs parameter
            if not urls:
                logging.warning("Scrape attempt with empty URLs")
                return self.fail_response("Valid URLs are required.")
            
            # Split the URLs string into a list
            url_list = [url.strip() for url in urls.split(',') if url.strip()]
            
            if not url_list:
                logging.warning("No valid URLs found in the input")
                return self.fail_response("No valid URLs provided.")
                
            if len(url_list) == 1:
                logging.warning("Only a single URL provided - for efficiency you should scrape multiple URLs at once")
            
            logging.info(f"Processing {len(url_list)} URLs: {url_list}")
            
            # Process each URL and collect results
            results = []
            for url in url_list:
                try:
                    # Add protocol if missing
                    if not (url.startswith('http://') or url.startswith('https://')):
                        url = 'https://' + url
                        logging.info(f"Added https:// protocol to URL: {url}")
                    
                    # Scrape this URL
                    result = await self._scrape_single_url(url)
                    results.append(result)
                    
                except Exception as e:
                    logging.error(f"Error processing URL {url}: {str(e)}")
                    results.append({
                        "url": url,
                        "success": False,
                        "error": str(e)
                    })
            
            # Summarize results
            successful = sum(1 for r in results if r.get("success", False))
            failed = len(results) - successful
            
            # Create success/failure message
            if successful == len(results):
                message = f"Successfully scraped all {len(results)} URLs. Results saved to:"
                for r in results:
                    if r.get("file_path"):
                        message += f"\n- {r.get('file_path')}"
            elif successful > 0:
                message = f"Scraped {successful} URLs successfully and {failed} failed. Results saved to:"
                for r in results:
                    if r.get("success", False) and r.get("file_path"):
                        message += f"\n- {r.get('file_path')}"
                message += "\n\nFailed URLs:"
                for r in results:
                    if not r.get("success", False):
                        message += f"\n- {r.get('url')}: {r.get('error', 'Unknown error')}"
            else:
                error_details = "; ".join([f"{r.get('url')}: {r.get('error', 'Unknown error')}" for r in results])
                return self.fail_response(f"Failed to scrape all {len(results)} URLs. Errors: {error_details}")
            
            return ToolResult(
                success=True,
                output=message
            )
        
        except Exception as e:
            error_message = str(e)
            logging.error(f"Error in scrape_webpage: {error_message}")
            return self.fail_response(f"Error processing scrape request: {error_message[:200]}")
    
    async def _scrape_single_url(self, url: str) -> dict:
        """
        Helper function to scrape a single URL and return the result information.
        """
        logging.info(f"Scraping single URL: {url}")
        
        try:
            # ---------- Firecrawl scrape endpoint ----------
            logging.info(f"Sending request to Firecrawl for URL: {url}")
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.firecrawl_api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "url": url,
                    "formats": ["markdown"]
                }
                
                # Use longer timeout and retry logic for more reliability
                max_retries = 3
                timeout_seconds = 120
                retry_count = 0
                
                while retry_count < max_retries:
                    try:
                        logging.info(f"Sending request to Firecrawl (attempt {retry_count + 1}/{max_retries})")
                        response = await client.post(
                            f"{self.firecrawl_url}/v1/scrape",
                            json=payload,
                            headers=headers,
                            timeout=timeout_seconds,
                        )
                        response.raise_for_status()
                        data = response.json()
                        logging.info(f"Successfully received response from Firecrawl for {url}")
                        break
                    except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ReadError) as timeout_err:
                        retry_count += 1
                        logging.warning(f"Request timed out (attempt {retry_count}/{max_retries}): {str(timeout_err)}")
                        if retry_count >= max_retries:
                            raise Exception(f"Request timed out after {max_retries} attempts with {timeout_seconds}s timeout")
                        # Exponential backoff
                        logging.info(f"Waiting {2 ** retry_count}s before retry")
                        await asyncio.sleep(2 ** retry_count)
                    except Exception as e:
                        # Don't retry on non-timeout errors
                        logging.error(f"Error during scraping: {str(e)}")
                        raise e

            # Format the response
            title = data.get("data", {}).get("metadata", {}).get("title", "")
            markdown_content = data.get("data", {}).get("markdown", "")
            logging.info(f"Extracted content from {url}: title='{title}', content length={len(markdown_content)}")
            
            formatted_result = {
                "title": title,
                "url": url,
                "text": markdown_content
            }
            
            # Add metadata if available
            if "metadata" in data.get("data", {}):
                formatted_result["metadata"] = data["data"]["metadata"]
                logging.info(f"Added metadata: {data['data']['metadata'].keys()}")
            
            # Create a simple filename from the URL domain and date
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Extract domain from URL for the filename
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")
            
            # Clean up domain for filename
            domain = "".join([c if c.isalnum() else "_" for c in domain])
            safe_filename = f"{timestamp}_{domain}.json"
            
            logging.info(f"Generated filename: {safe_filename}")
            
            # Save results to a file in the /workspace/scrape directory
            scrape_dir = f"{self.workspace_path}/scrape"
            await self.sandbox.fs.create_folder(scrape_dir, "755")
            
            results_file_path = f"{scrape_dir}/{safe_filename}"
            json_content = json.dumps(formatted_result, ensure_ascii=False, indent=2)
            logging.info(f"Saving content to file: {results_file_path}, size: {len(json_content)} bytes")
            
            await self.sandbox.fs.upload_file(
                json_content.encode(),
                results_file_path,
            )
            
            return {
                "url": url,
                "success": True,
                "title": title,
                "file_path": results_file_path,
                "content_length": len(markdown_content)
            }
        
        except Exception as e:
            error_message = str(e)
            logging.error(f"Error scraping URL '{url}': {error_message}")
            
            # Create an error result
            return {
                "url": url,
                "success": False,
                "error": error_message
            }

if __name__ == "__main__":
    async def test_web_search():
        """Test function for the web search tool"""
        # This test function is not compatible with the sandbox version
        print("Test function needs to be updated for sandbox version")
    
    async def test_scrape_webpage():
        """Test function for the webpage scrape tool"""
        # This test function is not compatible with the sandbox version
        print("Test function needs to be updated for sandbox version")
    
    async def run_tests():
        """Run all test functions"""
        await test_web_search()
        await test_scrape_webpage()
        
    asyncio.run(run_tests())