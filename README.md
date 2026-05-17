# ICCAD 2026 FloorSet Optimizer

This repository contains a runnable optimizer implementation for the ICCAD 2026 FloorSet contest environment.

The solution is designed around hard-constraint correctness first, then placement quality. It preserves required block dimensions and areas, keeps preplaced blocks fixed, avoids overlap, handles boundary constraints, and reduces soft-constraint penalties through cluster-aware constructive placement.

## Final local validation result

Validation set: LiteTensorDataTest, 100 cases.

- Feasible layouts: 100 / 100
- Total score: 2.0528
- Average cost: 3.7306
- Average runtime: 1.5472 seconds
- Average HPWL gap: 1.5280
- Average area gap: 1.4864
- Average soft violation ratio: 0.1261
- Worst per-case cost: 8.6318
- Unit tests: 2 / 2 passed
- Public regression tests: 30 / 30 passed with contest dependencies
- Official validator: PASSED

Lower score is better under the contest cost function.

## Repository contents

```text
contest_solution/
  my_optimizer.py          Main optimizer implementation
  test_my_optimizer.py     Local feasibility/unit tests with public fallback checks

tests/
  test_analyze_results.py  Regression tests for result diagnostics
  test_optimizer_soft_constraints.py
                           Standalone optimizer-helper regression tests

docs/extracted/
  C_20260325.txt           Extracted text from the contest specification PDF
  Problem C_QA_0508.txt    Extracted text from the contest Q&A PDF

results/
  summary.json             Compact result summary
  boundary_full.json        Full local evaluation JSON output

scripts/
  setup_and_evaluate.sh    Helper script for reproducing evaluation after cloning FloorSet
  analyze_results.py       Case-level diagnostics for full validation JSON outputs
  compare_results.py       Publication guard and weighted-delta report for candidate result JSON files
  audit_results.py         Result artifact integrity and score-consistency audit before publication
  check_public_release.py  Combined release guard for result audit, docs scan, and optimizer sync

PROJECT_STATUS.md          Development status and reproducibility notes
```

## Implementation summary

The optimizer uses a feasibility-first constructive floorplanning strategy.

Main components:

- exact preservation of preplaced block coordinates and dimensions;
- exact preservation of fixed/preplaced dimensions;
- exact soft-block target areas;
- overlap-free constructive placement;
- perimeter placement for movable boundary-constrained blocks;
- compact perimeter placement without artificial spacing around the final frame;
- connectivity-aware ordering for boundary blocks along each perimeter edge;
- boundary-aware cluster packing for same-edge boundary clusters;
- MIB dimension normalization when target-area constraints allow a shared shape;
- cluster-aware macro packing for non-boundary cluster groups;
- adaptive cluster-local shelf packing to avoid long, sparse group chains on large cases;
- bounded adaptive layout variants selected by a cheap HPWL, area, and soft-constraint proxy;
- direct construction for single-variant cases to avoid unused selection-score work;
- runtime-aware variant pruning on high-block-count cases;
- cached connectivity degrees for efficient ordering within cluster packing;
- vectorized connectivity preprocessing for large validation cases;
- targeted high-block-count row-width tuning, including the 111-, 112-, 113-, 114-, 115-, 116-, and 118-block validation sizes;
- tuned row-width parameters for score/runtime balance.

## Quality improvements

The current implementation focuses on reducing the main soft-constraint and placement-quality costs:

- boundary constraint violations;
- grouping constraint violations;
- MIB shape consistency where feasible;
- HPWL gap;
- bounding-box area gap;
- runtime penalty.

Soft-constraint diagnostics on the 100-case validation run:

- boundary violations: 122
- grouping violations: 369
- MIB violations: 55

Some remaining violations are caused by tradeoffs with hard constraints. For example, preplaced blocks cannot be moved to satisfy a soft boundary condition if that would break the required preplacement, and some MIB groups have incompatible target areas for one exact common shape.

The public regression suite also includes standalone tests for optimizer-local
boundary/corner accounting, grouping connectedness, MIB dimension normalization,
and boundary-cluster packing. These tests are intended as guardrails for future
score-focused solver changes. The copied contest smoke tests use official
evaluator helpers when available and otherwise fall back to equivalent local
checks. Torch-dependent optimizer tests are skipped automatically when Torch is
not installed, so diagnostics and result-guard tests can still run after a plain
clone.

