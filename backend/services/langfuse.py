import os
import logging
from langfuse import Langfuse

logger = logging.getLogger(__name__)

public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
secret_key = os.getenv("LANGFUSE_SECRET_KEY")
host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

enabled = False
langfuse = None

if public_key and secret_key:
    try:
        langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host
        )
        enabled = True
        logger.info(f"✅ Langfuse initialized successfully with host: {host}")
        logger.info(f"🔍 Langfuse public key: {public_key[:8]}...")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Langfuse: {e}")
        langfuse = None
        enabled = False
else:
    logger.info("⚠️ Langfuse environment variables not found. Monitoring disabled.")
    langfuse = Langfuse(enabled=False)
