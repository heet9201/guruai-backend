"""
Advanced Rate Limiting System
Configurable rate limiting per user, IP, endpoint with burst protection.
"""

import os
import time
import json
import logging
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from enum import Enum
import redis
from flask import request, g

class RateLimitType(Enum):
    PER_USER = "per_user"
    PER_IP = "per_ip"
    PER_ENDPOINT = "per_endpoint"
    PER_USER_ENDPOINT = "per_user_endpoint"
    GLOBAL = "global"

class RateLimitWindow(Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"

class RateLimitResult:
    def __init__(self, allowed: bool, limit: int, remaining: int, reset_time: float, retry_after: Optional[int] = None):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        self.retry_after = retry_after

class RateLimiter:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_RATE_LIMIT_DB', 4)),
            decode_responses=True
        )
        
        # Default rate limits
        self.default_limits = {
            'api_calls': {
                'per_user': {'limit': 1000, 'window': 'hour'},
                'per_ip': {'limit': 5000, 'window': 'hour'},
                'per_endpoint': {'limit': 10000, 'window': 'hour'}
            },
            'login_attempts': {
                'per_user': {'limit': 5, 'window': 'hour'},
                'per_ip': {'limit': 20, 'window': 'hour'}
            },
            'content_generation': {
                'per_user': {'limit': 100, 'window': 'hour'},
                'per_ip': {'limit': 200, 'window': 'hour'}
            },
            'file_uploads': {
                'per_user': {'limit': 50, 'window': 'hour'},
                'per_ip': {'limit': 100, 'window': 'hour'}
            },
            'search_queries': {
                'per_user': {'limit': 500, 'window': 'hour'},
                'per_ip': {'limit': 1000, 'window': 'hour'}
            }
        }
        
        # Burst allowances
        self.burst_limits = {
            'api_calls': 100,  # Allow 100 rapid calls
            'content_generation': 10,
            'search_queries': 50
        }
        
        # Premium user multipliers
        self.premium_multipliers = {
            'basic': 1.0,
            'premium': 2.0,
            'enterprise': 5.0
        }
        
        self.logger = logging.getLogger('rate_limiter')
        
        # Load custom limits
        self._load_custom_limits()
    
    def _load_custom_limits(self):
        """Load custom rate limits from Redis."""
        try:
            custom_limits = self.redis_client.get('rate_limits_config')
            if custom_limits:
                self.custom_limits = json.loads(custom_limits)
            else:
                self.custom_limits = {}
        except Exception as e:
            self.logger.error(f"Failed to load custom limits: {str(e)}")
            self.custom_limits = {}
    
    def check_rate_limit(self, 
                        key_type: RateLimitType,
                        resource: str,
                        identifier: str,
                        user_tier: str = 'basic',
                        custom_limit: Optional[Dict[str, Any]] = None) -> RateLimitResult:
        """
        Check if request is within rate limits.
        
        Args:
            key_type: Type of rate limiting (per_user, per_ip, etc.)
            resource: Resource being accessed (api_calls, login_attempts, etc.)
            identifier: User ID, IP address, or other identifier
            user_tier: User tier for premium multipliers
            custom_limit: Custom limit override
        
        Returns:
            RateLimitResult with limit check results
        """
        
        # Get limit configuration
        limit_config = self._get_limit_config(resource, key_type.value, custom_limit)
        if not limit_config:
            # No limit configured - allow
            return RateLimitResult(True, float('inf'), float('inf'), 0)
        
        # Apply premium multiplier
        multiplier = self.premium_multipliers.get(user_tier, 1.0)
        effective_limit = int(limit_config['limit'] * multiplier)
        window = limit_config['window']
        
        # Generate Redis key
        redis_key = self._generate_redis_key(key_type, resource, identifier, window)
        
        # Check current usage using sliding window
        current_time = time.time()
        result = self._sliding_window_check(redis_key, effective_limit, window, current_time)
        
        # Check burst limits
        if result.allowed and resource in self.burst_limits:
            burst_result = self._check_burst_limit(key_type, resource, identifier, current_time)
            if not burst_result.allowed:
                return burst_result
        
        # Log rate limit events
        if not result.allowed:
            self._log_rate_limit_exceeded(key_type, resource, identifier, limit_config)
        
        return result
    
    def _get_limit_config(self, resource: str, key_type: str, custom_limit: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get rate limit configuration for resource and key type."""
        
        if custom_limit:
            return custom_limit
        
        # Check custom limits first
        if resource in self.custom_limits:
            custom_resource = self.custom_limits[resource]
            if key_type in custom_resource:
                return custom_resource[key_type]
        
        # Check default limits
        if resource in self.default_limits:
            default_resource = self.default_limits[resource]
            if key_type in default_resource:
                return default_resource[key_type]
        
        return None
    
    def _generate_redis_key(self, key_type: RateLimitType, resource: str, identifier: str, window: str) -> str:
        """Generate Redis key for rate limiting."""
        timestamp = self._get_window_timestamp(window)
        return f"rate_limit:{key_type.value}:{resource}:{identifier}:{timestamp}"
    
    def _get_window_timestamp(self, window: str) -> int:
        """Get timestamp aligned to rate limit window."""
        current_time = int(time.time())
        
        if window == 'second':
            return current_time
        elif window == 'minute':
            return current_time // 60 * 60
        elif window == 'hour':
            return current_time // 3600 * 3600
        elif window == 'day':
            return current_time // 86400 * 86400
        else:
            return current_time
    
    def _sliding_window_check(self, redis_key: str, limit: int, window: str, current_time: float) -> RateLimitResult:
        """Implement sliding window rate limiting."""
        
        window_seconds = self._window_to_seconds(window)
        window_start = current_time - window_seconds
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(redis_key)
            
            # Add current request
            pipe.zadd(redis_key, {str(current_time): current_time})
            
            # Set expiry
            pipe.expire(redis_key, window_seconds + 1)
            
            results = pipe.execute()
            current_count = results[1] + 1  # +1 for the request we just added
            
            # Check if within limit
            allowed = current_count <= limit
            remaining = max(0, limit - current_count)
            reset_time = current_time + window_seconds
            
            if not allowed:
                # Remove the request we just added since it's not allowed
                self.redis_client.zrem(redis_key, str(current_time))
                remaining = 0
                retry_after = int(window_seconds)
            else:
                retry_after = None
            
            return RateLimitResult(allowed, limit, remaining, reset_time, retry_after)
            
        except Exception as e:
            self.logger.error(f"Rate limit check failed: {str(e)}")
            # Default to allowing request on Redis failure
            return RateLimitResult(True, limit, limit, current_time + window_seconds)
    
    def _check_burst_limit(self, key_type: RateLimitType, resource: str, identifier: str, current_time: float) -> RateLimitResult:
        """Check burst protection limits."""
        
        burst_limit = self.burst_limits.get(resource, 0)
        if burst_limit == 0:
            return RateLimitResult(True, float('inf'), float('inf'), 0)
        
        # Check requests in last 60 seconds for burst
        burst_key = f"burst:{key_type.value}:{resource}:{identifier}"
        burst_window_start = current_time - 60  # 60 seconds burst window
        
        try:
            # Remove expired entries
            self.redis_client.zremrangebyscore(burst_key, 0, burst_window_start)
            
            # Count current requests in burst window
            current_burst_count = self.redis_client.zcard(burst_key)
            
            if current_burst_count >= burst_limit:
                return RateLimitResult(False, burst_limit, 0, current_time + 60, 60)
            
            # Add current request to burst window
            self.redis_client.zadd(burst_key, {str(current_time): current_time})
            self.redis_client.expire(burst_key, 61)
            
            remaining = burst_limit - current_burst_count - 1
            return RateLimitResult(True, burst_limit, remaining, current_time + 60)
            
        except Exception as e:
            self.logger.error(f"Burst limit check failed: {str(e)}")
            return RateLimitResult(True, burst_limit, burst_limit, current_time + 60)
    
    def _window_to_seconds(self, window: str) -> int:
        """Convert window string to seconds."""
        if window == 'second':
            return 1
        elif window == 'minute':
            return 60
        elif window == 'hour':
            return 3600
        elif window == 'day':
            return 86400
        else:
            return 3600  # Default to hour
    
    def _log_rate_limit_exceeded(self, key_type: RateLimitType, resource: str, identifier: str, limit_config: Dict[str, Any]):
        """Log rate limit exceeded events."""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'event': 'rate_limit_exceeded',
                'key_type': key_type.value,
                'resource': resource,
                'identifier': identifier,
                'limit': limit_config['limit'],
                'window': limit_config['window'],
                'ip_address': getattr(request, 'remote_addr', None) if request else None,
                'user_agent': getattr(request, 'headers', {}).get('User-Agent', None) if request else None,
                'endpoint': getattr(request, 'endpoint', None) if request else None
            }
            
            # Store in Redis for monitoring
            log_key = f"rate_limit_log:{int(time.time())}"
            self.redis_client.setex(log_key, 86400 * 7, json.dumps(log_entry))  # 7 days
            
            # Update statistics
            stats_key = f"rate_limit_stats:{resource}:{key_type.value}"
            self.redis_client.incr(stats_key)
            self.redis_client.expire(stats_key, 86400 * 30)  # 30 days
            
            self.logger.warning(f"Rate limit exceeded: {log_entry}")
            
        except Exception as e:
            self.logger.error(f"Failed to log rate limit event: {str(e)}")
    
    def get_current_usage(self, key_type: RateLimitType, resource: str, identifier: str, window: str = 'hour') -> Dict[str, Any]:
        """Get current usage for a specific identifier."""
        
        redis_key = self._generate_redis_key(key_type, resource, identifier, window)
        window_seconds = self._window_to_seconds(window)
        current_time = time.time()
        window_start = current_time - window_seconds
        
        try:
            # Remove expired entries
            self.redis_client.zremrangebyscore(redis_key, 0, window_start)
            
            # Get current count
            current_count = self.redis_client.zcard(redis_key)
            
            # Get limit configuration
            limit_config = self._get_limit_config(resource, key_type.value, None)
            limit = limit_config['limit'] if limit_config else 0
            
            return {
                'current_count': current_count,
                'limit': limit,
                'remaining': max(0, limit - current_count),
                'window': window,
                'reset_time': current_time + window_seconds
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get current usage: {str(e)}")
            return {
                'current_count': 0,
                'limit': 0,
                'remaining': 0,
                'window': window,
                'reset_time': current_time + window_seconds
            }
    
    def reset_rate_limit(self, key_type: RateLimitType, resource: str, identifier: str, window: str = 'hour') -> bool:
        """Reset rate limit for specific identifier (admin function)."""
        
        try:
            redis_key = self._generate_redis_key(key_type, resource, identifier, window)
            self.redis_client.delete(redis_key)
            
            # Also reset burst limits
            burst_key = f"burst:{key_type.value}:{resource}:{identifier}"
            self.redis_client.delete(burst_key)
            
            self.logger.info(f"Rate limit reset for {key_type.value}:{resource}:{identifier}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to reset rate limit: {str(e)}")
            return False
    
    def update_rate_limits(self, new_limits: Dict[str, Any]) -> bool:
        """Update rate limit configurations."""
        
        try:
            # Validate new limits
            for resource, limits in new_limits.items():
                for key_type, config in limits.items():
                    if not isinstance(config, dict) or 'limit' not in config or 'window' not in config:
                        raise ValueError(f"Invalid limit configuration for {resource}:{key_type}")
                    
                    if config['window'] not in ['second', 'minute', 'hour', 'day']:
                        raise ValueError(f"Invalid window: {config['window']}")
            
            # Store new limits
            self.redis_client.setex('rate_limits_config', 86400 * 30, json.dumps(new_limits))
            
            # Reload limits
            self._load_custom_limits()
            
            self.logger.info("Rate limits updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update rate limits: {str(e)}")
            return False
    
    def get_rate_limit_stats(self, resource: str = None, time_range: str = 'day') -> Dict[str, Any]:
        """Get rate limiting statistics."""
        
        try:
            stats = {}
            
            # Get all rate limit stats keys
            pattern = f"rate_limit_stats:{resource}:*" if resource else "rate_limit_stats:*"
            keys = self.redis_client.keys(pattern)
            
            for key in keys:
                count = self.redis_client.get(key)
                if count:
                    parts = key.split(':')
                    if len(parts) >= 4:
                        resource_name = parts[2]
                        key_type = parts[3]
                        
                        if resource_name not in stats:
                            stats[resource_name] = {}
                        
                        stats[resource_name][key_type] = int(count)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get rate limit stats: {str(e)}")
            return {}
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is temporarily blocked due to rate limiting."""
        
        try:
            blocked_key = f"blocked_ip:{ip_address}"
            return self.redis_client.exists(blocked_key) > 0
            
        except Exception as e:
            self.logger.error(f"Failed to check IP block status: {str(e)}")
            return False
    
    def block_ip(self, ip_address: str, duration_seconds: int = 3600, reason: str = "Rate limit exceeded") -> bool:
        """Temporarily block an IP address."""
        
        try:
            blocked_key = f"blocked_ip:{ip_address}"
            block_info = {
                'blocked_at': datetime.now().isoformat(),
                'duration': duration_seconds,
                'reason': reason
            }
            
            self.redis_client.setex(blocked_key, duration_seconds, json.dumps(block_info))
            
            self.logger.warning(f"IP {ip_address} blocked for {duration_seconds}s: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to block IP: {str(e)}")
            return False
    
    def unblock_ip(self, ip_address: str) -> bool:
        """Unblock an IP address (admin function)."""
        
        try:
            blocked_key = f"blocked_ip:{ip_address}"
            result = self.redis_client.delete(blocked_key)
            
            if result:
                self.logger.info(f"IP {ip_address} unblocked")
            
            return bool(result)
            
        except Exception as e:
            self.logger.error(f"Failed to unblock IP: {str(e)}")
            return False
    
    def get_blocked_ips(self) -> list:
        """Get list of currently blocked IPs."""
        
        try:
            blocked_keys = self.redis_client.keys("blocked_ip:*")
            blocked_ips = []
            
            for key in blocked_keys:
                ip = key.split(':', 2)[2]  # Extract IP from key
                block_info_str = self.redis_client.get(key)
                
                if block_info_str:
                    block_info = json.loads(block_info_str)
                    ttl = self.redis_client.ttl(key)
                    
                    blocked_ips.append({
                        'ip_address': ip,
                        'blocked_at': block_info['blocked_at'],
                        'reason': block_info['reason'],
                        'expires_in': ttl
                    })
            
            return blocked_ips
            
        except Exception as e:
            self.logger.error(f"Failed to get blocked IPs: {str(e)}")
            return []
