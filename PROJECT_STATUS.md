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

## Current Optimizer

The optimizer is a fast feasibility-first constructive heuristic:

- keeps preplaced blocks at exact required `(x, y, w, h)`;
- keeps fixed/preplaced dimensions exact;
- preserves soft-block areas;
- avoids overlaps;
- places boundary-constrained blocks on the perimeter when possible;
- normalizes MIB dimensions when target areas allow it.

## Validation Results

Full local validation over 100 cases:

- Feasible: 100 / 100
- Average cost: 6.7683
- Total score: 9.8350
- Average runtime: 0.0481s

Result file:

- `/home/ubuntu/independent-workspace/boundary_full.json`

Solutions file:

- `/home/ubuntu/independent-workspace/new-project/external/FloorSet/iccad2026contest/my_optimizer_solutions.json`

## Useful Commands

From contest directory:

```bash
cd /home/ubuntu/independent-workspace/new-project/external/FloorSet/iccad2026contest
../../../.venv/bin/python -m pytest test_my_optimizer.py -q
../../../.venv/bin/python iccad2026_evaluate.py --validate my_optimizer.py
../../../.venv/bin/python iccad2026_evaluate.py --evaluate my_optimizer.py --verbose --save-solutions --output ../../../../boundary_full.json
```
