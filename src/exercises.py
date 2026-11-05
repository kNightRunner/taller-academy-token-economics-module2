"""Five measured exercises and the repeated baseline. No tests auto-run."""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path

from .provider import Ollama
from .repo_tools import Repository, tool_loop
from .utils import BASE, load, read_json, record, summarize_usage, token_count, estimate_output_savings


def _single(client: Ollama, system: str, prompt: str, limit: int = 768) -> dict:
    return client.chat([{"role": "system", "content": system},
                        {"role": "user", "content": prompt}], max_output=limit)


def _source_excerpt(repo: Repository, name: str, max_chars: int = 6000) -> str:
    matches = [(path, content) for path, content in repo.files.items()
               if path.endswith(name)]
    if not matches:
        raise ValueError(f"Required public source file not found: {name}")
    return f"FILE: {matches[0][0]}\n" + matches[0][1][:max_chars]


def ex1(repo: Repository, client: Ollama | None = None) -> dict:
    """Track B: baseline system/tool counts, slim them, estimate 25-turn savings."""
    full_system = load("config/policy_full.txt")
    slim_system = load("config/policy_slim.txt")
    full_tools = load("config/tools_full.json")
    slim_tools = load("config/tools_slim.json")
    # A repo instruction file is a third potential background consumer.
    instructions = [(path, text) for path, text in repo.files.items()
                    if Path(path).name in {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}]
    instruction_text = "\n".join(text for _, text in instructions)
    original = {"system": token_count(full_system),
                "tools": token_count(full_tools),
                "instruction_files": token_count(instruction_text) if instruction_text else 0}
    after = {"system": token_count(slim_system),
             "tools": token_count(slim_tools),
             "instruction_files": original["instruction_files"]}
    before_total, after_total = sum(original.values()), sum(after.values())
    result = {
        "track": "B (local tokenizer counts, NOT provider-billed context)",
        "before_first_message_tokens": before_total,
        "after_first_message_tokens": after_total,
        "before_categories": original,
        "after_categories": after,
        "three_largest_consumers": sorted(original.items(), key=lambda x: -x[1])[:3],
        "removed": ["write_file", "run_command", "send_notification",
                    "redundant system-prompt instructions"],
        "one_turn_saved": before_total - after_total,
        "saved_over_25_turns_if_resent_each_time": (before_total - after_total) * 25,
        "instruction_files_present": [p for p, _ in instructions],
        "quality_review": "pending manual review",
    }
    if client:
        question = read_json("config/quality_checklists.json")["ex1"]["question"]
        evidence = _source_excerpt(repo, "guardrails.py", max_chars=3500)
        old = _single(client, full_system + "\n" + full_tools, evidence + "\n" + question, 280)
        new = _single(client, slim_system + "\n" + slim_tools, evidence + "\n" + question, 280)
        result["observed_comparison"] = {
            "original": {"answer": old["text"], "usage": summarize_usage([old])},
            "slim": {"answer": new["text"], "usage": summarize_usage([new])},
        }
    record("ex1", result)
    return result


def ex2(repo: Repository, client: Ollama) -> dict:
    original_template = load("config/prompt_original.txt")
    diet_template = load("config/prompt_diet.txt")
    candidates = [(path, data) for path, data in repo.files.items()
                  if path.endswith("guardrails.py") or path.endswith("providers.py")]
    if not candidates:
        raise ValueError("This example requires a 100–200 line public Python source file")
    # Same 160 lines of the same file for both prompts.
    source_path, source_text = candidates[0]
    excerpt = "\n".join(source_text.splitlines()[:160])
    if len(excerpt.splitlines()) < 100:
        raise ValueError("Selected source excerpt is shorter than 100 lines")
    original = original_template.replace("[the file goes here]", "```python\n" + excerpt + "\n```")
    diet = diet_template.replace("[the file goes here]", "```python\n" + excerpt + "\n```")
    old = _single(client, "Review actual code; do not invent source facts.", original, limit=4096)
    new = _single(client, "Review actual code; do not invent source facts.", diet, limit=1024)
    # Count actionable findings, not how many distinct paragraphs appear.
    def findings(text: str) -> int:
        lines = text.splitlines()
        return sum(bool(re.match(r"^\s*(?:[-*]\s+|\d+[.)]\s+)(?:\*\*)?(?:P[0-3]|Critical|High|Medium|Low|Bug|Security|Performance|Finding)", line, re.I))
                   for line in lines)
    result = {
        "source_file": source_path, "source_lines": len(excerpt.splitlines()),
        "prompt_tokenizer": "tiktoken/o200k_base (content-only count)",
        "prompt_tokens_without_file": {"original": token_count(original_template), "diet": token_count(diet_template)},
        "output_tokens": {"original": old["output_tokens"], "diet": new["output_tokens"]},
        "findings_identified_heuristically": {"original": findings(old["text"]), "diet": findings(new["text"])},
        "answers": {"original": old["text"], "diet": new["text"]},
        "model_usage": {"original": summarize_usage([old]), "diet": summarize_usage([new])},
        "quality_review": "pending manual review of 3 precommitted criteria",
        "hypothesis": "Output and full-file rewrite avoidance should dominate savings; verify with real usage.",
    }
    record("ex2", result)
    return result


