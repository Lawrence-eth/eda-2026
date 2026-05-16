# ICCAD 2026 FloorSet Optimizer Baseline

This repository contains the autonomous workspace output for an ICCAD 2026 FloorSet contest baseline optimizer.

The goal was to turn the provided contest PDFs and the official IntelLabs/FloorSet repository into a complete, runnable, feasibility-first optimizer baseline.

## Final local validation result

- Validation set: LiteTensorDataTest, 100 cases
- Feasible layouts: 100 / 100
- Average cost: 6.7683
- Total score: 9.8350
- Average runtime: 0.0481 seconds
- Unit tests: 2 / 2 passed

Lower score is better under the contest cost function. This is a valid and fast baseline, not a final contest-winning optimizer.

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
8. Implemented a constructive heuristic optimizer in `my_optimizer.py`.
9. Added test coverage for important feasibility constraints.
10. Iteratively improved placement quality and runtime.
11. Ran full local validation on 100 cases.
12. Saved final metrics and documentation.

## Optimizer approach

The implemented baseline is a feasibility-first constructive floorplanning heuristic.

Main ideas:

- Preserve all preplaced blocks exactly.
- Preserve fixed/preplaced dimensions.
- Preserve soft-block target areas.
- Prevent overlaps through legal placement checks.
- Prioritize hard constraints before cost optimization.
- Place boundary-constrained blocks on the chip perimeter when possible.
- Normalize Multi-Instantiation Block dimensions when target-area constraints allow it.
- Use a greedy candidate-point strategy instead of exhaustive search to keep runtime low.
- Rank movable blocks partly by connectivity so highly connected blocks are placed earlier.

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
PYTHONPATH=.. ../../../.venv/bin/python iccad2026_evaluate.py --validate my_optimizer.py
PYTHONPATH=.. ../../../.venv/bin/python iccad2026_evaluate.py --evaluate my_optimizer.py --verbose --save-solutions --output ../../../results/boundary_full.json
```

Or use:

```bash
bash scripts/setup_and_evaluate.sh
```

## Notes

- The optimizer is designed to be reliable and fast before being aggressive.
- Further improvements could include analytical/global placement and local post-processing swaps/shifts for lower HPWL and area cost.
- The validation data and original contest repository should be obtained from their official sources.
