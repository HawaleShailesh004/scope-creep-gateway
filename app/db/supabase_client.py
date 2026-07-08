import logging
import os
import time
from typing import Any, Callable

import httpx
from supabase import Client, create_client

logger = logging.getLogger(__name__)

_client: Client | None = None

# Connection-level errors that mean the pooled socket went stale (Railway/Supabase
# drop idle keep-alive connections). Retrying on a fresh client recovers cleanly.
_RETRYABLE_ERRORS = (
    httpx.WriteError,
    httpx.ReadError,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.PoolTimeout,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
)


def get_supabase() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env"
            )
        _client = create_client(url, key)
    return _client


def _reset_client() -> None:
    global _client
    _client = None


def run_query(build: Callable[[Client], Any], *, retries: int = 2) -> Any:
    """Execute a Supabase query with resilience to stale pooled connections.

    `build` receives a fresh client and must return a query builder; we call
    `.execute()` here so a retry can rebuild the query against a new connection.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return build(get_supabase()).execute()
        except _RETRYABLE_ERRORS as exc:
            last_exc = exc
            logger.warning(
                "supabase_query_retry attempt=%s error=%s", attempt + 1, exc
            )
            _reset_client()
            if attempt < retries:
                time.sleep(0.2 * (attempt + 1))
    assert last_exc is not None
    raise last_exc
