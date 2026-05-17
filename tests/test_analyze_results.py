import json
import math

from scripts import analyze_results


def test_add_weights_matches_exponential_block_count_normalization():
    cases = [
        {"block_count": 10, "cost": 3.0},
        {"block_count": 12, "cost": 2.0},
    ]

    analyze_results.add_weights(cases)

    expected_low = math.exp(-2) / (math.exp(-2) + 1.0)
    expected_high = 1.0 / (math.exp(-2) + 1.0)
    assert math.isclose(cases[0]["_score_weight"], expected_low)
    assert math.isclose(cases[1]["_score_weight"], expected_high)
    assert math.isclose(cases[0]["_weighted_contribution"], 3.0 * expected_low)
    assert math.isclose(cases[1]["_weighted_contribution"], 2.0 * expected_high)


def test_fmt_case_includes_soft_violation_attribution_when_present():
    case = {
        "test_id": 7,
        "block_count": 42,
        "cost": 1.25,
        "_weighted_contribution": 0.5,
        "hpwl_gap": 0.1,
        "area_gap": 0.2,
        "violations_relative": 0.3,
        "boundary_violations": 1,
        "grouping_violations": 2,
        "mib_violations": 3,
        "total_soft_violations": 6,
        "max_possible_violations": 20,
        "runtime_seconds": 0.4,
    }

    formatted = analyze_results.fmt_case(case)

    assert "boundary=1" in formatted
    assert "grouping=2" in formatted
    assert "mib=3" in formatted
    assert "soft_count=6/20" in formatted


def test_fmt_case_keeps_tiny_weighted_contribution_visible():
    case = {
        "test_id": 1,
        "block_count": 21,
        "cost": 1.0,
        "_weighted_contribution": 2.5e-9,
        "hpwl_gap": 0.0,
        "area_gap": 0.0,
        "violations_relative": 0.0,
        "runtime_seconds": 0.1,
    }

    formatted = analyze_results.fmt_case(case)

    assert "weighted=2.500e-09" in formatted


def test_dominant_block_range_uses_reconstructed_score_contribution():
    cases = [
        {"block_count": 21, "_weighted_contribution": 0.1},
        {"block_count": 42, "_weighted_contribution": 0.2},
        {"block_count": 119, "_weighted_contribution": 1.7},
    ]

    label, share = analyze_results.dominant_block_range(cases)

    assert label == "101-120"
    assert math.isclose(share, 1.7 / 2.0)


def test_dominant_block_range_reflects_exponential_hidden_score_weighting():
    cases = [
        {"test_id": 1, "block_count": 99, "cost": 9.0},
        {"test_id": 2, "block_count": 120, "cost": 2.0},
    ]

    analyze_results.add_weights(cases)
    label, share = analyze_results.dominant_block_range(cases)

    assert label == "101-120"
    assert share > 0.999999


def test_recommendation_uses_available_soft_violation_driver():
    cases = []
    for idx in range(3):
        cases.append(
            {
                "test_id": idx,
                "block_count": 100 + idx,
                "cost": 5.0,
                "_weighted_contribution": 1.0 / (idx + 1),
                "hpwl_gap": 0.1,
                "area_gap": 0.1,
                "violations_relative": 0.8,
                "boundary_violations": 1,
                "grouping_violations": 5,
                "mib_violations": 0,
                "runtime_seconds": 0.1,
            }
        )

    recommendation = analyze_results.recommendation(cases)

    assert "soft constraints" in recommendation
    assert "grouping" in recommendation
    assert "Dominant score range" in recommendation


def test_write_enriched_result_preserves_score_and_adds_diagnostics(tmp_path):
    original = {
        "total_score": 2.052769,
        "summary": {"num_feasible": 1},
        "test_results": [{"test_id": 1, "cost": 3.0}],
    }
    cases = [
        {
            "test_id": 1,
            "cost": 3.0,
            "boundary_violations": 1,
            "grouping_violations": 2,
            "mib_violations": 0,
        }
    ]
    out = tmp_path / "diagnostics" / "enriched.json"

    analyze_results.write_enriched_result(original, cases, out, tmp_path / "baseline.json")

    written = json.loads(out.read_text())
    assert written["total_score"] == original["total_score"]
    assert written["summary"] == original["summary"]
    assert written["test_results"] == cases
    assert written["diagnostics"]["enriched_soft_counts"]["source_result"].endswith("baseline.json")
    assert "grouping_violations" in written["diagnostics"]["enriched_soft_counts"]["fields"]
