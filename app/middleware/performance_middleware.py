"""
Middleware for rate limiting, compression, and performance optimization.
"""

import time
import gzip
import json
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional, Callable
from flask import request, jsonify, g, current_app, Response

from app.services.performance_service import PerformanceService
from app.models.performance import (
    RateLimitRule, RateLimitScope, PerformanceMetric, CompressionType
)

class PerformanceMiddleware:
    """Middleware for performance optimization and monitoring."""
    
    def __init__(self, app=None, performance_service: Optional[PerformanceService] = None):
        """Initialize performance middleware."""
        self.app = app
        self.performance_service = performance_service or PerformanceService()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        self.app = app
        
        # Register middleware functions
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Add error handlers
        app.register_error_handler(429, self.rate_limit_exceeded)
    
    def before_request(self):
        """Execute before each request."""
        g.start_time = time.time()
        g.request_id = f"req_{int(time.time() * 1000)}"
        
        # Check rate limits
        rate_limit_result = self.check_rate_limits()
        if rate_limit_result:
            return rate_limit_result
        
        # Log request start
        self.log_request_start()
    
    def after_request(self, response):
        """Execute after each request."""
        try:
            # Calculate response time
            if hasattr(g, 'start_time'):
                response_time = (time.time() - g.start_time) * 1000  # Convert to milliseconds
                
                # Add performance headers
                response.headers['X-Response-Time'] = f"{response_time:.2f}ms"
                response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
                
                # Record performance metric
                try:
                    import asyncio
                    asyncio.run(self.record_response_metric(response_time, response.status_code))
                except Exception as metric_error:
                    print(f"Error recording metric: {metric_error}")
                
                # Apply compression if beneficial
                response = self.apply_compression(response)
                
                # Log request completion
                self.log_request_completion(response_time, response.status_code)
            
            return response
        except Exception as e:
            current_app.logger.error(f"Error in after_request middleware: {e}")
            return response
    
    def check_rate_limits(self) -> Optional[Response]:
        """Check rate limits for the current request."""
        try:
            endpoint = request.endpoint
            if not endpoint:
                return None
            
            # Get identifier based on request context
            user_id = getattr(g, 'user_id', None)
            identifier = user_id or request.remote_addr
            
            # Map endpoint to rate limit rule
            rate_limit_endpoint = self.map_endpoint_to_rate_limit(request.path)
            
            # Check rate limit
            import asyncio
            allowed, status = asyncio.run(
                self.performance_service.check_rate_limit(rate_limit_endpoint, identifier)
            )
            
            if not allowed:
                # Store rate limit info for error handler
                g.rate_limit_info = status
                return self.create_rate_limit_response(status)
            
            # Store rate limit headers for response
            g.rate_limit_headers = status
            
            return None
        except Exception as e:
            current_app.logger.error(f"Error checking rate limits: {e}")
            return None
    
    def map_endpoint_to_rate_limit(self, path: str) -> str:
        """Map request path to rate limit endpoint pattern."""
        # Authentication endpoints
        if '/auth/' in path:
            if 'login' in path:
                return '/api/v1/auth/login'
            elif 'register' in path:
                return '/api/v1/auth/register'
            return '/api/v1/auth/*'
        
        # Chat endpoints
        elif '/chat/' in path:
            if 'intelligent' in path:
                return '/api/v1/chat/intelligent'
            elif 'sessions' in path:
                return '/api/v1/chat/sessions/*'
            elif 'suggestions' in path:
                return '/api/v1/chat/suggestions'
            return '/api/v1/chat/*'
        
        # Content generation
        elif '/content/generate' in path:
            return '/api/v1/content/generate'
        
        # File upload
        elif '/files/upload' in path:
            return '/api/v1/files/upload'
        
        # Default API limit
        elif path.startswith('/api/v1/'):
            return '/api/v1/*'
        
        return path
    
    def create_rate_limit_response(self, status: Dict[str, Any]) -> Response:
        """Create rate limit exceeded response."""
        response_data = {
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Rate limit exceeded",
                "details": status
            }
        }
        
        response = jsonify(response_data)
        response.status_code = 429
        
        # Add rate limit headers
        if 'reset_at' in status:
            response.headers['X-RateLimit-Reset'] = status['reset_at']
        if 'retry_after' in status:
            response.headers['Retry-After'] = str(int(status['retry_after']))
        if 'current_count' in status:
            response.headers['X-RateLimit-Remaining'] = str(status.get('limit', 0) - status['current_count'])
        
        return response
    
    def apply_compression(self, response: Response) -> Response:
        """Apply response compression if beneficial."""
        try:
            # Check if compression is supported and beneficial
            accept_encoding = request.headers.get('Accept-Encoding', '').lower()
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Only compress JSON responses
            if 'application/json' not in content_type:
                return response
            
            # Check if client supports compression
            if 'gzip' not in accept_encoding:
                return response
            
            # Get response data
            response_data = response.get_data()
            
            # Only compress if response is large enough
            if len(response_data) < 1024:  # Don't compress small responses
                return response
            
            # Compress the data
            compressed_data = gzip.compress(response_data)
            
            # Only use compression if it provides significant benefit
            compression_ratio = len(compressed_data) / len(response_data)
            if compression_ratio > 0.9:  # Less than 10% reduction
                return response
            
            # Apply compression
            response.set_data(compressed_data)
            response.headers['Content-Encoding'] = 'gzip'
            response.headers['Content-Length'] = str(len(compressed_data))
            response.headers['X-Compression-Ratio'] = f"{compression_ratio:.3f}"
            
            return response
        except Exception as e:
            current_app.logger.error(f"Error applying compression: {e}")
            return response
    
    async def record_response_metric(self, response_time: float, status_code: int):
        """Record response time metric."""
        try:
            metric = PerformanceMetric(
                metric_name="api_response_time",
                value=response_time,
                unit="milliseconds",
                tags={
                    "endpoint": request.endpoint or "unknown",
                    "method": request.method,
                    "status_code": str(status_code)
                }
            )
            await self.performance_service.record_metric(metric)
        except Exception as e:
            print(f"Error recording response metric: {e}")  # Use print instead of current_app.logger
    
    def log_request_start(self):
        """Log request start information."""
        try:
            current_app.logger.info(
                f"Request started: {request.method} {request.path} "
                f"[{getattr(g, 'request_id', 'unknown')}] "
                f"from {request.remote_addr}"
            )
        except Exception as e:
            current_app.logger.error(f"Error logging request start: {e}")
    
    def log_request_completion(self, response_time: float, status_code: int):
        """Log request completion information."""
        try:
            current_app.logger.info(
                f"Request completed: {request.method} {request.path} "
                f"[{getattr(g, 'request_id', 'unknown')}] "
                f"in {response_time:.2f}ms with status {status_code}"
            )
        except Exception as e:
            current_app.logger.error(f"Error logging request completion: {e}")
    
    def rate_limit_exceeded(self, error):
        """Handle rate limit exceeded errors."""
        rate_limit_info = getattr(g, 'rate_limit_info', {})
        
        response_data = {
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests",
                "details": rate_limit_info
            }
        }
        
        response = jsonify(response_data)
        response.status_code = 429
        
        # Add rate limit headers
        if 'reset_at' in rate_limit_info:
            response.headers['X-RateLimit-Reset'] = rate_limit_info['reset_at']
        if 'retry_after' in rate_limit_info:
            response.headers['Retry-After'] = str(int(rate_limit_info['retry_after']))
        
        return response


