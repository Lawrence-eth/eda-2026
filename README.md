# ICCAD 2026 FloorSet Optimizer Baseline

This repository contains the autonomous workspace output for an ICCAD 2026 FloorSet contest optimizer baseline.

The work turns the provided contest PDFs and the official IntelLabs/FloorSet repository into a complete, runnable, feasibility-first optimizer. After review, the optimizer was improved from a simple shelf/perimeter baseline into a cluster-aware constructive heuristic.

## Final local validation result

Validation set: LiteTensorDataTest, 100 cases.

- Feasible layouts: 100 / 100
- Total score: 5.6087
- Average cost: 3.9135
- Average runtime: 0.1907 seconds
- Average HPWL gap: 1.6257
- Average area gap: 1.4171
- Average soft violation ratio: 0.1722
- Worst per-case cost: 7.8052
- Unit tests: 2 / 2 passed
- Official validator: PASSED

Lower score is better under the contest cost function. This is still a heuristic baseline, but it is materially stronger than the first valid version, which scored around 9.76-9.84 locally.

## Repository contents

```text
contest_solution/
  my_optimizer.py          Main optimizer implementation
  test_my_optimizer.py     Feasibility/unit tests created during development

docs/extracted/
  C_20260325.txt           Extracted text from the contest problem PDF
  Problem C_QA_0508.txt    Extracted text from the contest Q&A PDF

results/
  summary.json             Compact result summary
  boundary_full.json        Full local evaluation JSON output

scripts/
  setup_and_evaluate.sh    Helper script for reproducing evaluation after cloning FloorSet

PROJECT_STATUS.md          Detailed work log and final status from the development workspace
```

## What was done

1. Created an independent Linux workspace.
2. Set up a Python 3.12 virtual environment because Ubuntu 24.04 requires virtual environments for Python package management.
3. Installed the required dependencies, including PyTorch, Shapely, PyMuPDF, and pytest.
4. Extracted text from two provided PDFs:
   - contest problem specification
   - contest Q&A document
5. Cloned and inspected the official `IntelLabs/FloorSet` repository.
6. Downloaded the Lite validation dataset through the repository's data script.
7. Ran the template optimizer and confirmed it failed feasibility.
8. Implemented a feasibility-first optimizer in `my_optimizer.py`.
9. Added test coverage for important feasibility constraints.
10. Ran full local validation on 100 cases.
11. Used review feedback to identify score bottlenecks: boundary, grouping, HPWL, and area penalties.
12. Improved the optimizer with cluster-aware macro packing, systematic perimeter construction, faster degree precomputation, and tuned row-width parameters.
13. Saved final metrics and documentation.

## Optimizer approach

The current optimizer is a feasibility-first constructive floorplanning heuristic.

Main ideas:

- Preserve all preplaced blocks exactly.
- Preserve fixed/preplaced dimensions.
- Preserve soft-block target areas.
- Prevent overlaps through constructive legal placement.
- Prioritize hard constraints before cost optimization.
- Place movable boundary-constrained blocks on a constructed perimeter frame.
- Normalize Multi-Instantiation Block dimensions when target-area constraints allow it.
- Pack non-boundary cluster groups as connected macro-blocks to reduce grouping violations.
- Use compact cluster-local shelf packing so connected groups are not forced into one very long row.
- Precompute connectivity degrees for runtime efficiency.
- Tune cluster-local and global row widths through repeated full validation runs.

## Improvement over the first baseline

The first working baseline was valid but weak:

- Feasible: 100 / 100
- Total score: about 9.76-9.84
- Average cost: about 6.75
- Average soft violation ratio: about 0.4142

The improved version:

- Feasible: 100 / 100
- Total score: 5.6087
- Average cost: 3.9135
- Average soft violation ratio: 0.1722

Soft-constraint totals improved approximately from:

- boundary violations: 464 -> 122
- grouping violations: 1422 -> 581
- MIB violations: 55 -> 55

The remaining boundary violations are mainly preplaced boundary-constrained blocks, which cannot be moved without violating hard preplacement constraints. The remaining MIB violations are from groups whose target areas do not allow one common shape without causing hard area violations.

## Reproduction instructions

This repository intentionally does not vendor the entire official contest repository or the downloaded dataset. To reproduce the run, clone the official FloorSet repository, copy the optimizer into the contest folder, download the Lite dataset, and run the evaluator.

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

## Notes

- The optimizer is designed to be reliable and fast before being aggressive.
- Further improvements should focus on clusters that contain boundary-constrained blocks, local swap/shift search, and analytical placement before legalization.
- The validation data and original contest repository should be obtained from their official sources.
