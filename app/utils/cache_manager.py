"""
Cache Manager for intelligent chat functionality.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
import asyncio

logger = logging.getLogger(__name__)

class CacheManager:
    """Simple in-memory cache manager for chat functionality."""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._expiry_times: Dict[str, datetime] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            # Check if key exists and not expired
            if key not in self._cache:
                return None
            
            if key in self._expiry_times:
                if datetime.utcnow() > self._expiry_times[key]:
                    # Expired, remove from cache
                    del self._cache[key]
                    del self._expiry_times[key]
                    return None
            
            return self._cache[key].get('value')
            
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, expiry: Optional[timedelta] = None) -> bool:
        """Set value in cache with optional expiry."""
        try:
            self._cache[key] = {
                'value': value,
                'created_at': datetime.utcnow()
            }
            
            if expiry:
                self._expiry_times[key] = datetime.utcnow() + expiry
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            if key in self._cache:
                del self._cache[key]
            
            if key in self._expiry_times:
                del self._expiry_times[key]
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {str(e)}")
            return False
    
    async def clear(self) -> bool:
        """Clear all cache."""
        try:
            self._cache.clear()
            self._expiry_times.clear()
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, expiry in self._expiry_times.items()
            if now > expiry
        ]
        
        return {
            'total_keys': len(self._cache),
            'expired_keys': len(expired_keys),
            'active_keys': len(self._cache) - len(expired_keys),
            'memory_usage_mb': self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB (rough calculation)."""
        try:
            total_size = 0
            for key, value in self._cache.items():
                # Rough estimation
                total_size += len(str(key)) + len(str(value))
            
            return total_size / (1024 * 1024)  # Convert to MB
            
        except Exception:
            return 0.0
