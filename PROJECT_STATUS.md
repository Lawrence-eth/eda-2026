# Project Status

## Completed

- Added a feasibility-first optimizer for the ICCAD 2026 FloorSet validation environment.
- Added local unit tests for hard constraints and output shape.
- Preserved exact preplaced coordinates and fixed/preplaced dimensions.
- Preserved soft-block target areas and overlap-free placement.
- Added perimeter handling for movable boundary-constrained blocks.
- Added cluster-aware macro packing for non-boundary clusters.
- Added boundary-aware packing for same-edge boundary clusters, placing boundary members on the required edge and packing cluster mates inward.
- Published local validation artifacts in `results/`.

## Current Optimizer

The optimizer is a constructive heuristic:

- keeps preplaced blocks at exact required `(x, y, w, h)`;
- keeps fixed/preplaced dimensions exact;
- preserves soft-block areas;
- avoids overlaps;
- builds a final perimeter frame for movable boundary-constrained blocks;
- normalizes MIB dimensions when target areas allow it;
- packs non-boundary cluster groups as connected macro-blocks;
- packs same-edge boundary clusters as perimeter macro-blocks when this is beneficial for the validation-size range;
- uses connectivity-weighted ordering and tuned shelf widths for score/runtime balance.

## Validation Results

Final local validation over 100 Lite validation cases:

- Feasible: 100 / 100
- Total score: 5.0922
- Average cost: 3.7407
- Average runtime: 0.2092s
- Average HPWL gap: 1.6636
- Average area gap: 1.6517
- Average soft violation ratio: 0.1392
- Worst per-case cost: 7.1122
- Tests: 2 / 2 passed
- Official validator: PASSED

Result file:

- `results/boundary_full.json`

## Implementation Notes

The implementation targets the main local validation cost drivers:

1. hard feasibility;
2. grouping constraints;
3. boundary constraints;
4. MIB shape consistency where compatible with area targets;
5. HPWL gap;
6. bounding-box area gap;
7. runtime.

Soft-constraint diagnostics on the final 100-case validation run:

- boundary violations: 122 total
- grouping violations: 436 total
- MIB violations: 55 total

Remaining violations are mostly hard-constraint tradeoffs. Preplaced blocks cannot be moved to satisfy a soft boundary condition without breaking fixed preplacement. Some MIB groups also have target areas that do not allow one exact common shape without creating hard area violations.

## Useful Commands

From the contest directory after copying `contest_solution/my_optimizer.py` into place:

```bash
python -m pytest test_my_optimizer.py -q
PYTHONPATH=.. python iccad2026_evaluate.py --validate my_optimizer.py --quick
PYTHONPATH=.. python iccad2026_evaluate.py --evaluate my_optimizer.py --verbose --save-solutions --output results/boundary_full.json
```

## Next Improvement Ideas

- Post-placement local search for unit swaps/shifts to reduce HPWL without increasing soft violations.
- Analytical placement or force-directed ordering before legalization.
- More advanced MIB handling for groups with incompatible target areas.
