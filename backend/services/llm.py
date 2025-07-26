"""
LLM API interface for making calls to various language models.

This module provides a unified interface for making API calls to different LLM providers
(OpenAI, Anthropic, Groq, xAI, etc.) using LiteLLM. It includes support for:
- Streaming responses
- Tool calls and function calling
- Retry logic with exponential backoff
- Model-specific configurations
- Comprehensive error handling and logging
"""

from typing import Union, Dict, Any, Optional, AsyncGenerator, List
import os
import json
import asyncio
from openai import OpenAIError
import litellm
from litellm.files.main import ModelResponse
from utils.logger import logger
from utils.config import config

# litellm.set_verbose=True
litellm.modify_params=True

# Constants
MAX_RETRIES = 2
RATE_LIMIT_DELAY = 30
RETRY_DELAY = 0.1

class LLMError(Exception):
    """Base exception for LLM service errors."""
    pass

class LLMRetryError(LLMError):
    """Exception raised when LLM retries are exhausted."""
    pass

class LLMContextOverflowError(LLMError):
    """Exception raised when context overflow is detected."""
    pass

def setup_api_keys() -> None:
    """Set up API keys from environment variables."""
    providers = ['OPENAI', 'ANTHROPIC', 'GROQ', 'OPENROUTER', 'XAI']
    for provider in providers:
        key = getattr(config, f'{provider}_API_KEY')
        if key:
            logger.debug(f"API key set for provider: {provider}")
        else:
            logger.warning(f"No API key found for provider: {provider}")

    # Set up OpenRouter API base if not already set
    if config.OPENROUTER_API_KEY and config.OPENROUTER_API_BASE:
        os.environ['OPENROUTER_API_BASE'] = config.OPENROUTER_API_BASE
        logger.debug(f"Set OPENROUTER_API_BASE to {config.OPENROUTER_API_BASE}")

    # Set up AWS Bedrock credentials
    aws_access_key = config.AWS_ACCESS_KEY_ID
    aws_secret_key = config.AWS_SECRET_ACCESS_KEY
    aws_region = config.AWS_REGION_NAME

    if aws_access_key and aws_secret_key and aws_region:
        logger.debug(f"AWS credentials set for Bedrock in region: {aws_region}")
        # Configure LiteLLM to use AWS credentials
        os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key
        os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_key
        os.environ['AWS_REGION_NAME'] = aws_region
    else:
        logger.warning(f"Missing AWS credentials for Bedrock integration - access_key: {bool(aws_access_key)}, secret_key: {bool(aws_secret_key)}, region: {aws_region}")

def get_openrouter_fallback(model_name: str) -> Optional[str]:
    """Get OpenRouter fallback model for a given model name."""
    # Skip if already using OpenRouter
    if model_name.startswith("openrouter/"):
        return None
    
    # Model fallback mapping - prioritize specific OpenRouter routes
    fallback_mapping = {
        # Main model routing - prioritize OpenRouter for better availability
        "claude-sonnet-4": "openrouter/anthropic/claude-sonnet-4",
        "anthropic/claude-sonnet-4-20250514": "openrouter/anthropic/claude-sonnet-4", 
        "anthropic/claude-sonnet-4": "openrouter/anthropic/claude-sonnet-4",
        "claude-3.5-sonnet": "openrouter/anthropic/claude-3.5-sonnet",
        "anthropic/claude-3.5-sonnet": "openrouter/anthropic/claude-3.5-sonnet",
        
        # Kimi K2 routing
        "kimi-k2": "openrouter/moonshotai/kimi-k2",
        "moonshotai/kimi-k2": "openrouter/moonshotai/kimi-k2",
        "qwen3": "openrouter/qwen/qwen3-235b-a22b",
        "qwen3-32b": "openrouter/qwen/qwen3-32b",
        "qwen3-30b": "openrouter/qwen/qwen3-30b-a3b",
        "qwen3-30b-free": "openrouter/qwen/qwen3-30b-a3b:free",
        "qwen/qwen3-32b": "openrouter/qwen/qwen3-32b",
        "qwen/qwen3-30b-a3b": "openrouter/qwen/qwen3-30b-a3b",
        "qwen/qwen3-30b-a3b:free": "openrouter/qwen/qwen3-30b-a3b:free",
        "qwen/qwen3-235b-a22b": "openrouter/qwen/qwen3-235b-a22b",
    }

    # Apply fallback mapping first
    if model_name in fallback_mapping:
        logger.info(f"Mapping model {model_name} to {fallback_mapping[model_name]}")
        return fallback_mapping[model_name]
    
    # Check for partial matches (e.g., bedrock models)
    for key, value in fallback_mapping.items():
        if key in model_name:
            return value
    
    # Default fallbacks by provider
    if "claude" in model_name.lower() or "anthropic" in model_name.lower():
        return "openrouter/anthropic/claude-sonnet-4"
    elif "xai" in model_name.lower() or "grok" in model_name.lower():
        return "openrouter/x-ai/grok-4"
    elif "kimi" in model_name.lower() or "moonshot" in model_name.lower():
        return "openrouter/moonshotai/kimi-k2"
    elif "qwen" in model_name.lower():
        return "openrouter/qwen/qwen3-32b"
    
    return None

