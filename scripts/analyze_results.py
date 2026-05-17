#!/usr/bin/env python3
"""Analyze FloorSet validation result JSON files.

The official evaluator stores per-case quality metrics in results/boundary_full.json.
This script makes the next optimization step less blind by highlighting the cases
that dominate the score and by aggregating metrics by block-count range.

Usage:
    python scripts/analyze_results.py
    python scripts/analyze_results.py results/boundary_full.json --top 30
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = ROOT / "results" / "boundary_full.json"
RANGES = [(21, 40), (41, 60), (61, 80), (81, 100), (101, 120)]


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_any(case: dict[str, Any], names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        if name in case:
            return case[name]
    details = case.get("violations") or case.get("violation_counts") or case.get("soft_violations") or {}
    if isinstance(details, dict):
        for name in names:
            if name in details:
                return details[name]
    return default


def _violation(case: dict[str, Any], kind: str) -> Any:
    aliases = {
        "boundary": ["boundary_violations", "boundary", "num_boundary_violations"],
        "grouping": ["grouping_violations", "grouping", "cluster_violations", "num_grouping_violations"],
        "mib": ["mib_violations", "mib", "num_mib_violations"],
    }
    value = _get_any(case, aliases[kind], None)
    return "N/A" if value is None else value


def load_result(path: Path) -> dict[str, Any]:
    with path.open() as f:
        data = json.load(f)
    if "test_results" not in data or not isinstance(data["test_results"], list):
        raise SystemExit(f"No test_results list found in {path}")
    return data


def add_weights(cases: list[dict[str, Any]]) -> None:
    if not cases:
        return
    max_blocks = max(int(_num(c.get("block_count"))) for c in cases)
    raw_weights = [math.exp(int(_num(c.get("block_count"))) - max_blocks) for c in cases]
    total_weight = sum(raw_weights) or 1.0
    for case, weight in zip(cases, raw_weights):
        norm = weight / total_weight
        case["_score_weight"] = norm
        case["_weighted_contribution"] = _num(case.get("cost")) * norm


def fmt_case(case: dict[str, Any]) -> str:
    return (
        f"test_id={case.get('test_id'):>3} "
        f"blocks={case.get('block_count'):>3} "
        f"cost={_num(case.get('cost')):7.4f} "
        f"weighted={case.get('_weighted_contribution', 0.0):9.6f} "
        f"hpwl={_num(case.get('hpwl_gap')):7.4f} "
        f"area={_num(case.get('area_gap')):7.4f} "
        f"soft={_num(case.get('violations_relative')):7.4f} "
        f"boundary={_violation(case, 'boundary')} "
        f"grouping={_violation(case, 'grouping')} "
        f"mib={_violation(case, 'mib')} "
        f"runtime={_num(case.get('runtime_seconds')):6.3f}s"
    )


def print_cases(title: str, cases: list[dict[str, Any]], top: int) -> None:
    print(f"\n## {title}")
    for case in cases[:top]:
        print("- " + fmt_case(case))


def range_label(block_count: int) -> str:
    for lo, hi in RANGES:
        if lo <= block_count <= hi:
            return f"{lo}-{hi}"
    return "other"


def avg(items: list[float]) -> float:
    return mean(items) if items else 0.0


def print_aggregates(cases: list[dict[str, Any]]) -> None:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        buckets[range_label(int(_num(case.get("block_count"))))].append(case)

    print("\n## Aggregate averages by block-count range")
    for lo, hi in RANGES:
        label = f"{lo}-{hi}"
        group = buckets.get(label, [])
        if not group:
            print(f"- {label}: no cases")
            continue
        feasible = sum(1 for c in group if c.get("is_feasible"))
        print(
            f"- {label}: cases={len(group)}, feasible={feasible}/{len(group)}, "
            f"avg_cost={avg([_num(c.get('cost')) for c in group]):.4f}, "
            f"avg_weighted={sum(_num(c.get('_weighted_contribution')) for c in group):.6f}, "
            f"avg_hpwl={avg([_num(c.get('hpwl_gap')) for c in group]):.4f}, "
            f"avg_area={avg([_num(c.get('area_gap')) for c in group]):.4f}, "
            f"avg_soft={avg([_num(c.get('violations_relative')) for c in group]):.4f}, "
            f"avg_runtime={avg([_num(c.get('runtime_seconds')) for c in group]):.3f}s"
        )


def recommendation(cases: list[dict[str, Any]]) -> str:
    weighted = sorted(cases, key=lambda c: _num(c.get("_weighted_contribution")), reverse=True)
    focus = weighted[: max(1, min(20, len(weighted)))]
    hpwl = avg([_num(c.get("hpwl_gap")) for c in focus])
    area = avg([_num(c.get("area_gap")) for c in focus])
    soft = avg([_num(c.get("violations_relative")) for c in focus])
    runtime = avg([_num(c.get("runtime_seconds")) for c in focus])

    # Cost uses (1 + 0.5*(HPWL+area)) * exp(2*soft) * runtime factor.
    # Use this as a simple directional diagnosis rather than a proof.
    quality_term = 0.5 * (hpwl + area)
    soft_term = math.exp(2 * soft) - 1
    if soft_term > quality_term * 1.15:
        primary = "soft constraints, especially grouping/boundary if detailed counts confirm it"
    elif hpwl > area * 1.15:
        primary = "HPWL / connectivity-aware placement"
    elif area > hpwl * 1.15:
        primary = "bounding-box area compaction"
    else:
        primary = "combined HPWL and area improvement, while preserving current soft-constraint gains"

    if runtime > 5.0:
        primary += "; also watch runtime on the largest cases"
    return (
        f"Weighted worst-case averages: hpwl={hpwl:.4f}, area={area:.4f}, "
        f"soft={soft:.4f}, runtime={runtime:.3f}s. Suggested next target: {primary}."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_json", nargs="?", default=str(DEFAULT_RESULT), help="Path to full evaluator JSON")
    parser.add_argument("--top", type=int, default=20, help="Number of worst cases to print")
    args = parser.parse_args()

    path = Path(args.result_json)
    data = load_result(path)
    cases = [dict(c) for c in data["test_results"]]
    add_weights(cases)

    total_score = data.get("total_score")
    summary = data.get("summary") or {}
    feasible = summary.get("num_feasible", sum(1 for c in cases if c.get("is_feasible")))
    print(f"# FloorSet result analysis")
    print(f"Result file: {path}")
    print(f"Total score: {_num(total_score):.6f}")
    print(f"Feasible: {feasible}/{len(cases)}")

    print_cases("Worst cases by raw cost", sorted(cases, key=lambda c: _num(c.get("cost")), reverse=True), args.top)
    print_cases("Worst cases by weighted contribution", sorted(cases, key=lambda c: _num(c.get("_weighted_contribution")), reverse=True), args.top)
    print_aggregates(cases)
    print("\n## Recommendation")
    print("- " + recommendation(cases))
    if all(_violation(cases[0], k) == "N/A" for k in ("boundary", "grouping", "mib")) if cases else False:
        print("- Note: this result JSON does not include per-case boundary/grouping/MIB counts. Add evaluator instrumentation if exact soft-violation attribution is needed.")


if __name__ == "__main__":
    main()
