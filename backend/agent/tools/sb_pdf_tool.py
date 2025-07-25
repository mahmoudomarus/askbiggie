import asyncio
import os
from typing import Optional
from agentpress.tool import ToolResult, openapi_schema, xml_schema
from .sb_tools_base import SandboxToolsBase
from utils.logger import logger


class SandboxPDFTool(SandboxToolsBase):
    def __init__(self, sandbox):
        super().__init__(sandbox)

    @openapi_schema({
        "type": "function",
        "function": {
            "name": "create_pdf",
            "description": "Create a PDF document from HTML, Markdown, or text content. Supports various input formats and styling options. Perfect for generating reports, documents, and printable content from web pages or structured text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_file": {
                        "type": "string",
                        "description": "Path to the source file (HTML, Markdown, or text) to convert to PDF. Examples: 'report.html', 'document.md', 'data.txt'"
                    },
                    "output_file": {
                        "type": "string",
                        "description": "Path for the output PDF file. Example: 'report.pdf', 'document.pdf'"
                    },
                    "page_size": {
                        "type": "string",
                        "description": "PDF page size. Options: A4, Letter, Legal, A3, A5",
                        "default": "A4"
                    },
                    "orientation": {
                        "type": "string", 
                        "description": "Page orientation. Options: portrait, landscape",
                        "default": "portrait"
                    },
                    "margin_top": {
                        "type": "string",
                        "description": "Top margin (e.g., '1in', '2cm', '20mm')",
                        "default": "1in"
                    },
                    "margin_bottom": {
                        "type": "string",
                        "description": "Bottom margin (e.g., '1in', '2cm', '20mm')",
                        "default": "1in"
                    },
                    "margin_left": {
                        "type": "string",
                        "description": "Left margin (e.g., '1in', '2cm', '20mm')",
                        "default": "1in"
                    },
                    "margin_right": {
                        "type": "string",
                        "description": "Right margin (e.g., '1in', '2cm', '20mm')",
                        "default": "1in"
                    },
                    "css_file": {
                        "type": "string",
                        "description": "Optional path to CSS file for styling (for HTML/Markdown sources)"
                    },
                    "engine": {
                        "type": "string",
                        "description": "PDF generation engine. Options: wkhtmltopdf (for HTML), pandoc (for Markdown/text)",
                        "default": "auto"
                    }
                },
                "required": ["source_file", "output_file"]
            }
        }
    })
    @xml_schema(
        tag_name="create-pdf",
        mappings=[
            {"param_name": "source_file", "node_type": "attribute", "path": ".", "required": True},
            {"param_name": "output_file", "node_type": "attribute", "path": ".", "required": True},
            {"param_name": "page_size", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "orientation", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "margin_top", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "margin_bottom", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "margin_left", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "margin_right", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "css_file", "node_type": "attribute", "path": ".", "required": False},
            {"param_name": "engine", "node_type": "attribute", "path": ".", "required": False}
        ],
        example='''
        <function_calls>
        <invoke name="create_pdf">
        <parameter name="source_file">bittensor_subnets_table.html</parameter>
        <parameter name="output_file">bittensor_subnets_report.pdf</parameter>
        <parameter name="page_size">A4</parameter>
        <parameter name="orientation">portrait</parameter>
        </invoke>
        </function_calls>
        '''
    )
    async def create_pdf(
        self,
        source_file: str,
        output_file: str,
        page_size: str = "A4",
        orientation: str = "portrait",
        margin_top: str = "1in",
        margin_bottom: str = "1in", 
        margin_left: str = "1in",
        margin_right: str = "1in",
        css_file: Optional[str] = None,
        engine: str = "auto"
    ) -> ToolResult:
        """Create a PDF from HTML, Markdown, or text content."""
        
        try:
            # Validate source file exists
            source_path = os.path.join(self.workspace_path, source_file)
            if not await self._file_exists(source_path):
                return self.fail_response(f"Source file not found: {source_file}")
            
            # Determine file type and appropriate engine
            file_ext = source_file.lower().split('.')[-1]
            
            if engine == "auto":
                if file_ext == "html":
                    engine = "wkhtmltopdf"
                elif file_ext in ["md", "markdown", "txt"]:
                    engine = "pandoc"
                else:
                    engine = "wkhtmltopdf"  # Default for unknown types
            
            output_path = os.path.join(self.workspace_path, output_file)
            
            logger.info(f"Creating PDF from {source_file} to {output_file} using {engine}")
            
            if engine == "wkhtmltopdf":
                result = await self._create_pdf_wkhtmltopdf(
                    source_path, output_path, page_size, orientation,
                    margin_top, margin_bottom, margin_left, margin_right, css_file
                )
            elif engine == "pandoc":
                result = await self._create_pdf_pandoc(
                    source_path, output_path, page_size, orientation,
                    margin_top, margin_bottom, margin_left, margin_right, css_file
                )
            else:
                return self.fail_response(f"Unsupported PDF engine: {engine}")
            
            if await self._file_exists(output_path):
                file_size = await self._get_file_size(output_path)
                return self.success_response(
                    f"Successfully created PDF: {output_file} ({file_size} bytes)\n"
                    f"Engine: {engine}\n"
                    f"Page size: {page_size} ({orientation})\n"
                    f"Margins: {margin_top} top, {margin_bottom} bottom, {margin_left} left, {margin_right} right"
                )
            else:
                return self.fail_response(f"PDF generation failed. Output file not created: {output_file}")
                
        except Exception as e:
            logger.error(f"Error creating PDF: {str(e)}")
            return self.fail_response(f"PDF creation failed: {str(e)}")
    
    async def _create_pdf_wkhtmltopdf(
        self, source_path: str, output_path: str, page_size: str, orientation: str,
        margin_top: str, margin_bottom: str, margin_left: str, margin_right: str,
        css_file: Optional[str] = None
    ) -> bool:
        """Create PDF using wkhtmltopdf (best for HTML)."""
        
        cmd_parts = [
            "wkhtmltopdf",
            "--page-size", page_size,
            "--orientation", orientation,
            "--margin-top", margin_top,
            "--margin-bottom", margin_bottom,
            "--margin-left", margin_left,
            "--margin-right", margin_right,
            "--disable-smart-shrinking",
            "--print-media-type"
        ]
        
        if css_file:
            css_path = os.path.join(self.workspace_path, css_file)
            if await self._file_exists(css_path):
                cmd_parts.extend(["--user-style-sheet", css_path])
        
        cmd_parts.extend([source_path, output_path])
        
        result = await self._execute_command(" ".join(cmd_parts))
        return result.get("exit_code", 1) == 0
    
    async def _create_pdf_pandoc(
        self, source_path: str, output_path: str, page_size: str, orientation: str,
        margin_top: str, margin_bottom: str, margin_left: str, margin_right: str,
        css_file: Optional[str] = None
    ) -> bool:
        """Create PDF using pandoc (best for Markdown/text)."""
        
        cmd_parts = [
            "pandoc",
            source_path,
            "-o", output_path,
            "--pdf-engine=wkhtmltopdf",
            f"--variable=geometry:paper={page_size.lower()}",
            f"--variable=geometry:margin={margin_top}"
        ]
        
        if css_file:
            css_path = os.path.join(self.workspace_path, css_file)
            if await self._file_exists(css_path):
                cmd_parts.extend(["--css", css_path])
        
        result = await self._execute_command(" ".join(cmd_parts))
        return result.get("exit_code", 1) == 0
    
    async def _file_exists(self, file_path: str) -> bool:
        """Check if file exists."""
        try:
            files = await self.sandbox.fs.list_files(os.path.dirname(file_path))
            filename = os.path.basename(file_path)
            return any(f.name == filename for f in files)
        except:
            return False
    
    async def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes."""
        try:
            files = await self.sandbox.fs.list_files(os.path.dirname(file_path))
            filename = os.path.basename(file_path)
            for f in files:
                if f.name == filename:
                    return f.size
            return 0
        except:
            return 0
    
    async def _execute_command(self, command: str) -> dict:
        """Execute a shell command."""
        try:
            from daytona_sdk import SessionExecuteRequest
            
            # Create or get session
            session_id = await self._ensure_session("pdf_generation")
            
            req = SessionExecuteRequest(
                command=command,
                var_async=False,
                cwd=self.workspace_path
            )
            
            response = await self.sandbox.process.execute_session_command(
                session_id=session_id,
                req=req,
                timeout=60
            )
            
            return {
                "exit_code": response.exit_code,
                "output": response.output if hasattr(response, 'output') else ""
            }
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {"exit_code": 1, "output": str(e)}
    
    async def _ensure_session(self, session_name: str) -> str:
        """Ensure a tmux session exists."""
        try:
            sessions = await self.sandbox.process.get_sessions()
            session_id = None
            
            for session in sessions:
                if session.name == session_name:
                    session_id = session.session_id
                    break
            
            if not session_id:
                from daytona_sdk import CreateSessionRequest
                req = CreateSessionRequest(name=session_name)
                session = await self.sandbox.process.create_session(req)
                session_id = session.session_id
            
            return session_id
            
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            raise 