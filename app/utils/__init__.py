import logging
import time
import functools
from typing import Any, Callable

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry function calls on failure."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    logger.warning(f"Function {func.__name__} failed (attempt {retries}/{max_retries}), retrying in {current_delay}s: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
        return wrapper
    return decorator

def log_execution_time(func: Callable) -> Callable:
    """Decorator to log function execution time."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Function {func.__name__} executed in {execution_time:.3f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {execution_time:.3f}s: {str(e)}")
            raise
    return wrapper

def validate_input(schema: dict):
    """Decorator to validate function input against a schema."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Simple validation - in a real app, use a proper validation library
            for key, expected_type in schema.items():
                if key in kwargs:
                    value = kwargs[key]
                    if not isinstance(value, expected_type):
                        raise ValueError(f"Parameter {key} must be of type {expected_type.__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

def cache_result(ttl: int = 300):
    """Decorator to cache function results (simple in-memory cache)."""
    cache = {}
    cache_times = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            current_time = time.time()
            
            # Check if result is cached and not expired
            if cache_key in cache and cache_key in cache_times:
                if current_time - cache_times[cache_key] < ttl:
                    logger.debug(f"Returning cached result for {func.__name__}")
                    return cache[cache_key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[cache_key] = result
            cache_times[cache_key] = current_time
            
            logger.debug(f"Cached result for {func.__name__}")
            return result
        return wrapper
    return decorator

def format_error_response(error: Exception, status_code: int = 500) -> dict:
    """Format error response for API endpoints."""
    return {
        'error': type(error).__name__,
        'message': str(error),
        'status_code': status_code,
        'timestamp': time.time()
    }

def sanitize_input(text: str) -> str:
    """Sanitize user input by removing potentially harmful characters."""
    if not isinstance(text, str):
        return str(text)
    
    # Remove HTML tags and script tags
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'<script.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove potentially harmful characters
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    return text.strip()

def generate_unique_id() -> str:
    """Generate a unique ID."""
    import uuid
    return str(uuid.uuid4())

def validate_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> dict:
    """Validate password strength."""
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }
