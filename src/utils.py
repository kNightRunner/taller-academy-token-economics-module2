"""Portable measurement and persistence utilities (not tests)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
OUTPUT = BASE / "results" / "measurements.json"
PRICES = {"uncached_input": 2.0, "output": 10.0}  # Course sheet / 1M tokens


def load(relative: str) -> str:
    return (BASE / relative).read_text(encoding="utf-8")


def read_json(relative: str) -> Any:
    return json.loads(load(relative))


def token_count(text: str) -> int:
    import tiktoken
    return len(tiktoken.get_encoding("o200k_base").encode(text))


def estimate_output_savings(before: int, after: int, calls: int = 10_000) -> float:
    return (before - after) * PRICES["output"] / 1_000_000 * calls


def read_results() -> dict:
    if not OUTPUT.exists():
        return {}
    return json.loads(OUTPUT.read_text(encoding="utf-8"))


def record(case: str, result: dict) -> None:
    results = read_results()
    results[case] = {**result, "measured_at_utc": datetime.now(timezone.utc).isoformat()}
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def summarize_usage(responses: list[dict]) -> dict:
    return {
        "turns": len(responses),
        "total_input_tokens": sum((r.get("input_tokens") or 0) for r in responses),
        "total_output_tokens": sum((r.get("output_tokens") or 0) for r in responses),
        "context_at_end_tokens": (responses[-1].get("input_tokens") or 0) if responses else None,
        "usage_source": "Ollama /api/chat prompt_eval_count and eval_count",
    }
