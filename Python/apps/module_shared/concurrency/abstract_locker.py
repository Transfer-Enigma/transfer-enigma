from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class TaskAlreadyRunningError(Exception):
    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Key '{key}' is already acquired")


class Locker(ABC):
    def __init__(self, key: str):
        self._key = key

    @classmethod
    @abstractmethod
    def acquire(cls, key: str) -> None:
        pass

    @classmethod
    @abstractmethod
    def release(cls, key: str) -> None:
        pass

    @classmethod
    @abstractmethod
    def is_running(cls, key: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    async def aacquire(cls, key: str) -> None:
        pass

    @classmethod
    @abstractmethod
    async def arelease(cls, key: str) -> None:
        pass

    @classmethod
    @abstractmethod
    async def ais_running(cls, key: str) -> bool:
        pass

    def __enter__(self) -> Locker:
        self.acquire(self._key)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release(self._key)

    async def __aenter__(self) -> Locker:
        await self.aacquire(self._key)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.arelease(self._key)

    @classmethod
    def locked(cls, key: str | Callable[..., str]):
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            def wrapper(*args, **kwargs) -> T:
                k = key(*args, **kwargs) if callable(key) else key
                cls.acquire(k)
                try:
                    return func(*args, **kwargs)
                finally:
                    cls.release(k)

            wrapper.__name__ = getattr(func, "__name__", "wrapped")
            wrapper.__doc__ = func.__doc__
            return wrapper
        return decorator

    @classmethod
    def alocked(cls, key: str | Callable[..., str]):
        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            async def wrapper(*args, **kwargs) -> T:
                k = key(*args, **kwargs) if callable(key) else key
                await cls.aacquire(k)
                try:
                    return await func(*args, **kwargs)
                finally:
                    await cls.arelease(k)

            wrapper.__name__ = getattr(func, "__name__", "wrapped")
            wrapper.__doc__ = func.__doc__
            return wrapper
        return decorator
