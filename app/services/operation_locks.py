from __future__ import annotations

import threading
import time
from contextlib import asynccontextmanager
from typing import Protocol

DEFAULT_TTL_SECONDS = 120.0


class LockBackend(Protocol):
    def try_acquire(self, key: str, ttl_seconds: float) -> bool: ...

    def release(self, key: str) -> None: ...

    def is_locked(self, key: str) -> bool: ...


class InMemoryLockBackend:
    """Process-local locks. Swap for RedisLockBackend when running multiple instances."""

    def __init__(self) -> None:
        self._mutex = threading.Lock()
        self._locks: dict[str, float] = {}

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [key for key, expires_at in self._locks.items() if expires_at <= now]
        for key in expired:
            del self._locks[key]

    def try_acquire(self, key: str, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> bool:
        with self._mutex:
            self._purge_expired()
            if key in self._locks:
                return False
            self._locks[key] = time.monotonic() + ttl_seconds
            return True

    def release(self, key: str) -> None:
        with self._mutex:
            self._locks.pop(key, None)

    def is_locked(self, key: str) -> bool:
        with self._mutex:
            self._purge_expired()
            return key in self._locks


_backend: LockBackend = InMemoryLockBackend()


def set_lock_backend(backend: LockBackend) -> None:
    global _backend
    _backend = backend


class LockKeys:
    @staticmethod
    def setup(channel_id: str) -> str:
        return f"setup:{channel_id}"

    @staticmethod
    def change_order_submit(change_order_id: str) -> str:
        return f"change_order_submit:{change_order_id}"

    @staticmethod
    def payment(change_order_id: str) -> str:
        return f"pay:{change_order_id}"

    @staticmethod
    def draft(change_order_id: str) -> str:
        return f"draft:{change_order_id}"

    @staticmethod
    def bootstrap(channel_id: str, user_id: str) -> str:
        return f"bootstrap:{channel_id}:{user_id}"

    @staticmethod
    def canvas(project_id: str) -> str:
        return f"canvas:{project_id}"


def try_acquire(key: str, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> bool:
    return _backend.try_acquire(key, ttl_seconds)


def release(key: str) -> None:
    _backend.release(key)


def is_locked(key: str) -> bool:
    return _backend.is_locked(key)


@asynccontextmanager
async def operation_lock(key: str, ttl_seconds: float = DEFAULT_TTL_SECONDS):
    acquired = try_acquire(key, ttl_seconds)
    try:
        yield acquired
    finally:
        if acquired:
            release(key)
