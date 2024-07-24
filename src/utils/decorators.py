# Rate limiting decorator
import time
from functools import wraps

def rate_limit(limit_seconds):
    def decorator(func):  
        last_called = 0
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal last_called
            elapsed = time.time() - last_called
            if elapsed < limit_seconds:
                raise ValueError(f"Rate limit exceeded. Please wait {limit_seconds - elapsed:.2f} seconds.")
            result = func(*args, **kwargs)
            last_called = time.time()
            return result
        return wrapper
    return decorator