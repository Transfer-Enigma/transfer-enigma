from functools import wraps


def apply_mapper(mapper):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return mapper(await func(*args, **kwargs))

        return wrapper

    return decorator
