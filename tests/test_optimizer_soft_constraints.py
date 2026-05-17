import importlib
import math
import sys
import types
from pathlib import Path

import torch


def _load_optimizer():
    """Import the public optimizer with a tiny evaluator stub.

    The contest checkout provides iccad2026_evaluate.py at evaluation time.
    These regression tests exercise optimizer-local helpers, so a minimal stub
    keeps the public test suite runnable without vendoring the official repo.
    """

    if "iccad2026_evaluate" not in sys.modules:
        stub = types.ModuleType("iccad2026_evaluate")

        class FloorplanOptimizer:
            def __init__(self, verbose=False):
                self.verbose = verbose

        stub.FloorplanOptimizer = FloorplanOptimizer
        stub.calculate_bbox_area = lambda positions: 0.0
        stub.calculate_hpwl_b2b = lambda positions, conn: 0.0
        stub.calculate_hpwl_p2b = lambda positions, conn, pins: 0.0
        sys.modules["iccad2026_evaluate"] = stub

    solution_dir = Path(__file__).resolve().parents[1] / "contest_solution"
    sys.path.insert(0, str(solution_dir))
    return importlib.import_module("my_optimizer").MyOptimizer


MyOptimizer = _load_optimizer()


def _constraints(block_count):
    return torch.zeros((block_count, 5), dtype=torch.float32)


def test_group_components_require_shared_edge_not_corner_touch():
    opt = MyOptimizer()
    positions = [
        (0.0, 0.0, 2.0, 2.0),
        (2.0, 0.0, 3.0, 2.0),
        (5.0, 2.0, 1.0, 1.0),
    ]

    assert opt._group_components(positions, [0, 1, 2]) == 2


def test_soft_violation_count_handles_exact_corners_and_edges():
    opt = MyOptimizer()
    constraints = _constraints(3)
    constraints[0, 4] = 5   # left + top
    constraints[1, 4] = 8   # bottom
    constraints[2, 4] = 2   # right
    positions = [
        (0.0, 2.0, 2.0, 1.0),
        (0.0, 0.0, 2.0, 2.0),
        (2.0, 0.0, 1.0, 3.0),
    ]

    assert opt._soft_violation_count(positions, constraints) == 0

    shifted = [(0.25, 2.0, 2.0, 1.0), positions[1], positions[2]]
    assert opt._soft_violation_count(shifted, constraints) == 1


def test_mib_dimensions_normalize_only_when_areas_are_compatible():
    opt = MyOptimizer()
    target_positions = torch.full((2, 4), -1.0)
    constraints = _constraints(2)
    constraints[:, 2] = 1

    compatible = opt._choose_dimensions(2, torch.tensor([100.0, 100.5]), constraints, target_positions)
    assert compatible[0] == compatible[1]
    assert math.isclose(compatible[0][0] * compatible[0][1], 100.25)

    incompatible = opt._choose_dimensions(2, torch.tensor([100.0, 121.0]), constraints, target_positions)
    assert incompatible[0] != incompatible[1]
    assert math.isclose(incompatible[0][0] * incompatible[0][1], 100.0)
    assert math.isclose(incompatible[1][0] * incompatible[1][1], 121.0)


def test_boundary_cluster_pack_keeps_edge_members_on_edge_and_mates_inward():
    opt = MyOptimizer()
    dims = [(2.0, 3.0), (1.5, 2.0), (4.0, 2.0)]
    area_targets = torch.tensor([6.0, 3.0, 8.0])

    local, unit_w, unit_h = opt._boundary_cluster_local_pack(
        bmembers=[0, 1],
        mates=[2],
        code=1,
        dims=dims,
        area_targets=area_targets,
        b2b_connectivity=torch.empty((0, 3)),
        p2b_connectivity=torch.empty((0, 3)),
    )

    assert local[0][0] == 0.0
    assert local[1][0] == 0.0
    assert local[2][0] >= max(dims[0][0], dims[1][0])
    assert unit_w >= local[2][0] + local[2][2]
    assert unit_h >= max(local[i][1] + local[i][3] for i in local)
    assert opt._group_components([local[i] for i in range(3)], [0, 1, 2]) == 1