async def handle_error(error: Exception, attempt: int, max_attempts: int) -> None:
    """Handle API errors with appropriate delays and logging."""
    delay = RATE_LIMIT_DELAY if isinstance(error, litellm.exceptions.RateLimitError) else RETRY_DELAY
    logger.warning(f"Error on attempt {attempt + 1}/{max_attempts}: {str(error)}")
    logger.debug(f"Waiting {delay} seconds before retry...")
    await asyncio.sleep(delay)

def prepare_params(
    messages: List[Dict[str, Any]],
    model_name: str,
    temperature: float = 0,
    max_tokens: Optional[int] = None,
    response_format: Optional[Any] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    stream: bool = False,
    top_p: Optional[float] = None,
    model_id: Optional[str] = None,
    enable_thinking: Optional[bool] = False,
    reasoning_effort: Optional[str] = 'low'
) -> Dict[str, Any]:
    """Prepare parameters for the API call."""
    params = {
        "model": model_name,
        "messages": messages,
        "temperature": temperature,
        "response_format": response_format,
        "top_p": top_p,
        "stream": stream,
    }

    if api_key:
        params["api_key"] = api_key
    if api_base:
        params["api_base"] = api_base
    if model_id:
        params["model_id"] = model_id

    # Handle token limits
    if max_tokens is not None:
        # For Claude 3.7 in Bedrock, do not set max_tokens or max_tokens_to_sample
        # as it causes errors with inference profiles
        if model_name.startswith("bedrock/") and "claude-3-7" in model_name:
            logger.debug(f"Skipping max_tokens for Claude 3.7 model: {model_name}")
            # Do not add any max_tokens parameter for Claude 3.7
        else:
            param_name = "max_completion_tokens" if 'o1' in model_name else "max_tokens"
            params[param_name] = max_tokens

    # Add tools if provided
    if tools:
        params.update({
            "tools": tools,
            "tool_choice": tool_choice
        })
        logger.debug(f"Added {len(tools)} tools to API parameters")

    # # Add Claude-specific headers
    if "claude" in model_name.lower() or "anthropic" in model_name.lower():
        params["extra_headers"] = {
            # "anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"
            "anthropic-beta": "output-128k-2025-02-19"
        }
        params["fallbacks"] = [{
            "model": "openrouter/anthropic/claude-sonnet-4",
            "messages": messages,
        }]
        # params["mock_testing_fallback"] = True
        logger.debug("Added Claude-specific headers")

    # Add OpenRouter-specific parameters
    if model_name.startswith("openrouter/"):
        logger.debug(f"Preparing OpenRouter parameters for model: {model_name}")

        # Add optional site URL and app name from config
        site_url = config.OR_SITE_URL
        app_name = config.OR_APP_NAME
        if site_url or app_name:
            extra_headers = params.get("extra_headers", {})
            if site_url:
                extra_headers["HTTP-Referer"] = site_url
            if app_name:
                extra_headers["X-Title"] = app_name
            params["extra_headers"] = extra_headers
            logger.debug(f"Added OpenRouter site URL and app name to headers")

    # Add Bedrock-specific parameters
    if model_name.startswith("bedrock/"):
        logger.debug(f"Preparing AWS Bedrock parameters for model: {model_name}")

        if not model_id and "anthropic.claude-3-7-sonnet" in model_name:
            params["model_id"] = "arn:aws:bedrock:us-west-2:935064898258:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0"
            logger.debug(f"Auto-set model_id for Claude 3.7 Sonnet: {params['model_id']}")

    # Apply Anthropic prompt caching (minimal implementation)
    # Check model name *after* potential modifications (like adding bedrock/ prefix)
    effective_model_name = params.get("model", model_name) # Use model from params if set, else original
    if "claude" in effective_model_name.lower() or "anthropic" in effective_model_name.lower():
        messages = params["messages"] # Direct reference, modification affects params

        # Ensure messages is a list
        if not isinstance(messages, list):
            return params # Return early if messages format is unexpected

        # Apply cache control to the first 4 text blocks across all messages
        cache_control_count = 0
        max_cache_control_blocks = 4

        for message in messages:
            if cache_control_count >= max_cache_control_blocks:
                break
                
            content = message.get("content")
            
            if isinstance(content, str):
                message["content"] = [
                    {"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}
                ]
                cache_control_count += 1
            elif isinstance(content, list):
                for item in content:
                    if cache_control_count >= max_cache_control_blocks:
                        break
                    if isinstance(item, dict) and item.get("type") == "text" and "cache_control" not in item:
                        item["cache_control"] = {"type": "ephemeral"}
                        cache_control_count += 1

    # Add reasoning_effort for Anthropic models if enabled
    use_thinking = enable_thinking if enable_thinking is not None else False
    is_anthropic = "anthropic" in effective_model_name.lower() or "claude" in effective_model_name.lower()
    is_xai = "xai" in effective_model_name.lower() or model_name.startswith("xai/")

    if is_anthropic and use_thinking:
        effort_level = reasoning_effort if reasoning_effort else 'low'
        params["reasoning_effort"] = effort_level
        params["temperature"] = 1.0 # Required by Anthropic when reasoning_effort is used
        logger.info(f"Anthropic thinking enabled with reasoning_effort='{effort_level}'")

    # Add reasoning_effort for xAI models if enabled
    if is_xai and use_thinking:
        effort_level = reasoning_effort if reasoning_effort else 'low'
        params["reasoning_effort"] = effort_level
        logger.info(f"xAI thinking enabled with reasoning_effort='{effort_level}'")

    # Add xAI-specific parameters
    if model_name.startswith("xai/"):
        logger.debug(f"Preparing xAI parameters for model: {model_name}")
        # xAI models support standard parameters, no special handling needed beyond reasoning_effort

    return params

async def make_llm_api_call(
    messages: List[Dict[str, Any]],
    model_name: str,
    response_format: Optional[Any] = None,
    temperature: float = 0,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    stream: bool = False,
    top_p: Optional[float] = None,
    model_id: Optional[str] = None,
    enable_thinking: Optional[bool] = False,
    reasoning_effort: Optional[str] = 'low'
) -> Union[Dict[str, Any], AsyncGenerator, ModelResponse]:
    """
    Make an API call to a language model using LiteLLM.
    
    Args:
        messages: List of message dictionaries for the conversation
        model_name: Name of the model to use (e.g., "gpt-4", "claude-3", "openrouter/openai/gpt-4", "bedrock/anthropic.claude-3-sonnet-20240229-v1:0")
        response_format: Desired format for the response
        temperature: Sampling temperature (0-1)
        max_tokens: Maximum tokens in the response
        tools: List of tool definitions for function calling
        tool_choice: How to select tools ("auto" or "none")
        api_key: Override default API key
        api_base: Override default API base URL
        stream: Whether to stream the response
        top_p: Top-p sampling parameter
        model_id: Optional ARN for Bedrock inference profiles
        enable_thinking: Whether to enable thinking
        reasoning_effort: Level of reasoning effort
        
    Returns:
        Union[Dict[str, Any], AsyncGenerator]: API response or stream
        
    Raises:
        LLMRetryError: If API call fails after retries
        LLMError: For other API-related errors
    """
    logger.info(f"Making LLM API call to model: {model_name} (Thinking: {enable_thinking}, Effort: {reasoning_effort})")
    logger.info(f"📡 API Call: Using model {model_name}")
    
    # Special handling for Claude Sonnet 4 - implement OpenRouter-first fallback chain
    if "claude-sonnet-4" in model_name.lower() or model_name == "anthropic/claude-sonnet-4-20250514":
        logger.info(f"🎯 Using Claude Sonnet 4 fallback chain (OpenRouter → Groq → Anthropic)")
        
        for i, fallback_model in enumerate(CLAUDE_SONNET_4_FALLBACKS):
            try:
                logger.info(f"🔄 Attempting Claude Sonnet 4 fallback {i+1}/{len(CLAUDE_SONNET_4_FALLBACKS)}: {fallback_model}")
                
                fallback_params = prepare_params(
                    messages=messages,
                    model_name=fallback_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    tools=tools,
                    tool_choice=tool_choice,
                    api_key=api_key,
                    api_base=api_base,
                    stream=stream,
                    top_p=top_p,
                    model_id=None,  # Clear model_id for non-Bedrock models
                    enable_thinking=enable_thinking,
                    reasoning_effort=reasoning_effort
                )
                
                response = await litellm.acompletion(**fallback_params)
                logger.info(f"✅ Successfully connected via Claude Sonnet 4 fallback: {fallback_model}")
                return response
                
            except Exception as fallback_error:
                logger.warning(f"❌ Claude Sonnet 4 fallback {fallback_model} failed: {fallback_error}")
                if i == len(CLAUDE_SONNET_4_FALLBACKS) - 1:
                    logger.error(f"🚫 All Claude Sonnet 4 fallbacks exhausted")
                    raise LLMError(f"All Claude Sonnet 4 fallbacks failed. Last error: {fallback_error}")
                continue
    
    params = prepare_params(
        messages=messages,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
        tools=tools,
        tool_choice=tool_choice,
        api_key=api_key,
        api_base=api_base,
        stream=stream,
        top_p=top_p,
        model_id=model_id,
        enable_thinking=enable_thinking,
        reasoning_effort=reasoning_effort
    )
    
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Attempt {attempt + 1}/{MAX_RETRIES}")
            response = await litellm.acompletion(**params)
            logger.debug(f"Successfully received API response from {model_name}")
            return response
            
        except litellm.exceptions.BadRequestError as e:
            error_str = str(e).lower()
            # Check for context overflow/token limit errors
            context_overflow_indicators = [
                "context window",
                "token limit",
                "maximum context length",
                "too many tokens",
                "context_length_exceeded",
                "prompt is too long",
                "context too large",
                "input too long",
                "maximum tokens",
                "context window exceeded"
            ]
            
            if any(indicator in error_str for indicator in context_overflow_indicators):
                logger.warning(f"🔍 Context overflow detected for {model_name}: {str(e)}")
                raise LLMContextOverflowError(f"Context overflow in {model_name}: {str(e)}")
            else:
                # Other bad request errors
                last_error = e
                await handle_error(e, attempt, MAX_RETRIES)

        except litellm.exceptions.InternalServerError as e:
            # Check if it's an Anthropic overloaded error
            if "Overloaded" in str(e) and "AnthropicException" in str(e):
                logger.warning(f"🚨 Anthropic model {model_name} is overloaded, trying fallbacks...")
                
                # Try fallback models in order
                for fallback_model in ANTHROPIC_FALLBACKS:
                    try:
                        logger.info(f"🔄 Trying fallback model: {fallback_model}")
                        fallback_params = params.copy()
                        fallback_params["model"] = fallback_model
                        fallback_params.pop("model_id", None)  # Remove Bedrock-specific param
                        response = await litellm.acompletion(**fallback_params)
                        logger.info(f"✅ Successfully switched to fallback model: {fallback_model}")
                        return response
                        
                    except Exception as fallback_error:
                        logger.warning(f"❌ Fallback model {fallback_model} also failed: {fallback_error}")
                        continue
                
                # If all fallbacks failed, continue with retry logic
                logger.error(f"🚫 All fallback models failed for overloaded Anthropic model")
                last_error = e
                await handle_error(e, attempt, MAX_RETRIES)
            else:
                # Other internal server errors
                last_error = e
                await handle_error(e, attempt, MAX_RETRIES)

        except (litellm.exceptions.RateLimitError, OpenAIError, json.JSONDecodeError) as e:
            last_error = e
            await handle_error(e, attempt, MAX_RETRIES)

        except Exception as e:
            logger.error(f"Unexpected error during API call: {str(e)}", exc_info=True)
            raise LLMError(f"API call failed: {str(e)}")

    error_msg = f"Failed to make API call after {MAX_RETRIES} attempts"
    if last_error:
        error_msg += f". Last error: {str(last_error)}"
    logger.error(error_msg, exc_info=True)
    raise LLMRetryError(error_msg)

# Initialize API keys on module import
setup_api_keys()

# Multi-tier fallback hierarchy for different scenarios - MODULE LEVEL
CLAUDE_SONNET_4_FALLBACKS = [
    "openrouter/anthropic/claude-sonnet-4",      # OpenRouter first
    "groq/claude-sonnet-4",                      # Groq if available  
    "anthropic/claude-sonnet-4-20250514",       # Direct Anthropic last
    "openrouter/anthropic/claude-3.5-sonnet",   # 3.5 Sonnet backup
    "openrouter/qwen/qwen3-32b",                 # High-quality alternative
    "openrouter/x-ai/grok-2"                    # Final fallback
]

# Model fallback hierarchy for overload situations - MODULE LEVEL
ANTHROPIC_FALLBACKS = [
    "openrouter/anthropic/claude-3.5-sonnet",
    "openrouter/qwen/qwen3-32b",
    "openrouter/x-ai/grok-2",
    "openrouter/deepseek/deepseek-v3"
]
