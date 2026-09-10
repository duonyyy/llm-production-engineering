from __future__ import annotations

from typing import Any, AsyncIterator

import httpx


class InferenceUnavailable(RuntimeError):
    pass


class VLLMClient:
    def __init__(self, base_url: str, timeout_ms: int) -> None:
        self.base_url = base_url
        self.timeout = httpx.Timeout(timeout_ms / 1000)

    async def models_ready(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(f"{self.base_url}/v1/models")
                return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def completion(self, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers={"X-Request-ID": request_id},
                )
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise InferenceUnavailable(type(exc).__name__) from exc

    async def stream(self, payload: dict[str, Any], request_id: str) -> AsyncIterator[bytes]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/v1/chat/completions", json=payload, headers={"X-Request-ID": request_id}
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_raw():
                        yield chunk
        except httpx.HTTPError as exc:
            raise InferenceUnavailable(type(exc).__name__) from exc
