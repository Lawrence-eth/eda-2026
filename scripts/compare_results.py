#!/usr/bin/env python3
"""Compare a candidate FloorSet result JSON against a baseline.

This is a publication guard for score-focused experiments.  It fails when a
candidate is infeasible, evaluates fewer cases than the baseline, or does not
strictly improve the total score unless explicitly allowed.

Examples:
    python scripts/compare_results.py results/boundary_full.json candidate.json
    python scripts/compare_results.py results/boundary_full.json candidate.json --allow-equal
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def load_result(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if "test_results" not in data or not isinstance(data["test_results"], list):
        raise SystemExit(f"No test_results list found in {path}")
    return data


def feasible_count(data: dict[str, Any]) -> int:
    summary = data.get("summary") or {}
    if "num_feasible" in summary:
        return int(_num(summary["num_feasible"]))
    return sum(1 for case in data["test_results"] if case.get("is_feasible"))


def total_score(data: dict[str, Any]) -> float:
    if "total_score" not in data:
        raise SystemExit("Result JSON is missing total_score")
    return _num(data["total_score"])


def case_count(data: dict[str, Any]) -> int:
    return len(data["test_results"])


def avg_runtime(data: dict[str, Any]) -> float:
    summary = data.get("summary") or {}
    if "avg_runtime" in summary:
        return _num(summary["avg_runtime"])
    runtimes = [_num(case.get("runtime_seconds")) for case in data["test_results"]]
    return sum(runtimes) / len(runtimes) if runtimes else 0.0


def compare(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    allow_equal: bool = False,
    require_full_feasible: bool = True,
    min_cases: int | None = None,
) -> tuple[bool, list[str]]:
    baseline_score = total_score(baseline)
    candidate_score = total_score(candidate)
    baseline_cases = case_count(baseline)
    candidate_cases = case_count(candidate)
    required_cases = baseline_cases if min_cases is None else min_cases
    candidate_feasible = feasible_count(candidate)

    messages = [
        f"baseline_score={baseline_score:.6f}",
        f"candidate_score={candidate_score:.6f}",
        f"delta={candidate_score - baseline_score:+.6f}",
        f"candidate_feasible={candidate_feasible}/{candidate_cases}",
        f"candidate_avg_runtime={avg_runtime(candidate):.4f}s",
    ]

    ok = True
    if candidate_cases < required_cases:
        ok = False
        messages.append(f"FAIL: candidate has {candidate_cases} cases, expected at least {required_cases}")
    if require_full_feasible and candidate_feasible != candidate_cases:
        ok = False
        messages.append("FAIL: candidate is not fully feasible")
    improved = candidate_score < baseline_score
    equal = candidate_score == baseline_score
    if not improved and not (allow_equal and equal):
        ok = False
        comparator = "equal to" if equal else "worse than"
        messages.append(f"FAIL: candidate score is {comparator} baseline")
    if ok:
        messages.append("PASS: candidate satisfies the publication guard")
    return ok, messages


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_json", type=Path, help="Published baseline result JSON")
    parser.add_argument("candidate_json", type=Path, help="Candidate result JSON")
    parser.add_argument("--allow-equal", action="store_true", help="Allow equal total_score")
    parser.add_argument(
        "--allow-partial-feasible",
        action="store_true",
        help="Do not require all candidate cases to be feasible",
    )
    parser.add_argument(
        "--min-cases",
        type=int,
        default=None,
        help="Minimum candidate case count; defaults to baseline case count",
    )
    args = parser.parse_args()

    baseline = load_result(args.baseline_json)
    candidate = load_result(args.candidate_json)
    ok, messages = compare(
        baseline,
        candidate,
        allow_equal=args.allow_equal,
        require_full_feasible=not args.allow_partial_feasible,
        min_cases=args.min_cases,
    )
    for message in messages:
        print(message)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
