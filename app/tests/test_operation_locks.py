import time

import pytest

from services.operation_locks import (
    InMemoryLockBackend,
    LockKeys,
    operation_lock,
    release,
    set_lock_backend,
    try_acquire,
)


@pytest.fixture(autouse=True)
def fresh_backend():
    set_lock_backend(InMemoryLockBackend())
    yield


def test_try_acquire_prevents_duplicate():
    key = LockKeys.setup("C123")
    assert try_acquire(key) is True
    assert try_acquire(key) is False
    release(key)
    assert try_acquire(key) is True


def test_lock_expires():
    backend = InMemoryLockBackend()
    set_lock_backend(backend)
    key = "test:expiry"
    assert backend.try_acquire(key, ttl_seconds=0.05) is True
    time.sleep(0.06)
    assert backend.is_locked(key) is False
    assert backend.try_acquire(key, ttl_seconds=1) is True


@pytest.mark.asyncio
async def test_operation_lock_context_manager():
    key = LockKeys.payment("co-1")
    async with operation_lock(key) as first:
        assert first is True
        assert try_acquire(key) is False
    assert try_acquire(key) is True
    release(key)


def test_lock_keys_are_stable():
    assert LockKeys.setup("C1") == "setup:C1"
    assert LockKeys.change_order_submit("x") == "change_order_submit:x"
    assert LockKeys.payment("x") == "pay:x"
    assert LockKeys.draft("x") == "draft:x"
    assert LockKeys.bootstrap("C1", "U1") == "bootstrap:C1:U1"
    assert LockKeys.canvas("p1") == "canvas:p1"