## Reproduction instructions

This repository does not vendor the full official contest repository or the downloaded dataset. To reproduce the run, clone the official FloorSet repository, copy the optimizer into the contest folder, download the Lite dataset, and run the evaluator.

Example:

```bash
git clone https://github.com/IntelLabs/FloorSet.git external/FloorSet
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install torch shapely pymupdf pytest
cp contest_solution/my_optimizer.py external/FloorSet/iccad2026contest/my_optimizer.py
cp contest_solution/test_my_optimizer.py external/FloorSet/iccad2026contest/test_my_optimizer.py
cd external/FloorSet
PYTHONPATH=. python lite_dataset_test.py
cd iccad2026contest
PYTHONPATH=.. ../../../.venv/bin/python -m pytest test_my_optimizer.py -q
PYTHONPATH=.. ../../../.venv/bin/python iccad2026_evaluate.py --validate my_optimizer.py --quick
PYTHONPATH=.. ../../../.venv/bin/python iccad2026_evaluate.py --evaluate my_optimizer.py --verbose --save-solutions --output ../../../results/boundary_full.json
```

Or use:

```bash
bash scripts/setup_and_evaluate.sh
```

## Result analysis

After generating `results/boundary_full.json`, use the analysis helper to identify the cases that matter most for the next optimization cycle:

```bash
python scripts/analyze_results.py
python scripts/analyze_results.py results/boundary_full.json --top 30
python scripts/audit_results.py results/boundary_full.json --expected-cases 100 --require-positions
python scripts/compare_results.py results/boundary_full.json candidate_full.json
python scripts/check_public_release.py
python -m pytest -q
```

In an environment without Torch, `python -m pytest -q` still runs the
dependency-light diagnostics and comparison tests and skips the optimizer
tests that require contest tensor inputs. Use the contest environment for the
full 18-test regression suite before publishing solver changes.

The report prints the worst cases by raw cost, the worst weighted contributors to the total score, aggregate metrics by block-count range, and a recommended next target such as HPWL, area, grouping, boundary, MIB, runtime, tests, or documentation.
Small nonzero weighted contributions are printed in scientific notation, and
the range summary includes reconstructed score contribution, score share,
weight share, and the highest-impact case in each block-count range.
The test harness keeps repository-local scripts importable under both
`pytest` and `python -m pytest` so diagnostics can be checked consistently
across local shells and CI.

Use `scripts/compare_results.py` before publishing a solver update. It requires
the candidate result to remain fully feasible, include every baseline `test_id`,
include at least the baseline case count, and strictly lower `total_score` unless
`--allow-equal` is used for a reproducibility check. It also reports the top
weighted per-case regressions and improvements, including HPWL, area,
soft-violation, and runtime deltas, so a candidate run can be debugged without
manually diffing the full JSON.

Use `scripts/audit_results.py` before replacing a published result artifact. It
checks that result JSON files have unique case IDs, finite nonnegative metrics,
summary counts that match the case list, full feasibility by default, and valid
saved `[x, y, w, h]` rectangles when `--require-positions` is enabled. This
guard also reconstructs the block-count weighted total score and verifies
published summary averages when present, catching malformed, stale, or partial
evaluator outputs before score comparison.

Use `scripts/check_public_release.py` as the final local publication gate. It
runs the result audit, scans public-facing docs for blocked process wording and
sensitive terms, and can compare the public optimizer copy against an active
contest checkout with `--contest-optimizer`.

When an official FloorSet checkout with validation data is available, the analyzer can also reconstruct per-case boundary, grouping, and MIB violation counts from the saved positions:

```bash
python scripts/analyze_results.py results/boundary_full.json \
  --contest-dir external/FloorSet/iccad2026contest
```

Use the same Python environment as the official evaluator for this enriched mode.
To keep the published best-result artifact unchanged while saving the enriched
attribution for later debugging, write a separate diagnostic copy:

```bash
python scripts/analyze_results.py results/boundary_full.json \
  --contest-dir external/FloorSet/iccad2026contest \
  --write-enriched results/enriched_diagnostics.json
```

## Next improvement directions

- Local swap/shift refinement to reduce HPWL without increasing soft violations.
- Analytical or force-directed placement before legalization.
- Better MIB handling for groups with incompatible target areas.
