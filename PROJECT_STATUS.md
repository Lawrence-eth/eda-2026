# Project Status

Workspace: `/home/ubuntu/independent-workspace/new-project`

## Completed

- Created independent project workspace.
- Uploaded and extracted contest PDFs:
  - `Temp/C_20260325.pdf`
  - `Temp/Problem C_QA_0508.pdf`
  - extracted text in `extracted/`
- Cloned IntelLabs FloorSet contest code:
  - `external/FloorSet/iccad2026contest/`
- Created Python virtual environment:
  - `.venv/`
- Installed contest dependencies and pytest.
- Downloaded validation dataset:
  - `external/FloorSet/LiteTensorDataTest/`
- Created optimizer:
  - `external/FloorSet/iccad2026contest/my_optimizer.py`
- Created tests:
  - `external/FloorSet/iccad2026contest/test_my_optimizer.py`
- Improved the first feasible baseline after external-agent review.

## Current Optimizer

The optimizer is now a faster and stronger feasibility-first constructive heuristic:

- keeps preplaced blocks at exact required `(x, y, w, h)`;
- keeps fixed/preplaced dimensions exact;
- preserves soft-block areas;
- avoids overlaps;
- builds a final perimeter frame for movable boundary-constrained blocks;
- normalizes MIB dimensions when target areas allow it;
- packs non-boundary cluster groups as connected macro-blocks to reduce grouping violations;
- uses compact cluster-local shelf packing and tuned global row width for better score/runtime balance.

## Validation Results

Earlier baseline:

- Feasible: 100 / 100
- Average cost: about 6.75
- Total score: about 9.76–9.84, depending on runtime noise
- Average runtime: about 0.05s

Improved final local validation over 100 Lite validation cases:

- Feasible: 100 / 100
- Total score: 5.6087
- Average cost: 3.9135
- Average runtime: 0.1907s
- Average HPWL gap: 1.6257
- Average area gap: 1.4171
- Average soft violation ratio: 0.1722
- Worst per-case cost: 7.8052
- Tests: 2 / 2 passed
- Official validator: PASSED

Result file:

- `/home/ubuntu/independent-workspace/final_best_full.json`

Solutions file:

- `/home/ubuntu/independent-workspace/new-project/external/FloorSet/iccad2026contest/my_optimizer_solutions.json`

## Improvement Summary

The review correctly identified that the original solution was mostly shelf/perimeter packing and that the score was dominated by soft-constraint penalties. I addressed that by:

1. replacing the misleading documentation about candidate-point placement;
2. adding cluster-aware macro packing for non-boundary cluster groups;
3. making the perimeter construction more systematic for movable boundary blocks;
4. optimizing runtime by precomputing connectivity degrees instead of repeatedly scanning edge lists;
5. tuning cluster-local and global row-width factors through repeated full validation runs.

Soft-constraint diagnostics improved from approximately:

- boundary violations: 464 total
- grouping violations: 1422 total
- MIB violations: 55 total

To approximately:

- boundary violations: 122 total
- grouping violations: 581 total
- MIB violations: 55 total

The remaining boundary violations are primarily preplaced boundary-constrained blocks, which cannot be moved without breaking hard preplacement constraints. The remaining MIB violations come from groups whose target areas do not allow a common shape without creating hard area violations.

## Useful Commands

From contest directory:

```bash
cd /home/ubuntu/independent-workspace/new-project/external/FloorSet/iccad2026contest
../../../.venv/bin/python -m pytest test_my_optimizer.py -q
PYTHONPATH=.. ../../../.venv/bin/python iccad2026_evaluate.py --validate my_optimizer.py --quick
PYTHONPATH=.. ../../../.venv/bin/python iccad2026_evaluate.py --evaluate my_optimizer.py --verbose --save-solutions --output /home/ubuntu/independent-workspace/final_best_full.json
```

## Next Improvement Ideas

- Better handling of clusters that contain boundary-constrained blocks.
- Post-placement local search for unit swaps/shifts to reduce HPWL without increasing soft violations.
- Analytical placement or force-directed ordering before legalization.
- Case-specific boundary anchoring that respects preplaced boundary blocks without causing overlaps.
