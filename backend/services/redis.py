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
        
        # Connection pool configuration - FIXED for Redis Premium 0 (40 connection limit)
        # With 1 web + 1 worker dyno, allocate 15 connections per dyno with 10 connection buffer
        max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "15"))
        socket_timeout = 10.0  # Reduced from 15s for faster failover
        connect_timeout = 5.0   # Reduced from 10s for faster failover
        retry_on_timeout = True
        retry_on_error = [redis.ConnectionError, redis.TimeoutError]
        
        # SSL configuration for secure connections
        ssl_config = None
        if use_ssl:
            ssl_config = ssl.create_default_context()
            ssl_config.check_hostname = False
            ssl_config.verify_mode = ssl.CERT_NONE
        
        logger.info(f"Initializing Redis connection pool from URL with SSL: {use_ssl}, max {max_connections} connections")
        
        # Create connection pool from URL with optimized settings
        pool = redis.ConnectionPool.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=socket_timeout,
            socket_connect_timeout=connect_timeout,
            socket_keepalive=True,
            socket_keepalive_options={},
            retry_on_timeout=retry_on_timeout,
            retry_on_error=retry_on_error,
            health_check_interval=15,  # More frequent health checks
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
        
        # Connection pool configuration - optimized for connection limits
        max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "15"))
        socket_timeout = 10.0
        connect_timeout = 5.0
        retry_on_timeout = True
        retry_on_error = [redis.ConnectionError, redis.TimeoutError]

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
            socket_keepalive_options={},
            retry_on_timeout=retry_on_timeout,
            retry_on_error=retry_on_error,
            health_check_interval=15,
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
            # Test connection with shorter timeout for faster failover
            await asyncio.wait_for(client.ping(), timeout=3.0)
            logger.info("Successfully connected to Redis")
            _initialized = True
        except asyncio.TimeoutError:
            logger.error("Redis connection timeout during initialization")
            client = None
            _initialized = False
            raise ConnectionError("Redis connection timeout")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            client = None
            _initialized = False
            raise ConnectionError(f"Redis connection failed: {e}")
        except redis.AuthenticationError as e:
            logger.error(f"Redis authentication error: {e}")
            client = None
            _initialized = False
            raise ConnectionError(f"Redis authentication failed: {e}")
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
    
    # If client exists and is initialized, try to use it
    if client is not None and _initialized:
        try:
            # Quick health check
            await asyncio.wait_for(client.ping(), timeout=1.0)
            return client
        except (redis.ConnectionError, redis.TimeoutError, asyncio.TimeoutError) as e:
            logger.warning(f"Redis health check failed: {e}, reinitializing...")
            _initialized = False
            client = None
    
    # Initialize or reinitialize
    if client is None or not _initialized:
        try:
            await retry(lambda: initialize_async())
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise
    
    return client


async def check_redis_health():
    """Check Redis connection health and return status."""
    try:
        redis_client = await get_client()
        await asyncio.wait_for(redis_client.ping(), timeout=2.0)
        
        # Get connection pool stats if available
        if hasattr(redis_client.connection_pool, 'connection_kwargs'):
            max_conn = redis_client.connection_pool.max_connections
            created_conn = len(redis_client.connection_pool._created_connections)
            available_conn = len(redis_client.connection_pool._available_connections)
            
            return {
                "status": "healthy",
                "max_connections": max_conn,
                "created_connections": created_conn,
                "available_connections": available_conn,
                "connection_usage": f"{created_conn}/{max_conn}"
            }
        else:
            return {"status": "healthy", "details": "connection pool stats unavailable"}
            
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


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
