"""httpx-based HttpFetcher with retry/backoff and an optional session
context that persists cookies across requests (needed for sites like 591
that set tokens on a warm-up page before serving the real data).
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from alc_crawler.application.ports.fetcher import FetchResult

_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class HttpxFetcher:
    """Single-shot fetcher; each get() opens its own AsyncClient.

    For multi-request flows (warm-up + API), use `async with fetcher.session() as s`
    which returns an `HttpxSession` that shares cookies and connections.
    """

    def __init__(
        self,
        *,
        timeout: float = 15.0,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
        user_agent: str = _DEFAULT_UA,
        verify: bool = True,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._user_agent = user_agent
        self.verify = verify

    def _default_headers(self) -> dict[str, str]:
        return {"User-Agent": self._user_agent}

    async def get(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> FetchResult:
        merged = self._default_headers()
        if headers:
            merged.update(headers)

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=self._retry_backoff),
            retry=retry_if_exception_type(httpx.HTTPStatusError),
            reraise=True,
        ):
            with attempt:
                async with httpx.AsyncClient(
                    timeout=self._timeout, verify=self.verify
                ) as client:
                    response = await client.get(url, headers=merged)
                    response.raise_for_status()
                    return FetchResult(url=url, status=response.status_code, body=response.text)

        raise RuntimeError("retry loop exited without result")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[HttpxSession]:
        """Open a session that persists cookies and reuses connections."""
        async with httpx.AsyncClient(
            timeout=self._timeout,
            verify=self.verify,
            headers=self._default_headers(),
            follow_redirects=True,
        ) as client:
            yield HttpxSession(
                client,
                max_retries=self._max_retries,
                retry_backoff=self._retry_backoff,
            )


class HttpxSession:
    """Cookie-persistent fetcher backed by a shared httpx.AsyncClient."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        max_retries: int,
        retry_backoff: float,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff

    async def get(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> FetchResult:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=self._retry_backoff),
            retry=retry_if_exception_type(httpx.HTTPStatusError),
            reraise=True,
        ):
            with attempt:
                response = await self._client.get(url, headers=headers or {})
                response.raise_for_status()
                return FetchResult(url=url, status=response.status_code, body=response.text)

        raise RuntimeError("retry loop exited without result")
