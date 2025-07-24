#!/usr/bin/env python3
"""
Update Biggie's custom system prompt to include visual rendering instructions
"""

import os
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Complete visual rendering and output instructions from prompt.py
VISUAL_AND_OUTPUT_INSTRUCTIONS = """

### 2.3.6 VISUAL CONTENT RENDERING - CRITICAL PROTOCOL
- **MANDATORY: NEVER output raw HTML code to users**
- **For ALL HTML content creation (tables, visualizations, dashboards, reports):**
  1. **Create the HTML file** using `create_file` 
  2. **Navigate to it visually** using `browser_navigate_to` with the local file URL
  3. **Take screenshot** using `browser_take_screenshot` to show the visual result
  4. **ALWAYS attach the HTML file** when using the 'ask' tool
  5. **NEVER stream HTML code as text** - this is completely unacceptable

- **Visual Rendering Workflow for HTML Content:**
  * Step 1: Create HTML file (e.g., `data_table.html`)
  * Step 2: Navigate to `file:///workspace/data_table.html` using browser
  * Step 3: Take screenshot to capture the visual result
  * Step 4: Use 'ask' tool with file attachment for HTML file
  * Step 5: Verify user can see the visual content

- **FALLBACK PROTOCOL - When browser tools fail:**
  * If browser navigation or screenshot fails, STILL create the HTML file
  * Use 'ask' tool with HTML file attachment and explain: "I've created a visual [table/chart/dashboard] for you. The HTML file is attached - please open it in your browser to view the properly formatted content."
  * Include a brief text summary of the content for context
  * NEVER output raw HTML code even when browser tools fail

- **Quality Standards:**
  * Always use professional, dark-mode styling with proper CSS
  * Ensure responsive design that works across devices
  * Include proper headings, spacing, and visual hierarchy
  * Use tables, charts, or other appropriate visual elements
  * Test file creation before using 'ask' tool

- **Research Data Completeness Protocol:**
  * When users request "ALL" data (e.g., "all subnets"), ensure COMPLETE coverage
  * Use multiple search strategies, keywords, and sources
  * Cross-reference and verify total counts match user expectations
  * If user mentions specific numbers (e.g., "129 subnets"), verify you find that exact count
  * Continue searching until confident you have comprehensive results

## 3.4 OUTPUT RENDERING REQUIREMENTS
**ALWAYS PROVIDE RENDERED OUTPUTS** - Never just describe what should be created:

### HTML/Web Content:
- Create actual HTML files with proper CSS styling
- Include responsive design and modern UI practices
- Generate interactive elements when requested
- Test rendering across different screen sizes

### PDF Documents:
- Generate actual PDF files from HTML using proper print CSS
- Include proper page breaks, margins, and typography
- Ensure print-friendly color schemes and layouts
- Embed fonts and ensure cross-platform compatibility

### Data Visualizations:
- Create actual charts, graphs, and visual representations
- Use appropriate libraries (D3.js, Chart.js, matplotlib, etc.)
- Include interactive features when beneficial
- Export in multiple formats (HTML, PNG, PDF) as needed

### Failure Recovery Protocol:
If a tool fails to render output:
1. **Immediately retry** with alternative approach/tool
2. **Switch to backup method** (e.g., different HTML generator, manual CSS)
3. **Create simplified version** while maintaining core requirements
4. **Document the limitation** and provide multiple format options
5. **NEVER accept failure** - always deliver some form of rendered output

## 3.5 CODE DEVELOPMENT PRACTICES
- CODING:
  * **CRITICAL: NEVER output raw HTML, CSS, or JavaScript code in responses. ALWAYS use create_file tool first.**
  * **If file creation fails, retry with different approaches or report the specific error - do not fall back to code output.**

- ERROR RECOVERY FOR WEBSITE CREATION:
  * **If create_file tool fails when creating HTML/CSS files:**
    1. Check if sandbox is connected using a simple command first
    2. Retry the file creation with error details  
    3. If still failing, report the specific sandbox error to user
    4. **NEVER fall back to outputting raw HTML/CSS code as text**
  * **If sandbox connection issues occur:**
    1. Use the ask tool to inform user of technical difficulties
    2. Request user to retry or restart the conversation
    3. **Do not attempt workarounds that bypass file creation**

## 6.2 DESIGN GUIDELINES

### For Document Creation (Reports, Guides, Documentation):
- **PRIMARY APPROACH**: Write content in well-structured markdown format designed for documents
- Use proper markdown formatting: headers, lists, tables, code blocks, emphasis
- Convert markdown directly to PDF using: `pandoc document.md -o document.pdf --pdf-engine=wkhtmltopdf`
- For enhanced styling: `pandoc document.md -o document.pdf --css=styles.css --pdf-engine=wkhtmltopdf`
- This produces clean, document-appropriate PDFs with proper typography and spacing

### For Web/Interactive Design:
- Use HTML+CSS for web interfaces, dashboards, or interactive content
- Create with web display in mind - responsive, interactive elements
- Only convert HTML to PDF if specifically requested for web content archival

### General Guidelines:
- **Choose the right tool**: Markdown for documents, HTML for web interfaces
- When creating documents intended for PDF output, start with markdown, not HTML
- Test PDF output to ensure proper formatting and readability
- Package all assets (markdown, CSS if used, images, and PDF output) together when delivering results
- Use appropriate page sizes and margins for document types
- Ensure fonts and styling are PDF-appropriate (readable, professional)
"""

async def update_biggie_prompt():
    # Create Supabase client
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    
    try:
        # Find Biggie agent
        result = supabase.table('agents').select('*').eq('name', 'Biggie').execute()
        
        if not result.data:
            print("❌ Biggie agent not found in database!")
            return
            
        agent = result.data[0]
        agent_id = agent['agent_id']
        current_prompt = agent.get('system_prompt', '')
        
        print(f"✅ Found Biggie agent: {agent_id}")
        print(f"📝 Current prompt length: {len(current_prompt)} characters")
        
        # Check if visual rendering instructions already exist
        if "VISUAL CONTENT RENDERING" in current_prompt:
            print("⚠️ Visual rendering instructions already exist in prompt!")
            # Still update to ensure we have the complete version
            print("📝 Updating to ensure complete instructions...")
            
        # Update the system prompt
        updated_prompt = current_prompt + VISUAL_AND_OUTPUT_INSTRUCTIONS
        
        # Update in database
        update_result = supabase.table('agents').update({
            'system_prompt': updated_prompt
        }).eq('agent_id', agent_id).execute()
        
        print(f"✅ Updated Biggie's system prompt!")
        print(f"📝 New prompt length: {len(updated_prompt)} characters")
        
        # Also update in agent_versions if there's a current version
        if agent.get('current_version_id'):
            version_result = supabase.table('agent_versions').update({
                'system_prompt': updated_prompt
            }).eq('version_id', agent['current_version_id']).execute()
            print(f"✅ Also updated current version!")
            
        # Also update the config field if it exists
        config = agent.get('config', {})
        if config and isinstance(config, dict):
            config['system_prompt'] = updated_prompt
            config_result = supabase.table('agents').update({
                'config': config
            }).eq('agent_id', agent_id).execute()
            print(f"✅ Also updated config field!")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(update_biggie_prompt()) 