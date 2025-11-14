import asyncio
import json
import logging
from typing import Any, Optional, Dict
from redis import Redis, ConnectionError
from app.config import settings
import pickle
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Manages caching for improved performance
    """
    
    def __init__(self):
        self.redis_client = None
        self.use_redis = True
        
        try:
            if settings.redis_url:
                self.redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
                # Test connection
                self.redis_client.ping()
                logger.info("Connected to Redis successfully")
            else:
                logger.warning("Redis URL not configured, using in-memory cache")
                self.use_redis = False
                self._memory_cache = {}
        except ConnectionError:
            logger.warning("Could not connect to Redis, using in-memory cache")
            self.use_redis = False
            self._memory_cache = {}
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a cache key from prefix and parameters
        """
        # Create a unique key based on function name and parameters
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache
        """
        try:
            if self.use_redis:
                value = self.redis_client.get(key)
                if value:
                    return pickle.loads(value)
            else:
                # In-memory cache
                cache_entry = self._memory_cache.get(key)
                if cache_entry:
                    value, expiry = cache_entry
                    if expiry is None or expiry > datetime.now():
                        return value
                    else:
                        # Remove expired entry
                        del self._memory_cache[key]
        except Exception as e:
            logger.warning(f"Cache get error: {str(e)}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set a value in cache with TTL (in seconds)
        """
        try:
            if self.use_redis:
                serialized_value = pickle.dumps(value)
                self.redis_client.setex(key, ttl, serialized_value)
            else:
                # In-memory cache
                expiry = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
                self._memory_cache[key] = (value, expiry)
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete a value from cache
        """
        try:
            if self.use_redis:
                return bool(self.redis_client.delete(key))
            else:
                if key in self._memory_cache:
                    del self._memory_cache[key]
                    return True
                return False
        except Exception as e:
            logger.warning(f"Cache delete error: {str(e)}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern
        """
        try:
            if self.use_redis:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # For in-memory cache, we'd need to iterate
                keys_to_delete = []
                for key in self._memory_cache:
                    if pattern in key:
                        keys_to_delete.append(key)
                
                for key in keys_to_delete:
                    del self._memory_cache[key]
                
                return len(keys_to_delete)
        except Exception as e:
            logger.warning(f"Cache clear pattern error: {str(e)}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache
        """
        try:
            if self.use_redis:
                return bool(self.redis_client.exists(key))
            else:
                cache_entry = self._memory_cache.get(key)
                if cache_entry:
                    value, expiry = cache_entry
                    if expiry is None or expiry > datetime.now():
                        return True
                    else:
                        # Remove expired entry
                        del self._memory_cache[key]
                        return False
                return False
        except Exception as e:
            logger.warning(f"Cache exists error: {str(e)}")
            return False


class DocumentCache:
    """
    Specific cache for document-related operations
    """
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
    
    async def get_parsed_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a parsed document from cache
        """
        key = f"parsed_doc:{document_id}"
        return await self.cache_manager.get(key)
    
    async def set_parsed_document(self, document_id: str, document_data: Dict[str, Any], ttl: int = 7200) -> bool:
        """
        Cache a parsed document (2 hours default TTL)
        """
        key = f"parsed_doc:{document_id}"
        return await self.cache_manager.set(key, document_data, ttl)
    
    async def get_analyzed_content(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get analyzed content from cache
        """
        key = f"analyzed_content:{document_id}"
        return await self.cache_manager.get(key)
    
    async def set_analyzed_content(self, document_id: str, analysis_data: Dict[str, Any], ttl: int = 7200) -> bool:
        """
        Cache analyzed content (2 hours default TTL)
        """
        key = f"analyzed_content:{document_id}"
        return await self.cache_manager.set(key, analysis_data, ttl)
    
    async def get_study_guide(self, document_id: str, detail_level: str) -> Optional[Dict[str, Any]]:
        """
        Get a generated study guide from cache
        """
        key = f"study_guide:{document_id}:{detail_level}"
        return await self.cache_manager.get(key)
    
    async def set_study_guide(self, document_id: str, detail_level: str, guide_data: Dict[str, Any], ttl: int = 43200) -> bool:
        """
        Cache a generated study guide (12 hours default TTL)
        """
        key = f"study_guide:{document_id}:{detail_level}"
        return await self.cache_manager.set(key, guide_data, ttl)


class CacheDecorator:
    """
    Decorator class for caching function results
    """
    
    def __init__(self, cache_manager: CacheManager, ttl: int = 3600, prefix: str = "func"):
        self.cache_manager = cache_manager
        self.ttl = ttl
        self.prefix = prefix
    
    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key = self.cache_manager._generate_key(f"{self.prefix}:{func.__name__}", *args, **kwargs)
            
            # Try to get from cache first
            cached_result = await self.cache_manager.get(key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await self.cache_manager.set(key, result, self.ttl)
            
            return result
        return wrapper


# Global cache instances
cache_manager = CacheManager()
document_cache = DocumentCache(cache_manager)

# Decorator for easy caching
def cached_function(ttl: int = 3600, prefix: str = "func"):
    """
    Decorator to cache function results
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            key = cache_manager._generate_key(f"{prefix}:{func.__name__}", *args, **kwargs)
            
            # Try to get from cache first
            cached_result = await cache_manager.get(key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(key, result, ttl)
            
            return result
        return wrapper
    return decorator