def ex3(repo: Repository, client: Ollama) -> dict:
    question = read_json("config/quality_checklists.json")["ex3"]["question"]
    preload = repo.preload(file_limit=26, char_budget=180_000)
    if len(preload["files"]) < 20:
        # Report honestly rather than pretending a 20-file preload occurred.
        raise ValueError(f"Only {len(preload['files'])} files fit the preload limit; "
                         "use a larger repo or char budget for the requested 20+ file comparison")
    prompt = "Use ONLY the attached repository files; cite filenames.\n" + preload["text"] + "\nQUESTION: " + question
    a = _single(client, "Answer grounded repository questions. Cite paths.", prompt, limit=650)
    b = tool_loop(client, question, repo, max_turns=8, max_output=650)
    used_b = sorted({event["args"].get("path", "") for event in b["events"]
                     if event["tool"] == "read_file" and event["args"].get("path")})
    result = {
        "question": question,
        "answer_key_written_before_run": read_json("config/quality_checklists.json")["ex3"]["answer_key"],
        "run_a_preload": {"answer": a["text"], "context_at_end_tokens": a["input_tokens"],
                          "turns": 1, "usage": summarize_usage([a]),
                          "file_count": len(preload["files"]), "files_attached": preload["files"],
                          "preload_truncated": preload["truncated"]},
        "run_b_retrieve": {"answer": b["answer"], "usage": summarize_usage(b["responses"]),
                           "context_at_end_tokens": summarize_usage(b["responses"])["context_at_end_tokens"],
                           "turns": len(b["responses"]), "files_read": used_b,
                           "trace": b["events"], "hit_step_limit": b["hit_step_limit"]},
        "files_actually_needed_expected": ["runtime.py", "guardrails.py", "tests/test_production.py"],
        "quality_review": "pending manual review of 3 precommitted criteria",
        "when_preloading_is_right": "When almost all of a small, stable source set is required at once and retrieval overhead exceeds the cost of loading it.",
    }
    record("ex3", result)
    return result


def ex4(repo: Repository) -> dict:
    def git(*args: str) -> str:
        cmd = ["git", "-C", str(repo.root), *args]
        result = subprocess.run(cmd, text=True, capture_output=True, check=True, timeout=30)
        return result.stdout
    # The checklists explicitly require just the latest three SHAs and subjects.
    raw = git("log", "--all", "--stat", "--format=fuller", "-n", "100")
    filtered = git("log", "--oneline", "-n", "20")
    raw_count, filtered_count = token_count(raw), token_count(filtered)
    result = {
        "raw_command": "git log --all --stat --format=fuller -n 100",
        "filtered_command": "git log --oneline -n 20",
        "raw_output": raw, "filtered_output": filtered,
        "raw_tokens": raw_count, "filtered_tokens": filtered_count,
        "tokens_removed": raw_count - filtered_count,
        "repetition_count_turn_3_through_20": 18,
        "saved_over_20_turn_session": (raw_count - filtered_count) * 18,
        "quality_review": "pending manual review; latest three SHA/subjects must be preserved",
    }
    record("ex4", result)
    return result


