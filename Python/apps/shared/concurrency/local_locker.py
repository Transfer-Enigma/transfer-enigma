import threading

from . import Locker, TaskAlreadyRunningError


class LocalLocker(Locker):
    _lock: threading.Lock = threading.Lock()
    _active: dict[str, bool] = {}

    @classmethod
    def acquire(cls, key: str) -> None:
        with cls._lock:
            if cls._active.get(key):
                raise TaskAlreadyRunningError(key)
            cls._active[key] = True

    @classmethod
    async def aacquire(cls, key: str) -> None:
        cls.acquire(key)

    @classmethod
    def release(cls, key: str) -> None:
        with cls._lock:
            cls._active.pop(key, None)

    @classmethod
    async def arelease(cls, key: str) -> None:
        cls.release(key)

    @classmethod
    def is_running(cls, key: str) -> bool:
        with cls._lock:
            return cls._active.get(key, False)

    @classmethod
    async def ais_running(cls, key: str) -> bool:
        return cls.is_running(key)
