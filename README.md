# Token Economics — Module 2: Put Your Context on a Diet

**Taller Academy · Lever 1: Optimize Your Context · Lab 2**

A complete **implementation for all five exercises plus the Lab 1 baseline rerun**. The code is ready for the learner to run and review, but **the author has not run experiments or tests**. No simulated token counts are passed off as observations, and quality is **not** marked as passing until manually reviewed.

## Exercises and files

| Exercise | Code | Evidence created on execution |
|---|---|---|
| 1. Empty-session overhead | `src/exercises.py:ex1` | System/tools/instruction-token counts, three largest consumers, change, 25-turn saving; optional same-question quality comparison |
| 2. Prompt diet | `config/prompt_original.txt`, `config/prompt_diet.txt`, `ex2` | Both prompts run on the same 160-line source excerpt; measured outputs and a findings heuristic |
| 3. Preload versus retrieval | `src/repo_tools.py`, `ex3` | 20+ file preload versus live `search_files` and `read_file`, trace, turns, context and token usage |
| 4. Filter large tool output | `ex4` | Full `git log --stat` versus `git log --oneline -20` and cumulative token calculation for turns 3–20 |
| 5. Answer length limit | `ex5` | Same grounded source and question; unrestricted answer versus function-name-only answer, dollar difference for 10,000 calls |
| Baseline rerun | `fixtures/invoices.json`, `baseline` | Fixed March 2026 training clock and verified synthetic invoice; trimmed prompt + retrieval + concise answer |

**Precommitted checklists:** `config/quality_checklists.json`. **Measured output:** `results/measurements.json` (created when run). **Reviewer scores:** `results/quality_review.json` (created manually). **Submission:** `SUBMISSION.md` (regenerated from evidence with `python lab.py report`).

## Repository selection

The comparison uses your already-public [Day 3 Production training repo](https://github.com/kNightRunner/taller-academy-fde-day3-production), which contains 20+ source and documentation files. `prepare` clones it read-only into `./source_repo`, excluded from git. You can instead pass any existing local repository with `--repo /path/to/project`.

### Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python lab.py prepare
```

Choose a local Ollama tool-capable model; this is not a hosted API call and requires no credentials:

```bash
ollama pull qwen2.5:3b
ollama serve
```

In a second terminal, run **only what you want to validate**:

```bash
python lab.py ex1 --count-only       # deterministic count; no model call
python lab.py ex1                    # includes observed answer comparison
python lab.py ex2                    # original prompt versus diet
python lab.py ex3 --ctx-size 65536   # 20+ file preload versus retrieval
python lab.py ex4                    # git log versus filtered output
python lab.py ex5                    # long versus short answers
python lab.py baseline               # repeat Lab 1 fixture question
# or: python lab.py all --ctx-size 65536
```

The experiments use measured `prompt_eval_count` and `eval_count` from Ollama. For static content, `tiktoken/o200k_base` counts text *without* chat framing; distinguish these in the report. The context at end is the **input token count of the last model call**, not the cumulative input bill. `ex3` also reports total input across turns. The preload variant uses a larger context and can exceed available memory; change `--ctx-size` or model if needed. A failure is a real finding, not evidence of a completed run.

### Review the answers (required before claiming a quality-preserving cut)

Each case has three criteria written before the experiment. Open `results/measurements.json`, compare outputs with the source/answer key, then record one binary grade per criterion:

```bash
python lab.py review --case ex2_original --scores 1,1,0 --note "Performance risk unclear"
python lab.py review --case ex2_diet --scores 1,1,1 --note "All three criteria verified"
python lab.py review --case ex3_preload --scores 1,1,0
python lab.py review --case ex3_retrieve --scores 1,1,1
python lab.py report
```

All supported reviewer keys are printed by `python lab.py review --help`. Leave missing reviews blank rather than inventing passing marks. For Exercise 2, the reported findings count is explicitly **heuristic** and must be checked manually.

To submit, after your own validation, commit the measured artifacts:

```bash
git add -f results/measurements.json results/quality_review.json
python lab.py report
git add SUBMISSION.md
git commit -m "docs: record observed context optimizations and quality review"
git push
```

## Security and reproducibility

- Synthetic invoices only; no private customers or credentials.
- Read-only local repository search and allow-listed file access. No model tools for changing files or sending messages.
- No automation or GitHub Actions execute model experiments or tests by default; the student controls all runs.
- The baseline is taken from an actual public Day 1 Ollama trace (68 input / 58 output tokens, **not** a successful numerical answer). The repeat experiment has not been run by the author.
- Fixed course cost reference for Exercise 5: $10 USD per million **output** tokens. Not a quote of current vendor pricing.
- Source checkout is ignored by git. Model experiments may consume local RAM and compute.
