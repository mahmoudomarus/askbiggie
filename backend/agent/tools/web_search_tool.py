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
from typing import Optional

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
        # Add Exa AI support
        self.exa_api_key = getattr(config, 'EXA_API_KEY', None)
        
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY not found in configuration")
        if not self.firecrawl_api_key:
            raise ValueError("FIRECRAWL_API_KEY not found in configuration")

        # Tavily asynchronous search client
        self.tavily_client = AsyncTavilyClient(api_key=self.tavily_api_key)
        
        # Exa AI client initialization (if available)
        self.exa_client = None
        if self.exa_api_key:
            try:
                # Import Exa if available
                from exa_py import Exa
                self.exa_client = Exa(api_key=self.exa_api_key)
                logging.info("Exa AI client initialized successfully")
            except ImportError:
                logging.warning("Exa AI library not installed, falling back to Tavily only")
            except Exception as e:
                logging.warning(f"Failed to initialize Exa AI client: {e}")
        else:
            logging.info("No Exa API key found, using Tavily only")

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for up-to-date information on a specific topic using advanced Tavily Pro API features. This tool provides enterprise-grade search with domain filtering, content type targeting, and geographic filtering for precise results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant web pages. Be specific and include key terms to improve search accuracy. For best results, use natural language questions or keyword combinations that precisely describe what you're looking for."
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "The number of search results to return. Increase for more comprehensive research or decrease for focused, high-relevance results. Range: 1-100 for production strength.",
                        "default": 50
                    },
                    "include_domains": {
                        "type": "string",
                        "description": "Comma-separated list of domains to include in search (e.g., 'reddit.com,stackoverflow.com'). Use to focus on specific trusted sources."
                    },
                    "exclude_domains": {
                        "type": "string", 
                        "description": "Comma-separated list of domains to exclude from search (e.g., 'pinterest.com,quora.com'). Use to filter out low-quality sources."
                    },
                    "search_depth": {
                        "type": "string",
                        "description": "Search depth for quality vs speed trade-off. Options: 'basic' (fastest), 'advanced' (balanced), 'comprehensive' (highest quality, slower)",
                        "default": "advanced"
                    },
                    "use_exa": {
                        "type": "boolean",
                        "description": "Use Exa AI search in addition to Tavily for enhanced academic and professional results. Recommended for research and technical queries.",
                        "default": False
                    },
                    "topic": {
                        "type": "string",
                        "description": "Content topic filter. Options: 'general', 'news', 'finance', 'technology', 'science', 'sports', 'entertainment' to prioritize relevant content types."
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back for content. Use for time-sensitive queries (e.g., 7 for last week, 30 for last month)."
                    },
                    "max_tokens": {
                        "type": "integer", 
                        "description": "Maximum tokens per search result content. Higher values give more detail but use more context. Range: 500-4000.",
                        "default": 2000
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
            {"param_name": "num_results", "node_type": "attribute", "path": "."},
            {"param_name": "include_domains", "node_type": "attribute", "path": "."},
            {"param_name": "exclude_domains", "node_type": "attribute", "path": "."},
            {"param_name": "search_depth", "node_type": "attribute", "path": "."},
            {"param_name": "use_exa", "node_type": "attribute", "path": "."},
            {"param_name": "topic", "node_type": "attribute", "path": "."},
            {"param_name": "days", "node_type": "attribute", "path": "."},
            {"param_name": "max_tokens", "node_type": "attribute", "path": "."}
        ],
        example='''
        <function_calls>
        <invoke name="web_search">
        <parameter name="query">BMX bikes for urban commuting under $350</parameter>
        <parameter name="num_results">50</parameter>
        <parameter name="include_domains">reddit.com,bikeforums.net,specialized.com</parameter>
        <parameter name="exclude_domains">pinterest.com,amazon.com</parameter>
        <parameter name="search_depth">comprehensive</parameter>
        <parameter name="use_exa">true</parameter>
        <parameter name="topic">sports</parameter>
        <parameter name="days">30</parameter>
        </invoke>
        </function_calls>
        
        <!-- Academic research example with Exa AI -->
        <function_calls>
        <invoke name="web_search">
        <parameter name="query">latest AI research transformer models 2025</parameter>
        <parameter name="num_results">50</parameter>
        <parameter name="include_domains">arxiv.org,nature.com,acm.org</parameter>
        <parameter name="topic">technology</parameter>
        <parameter name="days">7</parameter>
        <parameter name="search_depth">comprehensive</parameter>
        <parameter name="use_exa">true</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def web_search(
        self, 
        query: str,
        num_results: int = 50,
        include_domains: Optional[str] = None,
        exclude_domains: Optional[str] = None,
        search_depth: str = "advanced",
        use_exa: bool = False,
        topic: Optional[str] = None,
        days: Optional[int] = None,
        max_tokens: int = 2000
    ) -> ToolResult:
        """
        Search the web using the Tavily API with advanced Pro features for enhanced results.
        """
        try:
            # Ensure we have a valid query
            if not query or not isinstance(query, str):
                return self.fail_response("A valid search query is required.")
            
            # Normalize num_results
            if num_results is None:
                num_results = 50
            elif isinstance(num_results, int):
                num_results = max(1, min(num_results, 100))  # Increased max for production strength
            elif isinstance(num_results, str):
                try:
                    num_results = max(1, min(int(num_results), 100))  # Increased max for production strength
                except ValueError:
                    num_results = 50
            else:
                num_results = 50

            # Build search parameters with advanced features
            search_params = {
                "query": query,
                "max_results": num_results,
                "include_images": True,
                "include_answer": "advanced",
                "search_depth": search_depth,
                "max_tokens": max_tokens
            }
            
            # Add domain filtering if specified
            if include_domains:
                domain_list = [d.strip() for d in include_domains.split(',') if d.strip()]
                if domain_list:
                    search_params["include_domains"] = domain_list
            
            if exclude_domains:
                domain_list = [d.strip() for d in exclude_domains.split(',') if d.strip()]
                if domain_list:
                    search_params["exclude_domains"] = domain_list
            
            # Add topic filtering if specified
            if topic and topic != "general":
                search_params["topic"] = topic
                
            # Add date filtering if specified
            if days and days > 0:
                search_params["days"] = days

            # Execute the search with Tavily Pro features
            logging.info(f"Executing advanced web search for query: '{query}' with {num_results} results, depth: {search_depth}")
            search_response = await self.tavily_client.search(**search_params)
            
            # Enhanced search with Exa AI if requested and available
            exa_results = None
            if use_exa and self.exa_client:
                try:
                    logging.info(f"Executing additional Exa AI search for query: '{query}'")
                    exa_search_params = {
                        "query": query,
                        "num_results": min(num_results // 2, 10),  # Use half the results for Exa
                        "include_domains": include_domains.split(',') if include_domains else None,
                        "exclude_domains": exclude_domains.split(',') if exclude_domains else None,
                        "use_autoprompt": True,  # Exa's neural search enhancement
                    }
                    
                    # Remove None values from params
                    exa_search_params = {k: v for k, v in exa_search_params.items() if v is not None}
                    
                    exa_response = self.exa_client.search_and_contents(**exa_search_params)
                    exa_results = {
                        "results": [
                            {
                                "title": result.title,
                                "url": result.url,
                                "content": result.text[:max_tokens] if hasattr(result, 'text') and result.text else "",
                                "published_date": result.published_date if hasattr(result, 'published_date') else None,
                                "score": result.score if hasattr(result, 'score') else None,
                                "source": "exa"
                            }
                            for result in exa_response.results
                        ],
                        "autoprompt_string": getattr(exa_response, 'autoprompt_string', '')
                    }
                    logging.info(f"Exa AI search completed with {len(exa_results['results'])} results")
                    
                except Exception as exa_error:
                    logging.warning(f"Exa AI search failed, continuing with Tavily only: {exa_error}")
                    exa_results = None
            elif use_exa and not self.exa_client:
                logging.warning("Exa AI search requested but client not available")
            
            # Combine results if both searches were successful
            if exa_results:
                # Mark Tavily results as source
                for result in search_response.get('results', []):
                    result['source'] = 'tavily'
                    
                # Combine results, interleaving for diversity
                combined_results = []
                tavily_results = search_response.get('results', [])
                exa_result_list = exa_results['results']
                
                max_combined = max(len(tavily_results), len(exa_result_list))
                for i in range(max_combined):
                    if i < len(tavily_results):
                        combined_results.append(tavily_results[i])
                    if i < len(exa_result_list):
                        combined_results.append(exa_result_list[i])
                
                # Update the search response with combined results
                search_response['results'] = combined_results[:num_results]  # Limit to requested number
                search_response['search_metadata'] = {
                    "tavily_results": len(tavily_results),
                    "exa_results": len(exa_result_list),
                    "exa_autoprompt": exa_results.get('autoprompt_string', ''),
                    "combined_total": len(combined_results)
                }
                logging.info(f"Combined search completed: {len(tavily_results)} Tavily + {len(exa_result_list)} Exa = {len(combined_results)} total")
            
            # Check if we have actual results or an answer
            results = search_response.get('results', [])
            answer = search_response.get('answer', '')
            
            # Return the complete Tavily response 
            # This includes the query, answer, results, images and more
            logging.info(f"Retrieved search results for query: '{query}' with answer and {len(results)} results")
            
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
            logging.error(f"Error performing web search for '{query}': {error_message}")
            
            # Implement retry logic for transient failures
            if "timeout" in error_message.lower() or "connection" in error_message.lower():
                logging.info(f"Retrying search for '{query}' due to transient error")
                try:
                    # Retry with simpler parameters
                    retry_params = {
                        "query": query,
                        "max_results": min(num_results, 20),  # Reduce results for retry
                        "include_answer": "basic",
                        "search_depth": "basic"
                    }
                    retry_response = await self.tavily_client.search(**retry_params)
                    logging.info(f"Retry successful for query: '{query}'")
                    return ToolResult(
                        success=True,
                        output=json.dumps(retry_response, ensure_ascii=False)
                    )
                except Exception as retry_error:
                    logging.error(f"Retry also failed for '{query}': {str(retry_error)}")
            
            simplified_message = f"Error performing web search: {error_message[:200]}"
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