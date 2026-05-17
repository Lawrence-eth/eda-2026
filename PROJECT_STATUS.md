# Project Status

## Completed

- Added a feasibility-first optimizer for the ICCAD 2026 FloorSet validation environment.
- Added local unit tests for hard constraints and output shape.
- Preserved exact preplaced coordinates and fixed/preplaced dimensions.
- Preserved soft-block target areas and overlap-free placement.
- Added perimeter handling for movable boundary-constrained blocks.
- Added compact perimeter placement to remove unnecessary spacing around the final boundary frame.
- Added cluster-aware macro packing for non-boundary clusters.
- Added boundary-aware packing for same-edge boundary clusters, placing boundary members on the required edge and packing cluster mates inward.
- Added connectivity-aware ordering for movable boundary blocks on each perimeter edge.
- Published local validation artifacts in `results/`.
- Added `scripts/analyze_results.py` for case-level score diagnostics, weighted-contribution analysis, and block-count range summaries.
- Added optional official-evaluator enrichment to `scripts/analyze_results.py` so saved full results can show per-case boundary, grouping, and MIB violation counts without rerunning the optimizer.
- Added analyzer regression tests covering weighted-score reconstruction and soft-violation reporting.
- Added standalone optimizer-helper regression tests for boundary/corner accounting, grouping connectedness, MIB dimension normalization, and boundary-cluster local packing.

## Current Optimizer

The optimizer is a constructive heuristic:

- keeps preplaced blocks at exact required `(x, y, w, h)`;
- keeps fixed/preplaced dimensions exact;
- preserves soft-block areas;
- avoids overlaps;
- builds a final perimeter frame for movable boundary-constrained blocks;
- compacts the perimeter frame against the interior layout without introducing overlaps;
- normalizes MIB dimensions when target areas allow it;
- packs non-boundary cluster groups as connected macro-blocks;
- packs same-edge boundary clusters as perimeter macro-blocks when this is beneficial for the validation-size range;
- orders movable perimeter blocks by nearby pins and already placed connected blocks while keeping clustered boundary members consecutive;
- uses connectivity-weighted ordering and adaptive shelf widths for score/runtime balance;
- preprocesses connectivity into lightweight tuples using vectorized tensor conversion on large cases;
- skips unused selection-score evaluation when a block count has only one deterministic layout variant;
- prunes high-block-count variant sets where the runtime cost outweighs placement-quality gains;
- applies targeted row-width tuning on the highest-weight validation sizes, including the 111-, 112-, 113-, 114-, 115-, 116-, and 118-block cases;
- reuses cached connectivity degrees for cluster member ordering to reduce high-block-count runtime;
- tries a bounded set of deterministic layout variants and selects with a cheap HPWL, area, and soft-constraint proxy.

## Validation Results

Final local validation over 100 Lite validation cases:

- Feasible: 100 / 100
- Total score: 2.0528
- Average cost: 3.7306
- Average runtime: 1.5472s
- Average HPWL gap: 1.5280
- Average area gap: 1.4864
- Average soft violation ratio: 0.1261
- Worst per-case cost: 8.6318
- Tests: 2 / 2 passed
- Public regression tests: 7 / 7 passed
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
- grouping violations: 369 total
- MIB violations: 55 total

Remaining violations are mostly hard-constraint tradeoffs. Preplaced blocks cannot be moved to satisfy a soft boundary condition without breaking fixed preplacement. Some MIB groups also have target areas that do not allow one exact common shape without creating hard area violations.

## Useful Commands

From the contest directory after copying `contest_solution/my_optimizer.py` into place:

```bash
python -m pytest test_my_optimizer.py -q
PYTHONPATH=.. python iccad2026_evaluate.py --validate my_optimizer.py --quick
PYTHONPATH=.. python iccad2026_evaluate.py --evaluate my_optimizer.py --verbose --save-solutions --output results/boundary_full.json
```

From the repository root:

```bash
python scripts/analyze_results.py results/boundary_full.json
python scripts/analyze_results.py results/boundary_full.json --contest-dir external/FloorSet/iccad2026contest
python -m pytest tests/test_analyze_results.py tests/test_optimizer_soft_constraints.py -q
```

## Next Improvement Ideas

- Post-placement local search for unit swaps/shifts to reduce HPWL without increasing soft violations.
- Analytical placement or force-directed ordering before legalization.
- More advanced MIB handling for groups with incompatible target areas.
- Use the optimizer-helper regression tests as guardrails before changing boundary-cluster packing, grouping, or MIB heuristics.
