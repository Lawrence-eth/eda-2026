# ICCAD 2026 FloorSet Optimizer

This repository contains a runnable optimizer implementation for the ICCAD 2026 FloorSet contest environment.

The solution is designed around hard-constraint correctness first, then placement quality. It preserves required block dimensions and areas, keeps preplaced blocks fixed, avoids overlap, handles boundary constraints, and reduces soft-constraint penalties through cluster-aware constructive placement.

## Final local validation result

Validation set: LiteTensorDataTest, 100 cases.

- Feasible layouts: 100 / 100
- Total score: 1.5221
- Average cost: 3.7788
- Average runtime: 1.5356 seconds
- Average HPWL gap: 1.5442
- Average area gap: 1.5097
- Average soft violation ratio: 0.1255
- Worst per-case cost: 8.7869
- Unit tests: 2 / 2 passed
- Public regression tests: 52 / 52 passed
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
  enriched_diagnostics.json Full diagnostic copy with reconstructed soft-violation attribution
  focus_cases.json          Compact weighted-case and sensitivity planning report

scripts/
  setup_and_evaluate.sh    Helper script for reproducing evaluation after cloning FloorSet
  analyze_results.py       Case-level diagnostics for full validation JSON outputs
  compare_results.py       Publication guard and weighted-delta report for candidate result JSON files
  audit_results.py         Result artifact geometry, integrity, and score-consistency audit before publication
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
- targeted high-block-count row-width tuning, including retuned 116- through 119-block settings from validation sweeps;
- obstacle-aware interior shelf packing for 116-block and larger preplaced cases, allowing movable units to use legal gaps around exact preplacements instead of being forced to the right of them;
- bounded post-placement translation of unconstrained cluster components to remove grouping splits without overlaps or bbox expansion;
- bounded post-placement shifts of unconstrained interior blocks on selected high-count cases to reduce incident wirelength without overlaps or bbox expansion;
- guarded participation of fixed-shape, non-preplaced interior blocks in the 117- through 119-block shift pass, preserving dimensions while reducing high-count HPWL;
- guarded combined-axis shift candidates for 116- through 119-block cases after independent overlap-free axis clamps;
- a trimmed 120-block interior shift pass over the highest-connectivity free blocks to improve the dominant weighted case while preserving runtime-cap behavior;
- guarded top-edge boundary compaction on the largest case when movable top-edge blocks can be pulled down without overlaps, soft-violation increase, or incident-wirelength regression;
- retuned 120-block row and large-cluster packing parameters to reduce the dominant weighted case HPWL and bounding-box area while preserving soft violations;
- incident-edge caches for boundary ordering on 116-block and larger cases, reducing score-dominant runtime while preserving layouts and median-runtime balance;
- a narrow equal-shape swap pass on 117- and 119-block cases to improve HPWL without changing soft violations;
- a 118-block-only boundary-line shift refinement that moves same-edge boundary rows or columns only when local wirelength improves without overlaps, bbox growth, or soft-violation increase;
- pre-resolved pin coordinates in free-block shift adjacency caches to reduce high-count local wirelength overhead without changing layouts;
- a bounded 120-block equal-shape swap probe that accepts up to two meaningful HPWL-improving swaps while preserving soft violations and bounding-box area;
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
- grouping violations: 366
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
python scripts/analyze_results.py results/boundary_full.json --diagnostic-sidecar results/enriched_diagnostics.json
python scripts/analyze_results.py results/boundary_full.json --write-focus-json results/focus_cases.json
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
The score-concentration section reports cumulative weight and score share for
the top weighted cases, making it clear when a candidate should be judged
primarily by the largest high-block-count instances rather than average cost.
The analyzer also estimates reconstructed-score pressure from small HPWL,
area, and soft-violation-ratio improvements, plus score-weighted soft-violation
drivers when enriched boundary/grouping/MIB counts are available. When a
compatible `results/enriched_diagnostics.json` companion exists, the analyzer
merges those derived fields into the in-memory report automatically; use
`--no-auto-sidecar` to inspect the raw evaluator JSON alone.
Use `--write-focus-json` to save a compact planning artifact with the dominant
score range, score concentration, metric-pressure estimates, recommendation,
top weighted cases, and top local-sensitivity cases. The committed
`results/focus_cases.json` tracks the current published best result and is
intended for experiment planning; it does not replace the published
best-result JSON.
The test harness keeps repository-local scripts importable under both
`pytest` and `python -m pytest` so diagnostics can be checked consistently
across local shells and CI.

Use `scripts/compare_results.py` before publishing a solver update. It requires
the candidate result to remain fully feasible according to per-case records,
include every baseline `test_id`, avoid duplicate candidate IDs, include at
least the baseline case count, and strictly lower `total_score` unless
`--allow-equal` is used for a reproducibility check. It reconstructs both
baseline and candidate weighted scores from the per-case costs before comparing
them, so stale or hand-edited `total_score` fields fail before publication. It
also reports the top weighted per-case regressions and improvements, including
HPWL, area, soft-violation, and runtime deltas, so a candidate run can be
debugged without manually diffing the full JSON.

Use `scripts/audit_results.py` before replacing a published result artifact. It
checks that result JSON files have unique case IDs, finite nonnegative metrics,
summary counts that match the case list, full feasibility by default, and valid
saved non-overlapping `[x, y, w, h]` rectangles when positions are present. This
guard also reconstructs the block-count weighted total score and verifies
published summary averages when present, catching malformed, stale, or partial
evaluator outputs before score comparison.

Use `scripts/check_public_release.py` as the final local publication gate. It
runs the result audit, audits any candidate result passed with `--candidate`,
scans public-facing docs for blocked process wording and sensitive terms, and
can compare the public optimizer copy against an active contest checkout with
`--contest-optimizer`.

When an official FloorSet checkout with validation data is available, the analyzer can also reconstruct per-case boundary, grouping, and MIB violation counts from the saved positions:

```bash
python scripts/analyze_results.py results/boundary_full.json \
  --contest-dir external/FloorSet/iccad2026contest
```

Use the same Python environment as the official evaluator for this enriched mode.
The enriched report also adds structural case profiles for the weighted focus
cases, including fixed/preplaced block counts, boundary demand, cluster and MIB
group pressure, and B2B/P2B net counts. This helps distinguish whether the next
solver experiment should focus on perimeter ordering, cluster packing,
connectivity-aware placement, or soft-constraint repair.
To keep the published best-result artifact unchanged while saving the enriched
attribution for later debugging, write a separate diagnostic copy:

```bash
python scripts/analyze_results.py results/boundary_full.json \
  --contest-dir external/FloorSet/iccad2026contest \
  --write-enriched results/enriched_diagnostics.json
```

The committed `results/enriched_diagnostics.json` preserves the published
score and summary while adding per-case boundary, grouping, MIB, and structural
constraint fields for diagnostics.

## Next improvement directions

- Local swap/shift refinement to reduce HPWL without increasing soft violations.
- Analytical or force-directed placement before legalization.
- Better MIB handling for groups with incompatible target areas.
