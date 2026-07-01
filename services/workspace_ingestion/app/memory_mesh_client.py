"""Minimal memoryd client — records a recall candidate after an ingest.

Mirrors services/finance_saa/app/memory_mesh_client.py. Writeback-after-action:
once the person-graph is updated, drop a summary memory so recall-before-action
can surface "the graph changed" to downstream agents. Graceful-degrade when
MEMORYD_BASE_URL is unset.
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx


class MemoryMeshClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.base_url = (base_url or os.getenv("MEMORYD_BASE_URL") or "").rstrip("/")
        self.api_key = api_key or os.getenv("MEMORYD_API_KEY") or ""
        self.timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    async def write_summary(self, *, envelope: dict[str, Any], content: dict[str, Any], tags: list[str], metadata: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {"stored": False, "reason": "memoryd disabled"}
        payload = {
            "envelope": envelope,
            "content": json.dumps(content, sort_keys=True, default=str),
            "memory_class": "summary",
            "persist_to_backend": True,
            "metadata": metadata,
            "tags": tags,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.post(f"{self.base_url}/v1/write", json=payload, headers=self.headers)
            resp.raise_for_status()
            return dict(resp.json())
