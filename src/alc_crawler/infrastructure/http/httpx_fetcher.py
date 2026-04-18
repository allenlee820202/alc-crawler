"""httpx-based HttpFetcher with retry/backoff via tenacity."""
from __future__ import annotations

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from alc_crawler.application.ports.fetcher import FetchResult

_DEFAULT_UA = "alc-crawler/0.1 (+https://github.com/anomalyco)"


class HttpxFetcher:
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

    async def get(
        self, url: str, *, headers: dict[str, str] | None = None
    ) -> FetchResult:
        merged_headers = {"User-Agent": self._user_agent}
        if headers:
            merged_headers.update(headers)

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
                    response = await client.get(url, headers=merged_headers)
                    response.raise_for_status()
                    return FetchResult(url=url, status=response.status_code, body=response.text)

        # Unreachable: tenacity either returns or raises.
        raise RuntimeError("retry loop exited without result")
