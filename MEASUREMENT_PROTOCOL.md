# Pre-registered measurement and quality protocol

The purpose of this protocol is to prevent the mistaken claim that a context cut improved an agent when it only shortened the answer.

1. **Freeze the questions, source files, and quality checklists first.** All six scenarios and their three-part checklists are in `config/quality_checklists.json`; the prompts in `config/` are checked in. Do not rewrite the checklist after seeing a response.
2. **Keep the control comparable.** Exercise 2 uses the same Python file and excerpt length. Exercise 3 asks the same question, changes only preload vs. search, and records both terminal context size and cumulative input. Exercise 5 uses the same source and question with only a length instruction changed.
3. **Record actual usage.** `tiktoken/o200k_base` counts raw text for overhead; Ollama returns `prompt_eval_count` and `eval_count` for live calls. If an endpoint fails to return usage, record null; do not estimate and report as measured.
4. **Grade quality manually.** Three binary criteria per answer, giving 0–3; 3/3 is the target for claiming a quality-preserving optimization. A 2/3 is a partial answer, not a full pass. Reviewer scores cannot be inferred from answer length.
5. **Keep an honest baseline.** The Day 1 observed `plain_call` lacked enough facts to calculate a number. It is recorded as incomplete, despite handling uncertainty honestly. The new baseline can be marked successful only after its response is inspected against synthetic invoice terms, the fixture date, holidays and business-day rule.
6. **Don't claim improvements from failed experiments.** A missing result, truncated long context, wrong answer, or token-count mismatch is documented as an issue. Never silently substitute an expected output for an observed response.

The original exercise 3 answer key is committed in `config/quality_checklists.json`. The approved tool subset is read-only (`search_files`, `read_file`). All file paths are checked against the allow-list loaded from the selected local repository; the model cannot execute shell commands in the retrieval experiment.