def rate_limit(endpoint: str, scope: RateLimitScope = RateLimitScope.USER_ID, 
               limit: int = 100, window_seconds: int = 3600):
    """Decorator for applying rate limits to specific endpoints."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Get performance service
                performance_service = PerformanceService()
                
                # Get identifier
                if scope == RateLimitScope.USER_ID:
                    identifier = getattr(g, 'user_id', request.remote_addr)
                elif scope == RateLimitScope.IP_ADDRESS:
                    identifier = request.remote_addr
                else:
                    identifier = "global"
                
                # Create rate limit rule
                rule = RateLimitRule(
                    endpoint=endpoint,
                    scope=scope,
                    limit=limit,
                    window_seconds=window_seconds
                )
                
                # Check rate limit
                import asyncio
                allowed, status = asyncio.run(
                    performance_service.check_rate_limit(endpoint, identifier, rule)
                )
                
                if not allowed:
                    response_data = {
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Rate limit exceeded for {endpoint}",
                            "details": status
                        }
                    }
                    
                    response = jsonify(response_data)
                    response.status_code = 429
                    
                    # Add rate limit headers
                    if 'reset_at' in status:
                        response.headers['X-RateLimit-Reset'] = status['reset_at']
                    if 'retry_after' in status:
                        response.headers['Retry-After'] = str(int(status['retry_after']))
                    
                    return response
                
                # Store rate limit info for response headers
                g.rate_limit_headers = status
                
                # Execute the original function
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Error in rate_limit decorator: {e}")
                return f(*args, **kwargs)  # Continue without rate limiting on error
        
        return wrapper
    return decorator


def cache_response(ttl: int = 300, key_prefix: str = "api_cache"):
    """Decorator for caching API responses."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                # Generate cache key
                cache_key = f"{key_prefix}:{request.path}:{request.query_string.decode()}"
                
                # Try to get from cache
                performance_service = PerformanceService()
                import asyncio
                cached_response = asyncio.run(
                    performance_service.get_cached_data(cache_key)
                )
                
                if cached_response:
                    # Return cached response
                    response = jsonify(cached_response)
                    response.headers['X-Cache'] = 'HIT'
                    response.headers['Cache-Control'] = f'public, max-age={ttl}'
                    return response
                
                # Execute function and cache result
                result = f(*args, **kwargs)
                
                # Cache the response if it's successful
                if hasattr(result, 'status_code') and result.status_code == 200:
                    response_data = result.get_json()
                    asyncio.run(
                        performance_service.set_cached_data(cache_key, response_data, ttl=ttl)
                    )
                    result.headers['X-Cache'] = 'MISS'
                    result.headers['Cache-Control'] = f'public, max-age={ttl}'
                
                return result
                
            except Exception as e:
                current_app.logger.error(f"Error in cache_response decorator: {e}")
                return f(*args, **kwargs)  # Continue without caching on error
        
        return wrapper
    return decorator


