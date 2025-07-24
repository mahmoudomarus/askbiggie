import os
import urllib.parse
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, APIRouter, Form, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel
from daytona_sdk import AsyncSandbox

from sandbox.sandbox import get_or_start_sandbox, delete_sandbox
from utils.logger import logger
from utils.auth_utils import get_optional_user_id
from services.supabase import DBConnection

# Initialize shared resources
router = APIRouter(tags=["sandbox"])
db = None

def initialize(_db: DBConnection):
    """Initialize the sandbox API with resources from the main API."""
    global db
    db = _db
    logger.info("Initialized sandbox API with database connection")

class FileInfo(BaseModel):
    """Model for file information"""
    name: str
    path: str
    is_dir: bool
    size: int
    mod_time: str
    permissions: Optional[str] = None

def normalize_path(path: str) -> str:
    """
    Normalize a path to ensure proper UTF-8 encoding and handling.
    
    Args:
        path: The file path, potentially containing URL-encoded characters
        
    Returns:
        Normalized path with proper UTF-8 encoding
    """
    try:
        # First, ensure the path is properly URL-decoded
        decoded_path = urllib.parse.unquote(path)
        
        # Handle Unicode escape sequences like \u0308
        try:
            # Replace Python-style Unicode escapes (\u0308) with actual characters
            # This handles cases where the Unicode escape sequence is part of the URL
            import re
            unicode_pattern = re.compile(r'\\u([0-9a-fA-F]{4})')
            
            def replace_unicode(match):
                hex_val = match.group(1)
                return chr(int(hex_val, 16))
            
            decoded_path = unicode_pattern.sub(replace_unicode, decoded_path)
        except Exception as unicode_err:
            logger.warning(f"Error processing Unicode escapes in path '{path}': {str(unicode_err)}")
        
        logger.debug(f"Normalized path from '{path}' to '{decoded_path}'")
        return decoded_path
    except Exception as e:
        logger.error(f"Error normalizing path '{path}': {str(e)}")
        return path  # Return original path if decoding fails

async def verify_sandbox_access(client, sandbox_id: str, user_id: Optional[str] = None):
    """
    Verify that a user has access to a specific sandbox based on account membership.
    
    Args:
        client: The Supabase client
        sandbox_id: The sandbox ID to check access for
        user_id: The user ID to check permissions for. Can be None for public resource access.
        
    Returns:
        dict: Project data containing sandbox information
        
    Raises:
        HTTPException: If the user doesn't have access to the sandbox or sandbox doesn't exist
    """
    # Find the project that owns this sandbox
    project_result = await client.table('projects').select('*').filter('sandbox->>id', 'eq', sandbox_id).execute()
    
    if not project_result.data or len(project_result.data) == 0:
        raise HTTPException(status_code=404, detail="Sandbox not found")
    
    project_data = project_result.data[0]

    if project_data.get('is_public'):
        return project_data
    
    # For private projects, we must have a user_id
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required for this resource")
    
    account_id = project_data.get('account_id')
    
    # Verify account membership
    if account_id:
        account_user_result = await client.schema('basejump').from_('account_user').select('account_role').eq('user_id', user_id).eq('account_id', account_id).execute()
        if account_user_result.data and len(account_user_result.data) > 0:
            return project_data
    
    raise HTTPException(status_code=403, detail="Not authorized to access this sandbox")

async def get_sandbox_by_id_safely(client, sandbox_id: str) -> AsyncSandbox:
    """
    Safely retrieve a sandbox object by its ID, using the project that owns it.
    Automatically starts the sandbox if it's stopped or archived.
    
    Args:
        client: The Supabase client
        sandbox_id: The sandbox ID to retrieve
    
    Returns:
        AsyncSandbox: The sandbox object
        
    Raises:
        HTTPException: If the sandbox doesn't exist or can't be retrieved
    """
    # Find the project that owns this sandbox
    project_result = await client.table('projects').select('project_id').filter('sandbox->>id', 'eq', sandbox_id).execute()
    
    if not project_result.data or len(project_result.data) == 0:
        logger.error(f"No project found for sandbox ID: {sandbox_id}")
        raise HTTPException(status_code=404, detail="Sandbox not found - no project owns this sandbox ID")
    
    # project_id = project_result.data[0]['project_id']
    # logger.debug(f"Found project {project_id} for sandbox {sandbox_id}")
    
    try:
        # Get or start the sandbox (this function already handles starting if needed)
        sandbox = await get_or_start_sandbox(sandbox_id)
        # Extract just the sandbox object from the tuple (sandbox, sandbox_id, sandbox_pass)
        # sandbox = sandbox_tuple[0]
        
        logger.info(f"Successfully retrieved/started sandbox {sandbox_id}")
        return sandbox
    except Exception as e:
        logger.error(f"Error retrieving sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sandbox: {str(e)}")

