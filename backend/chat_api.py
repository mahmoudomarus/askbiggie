from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
from datetime import datetime, timezone

from services.llm import make_llm_api_call
from services.billing import check_billing_status, can_use_model
from services.supabase import DBConnection
from utils.auth_utils import get_current_user_id_from_jwt
from utils.logger import logger
from utils.config import config
from utils.constants import MODEL_NAME_ALIASES

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None  # Default to config.MODEL_TO_USE
    temperature: Optional[float] = 0.1
    max_tokens: Optional[int] = None
    stream: Optional[bool] = True
    system_prompt: Optional[str] = None

class ChatResponse(BaseModel):
    message: ChatMessage
    model: str
    usage: Optional[Dict[str, Any]] = None

@router.post("/simple")
async def simple_chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id_from_jwt)
):
    """
    Simple chat endpoint for direct LLM communication.
    
    This endpoint provides a straightforward chat interface without agents, tools, or sandboxes.
    Perfect for:
    - API integrations with other UIs
    - Simple conversational AI
    - Quick prototyping
    - Direct research and question answering
    """
    try:
        # Get database client for billing checks
        db = DBConnection()
        client = await db.client
        account_id = user_id
        
        # Use model from config if not specified
        model_name = request.model or config.MODEL_TO_USE
        
        # Resolve model aliases
        resolved_model = MODEL_NAME_ALIASES.get(model_name, model_name)
        logger.info(f"Simple chat using model: {resolved_model}")
        
        # Check if user can use this model
        can_use, model_message, allowed_models = await can_use_model(client, account_id, resolved_model)
        if not can_use:
            raise HTTPException(status_code=403, detail={
                "error": "Model access denied",
                "message": model_message,
                "allowed_models": allowed_models
            })
        
        # Check billing status
        can_run, billing_message, subscription = await check_billing_status(client, account_id)
        if not can_run:
            raise HTTPException(status_code=402, detail={
                "error": "Billing limit reached",
                "message": billing_message,
                "subscription": subscription
            })
        
        # Prepare messages
        messages = []
        
        # Add system prompt if provided
        if request.system_prompt:
            messages.append({
                "role": "system",
                "content": request.system_prompt
            })
        
        # Add conversation messages
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Make LLM API call
        if request.stream:
            # Return streaming response
            async def generate_stream():
                try:
                    response = await make_llm_api_call(
                        messages=messages,
                        model_name=resolved_model,
                        temperature=request.temperature or 0.1,
                        max_tokens=request.max_tokens,
                        stream=True
                    )
                    
                    full_content = ""
                    if hasattr(response, '__aiter__'):
                        async for chunk in response:
                            if hasattr(chunk, 'choices') and len(chunk.choices) > 0:
                                delta = chunk.choices[0].delta
                                if hasattr(delta, 'content') and delta.content:
                                    full_content += delta.content
                                    yield f"data: {json.dumps({'content': delta.content, 'type': 'content'})}\n\n"
                    
                    # Send final message with complete response
                    final_response = {
                        "type": "complete",
                        "message": {
                            "role": "assistant",
                            "content": full_content
                        },
                        "model": resolved_model
                    }
                    yield f"data: {json.dumps(final_response)}\n\n"
                    
                except Exception as e:
                    logger.error(f"Streaming chat error: {str(e)}")
                    error_response = {
                        "type": "error",
                        "error": str(e)
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type",
                }
            )
        else:
            # Return non-streaming response
            response = await make_llm_api_call(
                messages=messages,
                model_name=resolved_model,
                temperature=request.temperature or 0.1,
                max_tokens=request.max_tokens,
                stream=False
            )
            
            # Extract response content
            content = ""
            usage = None
            
            try:
                if hasattr(response, 'choices') and len(response.choices) > 0:
                    content = response.choices[0].message.content
                
                if hasattr(response, 'usage'):
                    usage = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens
                    }
            except AttributeError:
                # Handle case where response structure is different
                content = str(response)
            
            return ChatResponse(
                message=ChatMessage(role="assistant", content=content),
                model=resolved_model,
                usage=usage
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Simple chat error: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": "Internal server error",
            "message": str(e)
        })

@router.get("/models")
async def get_available_models(
    user_id: str = Depends(get_current_user_id_from_jwt)
):
    """Get list of models available to the user for simple chat."""
    try:
        from services.billing import get_allowed_models_for_user
        
        db = DBConnection()
        client = await db.client
        account_id = user_id
        
        # Get allowed models for this user
        allowed_models = await get_allowed_models_for_user(client, account_id)
        
        return {
            "models": allowed_models,
            "default_model": config.MODEL_TO_USE
        }
        
    except Exception as e:
        logger.error(f"Error getting available models: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": "Failed to get available models",
            "message": str(e)
        })

@router.post("/quick")
async def quick_chat(
    prompt: str,
    model: Optional[str] = None,
    user_id: str = Depends(get_current_user_id_from_jwt)
):
    """
    Ultra-simple chat endpoint for quick questions.
    
    Just send a prompt and get a response. Perfect for:
    - Quick API calls
    - Simple integrations
    - Testing
    """
    try:
        # Create a simple chat request
        request = ChatRequest(
            messages=[ChatMessage(role="user", content=prompt)],
            model=model,
            stream=False,
            system_prompt="You are a helpful AI assistant. Provide clear, accurate, and helpful responses."
        )
        
        # Use the main chat endpoint
        return await simple_chat(request, user_id)
        
    except Exception as e:
        logger.error(f"Quick chat error: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": "Quick chat failed",
            "message": str(e)
        }) 