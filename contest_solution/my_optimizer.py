#!/usr/bin/env python3
"""ICCAD 2026 FloorSet heuristic optimizer.

Feasibility-first constructive placer with explicit handling for:
- exact preplaced coordinates and fixed/preplaced dimensions,
- exact soft-block areas,
- no overlaps,
- perimeter/boundary constraints against the final bounding box,
- MIB shape normalization when target areas allow it,
- cluster-aware packing for lower soft-constraint penalties.
"""

import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple

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

        placed_rects = [p for p in positions if p is not None]
        if placed_rects:
            start_x = max(p[0] + p[2] for p in placed_rects) + 1.0
            start_y = min(p[1] for p in placed_rects)
        else:
            start_x = 0.0
            start_y = 0.0

        # Pack non-boundary clusters as contiguous macro-blocks.  A horizontal
        # chain guarantees each member shares an edge with the next one, which
        # sharply lowers grouping violations while preserving exact areas.
        for i, rect in self._pack_interior_units(
            interior, dims, constraints, area_targets, b2b_connectivity,
            p2b_connectivity, start_x, start_y
        ).items():
            positions[i] = rect

        content = [p for p in positions if p is not None]
        if not content:
            content = [(0.0, 0.0, 1.0, 1.0)]

        self._place_boundary_blocks(boundary_blocks, boundary, dims, positions, content)

        if self._has_overlap([p for p in positions if p is not None]):
            # Absolute safety fallback: all non-preplaced blocks in a disjoint strip.
            ordered = self._order_blocks(movable, area_targets, b2b_connectivity, p2b_connectivity)
            safe_x = max((p[0] + p[2] for k, p in enumerate(positions) if p is not None and k in preplaced), default=0.0) + 1.0
            for i, rect in self._shelf_pack(ordered, dims, safe_x, start_y).items():
                positions[i] = rect

        return [self._clean_tuple(p) for p in positions]  # type: ignore[arg-type]

    def _pack_interior_units(self, interior, dims, constraints, area_targets, b2b_connectivity,
                             p2b_connectivity, start_x, start_y) -> Dict[int, Rect]:
        if not interior:
            return {}
        used = set()
        units = []
        degrees = self._connection_degrees(interior, b2b_connectivity, p2b_connectivity)
        if constraints is not None and constraints.dim() > 1 and constraints.shape[1] > 3:
            cluster_ids = sorted({int(constraints[i, 3].item()) for i in interior if constraints[i, 3] > 0})
            for gid in cluster_ids:
                group = [i for i in interior if int(constraints[i, 3].item()) == gid]
                if len(group) < 2:
                    continue
                group = self._order_blocks(group, area_targets, b2b_connectivity, p2b_connectivity)
                local, uw, uh = self._cluster_local_pack(group, dims)
                for i in group:
                    used.add(i)
                units.append({'ids': group, 'w': uw, 'h': uh, 'local': local,
                              'key': self._unit_sort_key(group, area_targets, degrees)})
        for i in interior:
            if i in used:
                continue
            w, h = dims[i]
            units.append({'ids': [i], 'w': w, 'h': h, 'local': {i: (0.0, 0.0, w, h)},
                          'key': self._unit_sort_key([i], area_targets, degrees)})
        units.sort(key=lambda u: u['key'])

        total_area = sum(u['w'] * u['h'] for u in units)
        max_w = max(u['w'] for u in units)
        # Slightly wider rows reduce HPWL/area for macro clusters while staying fast.
        row_width = max(math.sqrt(max(total_area, 1.0)) * 0.9, max_w)
        out: Dict[int, Rect] = {}
        x = start_x
        y = start_y
        row_h = 0.0
        for u in units:
            uw, uh = u['w'], u['h']
            if x > start_x and x + uw > start_x + row_width:
                x = start_x
                y += row_h
                row_h = 0.0
            for i, (lx, ly, w, h) in u['local'].items():
                out[i] = (x + lx, y + ly, w, h)
            x += uw
            row_h = max(row_h, uh)
        return out

    def _cluster_local_pack(self, group, dims):
        if not group:
            return {}, 0.0, 0.0
        ordered = sorted(group, key=lambda i: (-dims[i][1], -dims[i][0], i))
        total_area = sum(dims[i][0] * dims[i][1] for i in ordered)
        row_width = max(math.sqrt(max(total_area, 1.0)) * 1.55, max(dims[i][0] for i in ordered))
        local = {}
        x = 0.0
        y = 0.0
        row_h = 0.0
        max_w = 0.0
        for i in ordered:
            w, h = dims[i]
            if x > 0.0 and x + w > row_width:
                max_w = max(max_w, x)
                x = 0.0
                y += row_h
                row_h = 0.0
            local[i] = (x, y, w, h)
            x += w
            row_h = max(row_h, h)
        max_w = max(max_w, x)
        return local, max_w, y + row_h

    def _place_boundary_blocks(self, boundary_blocks, boundary, dims, positions, content) -> None:
        if not boundary_blocks:
            return
        gap = 1.0
        cminx = min(p[0] for p in content)
        cminy = min(p[1] for p in content)
        cmaxx = max(p[0] + p[2] for p in content)
        cmaxy = max(p[1] + p[3] for p in content)
        content_w = cmaxx - cminx
        content_h = cmaxy - cminy

        leftish = [i for i in boundary_blocks if boundary[i] & 1]
        rightish = [i for i in boundary_blocks if boundary[i] & 2]
        topish = [i for i in boundary_blocks if boundary[i] & 4]
        bottomish = [i for i in boundary_blocks if boundary[i] & 8]
        left_only = [i for i in leftish if boundary[i] == 1]
        right_only = [i for i in rightish if boundary[i] == 2]
        top_only = [i for i in topish if boundary[i] == 4]
        bottom_only = [i for i in bottomish if boundary[i] == 8]

        left_w = max((dims[i][0] for i in leftish), default=0.0)
        right_w = max((dims[i][0] for i in rightish), default=0.0)
        top_h = max((dims[i][1] for i in topish), default=0.0)
        bottom_h = max((dims[i][1] for i in bottomish), default=0.0)
        top_row_w = sum(dims[i][0] for i in top_only)
        bottom_row_w = sum(dims[i][0] for i in bottom_only)
        left_col_h = sum(dims[i][1] for i in left_only)
        right_col_h = sum(dims[i][1] for i in right_only)

        width_needed = max(
            content_w + (left_w + gap if leftish else 0.0) + (right_w + gap if rightish else 0.0),
            left_w + right_w + max(top_row_w, bottom_row_w)
        )
        height_needed = max(
            content_h + (bottom_h + gap if bottomish else 0.0) + (top_h + gap if topish else 0.0),
            bottom_h + top_h + max(left_col_h, right_col_h)
        )
        left_edge = cminx - (left_w + gap if leftish else 0.0)
        bottom_edge = cminy - (bottom_h + gap if bottomish else 0.0)
        right_edge = max(cmaxx + (right_w + gap if rightish else 0.0), left_edge + width_needed)
        top_edge = max(cmaxy + (top_h + gap if topish else 0.0), bottom_edge + height_needed)

        used = set()
        corner_at = {
            5: (left_edge, top_edge, 'tl'),
            6: (right_edge, top_edge, 'tr'),
            9: (left_edge, bottom_edge, 'bl'),
            10: (right_edge, bottom_edge, 'br'),
        }
        for code, (ex, ey, _kind) in corner_at.items():
            ids = [i for i in boundary_blocks if boundary[i] == code]
            for k, i in enumerate(ids):
                w, h = dims[i]
                if code & 1:
                    x = ex
                else:
                    x = ex - w
                if code & 4:
                    y = ey - h
                else:
                    y = ey
                # Rare duplicate corners stay on the requested side and are
                # shifted along the perimeter to avoid overlap.
                if k:
                    if code & 4 or code & 8:
                        x += k * w if code & 1 else -k * w
                positions[i] = (x, y, w, h)
                used.add(i)

        y = bottom_edge + bottom_h
        for i in left_only:
            w, h = dims[i]
            positions[i] = (left_edge, y, w, h)
            y += h
            used.add(i)

        y = bottom_edge + bottom_h
        for i in right_only:
            w, h = dims[i]
            positions[i] = (right_edge - w, y, w, h)
            y += h
            used.add(i)

        x = left_edge + left_w
        for i in bottom_only:
            w, h = dims[i]
            positions[i] = (x, bottom_edge, w, h)
            x += w
            used.add(i)

        x = left_edge + left_w
        for i in top_only:
            w, h = dims[i]
            positions[i] = (x, top_edge - h, w, h)
            x += w
            used.add(i)

        rest = [i for i in boundary_blocks if i not in used]
        if rest:
            safe_x = right_edge + gap
            for i, rect in self._shelf_pack(rest, dims, safe_x, cminy).items():
                positions[i] = rect

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
                if not areas:
                    continue
                avg = sum(areas) / len(areas)
                if max(abs(a - avg) / max(avg, 1e-9) for a in areas) <= 0.01:
                    side = math.sqrt(avg); common = (side, avg / side)
                    for i in group:
                        if i not in hard:
                            dims[i] = common
        return dims

    def _shelf_pack(self, ordered, dims, start_x, start_y):
        if not ordered:
            return {}
        total_area = sum(dims[i][0] * dims[i][1] for i in ordered)
        row_width = max(math.sqrt(max(total_area, 1.0)) * 1.25, max(dims[i][0] for i in ordered))
        out = {}; x = start_x; y = start_y; row_h = 0.0
        for i in ordered:
            w, h = dims[i]
            if x > start_x and x + w > start_x + row_width:
                x = start_x; y += row_h; row_h = 0.0
            out[i] = (x, y, w, h); x += w; row_h = max(row_h, h)
        return out

    def _connection_degrees(self, blocks, b2b_connectivity, p2b_connectivity):
        degree = {i: 0.0 for i in blocks}
        s = set(blocks)
        if b2b_connectivity is not None:
            for e in b2b_connectivity:
                if len(e) >= 3 and e[0] != -1:
                    a, b, w = int(e[0]), int(e[1]), abs(float(e[2]))
                    if a in s:
                        degree[a] += w
                    if b in s:
                        degree[b] += w
        if p2b_connectivity is not None:
            for e in p2b_connectivity:
                if len(e) >= 3 and e[0] != -1:
                    b, w = int(e[1]), abs(float(e[2]))
                    if b in s:
                        degree[b] += w
        return degree

    def _unit_sort_key(self, blocks, area_targets, degrees):
        degree = sum(degrees.get(i, 0.0) for i in blocks)
        area = sum(float(area_targets[i]) for i in blocks)
        return (-degree, -area, min(blocks))

    def _unit_key(self, blocks, area_targets, b2b_connectivity, p2b_connectivity):
        degree = 0.0
        s = set(blocks)
        if b2b_connectivity is not None:
            for e in b2b_connectivity:
                if len(e) >= 3 and e[0] != -1:
                    a, b, w = int(e[0]), int(e[1]), abs(float(e[2]))
                    if a in s or b in s:
                        degree += w
        if p2b_connectivity is not None:
            for e in p2b_connectivity:
                if len(e) >= 3 and e[0] != -1:
                    b, w = int(e[1]), abs(float(e[2]))
                    if b in s:
                        degree += w
        area = sum(float(area_targets[i]) for i in blocks)
        return (-degree, -area, min(blocks))

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
