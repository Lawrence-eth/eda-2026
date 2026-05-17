import json
from pathlib import Path

from scripts import check_public_release


def test_public_safe_scan_uses_word_boundaries(tmp_path):
    safe = tmp_path / "README.md"
    safe.write_text("Use PYTHONPATH for imports.\n", encoding="utf-8")

    ok, findings = check_public_release.scan_public_safe([safe])

    assert ok
    assert findings == []


def test_public_safe_scan_rejects_blocked_phrase_and_sensitive_word(tmp_path):
    unsafe = tmp_path / "PROJECT_STATUS.md"
    unsafe.write_text("after review, do not include a token here\n", encoding="utf-8")

    ok, findings = check_public_release.scan_public_safe([unsafe])

    assert not ok
    assert any("after review" in finding for finding in findings)
    assert any("token" in finding for finding in findings)


def test_optimizer_sync_detects_mismatch(tmp_path):
    public = tmp_path / "public.py"
    contest = tmp_path / "contest.py"
    public.write_text("x = 1\n", encoding="utf-8")
    contest.write_text("x = 2\n", encoding="utf-8")

    ok, messages = check_public_release.check_optimizer_sync(public, contest)

    assert not ok
    assert any("optimizer copies differ" in message for message in messages)


def test_run_checks_combines_audit_scan_and_sync(tmp_path, monkeypatch):
    result = tmp_path / "result.json"
    cases = [
        {
            "test_id": 0,
            "block_count": 21,
            "is_feasible": True,
            "cost": 2.0,
            "hpwl_gap": 0.5,
            "area_gap": 0.4,
            "violations_relative": 0.1,
            "runtime_seconds": 0.02,
            "error": None,
            "positions": [[float(i), 0.0, 1.0, 1.0] for i in range(21)],
        }
    ]
    result.write_text(
        json.dumps(
            {
                "total_score": 2.0,
                "summary": {"num_tests": 1, "num_feasible": 1, "avg_cost": 2.0, "avg_runtime": 0.02},
                "test_results": cases,
            }
        ),
        encoding="utf-8",
    )
    optimizer = tmp_path / "my_optimizer.py"
    optimizer.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(check_public_release, "DEFAULT_SCAN_PATHS", (tmp_path,))

    ok, messages = check_public_release.run_checks(
        result_json=result,
        expected_cases=1,
        max_score=2.0,
        require_positions=True,
        public_optimizer=optimizer,
        contest_optimizer=optimizer,
        candidate_json=None,
    )

    assert ok
    assert "result_audit=PASS" in messages
    assert "public_safe_scan=PASS" in messages
    assert "optimizer_sync=PASS" in messages
