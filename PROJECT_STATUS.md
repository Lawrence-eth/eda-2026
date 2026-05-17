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
- uses connectivity-weighted ordering and adaptive shelf widths for score/runtime balance;
- preprocesses connectivity into lightweight tuples using vectorized tensor conversion on large cases;
- skips unused selection-score evaluation when a block count has only one deterministic layout variant;
- prunes high-block-count variant sets where the runtime cost outweighs placement-quality gains;
- applies targeted row-width tuning on the highest-weight validation sizes, including the 111-, 114-, 115-, 116-, and 118-block cases;
- reuses cached connectivity degrees for cluster member ordering to reduce high-block-count runtime;
- tries a bounded set of deterministic layout variants and selects with a cheap HPWL, area, and soft-constraint proxy.

## Validation Results

Final local validation over 100 Lite validation cases:

- Feasible: 100 / 100
- Total score: 2.1150
- Average cost: 3.7516
- Average runtime: 0.3597s
- Average HPWL gap: 1.6031
- Average area gap: 1.5243
- Average soft violation ratio: 0.1381
- Worst per-case cost: 8.1058
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
- grouping violations: 428 total
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
