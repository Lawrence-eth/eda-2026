import math
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent))
from iccad2026_evaluate import check_overlap, check_area_tolerance, check_dimension_hard_constraints
from my_optimizer import MyOptimizer


def test_optimizer_keeps_preplaced_blocks_exact_and_avoids_overlap():
    opt = MyOptimizer()
    block_count = 4
    area_targets = torch.tensor([100.0, 25.0, 36.0, 49.0])
    b2b = torch.empty((0, 3))
    p2b = torch.empty((0, 3))
    pins = torch.empty((0, 2))
    constraints = torch.zeros((block_count, 5))
    constraints[0, 1] = 1  # preplaced
    target_positions = torch.full((block_count, 4), -1.0)
    target_positions[0] = torch.tensor([10.0, 20.0, 10.0, 10.0])

    pos = opt.solve(block_count, area_targets, b2b, p2b, pins, constraints, target_positions)

    assert len(pos) == block_count
    assert pos[0] == (10.0, 20.0, 10.0, 10.0)
    assert check_overlap(pos) == 0
    assert check_area_tolerance(pos, area_targets, skip_indices={0}) == 0
    assert check_dimension_hard_constraints(pos, target_positions, constraints, block_count) == 0


def test_optimizer_uses_exact_fixed_dimensions():
    opt = MyOptimizer()
    block_count = 3
    area_targets = torch.tensor([100.0, 64.0, 81.0])
    b2b = torch.empty((0, 3))
    p2b = torch.empty((0, 3))
    pins = torch.empty((0, 2))
    constraints = torch.zeros((block_count, 5))
    constraints[1, 0] = 1  # fixed shape
    target_positions = torch.full((block_count, 4), -1.0)
    target_positions[1, 2] = 4.0
    target_positions[1, 3] = 16.0

    pos = opt.solve(block_count, area_targets, b2b, p2b, pins, constraints, target_positions)

    assert math.isclose(pos[1][2], 4.0)
    assert math.isclose(pos[1][3], 16.0)
    assert check_overlap(pos) == 0
    assert check_dimension_hard_constraints(pos, target_positions, constraints, block_count) == 0
