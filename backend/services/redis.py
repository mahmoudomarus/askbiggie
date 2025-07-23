import redis.asyncio as redis
import os
from dotenv import load_dotenv
import asyncio
from utils.logger import logger
from typing import List, Any
from utils.retry import retry
from urllib.parse import urlparse
import ssl

# Redis client and connection pool
client: redis.Redis | None = None
pool: redis.ConnectionPool | None = None
_initialized = False
_init_lock = asyncio.Lock()

# Constants
REDIS_KEY_TTL = 3600 * 24  # 24 hour TTL as safety mechanism


def initialize():
    """Initialize Redis connection pool and client using environment variables."""
    global client, pool

    # Load environment variables if not already loaded
    load_dotenv()

    # Check if we have a REDIS_URL (preferred for Heroku and other cloud providers)
    redis_url = os.getenv("REDIS_URL")
    
    if redis_url:
        logger.info(f"Using REDIS_URL for connection")
        
        # Parse the Redis URL to extract SSL requirement
        parsed_url = urlparse(redis_url)
        use_ssl = parsed_url.scheme == 'rediss'
        
        # Connection pool configuration
        max_connections = 250
        socket_timeout = 15.0
        connect_timeout = 10.0
        retry_on_timeout = not (os.getenv("REDIS_RETRY_ON_TIMEOUT", "True").lower() != "true")
        
        # SSL configuration for secure connections
        ssl_config = None
        if use_ssl:
            ssl_config = ssl.create_default_context()
            ssl_config.check_hostname = False
            ssl_config.verify_mode = ssl.CERT_NONE
        
        logger.info(f"Initializing Redis connection pool from URL with SSL: {use_ssl}, max {max_connections} connections")
        
        # Create connection pool from URL
        pool = redis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=socket_timeout,
            socket_connect_timeout=connect_timeout,
            socket_keepalive=True,
            retry_on_timeout=retry_on_timeout,
            health_check_interval=30,
            max_connections=max_connections,
            ssl_cert_reqs=None if use_ssl else None,
            ssl_ca_certs=None if use_ssl else None,
            ssl_check_hostname=False if use_ssl else None,
        )
    else:
        # Fallback to individual host/port configuration
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD", "")
        use_ssl = os.getenv("REDIS_SSL", "false").lower() == "true"
        
        # Connection pool configuration - optimized for production
        max_connections = 250
        socket_timeout = 15.0
        connect_timeout = 10.0
        retry_on_timeout = not (os.getenv("REDIS_RETRY_ON_TIMEOUT", "True").lower() != "true")

        logger.info(f"Initializing Redis connection pool to {redis_host}:{redis_port} with SSL: {use_ssl}, max {max_connections} connections")

        # SSL configuration for secure connections
        ssl_config = None
        if use_ssl:
            ssl_config = ssl.create_default_context()
            ssl_config.check_hostname = False
            ssl_config.verify_mode = ssl.CERT_NONE

        # Create connection pool with production-optimized settings
        pool = redis.ConnectionPool(
            host=redis_host,
            port=redis_port,
            password=redis_password if redis_password else None,
            decode_responses=True,
            socket_timeout=socket_timeout,
            socket_connect_timeout=connect_timeout,
            socket_keepalive=True,
            retry_on_timeout=retry_on_timeout,
            health_check_interval=30,
            max_connections=max_connections,
            ssl=use_ssl,
            ssl_cert_reqs=None if use_ssl else None,
            ssl_ca_certs=None if use_ssl else None,
            ssl_check_hostname=False if use_ssl else None,
        )

    # Create Redis client from connection pool
    client = redis.Redis(connection_pool=pool)

    return client


async def initialize_async():
    """Initialize Redis connection asynchronously."""
    global client, _initialized

    async with _init_lock:
        if not _initialized:
            logger.info("Initializing Redis connection")
            initialize()

        try:
            # Test connection with timeout
            await asyncio.wait_for(client.ping(), timeout=5.0)
            logger.info("Successfully connected to Redis")
            _initialized = True
        except asyncio.TimeoutError:
            logger.error("Redis connection timeout during initialization")
            client = None
            _initialized = False
            raise ConnectionError("Redis connection timeout")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            client = None
            _initialized = False
            raise

    return client


async def close():
    """Close Redis connection and connection pool."""
    global client, pool, _initialized
    if client:
        logger.info("Closing Redis connection")
        try:
            await asyncio.wait_for(client.aclose(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Redis close timeout, forcing close")
        except Exception as e:
            logger.warning(f"Error closing Redis client: {e}")
        finally:
            client = None
    
    if pool:
        logger.info("Closing Redis connection pool")
        try:
            await asyncio.wait_for(pool.aclose(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Redis pool close timeout, forcing close")
        except Exception as e:
            logger.warning(f"Error closing Redis pool: {e}")
        finally:
            pool = None
    
    _initialized = False
    logger.info("Redis connection and pool closed")


async def get_client():
    """Get the Redis client, initializing if necessary."""
    global client, _initialized
    if client is None or not _initialized:
        await retry(lambda: initialize_async())
    return client


# Basic Redis operations
async def set(key: str, value: str, ex: int = None, nx: bool = False):
    """Set a Redis key."""
    redis_client = await get_client()
    return await redis_client.set(key, value, ex=ex, nx=nx)


async def get(key: str, default: str = None):
    """Get a Redis key."""
    redis_client = await get_client()
    result = await redis_client.get(key)
    return result if result is not None else default


async def delete(key: str):
    """Delete a Redis key."""
    redis_client = await get_client()
    return await redis_client.delete(key)


async def check_redis_health():
    """Check Redis health by attempting to ping."""
    try:
        redis_client = await get_client()
        result = await redis_client.ping()
        return {"status": "healthy", "ping": result}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def publish(channel: str, message: str):
    """Publish a message to a Redis channel."""
    redis_client = await get_client()
    return await redis_client.publish(channel, message)


async def create_pubsub():
    """Create a Redis pubsub object."""
    redis_client = await get_client()
    return redis_client.pubsub()


# List operations
async def rpush(key: str, *values: Any):
    """Append one or more values to a list."""
    redis_client = await get_client()
    return await redis_client.rpush(key, *values)


async def lrange(key: str, start: int, end: int) -> List[str]:
    """Get a range of elements from a list."""
    redis_client = await get_client()
    return await redis_client.lrange(key, start, end)


# Key management


async def keys(pattern: str) -> List[str]:
    redis_client = await get_client()
    return await redis_client.keys(pattern)


async def expire(key: str, seconds: int):
    redis_client = await get_client()
    return await redis_client.expire(key, seconds)
