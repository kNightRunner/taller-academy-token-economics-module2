"""Read-only, allow-listed repository search tools with bounded outputs."""
from __future__ import annotations

import json
import re
from pathlib import Path

EXTENSIONS = {".py", ".md", ".json", ".txt", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".ts", ".js"}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"}


class Repository:
    def __init__(self, root: Path):
        self.root = Path(root).resolve(strict=True)
        self.files = {}
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(self.root).parts):
                continue
            if path.suffix.lower() not in EXTENSIONS or path.stat().st_size > 100_000:
                continue
            try:
                contents = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            self.files[path.relative_to(self.root).as_posix()] = contents
        if not self.files:
            raise ValueError(f"No readable source files found under {self.root}")

    def get(self, path: str, max_chars: int = 8000) -> dict:
        if path not in self.files:
            return {"error": "Requested file is not in the allow-list", "path": path}
        text = self.files[path]
        return {"path": path, "content": text[:max_chars],
                "truncated": len(text) > max_chars, "total_characters": len(text)}

    def search(self, query: str, top_k: int = 5) -> dict:
        if not isinstance(query, str) or not query.strip():
            return {"error": "query must be non-empty"}
        if not isinstance(top_k, int) or not 1 <= top_k <= 8:
            return {"error": "top_k must be between 1 and 8"}
        words = set(re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", query.lower()))
        words -= {"the", "and", "this", "that", "where", "what", "how", "for", "with", "does"}
        scores = []
        for path, text in self.files.items():
            lower = (path + " " + text).lower()
            matches = [word for word in words if word in lower]
            if not matches:
                continue
            score = len(matches) + 3 * sum(word in path.lower() for word in matches)
            # The model receives a short excerpt, not an entire file on every search.
            first = min((lower.find(word) for word in matches if lower.find(word) >= 0), default=0)
            excerpt = text[max(0, first - 100):first + 350]
            scores.append((score, path, excerpt))
        scores.sort(key=lambda entry: (-entry[0], entry[1]))
        return {"query": query, "results": [
            {"path": path, "snippet": excerpt, "score": score}
            for score, path, excerpt in scores[:top_k]]}

    def preload(self, file_limit: int = 24, char_budget: int = 140_000) -> dict:
        # Preload many files, as asked by Exercise 3. Never include secret or binary files.
        all_files = sorted(self.files)
        text_parts, used, total = [], [], 0
        for path in all_files:
            content = self.files[path]
            part = f"### SOURCE: {path}\n{content}\n"
            if len(used) >= file_limit or total + len(part) > char_budget:
                break
            text_parts.append(part)
            used.append(path)
            total += len(part)
        return {"text": "\n".join(text_parts), "files": used,
                "characters": total, "available_files": len(all_files),
                "truncated": len(used) < len(all_files)}


def tool_specs() -> list[dict]:
    return [
        {"type": "function", "function": {
            "name": "search_files", "description": "Search repo files. Call before read_file and rephrase if no results.",
            "parameters": {"type": "object", "properties": {
                "query": {"type": "string"}, "top_k": {"type": "integer"}}, "required": ["query"]}}},
        {"type": "function", "function": {
            "name": "read_file", "description": "Read one allow-listed relative path from search results.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}}, "required": ["path"]}}},
    ]


def tool_loop(client, question: str, repo: Repository, max_turns: int = 8,
              max_output: int = 600) -> dict:
    messages = [
        {"role": "system", "content": "Answer from repository evidence. Search, open relevant files, "
         "cite relative filenames and identify uncertainty. Do not make up file contents."},
        {"role": "user", "content": question},
    ]
    responses, events = [], []
    for turn in range(max_turns):
        r = client.chat(messages, tools=tool_specs(), max_output=max_output)
        responses.append(r)
        calls = r["tool_calls"]
        if not calls:
            return {"answer": r["text"], "responses": responses, "events": events,
                    "hit_step_limit": False}
        messages.append({"role": "assistant", "content": r["text"], "tool_calls": calls})
        for call in calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments") or {}
            if isinstance(args, str):
                try: args = json.loads(args)
                except json.JSONDecodeError: args = {}
            if not isinstance(args, dict): args = {}
            if name == "search_files": output = repo.search(args.get("query", ""), args.get("top_k", 5))
            elif name == "read_file": output = repo.get(args.get("path", ""))
            else: output = {"error": "unapproved tool name"}
            events.append({"turn": turn + 1, "tool": name, "args": args, "result": output})
            messages.append({"role": "tool", "tool_name": name,
                             "content": json.dumps(output, ensure_ascii=False)})
    return {"answer": "Incomplete: step limit reached", "responses": responses,
            "events": events, "hit_step_limit": True}
