"""Generate a truthful English submission from measured results and manual review."""
from __future__ import annotations

import json
from pathlib import Path
from src.utils import BASE, read_json, read_results

NOT_RUN = "**NOT RUN — pending user validation**"


def show(value, suffix=""):
    return f"{value}{suffix}" if value is not None else "NOT MEASURED"


def checklist(section: str, reviews: dict, definition: dict) -> list[str]:
    lines = ["", "**Quality checklist defined before the run:**"]
    saved = reviews.get(section, {})
    for index, criterion in enumerate(definition["criteria"], 1):
        score = (saved.get("scores") or [None, None, None])[index-1]
        lines.append(f"{index}. {criterion} — **{show(score)}**")
    score = saved.get("score")
    lines.append(f"\n**Quality score:** {show(score, '/3' if score is not None else '')}. "
                 "A blank score is NOT a pass.")
    note = saved.get("note")
    if note:
        lines.append(f"**Reviewer notes:** {note}")
    return lines


def format_result(text: str | None):
    return "\n".join("> " + line for line in (text or "(no response)").splitlines())


def create_report() -> Path:
    runs = read_results()
    checks = read_json("config/quality_checklists.json")
    review_path = BASE / "results" / "quality_review.json"
    reviews = json.loads(review_path.read_text(encoding="utf-8")) if review_path.exists() else {}
    baseline_old = read_json("fixtures/baseline_day1.json")
    out = [
        "# Lab 2 — Put Your Context on a Diet", "",
        "**Module:** Lever 1 — Optimize Your Context · Taller Academy", "",
        "**Evidence policy:** No experiments were executed by the project author on delivery. "
        "Results below are populated only by running the local scripts. Manual quality "
        "scores remain pending until a reviewer enters them. Never treat a missing count as zero.", "",
        "**Tokenizer note:** `tiktoken/o200k_base` provides content-only comparisons; "
        "Ollama `prompt_eval_count` and `eval_count` record real local-model usage. "
        "Neither is a paid provider invoice. The $10/M output rate is the course's illustrative price sheet.", "",
        "## Exercise 1 — What's in an empty session?", "",
    ]
    x = runs.get("ex1")
    if not x:
        out += [NOT_RUN, ""]
    else:
        out += ["| Track B metric | Original | Slim |", "|---|---:|---:|",
            f'| Context before first message (content tokens) | {x["before_first_message_tokens"]} | {x["after_first_message_tokens"]} |']
        for category in ("system", "tools", "instruction_files"):
            out += [f'| {category.replace("_", " ").title()} | {x["before_categories"][category]} | {x["after_categories"][category]} |']
        out += ["", f'**Largest three consumers:** {x["three_largest_consumers"]}.',
                 f'**Removed:** {", ".join(x["removed"])}.',
                 f'**Saved at 25 turns:** {x["saved_over_25_turns_if_resent_each_time"]:,} '
                 "tokens if this same prefix would otherwise be resent each turn."]
        if "observed_comparison" in x:
            out.append("**Optional observed answers:**")
            for label, row in x["observed_comparison"].items():
                out += [f'- {label}: {row["usage"]}', format_result(row["answer"])]
    out += checklist("ex1_original", reviews, checks["ex1"])
    out += checklist("ex1_slim", reviews, checks["ex1"])
    out += ["", "## Exercise 2 — The prompt diet", ""]
    x = runs.get("ex2")
    if not x:
        out += [NOT_RUN]
    else:
        out += [f'**Same file:** `{x["source_file"]}` ({x["source_lines"]} lines).', "",
            "| Metric | Original | Diet |", "|---|---:|---:|",
            f'| Prompt tokens without file | {x["prompt_tokens_without_file"]["original"]} | {x["prompt_tokens_without_file"]["diet"]} |',
            f'| Actual output tokens | {show(x["output_tokens"]["original"])} | {show(x["output_tokens"]["diet"])} |',
            f'| Heuristic findings (needs human check) | {x["findings_identified_heuristically"]["original"]} | {x["findings_identified_heuristically"]["diet"]} |',
            f'| Quality checklist | {show(reviews.get("ex2_original",{}).get("score"),"/3")} | {show(reviews.get("ex2_diet",{}).get("score"),"/3")} |',
            "", "**Prompt or output savings?** Compare measured deltas above; if output usage is missing, no conclusion is warranted.",
            "", "**Original response:**", format_result(x["answers"]["original"]),
            "", "**Diet response:**", format_result(x["answers"]["diet"])]
    out += checklist("ex2_original", reviews, checks["ex2"])
    out += checklist("ex2_diet", reviews, checks["ex2"])
    out += ["", "## Exercise 3 — Paste everything versus retrieval", "",
            f'**Question (precommitted):** {checks["ex3"]["question"]}',
            f'**Correct answer written in advance:** {checks["ex3"]["answer_key"]}', ""]
    x = runs.get("ex3")
    if not x:
        out += [NOT_RUN]
    else:
        a, b = x["run_a_preload"], x["run_b_retrieve"]
        out += ["| Metric | Run A: preload | Run B: retrieve |", "|---|---:|---:|",
          f'| Context tokens at end | {show(a["context_at_end_tokens"])} | {show(b["context_at_end_tokens"])} |',
          f'| Model turns | {a["turns"]} | {b["turns"]} |',
          f'| Correct (yes/partly/no) | {quality_label(reviews,"ex3_preload")} | {quality_label(reviews,"ex3_retrieve")} |',
          f'| Files actually needed | {", ".join(x["files_actually_needed_expected"])} | {", ".join(b["files_read"])} |',
          f'| Total input tokens (loop-aware) | {a["usage"]["total_input_tokens"]} | {b["usage"]["total_input_tokens"]} |',
          "", f'**Run A attached files ({a["file_count"]}):** {", ".join(a["files_attached"])}.',
          "", f'**When preloading wins:** {x["when_preloading_is_right"]}',
          "", "**Run A answer:**", format_result(a["answer"]),
          "", "**Run B answer:**", format_result(b["answer"])]
    out += checklist("ex3_preload", reviews, checks["ex3"])
    out += checklist("ex3_retrieve", reviews, checks["ex3"])
    out += ["", "## Exercise 4 — Trim the tool output", ""]
    x = runs.get("ex4")
    if not x:
        out += [NOT_RUN]
    else:
        out += [f'**Original:** `{x["raw_command"]}`',
                f'**Filtered:** `{x["filtered_command"]}`',
                f'**Actual content tokens:** raw **{x["raw_tokens"]:,}**; filtered **{x["filtered_tokens"]:,}**.',
                f'**Savings:** {x["tokens_removed"]:,} tokens per observation; repeated '
                f'**{x["repetition_count_turn_3_through_20"]}** times in turns 3–20 = '
                f'**{x["saved_over_20_turn_session"]:,}** tokens saved.',
                "", "The three latest commit SHA/subject pairs are the precommitted quality criterion."]
    out += checklist("ex4_raw", reviews, checks["ex4"])
    out += checklist("ex4_filtered", reviews, checks["ex4"])
    out += ["", "## Exercise 5 — Put a limit on the answer", "",
            f'**Question:** {checks["ex5"]["question"]}',
            f'**Sufficient correct answer:** `{checks["ex5"]["expected_answer"]}`.', ""]
    x = runs.get("ex5")
    if not x:
        out += [NOT_RUN]
    else:
        a, b = x["without_limit"], x["with_explicit_limit"]
        out += ["| Metric | Unrestricted | Explicit short answer |", "|---|---:|---:|",
               f'| Actual output tokens | {show(a["output_tokens"])} | {show(b["output_tokens"])} |',
               f'| Quality score | {show(reviews.get("ex5_unrestricted",{}).get("score"),"/3")} | {show(reviews.get("ex5_limited",{}).get("score"),"/3")} |',
               "", f'**Difference per 10,000 calls at $10/M output:** ${show(x["cost_difference_10000_calls_usd"])}.',
               "", "**Unrestricted answer:**", format_result(a["answer"]),
               "", "**Limited answer:**", format_result(b["answer"])]
    out += checklist("ex5_unrestricted", reviews, checks["ex5"])
    out += checklist("ex5_limited", reviews, checks["ex5"])
    out += ["", "## Wrap-up — repeat the Lab 1 baseline", "",
           f'**Task:** {baseline_old["task"]}',
           f'**Original trace:** {baseline_old["turns"]} turn, '
           f'{baseline_old["input_tokens"]} input tokens, '
           f'{baseline_old["output_tokens"]} output tokens; '
           f'quality bar met: **NO**. [Source]({baseline_old["source"]}).', ""]
    x = runs.get("baseline")
    if not x:
        out += [NOT_RUN, "Changes already designed: trimmed instructions, on-demand "
                "synthetic invoice retrieval, a fresh context, and a two-sentence cap."]
    else:
        new = x["new_usage"]
        out += [f'**Changes applied:** {", ".join(x["changes_applied"])}.',
                f'**Context at end:** before {baseline_old["input_tokens"]} → after '
                f'{show(new["context_at_end_tokens"])} input tokens.',
                f'**Turns:** before {baseline_old["turns"]} → after {new["turns"]}.',
                f'**Total input/output tokens after:** {new["total_input_tokens"]} / {new["total_output_tokens"]}.',
                f'**Completed to quality bar:** {quality_label(reviews,"baseline_after")} '
                '(must be confirmed by reviewer).',
                f'**Fixture expectation:** {x["expected_fixture_result_for_manual_check"]}.',
                "", "**New observed answer:**", format_result(x["new_response"])]
    out += checklist("baseline_before", reviews, checks["baseline"])
    out += checklist("baseline_after", reviews, checks["baseline"])
    out += ["", "## Reproduction (user-run; not automatically executed)", "",
            "```bash", "python -m pip install -r requirements.txt", "python lab.py prepare",
            "ollama pull qwen2.5:3b", "ollama serve",
            "python lab.py all", "# Review original and optimized answers before scoring:",
            "python lab.py review --case ex2_diet --scores 1,1,1 --note 'Manual evidence review'",
            "python lab.py report", "```", "",
            "Do not count a token reduction as a successful optimization without a valid answer and manual quality review."]
    target = BASE / "SUBMISSION.md"
    target.write_text("\n".join(out) + "\n", encoding="utf-8")
    return target


def quality_label(reviews: dict, key: str) -> str:
    value = reviews.get(key, {}).get("score")
    if value is None:
        return "not reviewed"
    if value == 3:
        return "yes"
    if value == 2:
        return "partly"
    return "no"


if __name__ == "__main__":
    print(create_report())