def compress_response_decorator(compression_type: CompressionType = CompressionType.GZIP):
    """Decorator for compressing API responses."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                result = f(*args, **kwargs)
                
                # Check if client supports compression
                accept_encoding = request.headers.get('Accept-Encoding', '').lower()
                if compression_type.value not in accept_encoding:
                    return result
                
                # Apply compression
                if hasattr(result, 'get_data') and hasattr(result, 'set_data'):
                    response_data = result.get_data()
                    
                    # Only compress if response is large enough
                    if len(response_data) > 1024:
                        performance_service = PerformanceService()
                        import asyncio
                        
                        if compression_type == CompressionType.GZIP:
                            compressed_data = gzip.compress(response_data)
                        else:
                            # Use performance service for other compression types
                            compressed_data = asyncio.run(
                                performance_service._compress_data(response_data, compression_type)
                            )
                        
                        # Apply compression if beneficial
                        compression_ratio = len(compressed_data) / len(response_data)
                        if compression_ratio < 0.9:  # At least 10% reduction
                            result.set_data(compressed_data)
                            result.headers['Content-Encoding'] = compression_type.value
                            result.headers['Content-Length'] = str(len(compressed_data))
                            result.headers['X-Compression-Ratio'] = f"{compression_ratio:.3f}"
                
                return result
                
            except Exception as e:
                current_app.logger.error(f"Error in compress_response decorator: {e}")
                return f(*args, **kwargs)  # Continue without compression on error
        
        return wrapper
    return decorator


def monitor_performance(metric_name: str = "custom_metric"):
    """Decorator for monitoring performance of specific functions."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                
                # Record success metric
                execution_time = (time.time() - start_time) * 1000  # milliseconds
                performance_service = PerformanceService()
                import asyncio
                
                metric = PerformanceMetric(
                    metric_name=metric_name,
                    value=execution_time,
                    unit="milliseconds",
                    tags={
                        "function": f.__name__,
                        "status": "success",
                        "endpoint": getattr(request, 'endpoint', 'unknown')
                    }
                )
                
                asyncio.run(performance_service.record_metric(metric))
                
                return result
                
            except Exception as e:
                # Record error metric
                execution_time = (time.time() - start_time) * 1000  # milliseconds
                performance_service = PerformanceService()
                import asyncio
                
                metric = PerformanceMetric(
                    metric_name=metric_name,
                    value=execution_time,
                    unit="milliseconds",
                    tags={
                        "function": f.__name__,
                        "status": "error",
                        "error_type": type(e).__name__,
                        "endpoint": getattr(request, 'endpoint', 'unknown')
                    }
                )
                
                asyncio.run(performance_service.record_metric(metric))
                
                raise  # Re-raise the exception
        
        return wrapper
    return decorator
