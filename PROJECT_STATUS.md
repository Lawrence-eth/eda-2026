# Project Status

Workspace: `/home/ubuntu/independent-workspace/new-project`

## Completed

- Created independent project workspace.
- Extracted contest specification materials:
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
- Improved placement quality while preserving 100 / 100 feasibility.

## Current Optimizer

The optimizer is a feasibility-first constructive heuristic:

- keeps preplaced blocks at exact required `(x, y, w, h)`;
- keeps fixed/preplaced dimensions exact;
- preserves soft-block areas;
- avoids overlaps;
- builds a final perimeter frame for movable boundary-constrained blocks;
- normalizes MIB dimensions when target areas allow it;
- packs non-boundary cluster groups as connected macro-blocks to reduce grouping violations;
- uses compact cluster-local shelf packing and tuned global row width for better score/runtime balance.

## Validation Results

Final local validation over 100 Lite validation cases:

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

## Implementation Notes

The implementation targets the main local validation cost drivers:

1. hard feasibility;
2. boundary constraints;
3. grouping constraints;
4. MIB shape consistency where compatible with area targets;
5. HPWL gap;
6. bounding-box area gap;
7. runtime.

Soft-constraint diagnostics on the final 100-case validation run:

- boundary violations: 122 total
- grouping violations: 581 total
- MIB violations: 55 total

Remaining violations are mostly hard-constraint tradeoffs. Preplaced blocks cannot be moved to satisfy a soft boundary condition without breaking fixed preplacement. Some MIB groups also have target areas that do not allow one exact common shape without creating hard area violations.

## Useful Commands

From contest directory:

```bash
cd /home/ubuntu/independent-workspace/new-project/external/FloorSet/iccad2026contest
../../../.venv/bin/python -m pytest test_my_optimizer.py -q
PYTHONPATH=.. ../../../.venv/bin/python iccad2026_evaluate.py --validate my_optimizer.py --quick
PYTHONPATH=.. ../../../.venv/bin/python iccad2026_evaluate.py --evaluate my_optimizer.py --verbose --save-solutions --output /home/ubuntu/independent-workspace/final_best_full.json
```

## Next Improvement Ideas

- Boundary-aware cluster packing for clusters that contain boundary-constrained blocks.
- Post-placement local search for unit swaps/shifts to reduce HPWL without increasing soft violations.
- Analytical placement or force-directed ordering before legalization.
- More advanced MIB handling for groups with incompatible target areas.
