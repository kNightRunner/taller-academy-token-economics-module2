"""Command-line runner. Running scripts is explicitly left to the student."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from src.exercises import ex1, ex2, ex3, ex4, ex5, baseline
from src.provider import Ollama
from src.repo_tools import Repository
from src.utils import BASE
from report import create_report

SOURCE_URL = "https://github.com/kNightRunner/taller-academy-fde-day3-production.git"
RUN_CASES = {"ex1": ex1, "ex2": ex2, "ex3": ex3, "ex4": ex4, "ex5": ex5,
             "baseline": baseline}
REVIEW_CASES = [
    "ex1_original", "ex1_slim", "ex2_original", "ex2_diet",
    "ex3_preload", "ex3_retrieve", "ex4_raw", "ex4_filtered",
    "ex5_unrestricted", "ex5_limited", "baseline_before", "baseline_after",
]


def prepare(path: Path) -> None:
    if path.exists():
        print(f"Repository already exists: {path}")
        return
    if path.resolve() != (BASE / "source_repo").resolve():
        raise ValueError("Automatic clone only targets the local ./source_repo directory")
    subprocess.run(["git", "clone", "--depth", "1", SOURCE_URL, str(path)], check=True)
    print(f"Cloned public training repository: {path}")


def review(case: str, scores: str, note: str) -> None:
    if case not in REVIEW_CASES:
        raise ValueError(f"Allowed cases: {', '.join(REVIEW_CASES)}")
    values = [int(piece.strip()) for piece in scores.split(",")]
    if len(values) != 3 or any(value not in (0, 1) for value in values):
        raise ValueError("Give three manual Boolean grades, e.g. --scores 1,0,1")
    target = BASE / "results" / "quality_review.json"
    all_reviews = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    all_reviews[case] = {"scores": values, "score": sum(values),
                         "note": note, "source": "student manual review"}
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(all_reviews, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(f"Recorded manual {case}: {sum(values)}/3")


def main() -> None:
    parser = argparse.ArgumentParser(description="Taller Academy Module 2 — context optimization")
    parser.add_argument("command", choices=["prepare", "ex1", "ex2", "ex3", "ex4",
                                              "ex5", "baseline", "all", "review", "report"])
    parser.add_argument("--repo", type=Path, default=BASE / "source_repo",
                        help="Local clone of the public Day 3 repository (or your own)")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--ctx-size", type=int, default=32768)
    parser.add_argument("--case", choices=REVIEW_CASES)
    parser.add_argument("--scores", help="Three comma-separated 0/1 grades")
    parser.add_argument("--note", default="")
    parser.add_argument("--count-only", action="store_true",
                        help="Exercise 1: count token budget without making model calls")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.repo)
        return
    if args.command == "review":
        if not args.case or not args.scores:
            parser.error("review requires --case and --scores")
        review(args.case, args.scores, args.note)
        print(create_report())
        return
    if args.command == "report":
        print(create_report())
        return
    if not args.repo.exists():
        parser.error(f"Source checkout does not exist: {args.repo}. Run `python lab.py prepare`.")
    repo = Repository(args.repo)
    client = Ollama(model=args.model, num_ctx=args.ctx_size)
    commands = ["ex1", "ex2", "ex3", "ex4", "ex5", "baseline"] if args.command == "all" else [args.command]
    for command in commands:
        if command == "baseline":
            measured = baseline(client)
        elif command == "ex1":
            measured = ex1(repo, None if args.count_only else client)
        elif command == "ex4":
            measured = ex4(repo)
        else:
            measured = RUN_CASES[command](repo, client)
        print(f"Recorded {command}: {', '.join(measured.keys())}")
    print(f"Report: {create_report()}")
    print("Manual quality review remains necessary; no automatic grade has been assigned.")


if __name__ == "__main__":
    main()