@router.post("/sandboxes/{sandbox_id}/files")
async def create_file(
    sandbox_id: str, 
    path: str = Form(...),
    file: UploadFile = File(...),
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Create a file in the sandbox using direct file upload"""
    # Normalize the path to handle UTF-8 encoding correctly
    path = normalize_path(path)
    
    logger.info(f"Received file upload request for sandbox {sandbox_id}, path: {path}, user_id: {user_id}")
    client = await db.client
    
    # Verify the user has access to this sandbox
    await verify_sandbox_access(client, sandbox_id, user_id)
    
    try:
        # Get sandbox using the safer method
        sandbox = await get_sandbox_by_id_safely(client, sandbox_id)
        
        # Read file content directly from the uploaded file
        content = await file.read()
        
        # Create file using raw binary content
        await sandbox.fs.upload_file(content, path)
        logger.info(f"File created at {path} in sandbox {sandbox_id}")
        
        return {"status": "success", "created": True, "path": path}
    except Exception as e:
        logger.error(f"Error creating file in sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sandboxes/{sandbox_id}/files")
async def list_files(
    sandbox_id: str, 
    path: str,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """List files and directories at the specified path"""
    # Normalize the path to handle UTF-8 encoding correctly
    path = normalize_path(path)
    
    logger.info(f"Received list files request for sandbox {sandbox_id}, path: {path}, user_id: {user_id}")
    client = await db.client
    
    # Verify the user has access to this sandbox
    await verify_sandbox_access(client, sandbox_id, user_id)
    
    try:
        # Get sandbox using the safer method
        sandbox = await get_sandbox_by_id_safely(client, sandbox_id)
        
        # List files
        files = await sandbox.fs.list_files(path)
        result = []
        
        for file in files:
            # Convert file information to our model
            # Ensure forward slashes are used for paths, regardless of OS
            full_path = f"{path.rstrip('/')}/{file.name}" if path != '/' else f"/{file.name}"
            file_info = FileInfo(
                name=file.name,
                path=full_path, # Use the constructed path
                is_dir=file.is_dir,
                size=file.size,
                mod_time=str(file.mod_time),
                permissions=getattr(file, 'permissions', None)
            )
            result.append(file_info)
        
        logger.info(f"Successfully listed {len(result)} files in sandbox {sandbox_id}")
        return {"files": [file.dict() for file in result]}
    except Exception as e:
        logger.error(f"Error listing files in sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sandboxes/{sandbox_id}/files/content")
async def read_file(
    sandbox_id: str, 
    path: str,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Read a file from the sandbox"""
    # Normalize the path to handle UTF-8 encoding correctly
    original_path = path
    path = normalize_path(path)
    
    logger.info(f"Received file read request for sandbox {sandbox_id}, path: {path}, user_id: {user_id}")
    if original_path != path:
        logger.info(f"Normalized path from '{original_path}' to '{path}'")
    
    client = await db.client
    
    # Verify the user has access to this sandbox
    await verify_sandbox_access(client, sandbox_id, user_id)
    
    try:
        # Get sandbox using the safer method
        sandbox = await get_sandbox_by_id_safely(client, sandbox_id)
        
        # Read file directly - don't check existence first with a separate call
        try:
            content = await sandbox.fs.download_file(path)
        except Exception as download_err:
            error_msg = str(download_err)
            logger.error(f"Error downloading file {path} from sandbox {sandbox_id}: {error_msg}")
            
            # Check if this is a sandbox state issue
            if "not running" in error_msg.lower() or "stopped" in error_msg.lower() or "archived" in error_msg.lower():
                raise HTTPException(
                    status_code=503, 
                    detail=f"Sandbox is not running. The sandbox may have been stopped due to inactivity or storage limits. Please restart your conversation to create a new sandbox."
                )
            elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                raise HTTPException(
                    status_code=404, 
                    detail=f"File not found: {path}"
                )
            else:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to download file: {error_msg}"
                )
        
        # Return a Response object with the content directly
        filename = os.path.basename(path)
        logger.info(f"Successfully read file {filename} from sandbox {sandbox_id}")
        
        # Ensure proper encoding by explicitly using UTF-8 for the filename in Content-Disposition header
        # This applies RFC 5987 encoding for the filename to support non-ASCII characters
        encoded_filename = filename.encode('utf-8').decode('latin-1')
        content_disposition = f"attachment; filename*=UTF-8''{encoded_filename}"
        
        return Response(
            content=content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": content_disposition}
        )
    except HTTPException:
        # Re-raise HTTP exceptions without wrapping
        raise
    except Exception as e:
        logger.error(f"Error reading file in sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sandboxes/{sandbox_id}/files")
