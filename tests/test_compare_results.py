import copy

from scripts import compare_results


def _result(score=2.0, feasible=True, cases=2):
    test_results = [
        {
            "test_id": i,
            "block_count": 100 + i,
            "is_feasible": feasible,
            "runtime_seconds": 0.1 + i,
            "cost": score,
        }
        for i in range(cases)
    ]
    return {
        "total_score": score,
        "test_results": test_results,
        "summary": {
            "num_feasible": cases if feasible else cases - 1,
            "avg_runtime": 0.2,
        },
    }


def test_compare_accepts_strictly_lower_fully_feasible_score():
    ok, messages = compare_results.compare(_result(score=2.0), _result(score=1.9))

    assert ok
    assert any("PASS" in message for message in messages)


def test_compare_rejects_equal_score_by_default():
    ok, messages = compare_results.compare(_result(score=2.0), _result(score=2.0))

    assert not ok
    assert any("candidate score is equal to baseline" in message for message in messages)


def test_compare_can_allow_equal_for_reproducibility_checks():
    ok, _ = compare_results.compare(_result(score=2.0), _result(score=2.0), allow_equal=True)

    assert ok


def test_compare_rejects_infeasible_candidate_even_when_score_is_lower():
    candidate = _result(score=1.5, feasible=False)

    ok, messages = compare_results.compare(_result(score=2.0), candidate)

    assert not ok
    assert any("not fully feasible" in message for message in messages)


def test_compare_rejects_truncated_candidate_result():
    baseline = _result(score=2.0, cases=3)
    candidate = copy.deepcopy(_result(score=1.5, cases=2))

    ok, messages = compare_results.compare(baseline, candidate)

    assert not ok
    assert any("expected at least 3" in message for message in messages)


def test_compare_reports_top_weighted_case_deltas():
    baseline = _result(score=2.0, cases=3)
    candidate = copy.deepcopy(baseline)
    candidate["total_score"] = 1.8
    candidate["test_results"][0]["cost"] = 1.5
    candidate["test_results"][1]["cost"] = 2.5
    candidate["test_results"][2]["cost"] = 1.2
    candidate["test_results"][2]["hpwl_gap"] = 0.3
    baseline["test_results"][2]["hpwl_gap"] = 0.5

    ok, messages = compare_results.compare(baseline, candidate)
    joined = "\n".join(messages)

    assert ok
    assert "Top weighted regressions:" in joined
    assert "Top weighted improvements:" in joined
    assert "test_id=1" in joined
    assert "test_id=2" in joined
    assert "hpwl_delta=-0.2000" in joined


def test_weighted_case_deltas_uses_high_block_cases_first():
    baseline = _result(score=2.0, cases=3)
    candidate = copy.deepcopy(baseline)
    # A smaller raw regression on the highest-block case should dominate.
    candidate["test_results"][0]["cost"] = 4.0
    candidate["test_results"][2]["cost"] = 3.0

    regressions, _ = compare_results.weighted_case_deltas(baseline, candidate, top=2)

    assert regressions[0].startswith("test_id=2")
