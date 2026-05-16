#!/usr/bin/env python3
"""ICCAD 2026 FloorSet heuristic optimizer.

Fast feasibility-first constructive placer:
- exact preplaced coordinates and fixed/preplaced dimensions,
- exact soft-block areas,
- non-overlapping shelf placement,
- boundary-constrained blocks placed on the layout perimeter when possible,
- MIB groups normalized to a common shape when target areas allow it.
"""

import math
import sys
from pathlib import Path
from typing import List, Tuple

import torch

sys.path.insert(0, str(Path(__file__).parent))
from iccad2026_evaluate import FloorplanOptimizer, calculate_bbox_area, calculate_hpwl_b2b, calculate_hpwl_p2b

Rect = Tuple[float, float, float, float]


class MyOptimizer(FloorplanOptimizer):
    def __init__(self, verbose: bool = False):
        super().__init__(verbose)

    def solve(self, block_count: int, area_targets: torch.Tensor, b2b_connectivity: torch.Tensor,
              p2b_connectivity: torch.Tensor, pins_pos: torch.Tensor, constraints: torch.Tensor,
              target_positions: torch.Tensor = None) -> List[Rect]:
        dims = self._choose_dimensions(block_count, area_targets, constraints, target_positions)
        positions: List[Rect | None] = [None] * block_count
        preplaced = set()
        if constraints is not None and constraints.dim() > 1 and constraints.shape[1] > 1:
            for i in range(block_count):
                if constraints[i, 1] != 0 and self._has_xywh(target_positions, i):
                    positions[i] = tuple(float(target_positions[i, k]) for k in range(4))  # type: ignore[assignment]
                    preplaced.add(i)

        movable = [i for i in range(block_count) if i not in preplaced]
        boundary = {i: self._boundary_code(constraints, i) for i in movable}
        boundary_blocks = [i for i in movable if boundary[i] != 0]
        interior = [i for i in movable if boundary[i] == 0]
        interior = self._order_blocks(interior, area_targets, b2b_connectivity, p2b_connectivity)

        # First pack unconstrained/movable interior in a compact region disjoint
        # from preplaced blocks.
        placed_rects = [p for p in positions if p is not None]
        if placed_rects:
            start_x = max(p[0] + p[2] for p in placed_rects) + 1.0
            start_y = min(p[1] for p in placed_rects)
        else:
            start_x = 0.0
            start_y = 0.0
        for i, rect in self._shelf_pack(interior, dims, start_x, start_y).items():
            positions[i] = rect

        # Compute the content box before perimeter blocks.
        content = [p for p in positions if p is not None]
        if not content:
            content = [(0.0, 0.0, 1.0, 1.0)]
        cminx = min(p[0] for p in content)
        cminy = min(p[1] for p in content)
        cmaxx = max(p[0] + p[2] for p in content)
        cmaxy = max(p[1] + p[3] for p in content)

        leftish = [i for i in boundary_blocks if boundary[i] & 1]
        rightish = [i for i in boundary_blocks if boundary[i] & 2]
        topish = [i for i in boundary_blocks if boundary[i] & 4]
        bottomish = [i for i in boundary_blocks if boundary[i] & 8]
        gap = 1.0
        left_w = max((dims[i][0] for i in leftish), default=0.0)
        right_w = max((dims[i][0] for i in rightish), default=0.0)
        top_h = max((dims[i][1] for i in topish), default=0.0)
        bottom_h = max((dims[i][1] for i in bottomish), default=0.0)
        left_edge = cminx - left_w - gap if leftish else cminx
        right_edge = cmaxx + right_w + gap if rightish else cmaxx
        bottom_edge = cminy - bottom_h - gap if bottomish else cminy
        top_edge = cmaxy + top_h + gap if topish else cmaxy

        used = set()
        # Corners first. Contest data normally has at most one block per corner.
        corner_specs = [(5, left_edge, top_edge, 'tl'), (6, right_edge, top_edge, 'tr'),
                        (9, left_edge, bottom_edge, 'bl'), (10, right_edge, bottom_edge, 'br')]
        for code, ex, ey, kind in corner_specs:
            ids = [i for i in boundary_blocks if boundary[i] == code]
            for k, i in enumerate(ids):
                w, h = dims[i]
                x = ex if code & 1 else ex - w
                y = ey - h if code & 4 else ey
                # Additional same-corner blocks are shifted inward while keeping
                # one requested edge if exact corner sharing is impossible.
                if k:
                    x += (w + gap) * k if code & 1 else -(w + gap) * k
                positions[i] = (x, y, w, h)
                used.add(i)

        # Edge-only perimeter stacks/rows.
        y = bottom_edge + bottom_h + gap if bottomish else cminy
        for i in [j for j in leftish if j not in used]:
            w, h = dims[i]
            positions[i] = (left_edge, y, w, h)
            y += h
            used.add(i)
        y = bottom_edge + bottom_h + gap if bottomish else cminy
        for i in [j for j in rightish if j not in used]:
            w, h = dims[i]
            positions[i] = (right_edge - w, y, w, h)
            y += h
            used.add(i)
        x = left_edge + left_w + gap if leftish else cminx
        for i in [j for j in bottomish if j not in used]:
            w, h = dims[i]
            positions[i] = (x, bottom_edge, w, h)
            x += w
            used.add(i)
        x = left_edge + left_w + gap if leftish else cminx
        for i in [j for j in topish if j not in used]:
            w, h = dims[i]
            positions[i] = (x, top_edge - h, w, h)
            x += w
            used.add(i)

        # Any remaining unusual boundary code gets safe shelf placement.
        rest = [i for i in boundary_blocks if i not in used]
        if rest:
            safe_x = max(p[0] + p[2] for p in positions if p is not None) + gap
            for i, rect in self._shelf_pack(rest, dims, safe_x, cminy).items():
                positions[i] = rect

        if self._has_overlap([p for p in positions if p is not None]):
            # Absolute safety fallback: all non-preplaced blocks in a disjoint strip.
            ordered = self._order_blocks(movable, area_targets, b2b_connectivity, p2b_connectivity)
            safe_x = max((p[0] + p[2] for k, p in enumerate(positions) if p is not None and k in preplaced), default=0.0) + 1.0
            for i, rect in self._shelf_pack(ordered, dims, safe_x, start_y).items():
                positions[i] = rect

        return [self._clean_tuple(p) for p in positions]  # type: ignore[arg-type]

    def _choose_dimensions(self, block_count, area_targets, constraints, target_positions):
        dims = []
        hard = set()
        for i in range(block_count):
            if self._has_wh(target_positions, i):
                w = float(target_positions[i, 2]); h = float(target_positions[i, 3]); hard.add(i)
            else:
                area = float(area_targets[i]) if i < len(area_targets) and area_targets[i] > 0 else 1.0
                side = math.sqrt(max(area, 1e-9)); w = side; h = area / side
            dims.append((max(w, 1e-9), max(h, 1e-9)))
        if constraints is not None and constraints.dim() > 1 and constraints.shape[1] > 2:
            gids = sorted({int(constraints[i, 2].item()) for i in range(block_count) if constraints[i, 2] > 0})
            for gid in gids:
                group = [i for i in range(block_count) if int(constraints[i, 2].item()) == gid]
                areas = [float(area_targets[i]) for i in group if area_targets[i] > 0]
                if not areas: continue
                avg = sum(areas) / len(areas)
                if max(abs(a - avg) / max(avg, 1e-9) for a in areas) <= 0.01:
                    side = math.sqrt(avg); common = (side, avg / side)
                    for i in group:
                        if i not in hard: dims[i] = common
        return dims

    def _shelf_pack(self, ordered, dims, start_x, start_y):
        if not ordered: return {}
        total_area = sum(dims[i][0] * dims[i][1] for i in ordered)
        row_width = max(math.sqrt(max(total_area, 1.0)) * 1.25, max(dims[i][0] for i in ordered))
        out = {}; x = start_x; y = start_y; row_h = 0.0
        for i in ordered:
            w, h = dims[i]
            if x > start_x and x + w > start_x + row_width:
                x = start_x; y += row_h; row_h = 0.0
            out[i] = (x, y, w, h); x += w; row_h = max(row_h, h)
        return out

    def _order_blocks(self, blocks, area_targets, b2b_connectivity, p2b_connectivity):
        degree = {i: 0.0 for i in blocks}; s = set(blocks)
        if b2b_connectivity is not None:
            for e in b2b_connectivity:
                if len(e) >= 3 and e[0] != -1:
                    a, b, w = int(e[0]), int(e[1]), abs(float(e[2]))
                    if a in s: degree[a] += w
                    if b in s: degree[b] += w
        if p2b_connectivity is not None:
            for e in p2b_connectivity:
                if len(e) >= 3 and e[0] != -1:
                    b, w = int(e[1]), abs(float(e[2]))
                    if b in s: degree[b] += w
        return sorted(blocks, key=lambda i: (-degree.get(i, 0.0), -float(area_targets[i]), i))

    def _boundary_code(self, constraints, i):
        if constraints is not None and constraints.dim() > 1 and constraints.shape[1] > 4:
            return int(constraints[i, 4].item())
        return 0

    def _has_wh(self, target_positions, i):
        return target_positions is not None and i < len(target_positions) and float(target_positions[i, 2]) != -1.0 and float(target_positions[i, 3]) != -1.0

    def _has_xywh(self, target_positions, i):
        return self._has_wh(target_positions, i) and float(target_positions[i, 0]) != -1.0 and float(target_positions[i, 1]) != -1.0

    def _overlaps_any(self, rect, others):
        x1, y1, w1, h1 = rect
        for x2, y2, w2, h2 in others:
            if min(x1 + w1, x2 + w2) - max(x1, x2) > 1e-6 and min(y1 + h1, y2 + h2) - max(y1, y2) > 1e-6:
                return True
        return False

    def _has_overlap(self, positions):
        return any(self._overlaps_any(positions[i], positions[i + 1:]) for i in range(len(positions)))

    def _clean_tuple(self, p):
        x, y, w, h = p
        return (float(x), float(y), float(w), float(h))

    def _cost(self, positions, b2b_conn, p2b_conn, pins_pos) -> float:
        return calculate_hpwl_b2b(positions, b2b_conn) + calculate_hpwl_p2b(positions, p2b_conn, pins_pos) + 0.01 * calculate_bbox_area(positions)