async def delete_file(
    sandbox_id: str, 
    path: str,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Delete a file from the sandbox"""
    # Normalize the path to handle UTF-8 encoding correctly
    path = normalize_path(path)
    
    logger.info(f"Received file delete request for sandbox {sandbox_id}, path: {path}, user_id: {user_id}")
    client = await db.client
    
    # Verify the user has access to this sandbox
    await verify_sandbox_access(client, sandbox_id, user_id)
    
    try:
        # Get sandbox using the safer method
        sandbox = await get_sandbox_by_id_safely(client, sandbox_id)
        
        # Delete file
        await sandbox.fs.delete_file(path)
        logger.info(f"File deleted at {path} in sandbox {sandbox_id}")
        
        return {"status": "success", "deleted": True, "path": path}
    except Exception as e:
        logger.error(f"Error deleting file in sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sandboxes/{sandbox_id}")
async def delete_sandbox_route(
    sandbox_id: str,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """Delete an entire sandbox"""
    logger.info(f"Received sandbox delete request for sandbox {sandbox_id}, user_id: {user_id}")
    client = await db.client
    
    # Verify the user has access to this sandbox
    await verify_sandbox_access(client, sandbox_id, user_id)
    
    try:
        # Delete the sandbox using the sandbox module function
        await delete_sandbox(sandbox_id)
        
        return {"status": "success", "deleted": True, "sandbox_id": sandbox_id}
    except Exception as e:
        logger.error(f"Error deleting sandbox {sandbox_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Should happen on server-side fully
@router.post("/project/{project_id}/sandbox/ensure-active")
async def ensure_project_sandbox_active(
    project_id: str,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """
    Ensure that a project's sandbox is active and running.
    Checks the sandbox status and starts it if it's not running.
    """
    logger.info(f"Received ensure sandbox active request for project {project_id}, user_id: {user_id}")
    client = await db.client
    
    # Find the project and sandbox information
    project_result = await client.table('projects').select('*').eq('project_id', project_id).execute()
    
    if not project_result.data or len(project_result.data) == 0:
        logger.error(f"Project not found: {project_id}")
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_data = project_result.data[0]
    
    # For public projects, no authentication is needed
    if not project_data.get('is_public'):
        # For private projects, we must have a user_id
        if not user_id:
            logger.error(f"Authentication required for private project {project_id}")
            raise HTTPException(status_code=401, detail="Authentication required for this resource")
            
        account_id = project_data.get('account_id')
        
        # Verify account membership
        if account_id:
            account_user_result = await client.schema('basejump').from_('account_user').select('account_role').eq('user_id', user_id).eq('account_id', account_id).execute()
            if not (account_user_result.data and len(account_user_result.data) > 0):
                logger.error(f"User {user_id} not authorized to access project {project_id}")
                raise HTTPException(status_code=403, detail="Not authorized to access this project")
    
    try:
        # Get sandbox ID from project data
        sandbox_info = project_data.get('sandbox', {})
        if not sandbox_info.get('id'):
            raise HTTPException(status_code=404, detail="No sandbox found for this project")
            
        sandbox_id = sandbox_info['id']
        
        # Get or start the sandbox
        logger.info(f"Ensuring sandbox is active for project {project_id}")
        sandbox = await get_or_start_sandbox(sandbox_id)
        
        logger.info(f"Successfully ensured sandbox {sandbox_id} is active for project {project_id}")
        
        return {
            "status": "success", 
            "sandbox_id": sandbox_id,
            "message": "Sandbox is active"
        }
    except Exception as e:
        logger.error(f"Error ensuring sandbox is active for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sandboxes/{sandbox_id}/health")
async def check_sandbox_health(
    sandbox_id: str,
    request: Request = None,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """
    Check the health and status of a sandbox.
    Returns information about sandbox state, storage usage, and availability.
    """
    logger.info(f"Checking health for sandbox {sandbox_id}, user_id: {user_id}")
    client = await db.client
    
    # Verify the user has access to this sandbox
    await verify_sandbox_access(client, sandbox_id, user_id)
    
    try:
        # Import necessary modules
        from daytona_sdk import SandboxState
        from sandbox.sandbox import daytona
        
        # Try to get sandbox status
        sandbox_status = {
            "sandbox_id": sandbox_id,
            "status": "unknown",
            "is_running": False,
            "message": ""
        }
        
        try:
            # Get sandbox directly from Daytona
            sandbox = await daytona.get(sandbox_id)
            
            # Check sandbox state
            if hasattr(sandbox, 'state'):
                state = sandbox.state
                sandbox_status["status"] = str(state)
                sandbox_status["is_running"] = state not in [SandboxState.ARCHIVED, SandboxState.STOPPED]
                
                if state == SandboxState.RUNNING:
                    sandbox_status["message"] = "Sandbox is running and accessible"
                elif state == SandboxState.ARCHIVED:
                    sandbox_status["message"] = "Sandbox is archived. It needs to be restarted to access files."
                elif state == SandboxState.STOPPED:
                    sandbox_status["message"] = "Sandbox is stopped. It needs to be restarted to access files."
                else:
                    sandbox_status["message"] = f"Sandbox is in {state} state"
            
            # Try to get storage info if available
            if hasattr(sandbox, 'storage_used'):
                sandbox_status["storage_used_mb"] = getattr(sandbox, 'storage_used', 0) / (1024 * 1024)
            if hasattr(sandbox, 'storage_limit'):
                sandbox_status["storage_limit_mb"] = getattr(sandbox, 'storage_limit', 0) / (1024 * 1024)
                
        except Exception as status_error:
            logger.error(f"Error getting sandbox status: {str(status_error)}")
            sandbox_status["error"] = str(status_error)
            sandbox_status["message"] = "Could not retrieve sandbox status"
        
        return sandbox_status
        
    except Exception as e:
        logger.error(f"Error checking sandbox health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