def ex5(repo: Repository, client: Ollama) -> dict:
    question = read_json("config/quality_checklists.json")["ex5"]["question"]
    full = repo.files.get("guardrails.py") or _source_excerpt(repo, "guardrails.py", 6500)
    # Identical grounded input context in two fresh, independent calls.
    snippet = full[full.find("def guarded_call("):full.find("def guarded_call(") + 3600]
    if not snippet or "def guarded_call" not in snippet:
        raise ValueError("Could not find guarded_call to ground the output-length experiment")
    old = _single(client, "You answer repository questions using the attached Python source.",
                  snippet + "\n\n" + question, limit=768)
    new = _single(client, "You answer repository questions using the attached Python source.",
                  snippet + "\n\n" + question + "\nReply with only the Python function name, no explanation.", limit=64)
    result = {
        "question": question,
        "answer_expected_written_before_run": "guarded_call",
        "without_limit": {"answer": old["text"], "usage": summarize_usage([old]),
                          "output_tokens": old["output_tokens"]},
        "with_explicit_limit": {"answer": new["text"], "usage": summarize_usage([new]),
                                "output_tokens": new["output_tokens"]},
        "price_per_million_output_usd": 10.0,
        "cost_difference_10000_calls_usd": estimate_output_savings(old["output_tokens"], new["output_tokens"])
                                              if isinstance(old["output_tokens"], int) and isinstance(new["output_tokens"], int) else None,
        "quality_review": "pending manual review of 3 precommitted criteria",
    }
    record("ex5", result)
    return result


def invoice_tool(order_id: str) -> dict:
    fixture = read_json("fixtures/invoices.json")
    invoice = fixture["invoices"].get(str(order_id))
    if invoice is None:
        return {"error": "No such synthetic invoice; do not invent the record"}
    issued = dt.date.fromisoformat(invoice["invoiced"])
    due = issued + dt.timedelta(days=invoice["terms_days"])
    today = dt.date.fromisoformat(fixture["today"])
    holidays = set(fixture["holidays"])
    days = 0
    cursor = today
    while cursor < due:
        cursor += dt.timedelta(days=1)
        if cursor.weekday() < 5 and cursor.isoformat() not in holidays:
            days += 1
    return {"source": fixture["source_repo"], "clock_type": fixture["clock_type"],
            "order_id": str(order_id), "invoiced": invoice["invoiced"],
            "terms_days": invoice["terms_days"], "today": fixture["today"],
            "due_date": due.isoformat(), "business_days_remaining": days,
            "holidays_excluded": sorted(holidays),
            "count_rule": "(today, due_date] excluding weekends and configured holidays"}


def baseline(client: Ollama) -> dict:
    old = read_json("fixtures/baseline_day1.json")
    question = read_json("config/quality_checklists.json")["baseline"]["question"]
    system = ("Use only the provided synthetic invoice tool. If a fact is missing, say so. "
              "Reply in at most two concise sentences, giving date and day count.")
    specification = [{"type": "function", "function": {
        "name": "lookup_invoice", "description": "Read synthetic invoice terms and calculate remaining business days using the fixed training calendar. Always call before giving a number.",
        "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]}}}]
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    responses, actions = [], []
    final_answer = "Incomplete"
    for step in range(5):
        response = client.chat(messages, tools=specification, max_output=150)
        responses.append(response)
        if not response["tool_calls"]:
            final_answer = response["text"]
            break
        messages.append({"role": "assistant", "content": response["text"], "tool_calls": response["tool_calls"]})
        for call in response["tool_calls"]:
            fn = call.get("function") or {}
            raw_args = fn.get("arguments") or {}
            if isinstance(raw_args, str):
                try: raw_args = json.loads(raw_args)
                except json.JSONDecodeError: raw_args = {}
            if not isinstance(raw_args, dict): raw_args = {}
            output = invoice_tool(raw_args.get("order_id", "")) if fn.get("name") == "lookup_invoice" else {"error": "Unapproved tool"}
            actions.append({"tool": fn.get("name"), "args": raw_args, "result": output})
            messages.append({"role": "tool", "tool_name": fn.get("name", "unknown"),
                             "content": json.dumps(output)})
    result = {
        "previous_real_measurement": old,
        "changes_applied": ["trimmed system instructions", "retrieved relevant invoice fixture only when needed", "two-sentence answer cap", "fresh session"],
        "new_response": final_answer,
        "new_usage": summarize_usage(responses),
        "tool_actions": actions,
        "expected_fixture_result_for_manual_check": invoice_tool("4471"),
        "quality_review": "pending manual review; do not assume completed",
    }
    record("baseline", result)
    return result
