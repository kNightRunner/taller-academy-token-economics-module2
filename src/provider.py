"""Minimal local Ollama adapter; real provider usage is never guessed."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class Ollama:
    def __init__(self, model: str | None = None, host: str | None = None,
                 num_ctx: int = 32768):
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
        self.host = (host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.num_ctx = num_ctx

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             max_output: int = 768) -> dict[str, Any]:
        payload = {
            "model": self.model, "messages": messages, "stream": False,
            "options": {"temperature": 0, "num_ctx": self.num_ctx, "num_predict": max_output},
        }
        if tools is not None:
            payload["tools"] = tools
        request = urllib.request.Request(
            self.host + "/api/chat", data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=360) as response:
                result = json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError("Ollama unavailable. Start `ollama serve` and pull your "
                               "selected model before running measurements.") from exc
        message = result.get("message") or {}
        # None means absent: never replace missing real usage with an estimated count.
        return {
            "message": message,
            "text": message.get("content", ""),
            "tool_calls": message.get("tool_calls") or [],
            "input_tokens": result.get("prompt_eval_count"),
            "output_tokens": result.get("eval_count"),
            "model": result.get("model", self.model),
            "done_reason": result.get("done_reason"),
        }


def usage_available(responses: list[dict]) -> bool:
    return bool(responses) and all(isinstance(r.get("input_tokens"), int)
                                   and isinstance(r.get("output_tokens"), int)
                                   for r in responses)
