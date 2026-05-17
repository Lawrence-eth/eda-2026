import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path):
    with path.open() as f:
        return json.load(f)


def test_focus_cases_track_published_result_without_positions():
    baseline = _load_json(ROOT / "results" / "boundary_full.json")
    focus = _load_json(ROOT / "results" / "focus_cases.json")

    assert focus["source_result"] == "results/boundary_full.json"
    assert math.isclose(focus["total_score"], baseline["total_score"])
    assert focus["dominant_score_range"]["range"] == "101-120"
    assert focus["score_concentration"][0]["test_ids"] == [99]
    assert focus["soft_driver_pressure"]["grouping"] > focus["soft_driver_pressure"]["boundary"]

    for section in ("top_weighted_cases", "top_sensitivity_cases"):
        assert focus[section]
        assert all("positions" not in case for case in focus[section])


def test_enriched_diagnostics_preserve_score_and_add_soft_attribution():
    baseline = _load_json(ROOT / "results" / "boundary_full.json")
    enriched = _load_json(ROOT / "results" / "enriched_diagnostics.json")

    assert math.isclose(enriched["total_score"], baseline["total_score"])
    assert enriched["summary"] == baseline["summary"]
    assert len(enriched["test_results"]) == len(baseline["test_results"]) == 100
    assert enriched["diagnostics"]["enriched_soft_counts"]["source_result"] == "results/boundary_full.json"

    top_case = next(case for case in enriched["test_results"] if case["test_id"] == 99)
    assert top_case["boundary_violations"] == 2
    assert top_case["grouping_violations"] == 3
    assert top_case["mib_violations"] == 0
    assert top_case["constraint_boundary_blocks"] == 36
    assert top_case["b2b_edges"] == 7056
