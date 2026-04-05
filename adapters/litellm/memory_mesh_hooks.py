from __future__ import annotations

import os
from typing import Any, Dict, Iterable, Literal, Optional

import httpx
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy.proxy_server import DualCache, UserAPIKeyAuth


class MemoryMeshHook(CustomLogger):
    def __init__(self) -> None:
        super().__init__()
        self.base_url = os.getenv("MEMORYD_BASE_URL", "http://127.0.0.1:8787").rstrip("/")
        self.api_key = os.getenv("MEMORYD_API_KEY", "")
        self.timeout_seconds = float(os.getenv("MEMORYD_TIMEOUT_SECONDS", "5"))
        self.default_workload_id = os.getenv("MEMORYD_WORKLOAD_ID", "litellm-gateway")
        self.default_agent_id = os.getenv("MEMORYD_AGENT_ID", "litellm-gateway")
        self.default_source_interface = os.getenv("MEMORYD_SOURCE_INTERFACE", "litellm")
        self.default_writeback_class = os.getenv("MEMORYD_WRITEBACK_CLASS", "interaction")
        self.recall_top_k = int(os.getenv("MEMORYD_RECALL_TOP_K", "5"))
        self.writeback_enabled = os.getenv("MEMORYD_WRITEBACK_ENABLED", "true").lower() in {"1", "true", "yes"}

    @property
    def headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
        ],
    ) -> dict:
        if call_type not in {"completion", "text_completion"}:
            return data

        user_id = data.get("user")
        if not user_id:
            raise ValueError("LiteLLM request missing required 'user' field for memory mesh")

        envelope = self._build_envelope(data=data, user_id=str(user_id))
        recall_query = self._build_recall_query(data)
        if not recall_query:
            return data

        payload = {
            "envelope": envelope,
            "query": recall_query,
            "top_k": self.recall_top_k,
            "scope_order": ["run", "agent", "user"],
            "include_relations": False,
            "include_raw_events": False,
            "filters": {},
        }

        hits = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/v1/recall", json=payload, headers=self.headers)
                response.raise_for_status()
                body = response.json()
                hits = body.get("hits", []) if isinstance(body, dict) else []
        except Exception as exc:  # pragma: no cover
            data.setdefault("metadata", {})["memory_mesh_error"] = str(exc)
            return data

        if not hits:
            return data

        memory_block = self._format_memory_block(hits)
        messages = data.setdefault("messages", [])
        messages.insert(0, {"role": "system", "content": memory_block})

        metadata = data.setdefault("metadata", {})
        metadata["memory_mesh_envelope"] = envelope
        metadata["memory_mesh_hit_count"] = len(hits)
        metadata["memory_mesh_recalled_ids"] = [hit.get("memory_id") for hit in hits if isinstance(hit, dict) and hit.get("memory_id")]
        return data

    async def async_post_call_success_hook(self, data: dict, user_api_key_dict: UserAPIKeyAuth, response: Any) -> Any:
        if not self.writeback_enabled:
            return response

        metadata = data.get("metadata") or {}
        envelope = metadata.get("memory_mesh_envelope")
        if not envelope:
            return self._attach_headers(response, recalled=0, written=0)

        recalled = int(metadata.get("memory_mesh_hit_count") or 0)
        assistant_text = self._extract_assistant_text(response)
        user_text = self._build_recall_query(data)
        if not assistant_text and not user_text:
            return self._attach_headers(response, recalled=recalled, written=0)

        content = self._build_interaction_record(user_text=user_text, assistant_text=assistant_text)
        payload = {
            "envelope": envelope,
            "content": content,
            "memory_class": self.default_writeback_class,
            "persist_to_backend": True,
            "metadata": {
                "model": data.get("model"),
                "recalled_count": recalled,
                "source": "litellm-hook",
            },
            "tags": ["litellm", "interaction"],
        }

        written = 0
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                write_response = await client.post(f"{self.base_url}/v1/write", json=payload, headers=self.headers)
                write_response.raise_for_status()
                written = 1
        except Exception as exc:  # pragma: no cover
            metadata["memory_mesh_write_error"] = str(exc)

        return self._attach_headers(response, recalled=recalled, written=written)

    async def async_log_failure_event(self, kwargs: dict, response_obj: Any, start_time: Any, end_time: Any) -> None:
        return None

    @staticmethod
    def _extract_assistant_text(response: Any) -> str:
        try:
            choices = getattr(response, "choices", None)
            if not choices:
                return ""
            choice0 = choices[0]
            message = getattr(choice0, "message", None)
            if message is not None:
                content = getattr(message, "content", "")
                if isinstance(content, list):
                    return "\n".join(str(part) for part in content)
                return str(content or "")
            text = getattr(choice0, "text", "")
            return str(text or "")
        except Exception:
            return ""

    def _build_envelope(self, data: dict, user_id: str) -> Dict[str, Any]:
        metadata = data.get("metadata") or {}
        run_id = metadata.get("run_id") or data.get("session_id") or f"litellm:{user_id}"
        return {
            "user_id": user_id,
            "agent_id": str(metadata.get("agent_id") or self.default_agent_id),
            "run_id": str(run_id),
            "workload_id": str(metadata.get("workload_id") or self.default_workload_id),
            "workspace_id": metadata.get("workspace_id"),
            "channel": metadata.get("channel"),
            "thread_id": metadata.get("thread_id"),
            "source_interface": str(metadata.get("source_interface") or self.default_source_interface),
            "metadata": {
                "request_model": data.get("model"),
                **{k: v for k, v in metadata.items() if k not in {"memory_mesh_envelope", "memory_mesh_hit_count", "memory_mesh_recalled_ids"}},
            },
        }

    @staticmethod
    def _build_recall_query(data: dict) -> str:
        messages = data.get("messages") or []
        if not isinstance(messages, list):
            return ""
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if message.get("role") != "user":
                continue
            content = message.get("content", "")
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text") or item.get("content")
                        if text:
                            parts.append(str(text))
                return "\n".join(parts).strip()
            return str(content).strip()
        return ""

    @staticmethod
    def _format_memory_block(hits: Iterable[Dict[str, Any]]) -> str:
        lines = [
            "Relevant recalled memory follows. Use it when helpful, but do not treat it as infallible if the user contradicts it.",
            "",
        ]
        for index, hit in enumerate(hits, start=1):
            lines.append(f"[{index}] {hit.get('text', '')}")
        return "\n".join(lines)

    @staticmethod
    def _build_interaction_record(user_text: str, assistant_text: str) -> str:
        parts = []
        if user_text:
            parts.append(f"User: {user_text}")
        if assistant_text:
            parts.append(f"Assistant: {assistant_text}")
        return "\n".join(parts)

    @staticmethod
    def _attach_headers(response: Any, recalled: int, written: int) -> Any:
        additional_headers = getattr(response, "_hidden_params", {}).get("additional_headers", {}) or {}
        additional_headers["x-memory-mesh-recalled"] = str(recalled)
        additional_headers["x-memory-mesh-written"] = str(written)
        if not hasattr(response, "_hidden_params"):
            response._hidden_params = {}
        response._hidden_params["additional_headers"] = additional_headers
        return response


proxy_handler_instance = MemoryMeshHook()
