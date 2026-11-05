# Lab 2 — Put Your Context on a Diet

**Module:** Lever 1 — Optimize Your Context · Taller Academy  
**Status:** Code and precommitted quality checklists are ready; **experiments not executed at the user's request**. The learner will validate and record real measurements. This document is automatically rebuilt by `python lab.py report` after running the exercises.

## Exercise 1 — What's in an empty session?

- **Track:** B — content-token count of system prompt, tool definitions, and local instruction files.
- **Before / after tokens:** NOT MEASURED.
- **Three largest consumers:** NOT MEASURED.
- **Change:** Remove unused `write_file`, `run_command`, and `send_notification` tool definitions and redundant system-prompt prose.
- **25-turn saving:** `(baseline_context_tokens − slim_context_tokens) × 25` (calculate after measuring).
- **Prewritten quality checklist (for original and trimmed):** correctly identify `guarded_call`; permissions and argument validation precede execution; answer remains grounded in actual repository files. Scores: **pending /3** for each version.

## Exercise 2 — The prompt diet

Two prompts are in `config/prompt_original.txt` and `config/prompt_diet.txt`. Both will review the **same 160 lines** from the public training repository. The diet keeps bugs including off-by-one, security, and performance, but requests a short findings list with a minimal diff per issue instead of rewriting the whole source.

| Metric | Original | Diet |
|---|---:|---:|
| Prompt tokens (without file) | NOT MEASURED | NOT MEASURED |
| Output tokens | NOT MEASURED | NOT MEASURED |
| Findings | NOT REVIEWED | NOT REVIEWED |
| Quality checklist | pending /3 | pending /3 |

**Prewritten quality checklist:** accurately evaluate bugs/off-by-one, security, and performance with actionable remedies. **Where savings came from:** to be determined from observed prompt and output differences, not guessed.

## Exercise 3 — Paste everything versus retrieval

**Repository question, committed before measurement:** How is a model tool call converted into tool results, where is a refund action authorized or blocked, and which offline tests check that gate? Cite source filenames.

**Correct answer key:** `runtime.py` handles model/tool message translation; `guardrails.py:guarded_call` enforces allow-list, validation, limits, and human approval; `tests/test_production.py` checks blocking, thresholds, and approval. All examples use synthetic data.

| Metric | Run A: preload | Run B: retrieve |
|---|---|---|
| Context tokens at end | NOT MEASURED | NOT MEASURED |
| Turns | NOT MEASURED | NOT MEASURED |
| Correct answer | NOT REVIEWED | NOT REVIEWED |
| Files actually needed | `runtime.py`, `guardrails.py`, `tests/test_production.py` | To observe |

**Prewritten quality checklist:** adapter correct; authorization gate correct; offline tests and citations correct. Preloading may be preferable when nearly all files are relevant to the same small, stable task and retrieval overhead would dominate.

## Exercise 4 — Trim the tool output

**Before:** `git log --all --stat --format=fuller -n 100`  
**After:** `git log --oneline -n 20`

- **Raw / filtered tokens:** NOT MEASURED.
- **20-turn saving:** `(raw_tokens − filtered_tokens) × 18`, because an observation inserted at turn 3 persists in turns 3–20.
- **Prewritten quality checklist:** three newest commits in order, unambiguous abbreviated SHAs, correct subjects. Both versions pending manual review.

## Exercise 5 — Put a limit on the answer

Question: Which Python function in `guardrails.py` enforces the authorization and approval gate before a refund can execute?  
Sufficient answer: `guarded_call`.

- **Without limit / with “function name only”:** NOT MEASURED output tokens.
- **Cost difference for 10,000 calls:** `(unrestricted_output_tokens − short_output_tokens) × $10 / 1,000,000 × 10,000` USD.
- **Prewritten quality checklist:** names `guarded_call`, avoids naming an incorrect gate, and gives enough information. Both pending manual review.

## Wrap-up — return to Lab 1 baseline

**Prior task:** Calculate remaining business days for synthetic invoice #4471. The previous real Ollama `plain_call` had **1 turn, 68 input tokens, 58 output tokens**, but **did not meet the numerical quality bar**. [Public trace](https://github.com/kNightRunner/taller-academy-fde-day1-foundations/blob/main/results/experiments.json).

**Changes prepared:** trimmed system instructions; retrieve the synthetic invoice fixture instead of expecting the model to invent its contents; answer limit of two short sentences; fresh session.

- **Context at end:** before **68** → after **NOT MEASURED**.
- **Turns:** before **1** → after **NOT MEASURED**.
- **Completed to quality bar:** before **NO** → after **NOT REVIEWED**.
- **Prewritten quality checklist:** compute numerical result from actual invoice/date facts; apply working days and synthetic holidays; give a concise justified answer without invented data.
- **Expected fixture:** invoice date 2026-03-03; 30-day calendar term; training clock 2026-03-24; holiday 2026-03-30 excluded. Dates are synthetic and historical, not a statement about any current invoice.

## Reproduction

See `README.md`. Run individual cases with `python lab.py ex1` through `ex5` and `python lab.py baseline`; enter manual checklist grades; rebuild with `python lab.py report`. No measurement or success outcome in this initial file is fabricated.
