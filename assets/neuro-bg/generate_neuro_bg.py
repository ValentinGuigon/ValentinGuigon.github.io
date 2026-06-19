#!/usr/bin/env python3
r"""Generate probabilistic computational-neuroscience SVG backgrounds.

This version uses a probabilistic scene grammar rather than a fixed motif list.
Each output can differ in motif presence, region placement, shape mode, density,
labels, and internal geometry.

Example PowerShell usage:

New-Item -ItemType Directory -Force .\outputs | Out-Null; 1..40 | ForEach-Object { $s = Get-Random -Minimum 1 -Maximum 999999; python .\generate_neuro_bg.py --variant maximal --seed $s --output ".\outputs\maximal-seed-$s.svg" --stats-output ".\outputs\maximal-seed-$s.stats.json" }

Variants:
    minimal, spacefill, maximal

Main ideas:
    variant -> probabilistic palette -> motif presence -> motif count -> region ->
    internal shape mode -> local geometry.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

Point = Tuple[float, float]
Rect = Tuple[float, float, float, float]

DEFAULT_WIDTH = 2400
DEFAULT_HEIGHT = 1800
DEFAULT_VARIANT = "minimal"

# Global opacity scale. If outputs feel too heavy, lower this first.
OPACITY_SCALE = 1.35

ROLE_AMBIENT = "ambient"
ROLE_STRUCTURAL = "structural"
ROLE_ANCHOR = "anchor"

COLORS: Dict[str, str] = {
    "ink_strong": "rgb(12, 14, 20)",
    "ink": "rgb(22, 28, 38)",
    "ink_soft": "rgb(42, 50, 66)",
    "gray": "rgb(96, 102, 116)",
    "gray_soft": "rgb(144, 150, 164)",
    "blue": "rgb(72, 114, 184)",
    "blue_soft": "rgb(110, 148, 212)",
    "indigo": "rgb(92, 98, 176)",
    "indigo_soft": "rgb(126, 132, 214)",
    "violet": "rgb(130, 110, 194)",
    "violet_soft": "rgb(176, 162, 226)",
}

REGION_DEBUG_STYLES = {
    "left_outer": ("rgba(65,125,206,0.05)", "rgba(65,125,206,0.7)"),
    "left_upper": ("rgba(120,113,206,0.05)", "rgba(120,113,206,0.7)"),
    "left_middle": ("rgba(96,148,214,0.05)", "rgba(96,148,214,0.7)"),
    "center_bridge": ("rgba(103,108,186,0.05)", "rgba(103,108,186,0.7)"),
    "right_upper": ("rgba(148,124,214,0.05)", "rgba(148,124,214,0.7)"),
    "right_middle": ("rgba(126,148,216,0.05)", "rgba(126,148,216,0.7)"),
    "right_lower": ("rgba(112,114,184,0.05)", "rgba(112,114,184,0.7)"),
}


@dataclass(frozen=True)
class Region:
    name: str
    bounds: Rect


@dataclass(frozen=True)
class MotifSpec:
    name: str
    p: float
    count_range: Tuple[int, int]
    region_weights: Sequence[Tuple[str, float]]
    role_weights: Sequence[Tuple[str, float]]


@dataclass
class CoverageMask:
    width: float
    height: float
    cols: int = 72
    rows: int = 54
    cells: List[List[bool]] = field(init=False)

    def __post_init__(self) -> None:
        self.cells = [[False for _ in range(self.cols)]
                      for _ in range(self.rows)]

    def mark_rect(self, rect: Rect, pad: float = 0.0) -> None:
        x1, y1, x2, y2 = rect
        x1 = clamp(x1 - pad, 0.0, self.width)
        y1 = clamp(y1 - pad, 0.0, self.height)
        x2 = clamp(x2 + pad, 0.0, self.width)
        y2 = clamp(y2 + pad, 0.0, self.height)
        c1 = max(0, min(self.cols - 1, int((x1 / self.width) * self.cols)))
        c2 = max(1, min(self.cols, int(math.ceil((x2 / self.width) * self.cols))))
        r1 = max(0, min(self.rows - 1, int((y1 / self.height) * self.rows)))
        r2 = max(1, min(self.rows, int(math.ceil((y2 / self.height) * self.rows))))
        for rr in range(r1, r2):
            for cc in range(c1, c2):
                self.cells[rr][cc] = True

    def fraction_for_rect(self, rect: Rect) -> float:
        x1, y1, x2, y2 = rect
        c1 = max(0, min(self.cols - 1, int((x1 / self.width) * self.cols)))
        c2 = max(
            c1 + 1, min(self.cols, int(math.ceil((x2 / self.width) * self.cols))))
        r1 = max(0, min(self.rows - 1, int((y1 / self.height) * self.rows)))
        r2 = max(
            r1 + 1, min(self.rows, int(math.ceil((y2 / self.height) * self.rows))))
        total = max(1, (r2 - r1) * (c2 - c1))
        occupied = sum(1 for rr in range(r1, r2)
                       for cc in range(c1, c2) if self.cells[rr][cc])
        return occupied / total

    def overall_fraction(self) -> float:
        return sum(1 for row in self.cells for cell in row if cell) / (self.cols * self.rows)


@dataclass
class GenerationStats:
    motif_counts: Dict[str, int] = field(default_factory=dict)
    region_coverage: Dict[str, float] = field(default_factory=dict)
    overall_coverage: float = 0.0
    attempts: int = 1


class Builder:
    def __init__(self, width: int, height: int, seed: int, variant: str, debug_overlay: bool = False) -> None:
        self.width = width
        self.height = height
        self.seed = seed
        self.variant = variant
        self.debug_overlay = debug_overlay
        self.rng = random.Random(seed)
        self.coverage = CoverageMask(width, height)
        self.elements: List[str] = []
        self.debug_elements: List[str] = []
        self.stats = GenerationStats()
        self.matrix_rect: Optional[Rect] = None
        self.matrix_region: Optional[str] = None
        self.regions = define_regions(width, height)
        self.used_regions_by_family: Dict[str, set[str]] = {}

    def region(self, name: str) -> Region:
        return self.regions[name]

    def add(self, motif: str, region: str, element: str, rect: Rect, pad: float = 0.0) -> None:
        self.elements.append(element)
        self.coverage.mark_rect(rect, pad=pad)
        self.stats.motif_counts[motif] = self.stats.motif_counts.get(
            motif, 0) + 1
        if self.debug_overlay:
            _, stroke = REGION_DEBUG_STYLES.get(
                region, ("rgba(0,0,0,.03)", "rgba(0,0,0,.25)"))
            x1, y1, x2, y2 = rect
            self.debug_elements.append(
                f'<rect x="{fmt(x1)}" y="{fmt(y1)}" width="{fmt(x2 - x1)}" height="{fmt(y2 - y1)}" '
                f'fill="none" stroke="{stroke}" stroke-width="1.2" stroke-dasharray="6 6" opacity="0.45" />'
            )


def define_regions(width: float, height: float) -> Dict[str, Region]:
    return {
        "left_outer": Region("left_outer", (0.0, 0.0, 0.24 * width, height)),
        "left_upper": Region("left_upper", (0.06 * width, 0.03 * height, 0.42 * width, 0.28 * height)),
        "left_middle": Region("left_middle", (0.0, 0.24 * height, 0.42 * width, 0.74 * height)),
        "center_bridge": Region("center_bridge", (0.28 * width, 0.08 * height, 0.68 * width, 0.72 * height)),
        "right_upper": Region("right_upper", (0.64 * width, 0.03 * height, 0.98 * width, 0.30 * height)),
        "right_middle": Region("right_middle", (0.56 * width, 0.24 * height, 0.98 * width, 0.68 * height)),
        "right_lower": Region("right_lower", (0.54 * width, 0.62 * height, 0.98 * width, 0.95 * height)),
    }


def fmt(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def rect_center(rect: Rect) -> Point:
    x1, y1, x2, y2 = rect
    return ((x1 + x2) * 0.5, (y1 + y2) * 0.5)


def rect_union(rects: Sequence[Rect]) -> Rect:
    return (min(r[0] for r in rects), min(r[1] for r in rects), max(r[2] for r in rects), max(r[3] for r in rects))


def polyline_bounds(points: Sequence[Point], pad: float = 0.0) -> Rect:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def path_from_points(points: Sequence[Point]) -> str:
    if not points:
        return ""
    if len(points) == 1:
        return f"M {fmt(points[0][0])} {fmt(points[0][1])}"
    out = [f"M {fmt(points[0][0])} {fmt(points[0][1])}"]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        out.append(
            f"C {fmt(c1x)} {fmt(c1y)}, {fmt(c2x)} {fmt(c2y)}, {fmt(p2[0])} {fmt(p2[1])}")
    return " ".join(out)


def weighted_choice(rng: random.Random, pairs: Sequence[Tuple[str, float]]) -> str:
    total = sum(w for _, w in pairs)
    threshold = rng.uniform(0, total)
    cursor = 0.0
    for item, weight in pairs:
        cursor += weight
        if threshold <= cursor:
            return item
    return pairs[-1][0]


def choose_region(builder: Builder, family: str, candidates: Sequence[Tuple[str, float]], avoid_reuse: bool = False) -> str:
    used = builder.used_regions_by_family.setdefault(family, set())
    available = [(name, weight) for name,
                 weight in candidates if not avoid_reuse or name not in used]
    if not available:
        available = list(candidates)
    chosen = weighted_choice(builder.rng, available)
    used.add(chosen)
    return chosen


def one_of(builder: Builder, p: float) -> bool:
    return builder.rng.random() < p


def rotation_for(builder: Builder, kind: str) -> float:
    ranges = {
        "matrix": (-10.0, 10.0),
        "traces": (-6.0, 6.0),
        "raster": (-7.0, 7.0),
        "voxel": (-12.0, 12.0),
        "density": (-5.0, 5.0),
        "axes": (-8.0, 8.0),
    }
    lo, hi = ranges.get(kind, (-4.0, 4.0))
    return builder.rng.uniform(lo, hi)


def group_with_rotation(inner: str, rect: Rect, angle: float) -> str:
    if abs(angle) < 0.5:
        return inner
    cx, cy = rect_center(rect)
    return f'<g transform="rotate({fmt(angle)} {fmt(cx)} {fmt(cy)})">{inner}</g>'


def sample_point(
    rng: random.Random,
    rect: Rect,
    x_bias: Optional[Tuple[float, float]] = None,
    y_bias: Optional[Tuple[float, float]] = None,
) -> Point:
    x1, y1, x2, y2 = rect
    tx = rng.betavariate(*x_bias) if x_bias else rng.random()
    ty = rng.betavariate(*y_bias) if y_bias else rng.random()
    return (lerp(x1, x2, tx), lerp(y1, y2, ty))


def color_for(rng: random.Random, motif: str, role: str) -> str:
    del role
    table = {
        "latent_trajectory": [("blue", 1.6), ("indigo", 2.2), ("violet", 1.2), ("ink", 0.7)],
        "posterior_cloud": [("violet", 2.0), ("indigo_soft", 1.6), ("blue_soft", 1.3), ("gray_soft", 0.8)],
        "vector_field": [("blue_soft", 1.9), ("indigo_soft", 1.8), ("gray_soft", 1.1)],
        "flow_streamlines": [("blue_soft", 1.9), ("indigo_soft", 1.8), ("gray_soft", 1.1)],
        "density_contours": [("gray_soft", 1.8), ("indigo_soft", 1.6), ("violet_soft", 1.4), ("blue_soft", 1.2)],
        "matrix": [("gray", 1.8), ("blue_soft", 1.2), ("indigo_soft", 1.1), ("violet_soft", 0.8)],
        "traces": [("gray_soft", 1.5), ("blue_soft", 1.3), ("violet_soft", 1.1), ("indigo_soft", 1.1)],
        "axes": [("ink_soft", 1.6), ("gray", 1.1), ("blue_soft", 0.9)],
        "curve": [("blue", 1.5), ("indigo", 1.6), ("violet", 1.2), ("ink_soft", 0.7)],
    }
    if motif in {"connectivity_matrix", "design_matrix_fragment", "voxel_fragment"}:
        key = "matrix"
    elif motif in {"time_series_stack", "event_raster_fragment", "ambient_dot_grid"}:
        key = "traces"
    elif motif in {"latent_axes", "scalar_legend", "state_space_label"}:
        key = "axes"
    elif motif in {"belief_update_curve", "prediction_error_pulses", "posterior_density_ridge"}:
        key = "curve"
    else:
        key = motif if motif in table else "traces"
    return COLORS[weighted_choice(rng, table[key])]


def opacity_for(rng: random.Random, motif: str, role: str) -> float:
    ranges = {
        "flow_streamlines": {
            ROLE_AMBIENT: (0.10, 0.18),
            ROLE_STRUCTURAL: (0.13, 0.24),
            ROLE_ANCHOR: (0.18, 0.32),
        },
        "vector_field": {
            ROLE_AMBIENT: (0.14, 0.25),
            ROLE_STRUCTURAL: (0.18, 0.34),
            ROLE_ANCHOR: (0.24, 0.40),
        },
        "latent_trajectory": {
            ROLE_AMBIENT: (0.24, 0.36),
            ROLE_STRUCTURAL: (0.34, 0.50),
            ROLE_ANCHOR: (0.44, 0.66),
        },
        "posterior_cloud": {
            ROLE_AMBIENT: (0.12, 0.22),
            ROLE_STRUCTURAL: (0.17, 0.30),
            ROLE_ANCHOR: (0.24, 0.40),
        },
        "density_contours": {
            ROLE_AMBIENT: (0.12, 0.22),
            ROLE_STRUCTURAL: (0.17, 0.30),
            ROLE_ANCHOR: (0.22, 0.38),
        },
    }
    default = {
        ROLE_AMBIENT: (0.11, 0.22),
        ROLE_STRUCTURAL: (0.16, 0.30),
        ROLE_ANCHOR: (0.22, 0.38),
    }
    low, high = ranges.get(motif, default)[role]
    return clamp(rng.uniform(low, high) * OPACITY_SCALE, 0.02, 0.86)


# -----------------------------------------------------------------------------
# Motif generators
# -----------------------------------------------------------------------------


def add_ambient_dot_grid(builder: Builder, region_name: str, role: str = ROLE_AMBIENT, cols: int = 18, rows: int = 12) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    color = color_for(rng, "ambient_dot_grid", role)
    base = opacity_for(rng, "ambient_dot_grid", role)
    shape_mode = weighted_choice(rng, [(
        "rectangular", 0.75), ("oval", 0.70), ("wedge", 0.45), ("ragged", 0.80), ("arc", 0.45)])
    dots: List[str] = []
    pts: List[Point] = []
    x1, y1, x2, y2 = rect
    for rr in range(rows):
        for cc in range(cols):
            nx = cc / max(1, cols - 1) * 2 - 1
            ny = rr / max(1, rows - 1) * 2 - 1
            if shape_mode == "oval" and nx * nx / 1.05 + ny * ny / 0.72 > 1.0:
                continue
            if shape_mode == "wedge" and cc < rr * rng.uniform(0.45, 0.90) and rng.random() < 0.85:
                continue
            if shape_mode == "ragged":
                edge = max(abs(nx), abs(ny))
                keep = clamp(1.10 - 0.55 * edge +
                             rng.uniform(-0.22, 0.18), 0.18, 1.0)
                if rng.random() > keep:
                    continue
            if shape_mode == "arc":
                radius = math.hypot(nx, ny)
                if not (0.45 < radius < 1.10 and nx > -0.85):
                    continue
            if rng.random() < 0.16:
                continue
            x = lerp(x1, x2, cc / max(1, cols - 1)) + \
                rng.uniform(-(x2 - x1) * 0.012, (x2 - x1) * 0.012)
            y = lerp(y1, y2, rr / max(1, rows - 1)) + \
                rng.uniform(-(y2 - y1) * 0.014, (y2 - y1) * 0.014)
            a = clamp(base * rng.uniform(0.62, 1.24), 0.08, 0.40)
            r = rng.uniform(0.75, 2.5)
            dots.append(
                f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{color}" opacity="{fmt(a)}" />')
            pts.append((x, y))
    if pts:
        builder.add("ambient_dot_grid", region_name,
                    f'<g data-motif-type="ambient_dot_grid" data-shape-mode="{shape_mode}">{"".join(dots)}</g>', polyline_bounds(pts, 8), 20)


def add_density_contours(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL, bands: int = 6) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    cx, cy = rect_center(rect)
    cx += rng.uniform(-(rect[2] - rect[0]) * 0.10, (rect[2] - rect[0]) * 0.10)
    cy += rng.uniform(-(rect[3] - rect[1]) * 0.10, (rect[3] - rect[1]) * 0.10)
    rx0 = (rect[2] - rect[0]) * rng.uniform(0.24, 0.54)
    ry0 = (rect[3] - rect[1]) * rng.uniform(0.14, 0.36)
    color = color_for(rng, "density_contours", role)
    elems: List[str] = []
    all_pts: List[Point] = []
    contour_mode = weighted_choice(
        rng, [("nested", 1.0), ("open", 0.5), ("lopsided", 0.7)])
    for band in range(bands):
        t = 1 - band / max(1, bands - 1)
        rx, ry = rx0 * (0.35 + 0.78 * t), ry0 * (0.35 + 0.82 * t)
        phase = rng.uniform(0, 2 * math.pi)
        steps = rng.randint(14, 24)
        pts: List[Point] = []
        for i in range(steps):
            a = phase + 2 * math.pi * i / steps
            rough = 1 + 0.10 * math.sin(a * rng.uniform(1.2, 2.5) +
                                        rng.uniform(0, 2 * math.pi)) + rng.uniform(-0.05, 0.05)
            if contour_mode == "lopsided":
                rough *= 1 + 0.12 * math.cos(a - 0.7)
            p = (cx + math.cos(a) * rx * rough + rng.uniform(-8, 8),
                 cy + math.sin(a) * ry * rough + rng.uniform(-6, 6))
            pts.append(p)
            all_pts.append(p)
        if contour_mode != "open":
            pts.append(pts[0])
        op = clamp(opacity_for(rng, "density_contours", role)
                   * (0.70 + 0.46 * t), 0.08, 0.50)
        sw = rng.uniform(
            0.7, 1.6) if role != ROLE_AMBIENT else rng.uniform(0.5, 1.1)
        close = " Z" if contour_mode != "open" else ""
        elems.append(
            f'<path d="{path_from_points(pts)}{close}" fill="none" stroke="{color}" stroke-width="{fmt(sw)}" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(op)}" />'
        )
    if all_pts:
        plot_rect = polyline_bounds(all_pts, 12)
        group = f'<g data-motif-type="density_contours" data-shape-mode="{contour_mode}">{"".join(elems)}</g>'
        group = group_with_rotation(
            group, plot_rect, rotation_for(builder, "density"))
        builder.add("density_contours", region_name, group, plot_rect, 32)


def field_direction(x: float, y: float, rect: Rect, mode: str) -> Point:
    x1, y1, x2, y2 = rect
    nx = (x - (x1 + x2) / 2) / max(1, (x2 - x1) / 2)
    ny = (y - (y1 + y2) / 2) / max(1, (y2 - y1) / 2)
    if mode == "rotational":
        u, v = -ny + 0.18 * math.sin(2.4 * nx), nx + 0.14 * math.cos(1.9 * ny)
    elif mode == "saddle":
        u, v = nx - 0.35 * ny, -ny + 0.35 * nx
    elif mode == "drift":
        u, v = 0.8 + 0.28 * math.sin(2.0 * ny), 0.26 * \
            math.sin(2.5 * nx) - 0.18 * ny
    elif mode == "sink":
        u, v = -0.75 * nx + 0.18 * \
            math.sin(2.0 * ny), -0.75 * ny + 0.18 * math.cos(2.0 * nx)
    else:
        u, v = -0.7 * ny - 0.28 * nx, 0.7 * nx - 0.28 * ny
    n = math.hypot(u, v) or 1
    return u / n, v / n


def add_flow_streamlines(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL, lines: int = 18) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    mode = weighted_choice(rng, [(
        "rotational", 1.5), ("spiral", 1.5), ("drift", 0.9), ("saddle", 0.7), ("sink", 0.6)])
    color = color_for(rng, "flow_streamlines", role)
    base = opacity_for(rng, "flow_streamlines", role)
    elems: List[str] = []
    boxes: List[Rect] = []
    x1, y1, x2, y2 = rect
    for _ in range(lines):
        x, y = sample_point(rng, rect, (1.25, 1.25), (1.25, 1.25))
        pts: List[Point] = []
        step = rng.uniform(16, 32)
        for _ in range(rng.randint(14, 34)):
            if not (x1 <= x <= x2 and y1 <= y <= y2):
                break
            pts.append((x, y))
            u, v = field_direction(x, y, rect, mode)
            x += u * step + rng.uniform(-3, 3)
            y += v * step + rng.uniform(-3, 3)
        if len(pts) >= 5:
            op = clamp(base * rng.uniform(0.34, 0.78), 0.06, 0.38)
            sw = rng.uniform(0.6, 1.35)
            elems.append(
                f'<path d="{path_from_points(pts)}" fill="none" stroke="{color}" stroke-width="{fmt(sw)}" '
                f'stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(op)}" />'
            )
            boxes.append(polyline_bounds(pts, 10))
    if boxes:
        builder.add("flow_streamlines", region_name,
                    f'<g data-motif-type="flow_streamlines" data-field-mode="{mode}">{"".join(elems)}</g>', rect_union(boxes), 36)


def add_vector_field(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL, cols: int = 16, rows: int = 10) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    mode = weighted_choice(rng, [(
        "rotational", 1.4), ("saddle", 1.0), ("drift", 1.2), ("spiral", 1.4), ("sink", 0.7)])
    opacity_mode = weighted_choice(
        rng, [("uniform", 0.65), ("gradient", 0.85), ("patchy", 0.75)])
    color = color_for(rng, "vector_field", role)
    base = opacity_for(rng, "vector_field", role)
    x1, y1, x2, y2 = rect
    elems: List[str] = []
    pts: List[Point] = []
    for rr in range(rows):
        for cc in range(cols):
            if rng.random() < 0.06:
                continue
            x = lerp(x1 + 16, x2 - 16, cc / max(1, cols - 1)) + \
                rng.uniform(-8, 8)
            y = lerp(y1 + 16, y2 - 16, rr / max(1, rows - 1)) + \
                rng.uniform(-8, 8)
            u, v = field_direction(x, y, rect, mode)
            length = rng.uniform((x2 - x1) * 0.012, (x2 - x1) * 0.030)
            xe, ye = x + u * length, y + v * length
            a = math.atan2(v, u)
            h = length * rng.uniform(0.16, 0.26)
            lx, ly = xe - h * math.cos(a - 0.55), ye - h * math.sin(a - 0.55)
            rx, ry = xe - h * math.cos(a + 0.55), ye - h * math.sin(a + 0.55)
            if opacity_mode == "gradient":
                spatial = 0.45 + 0.75 * (cc / max(1, cols - 1))
                op = clamp(base * spatial *
                           rng.uniform(0.75, 1.10), 0.05, 0.62)
            elif opacity_mode == "patchy":
                patch = 0.45 + 0.75 * \
                    math.exp(-((cc / cols - 0.65) ** 2 +
                             (rr / rows - 0.45) ** 2) / 0.06)
                op = clamp(base * patch * rng.uniform(0.65, 1.15), 0.05, 0.64)
            else:
                op = clamp(base * rng.uniform(0.55, 1.25), 0.05, 0.58)
            elems.append(
                f'<line x1="{fmt(x)}" y1="{fmt(y)}" x2="{fmt(xe)}" y2="{fmt(ye)}" '
                f'stroke="{color}" stroke-width="{fmt(rng.uniform(0.5, 1.15))}" stroke-linecap="round" opacity="{fmt(op)}" />'
            )
            elems.append(
                f'<path d="M {fmt(xe)} {fmt(ye)} L {fmt(lx)} {fmt(ly)} L {fmt(rx)} {fmt(ry)} Z" '
                f'fill="{color}" opacity="{fmt(op * 0.88)}" />'
            )
            pts.extend([(x, y), (xe, ye)])
    if pts:
        builder.add("vector_field", region_name,
                    f'<g data-motif-type="vector_field" data-field-mode="{mode}" data-opacity-mode="{opacity_mode}">{"".join(elems)}</g>', polyline_bounds(pts, 12), 32)


def add_posterior_cloud(builder: Builder, region_name: str, role: str = ROLE_ANCHOR, count: int = 320) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    cx, cy = sample_point(rng, rect, (1.5, 1.5), (1.4, 1.6))
    sx = (rect[2] - rect[0]) * rng.uniform(0.08, 0.24)
    sy = (rect[3] - rect[1]) * rng.uniform(0.08, 0.20)
    mode = weighted_choice(
        rng, [("single", 1.0), ("double", 0.65), ("trail", 0.45)])
    color = color_for(rng, "posterior_cloud", role)
    base = opacity_for(rng, "posterior_cloud", role)
    elems: List[str] = []
    pts: List[Point] = []
    for i in range(count):
        if mode == "double" and rng.random() < 0.48:
            mx = cx + sx * rng.uniform(-1.25, 1.25)
            my = cy + sy * rng.uniform(-1.1, 1.1)
        elif mode == "trail":
            t = i / max(1, count - 1)
            mx = cx + (t - 0.5) * sx * rng.uniform(1.8, 3.2)
            my = cy + math.sin(t * math.pi * 2) * sy * rng.uniform(0.6, 1.3)
        else:
            mx, my = cx, cy
        x = clamp(rng.gauss(mx, sx), rect[0], rect[2])
        y = clamp(rng.gauss(my, sy), rect[1], rect[3])
        r = rng.uniform(0.55, 2.8 if role != ROLE_ANCHOR else 3.3)
        op = clamp(base * rng.uniform(0.45, 1.20), 0.06, 0.58)
        elems.append(
            f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(r)}" fill="{color}" opacity="{fmt(op)}" />')
        pts.append((x, y))
    builder.add("posterior_cloud", region_name,
                f'<g data-motif-type="posterior_cloud" data-shape-mode="{mode}">{"".join(elems)}</g>', polyline_bounds(pts, 12), 24)


def trajectory_points(rng: random.Random, rect: Rect) -> List[Point]:
    x1, y1, x2, y2 = rect
    mode = weighted_choice(rng, [("s", 1.2), ("fan", 1.0), ("arc", 1.2),
                           ("loop", 1.0), ("diag", 0.8), ("orbit", 1.0), ("kink", 0.8)])
    pts: List[Point] = []
    if mode == "s":
        start = sample_point(rng, rect, (1.2, 1.8), (1.4, 1.5))
        w = (x2 - x1) * rng.uniform(0.25, 0.50)
        h = (y2 - y1) * rng.uniform(0.18, 0.34)
        n = rng.randint(5, 8)
        for i in range(n):
            t = i / (n - 1)
            pts.append((clamp(start[0] + w * t, x1, x2), clamp(start[1] + math.sin(
                (t * 2.2 + 0.2) * math.pi) * h * 0.45 + (t - 0.5) * h * 0.25 + rng.uniform(-10, 10), y1, y2)))
    elif mode == "fan":
        base = sample_point(rng, rect, (1.7, 1.4), (1.4, 1.8))
        w = (x2 - x1) * rng.uniform(0.18, 0.38)
        h = (y2 - y1) * rng.uniform(0.18, 0.30)
        n = rng.randint(5, 7)
        for i in range(n):
            t = i / (n - 1)
            pts.append((base[0] + w * t, base[1] - h *
                       math.sin(t * math.pi * 0.9) + rng.uniform(-6, 6)))
    elif mode == "arc":
        c = sample_point(rng, rect, (1.4, 1.5), (1.2, 1.6))
        rx = (x2 - x1) * rng.uniform(0.16, 0.32)
        ry = (y2 - y1) * rng.uniform(0.10, 0.26)
        a0 = rng.uniform(math.pi * 0.1, math.pi * 0.9)
        a1 = rng.uniform(math.pi * 1.0, math.pi * 1.75)
        for i in range(6):
            a = lerp(a0, a1, i / 5)
            pts.append((c[0] + math.cos(a) * rx + rng.uniform(-5, 5),
                       c[1] + math.sin(a) * ry + rng.uniform(-5, 5)))
    elif mode == "kink":
        start = sample_point(rng, rect)
        n = rng.randint(6, 9)
        for i in range(n):
            t = i / (n - 1)
            pts.append((start[0] + (x2 - x1) * rng.uniform(0.04, 0.10) * i, start[1] + (
                rng.choice([-1, 1]) * rng.uniform(20, 80) if i % 2 else rng.uniform(-20, 20))))
    else:
        c = sample_point(rng, rect)
        rx = (x2 - x1) * rng.uniform(0.10, 0.25)
        ry = (y2 - y1) * rng.uniform(0.08, 0.20)
        turns = 2 * math.pi if mode == "loop" else 1.5 * math.pi
        for i in range(7):
            a = i / 6 * turns + rng.uniform(0, math.pi)
            pts.append((c[0] + math.cos(a) * rx, c[1] + math.sin(a) * ry))
    return [(clamp(x, x1, x2), clamp(y, y1, y2)) for x, y in pts]


def add_latent_trajectory(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL, multiplicity: int = 2) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    color = color_for(rng, "latent_trajectory", role)
    base = opacity_for(rng, "latent_trajectory", role)
    elems: List[str] = []
    boxes: List[Rect] = []
    for i in range(multiplicity):
        pts = trajectory_points(rng, rect)
        if len(pts) < 4:
            continue
        sw = rng.uniform(1.8, 3.8) if i == 0 else rng.uniform(0.9, 2.0)
        op = clamp(
            base * (1.08 if i == 0 else rng.uniform(0.55, 0.92)), 0.18, 0.78)
        dash = "" if rng.random(
        ) < 0.72 else f' stroke-dasharray="{fmt(rng.uniform(8,16))} {fmt(rng.uniform(8,16))}"'
        elems.append(
            f'<path d="{path_from_points(pts)}" fill="none" stroke="{color}" stroke-width="{fmt(sw)}" '
            f'stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(op)}"{dash} />'
        )
        for node in rng.sample(pts[1:-1], k=min(len(pts) - 2, rng.randint(1, 4))):
            fill_mode = "none" if rng.random() < 0.25 else color
            stroke = f' stroke="{color}" stroke-width="{fmt(rng.uniform(0.8, 1.4))}"' if fill_mode == "none" else ""
            elems.append(
                f'<circle cx="{fmt(node[0])}" cy="{fmt(node[1])}" r="{fmt(rng.uniform(2.0, 5.8))}" fill="{fill_mode}"{stroke} opacity="{fmt(op * 0.80)}" />')
        boxes.append(polyline_bounds(pts, 12))
    if boxes:
        builder.add("latent_trajectory", region_name,
                    f'<g data-motif-type="latent_trajectory">{"".join(elems)}</g>', rect_union(boxes), 28)


def add_latent_axes(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    color = color_for(rng, "latent_axes", role)
    op = opacity_for(rng, "latent_axes", role)
    mode = weighted_choice(rng, [("simple_axes", 0.55), ("projected_grid", 0.85), (
        "multi_origin", 0.55), ("trajectory_axes", 0.70)])
    elems: List[str] = []
    pts: List[Point] = []
    o = sample_point(rng, rect, (1.4, 1.4), (1.4, 1.4))
    pts.append(o)
    base_angle = rng.uniform(-0.20, 0.20)
    angles = [-0.75 + base_angle, 0.08 + base_angle, 0.86 + base_angle]
    lengths = [rng.uniform(60, 130), rng.uniform(
        70, 150), rng.uniform(50, 115)]
    for i, a in enumerate(angles):
        length = lengths[i]
        p = (o[0] + math.cos(a) * length, o[1] + math.sin(a) * length)
        pts.append(p)
        local_op = clamp(op * rng.uniform(0.45, 1.15), 0.06, 0.50)
        elems.append(
            f'<line x1="{fmt(o[0])}" y1="{fmt(o[1])}" x2="{fmt(p[0])}" y2="{fmt(p[1])}" stroke="{color}" stroke-width="{fmt(rng.uniform(0.7, 1.4))}" stroke-linecap="round" opacity="{fmt(local_op)}" />')
        if one_of(builder, 0.72):
            elems.append(
                f'<text x="{fmt(p[0] + 6)}" y="{fmt(p[1] + 4)}" font-size="{fmt(rng.uniform(13, 18))}" font-family="Inter, Arial, sans-serif" fill="{color}" opacity="{fmt(local_op * .9)}">z_{i + 1}</text>')
    if mode in {"projected_grid", "trajectory_axes"}:
        for step in range(1, rng.randint(3, 6)):
            t = step / 6
            for a in angles[:2]:
                dx = math.cos(a) * lengths[0] * t
                dy = math.sin(a) * lengths[0] * t
                p1 = (o[0] + dx, o[1] + dy)
                p2 = (p1[0] + math.cos(angles[2]) * rng.uniform(35, 90),
                      p1[1] + math.sin(angles[2]) * rng.uniform(35, 90))
                pts.extend([p1, p2])
                elems.append(
                    f'<line x1="{fmt(p1[0])}" y1="{fmt(p1[1])}" x2="{fmt(p2[0])}" y2="{fmt(p2[1])}" stroke="{color}" stroke-width="0.6" stroke-dasharray="4 6" opacity="{fmt(op * rng.uniform(.18, .42))}" />')
    if mode == "multi_origin":
        for _ in range(rng.randint(2, 4)):
            oo = (o[0] + rng.uniform(-90, 90), o[1] + rng.uniform(-70, 70))
            pts.append(oo)
            for a in rng.sample(angles, k=2):
                length = rng.uniform(28, 75)
                p = (oo[0] + math.cos(a) * length,
                     oo[1] + math.sin(a) * length)
                pts.append(p)
                elems.append(
                    f'<line x1="{fmt(oo[0])}" y1="{fmt(oo[1])}" x2="{fmt(p[0])}" y2="{fmt(p[1])}" stroke="{color}" stroke-width="0.7" stroke-linecap="round" opacity="{fmt(op * rng.uniform(.20, .50))}" />')
    if mode == "trajectory_axes":
        traj: List[Point] = []
        for i in range(rng.randint(5, 8)):
            t = i / 6
            traj.append((o[0] + math.cos(angles[0]) * lengths[0] * t + math.sin(t * math.pi * 2)
                        * 18, o[1] + math.sin(angles[1]) * lengths[1] * t + math.cos(t * math.pi * 2) * 14))
        pts.extend(traj)
        elems.append(
            f'<path d="{path_from_points(traj)}" fill="none" stroke="{color}" stroke-width="{fmt(rng.uniform(0.9, 1.5))}" stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(op * .72)}" />')
        for p in rng.sample(traj, k=min(len(traj), rng.randint(2, 4))):
            elems.append(
                f'<circle cx="{fmt(p[0])}" cy="{fmt(p[1])}" r="{fmt(rng.uniform(1.8, 3.6))}" fill="{color}" opacity="{fmt(op * .65)}" />')
    if pts:
        group = f'<g data-motif-type="latent_axes" data-shape-mode="{mode}">{"".join(elems)}</g>'
        group = group_with_rotation(group, polyline_bounds(
            pts, 24), rotation_for(builder, "axes"))
        builder.add("latent_axes", region_name, group,
                    polyline_bounds(pts, 24), 18)


def add_connectivity_matrix(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    size = min(rect[2] - rect[0], rect[3] - rect[1]) * rng.uniform(0.34, 0.64)
    x = rng.uniform(rect[0] + 24, rect[2] - size - 48)
    y = rng.uniform(rect[1] + 32, rect[3] - size - 12)
    cols = rng.randint(10, 20)
    cell = size / cols
    outer = opacity_for(rng, "connectivity_matrix", role)
    shape_mode = weighted_choice(rng, [("square", 1.0), ("oval_clip", 0.75), (
        "ragged", 0.75), ("diagonal_band", 0.65), ("island", 0.55)])
    elems: List[str] = []
    if one_of(builder, 0.55):
        elems.append(
            f'<text x="{fmt(x)}" y="{fmt(y - 14)}" font-size="18" font-family="Inter, Arial, sans-serif" fill="{COLORS["ink_soft"]}" opacity="{fmt(clamp(outer * .85, .12, .42))}"></text>')
    if shape_mode in {"square", "diagonal_band"}:
        elems.append(
            f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(size)}" height="{fmt(size)}" fill="none" stroke="{COLORS["gray_soft"]}" stroke-width="1" opacity="{fmt(outer * .7)}" />')
    edges = sorted(set([0] + [rng.randint(1, cols - 2)
                   for _ in range(rng.randint(1, 3))] + [cols]))
    for rr in range(cols):
        for cc in range(cols):
            nr = (rr + 0.5) / cols * 2 - 1
            nc = (cc + 0.5) / cols * 2 - 1
            if shape_mode == "oval_clip" and (nr * nr) / 1.05 + (nc * nc) / 0.75 > 1.0:
                continue
            if shape_mode == "ragged":
                edge_distance = max(abs(nr), abs(nc))
                keep_prob = clamp(1.15 - edge_distance *
                                  0.75 + rng.uniform(-0.18, 0.18), 0.15, 1.0)
                if rng.random() > keep_prob:
                    continue
            if shape_mode == "diagonal_band" and abs(rr - cc) > rng.randint(2, 5) and rng.random() < 0.70:
                continue
            if shape_mode == "island":
                island1 = math.exp(-((nr - 0.35) ** 2 +
                                   (nc - 0.20) ** 2) / 0.16)
                island2 = math.exp(-((nr + 0.30) ** 2 +
                                   (nc + 0.35) ** 2) / 0.12)
                if rng.random() > clamp(island1 + island2 + 0.10, 0.05, 0.95):
                    continue
            if rng.random() < 0.18:
                continue
            fill = COLORS[weighted_choice(rng, [(
                "gray", 1.0), ("blue_soft", 1.0), ("indigo_soft", 1.0), ("violet_soft", 0.8)])]
            a = rng.uniform(0.10, outer)
            if abs(rr - cc) <= 1:
                a = clamp(a * 1.35, 0.08, 0.50)
            for i in range(len(edges) - 1):
                if edges[i] <= rr < edges[i + 1] and edges[i] <= cc < edges[i + 1]:
                    a = clamp(a * 1.20, 0.08, 0.48)
                    break
            rx = rng.uniform(0.5, 3.0) if shape_mode != "square" else 1.4
            elems.append(
                f'<rect x="{fmt(x + cc * cell)}" y="{fmt(y + rr * cell)}" width="{fmt(cell - 1.2)}" height="{fmt(cell - 1.2)}" fill="{fill}" opacity="{fmt(a)}" rx="{fmt(rx)}" />')
    matrix_rect = (x, y - 24, x + size, y + size)
    builder.matrix_rect = (x, y, x + size, y + size)
    builder.matrix_region = region_name
    group = f'<g data-motif-type="connectivity_matrix" data-shape-mode="{shape_mode}">{"".join(elems)}</g>'
    group = group_with_rotation(
        group, matrix_rect, rotation_for(builder, "matrix"))
    builder.add("connectivity_matrix", region_name, group, matrix_rect, 18)


def add_scalar_legend(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    if builder.matrix_rect:
        mx1, my1, mx2, my2 = builder.matrix_rect
        h, w = (my2 - my1) * rng.uniform(0.70, 0.96), rng.uniform(12, 22)
        x = clamp(mx2 + rng.uniform(12, 28), rect[0], rect[2] - w)
        y = clamp(my1 + rng.uniform(0, (my2 - my1) * .1), rect[1], rect[3] - h)
    else:
        w, h = rng.uniform(12, 22), rng.uniform(110, 220)
        x = rng.uniform(rect[0] + 24, rect[2] - w - 24)
        y = rng.uniform(rect[1] + 12, rect[3] - h - 12)
    op = opacity_for(rng, "scalar_legend", role)
    grad = f"grad_{builder.seed}_{rng.randint(0, 999999)}"
    elems = [
        f'<defs><linearGradient id="{grad}" x1="0" y1="1" x2="0" y2="0">'
        f'<stop offset="0%" stop-color="{COLORS["gray_soft"]}" />'
        f'<stop offset="38%" stop-color="{COLORS["blue_soft"]}" />'
        f'<stop offset="68%" stop-color="{COLORS["indigo_soft"]}" />'
        f'<stop offset="100%" stop-color="{COLORS["violet_soft"]}" />'
        f'</linearGradient></defs>'
    ]
    elems.append(
        f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="3" fill="url(#{grad})" opacity="{fmt(op)}" />')
    if one_of(builder, 0.65):
        for val, label in [(0, "-1.0"), (.5, "0"), (1, "1.0")]:
            yy = y + h * (1 - val)
            elems.append(
                f'<line x1="{fmt(x + w + 5)}" y1="{fmt(yy)}" x2="{fmt(x + w + 10)}" y2="{fmt(yy)}" stroke="{COLORS["ink_soft"]}" stroke-width="1" opacity="{fmt(op)}" />')
            elems.append(
                f'<text x="{fmt(x + w + 14)}" y="{fmt(yy + 5)}" font-size="14" font-family="Inter, Arial, sans-serif" fill="{COLORS["ink_soft"]}" opacity="{fmt(op)}">{label}</text>')
    builder.add("scalar_legend", region_name,
                f'<g data-motif-type="scalar_legend">{"".join(elems)}</g>', (x, y, x + w + 48, y + h), 10)


def add_time_series_stack(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL, rows: int = 5) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    w = (rect[2] - rect[0]) * rng.uniform(0.26, 0.54)
    h = (rect[3] - rect[1]) * rng.uniform(0.10, 0.24)
    x = rng.uniform(rect[0] + 48, rect[2] - w - 12)
    y = rng.uniform(rect[1] + 38, rect[3] - h - 36)
    color = color_for(rng, "time_series_stack", role)
    label_op = clamp(opacity_for(
        rng, "time_series_stack", role) * .70, .10, .36)
    show_trial_labels = one_of(builder, 0.62)
    show_time_arrow = one_of(builder, 0.52)
    wave_mode = weighted_choice(rng, [(
        "few_smooth", 0.7), ("many_noisy", 0.9), ("flat_drift", 0.45), ("burst", 0.55)])
    elems: List[str] = []
    if show_trial_labels:
        elems.append(
            f'<text x="{fmt(x)}" y="{fmt(y - 14)}" font-size="16" font-family="Inter, Arial, sans-serif" fill="{color}" opacity="{fmt(label_op)}">trial</text>')
    elif one_of(builder, 0.35):
        elems.append(
            f'<text x="{fmt(x)}" y="{fmt(y - 14)}" font-size="16" font-family="Inter, Arial, sans-serif" fill="{color}" opacity="{fmt(label_op)}">signal</text>')
    all_pts: List[Point] = []
    gap = h / max(1, rows - 1)
    samples = 12 if wave_mode != "many_noisy" else rng.randint(16, 28)
    for row in range(rows):
        pts: List[Point] = []
        base = y + row * gap
        if show_trial_labels:
            if row == rows - 1 and rows > 4:
                label = "N"
            elif row == rows - 2 and rows > 5:
                label = "…"
            else:
                label = f"{row + 1:02d}"
            elems.append(
                f'<text x="{fmt(x - 38)}" y="{fmt(base + 5)}" font-size="13" font-family="Inter, Arial, sans-serif" fill="{color}" opacity="{fmt(label_op * .85)}">{label}</text>')
        freq = rng.uniform(.75, 2.2)
        amp = gap * rng.uniform(.12, .38)
        if wave_mode == "flat_drift":
            amp *= 0.42
        if wave_mode == "burst":
            burst_center = rng.uniform(0.30, 0.75)
        else:
            burst_center = 0.5
        for i in range(samples):
            t = i / max(1, samples - 1)
            burst_gain = 1.0
            if wave_mode == "burst":
                burst_gain += 2.2 * \
                    math.exp(-((t - burst_center) ** 2) / 0.018)
            noise = rng.uniform(-2.5,
                                2.5) if wave_mode != "many_noisy" else rng.uniform(-5.0, 5.0)
            p = (x + w * t, base + math.sin(t * math.pi * 2 *
                 freq + row * .4) * amp * burst_gain + noise)
            pts.append(p)
            all_pts.append(p)
        op = clamp(opacity_for(rng, "time_series_stack", role)
                   * rng.uniform(.62, 1.02), .08, .40)
        elems.append(
            f'<path d="{path_from_points(pts)}" fill="none" stroke="{color}" stroke-width="{fmt(rng.uniform(0.75, 1.6))}" stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(op)}" />')
    if show_time_arrow:
        arrow_y = y + h + 24
        elems.append(
            f'<line x1="{fmt(x)}" y1="{fmt(arrow_y)}" x2="{fmt(x + w * .92)}" y2="{fmt(arrow_y)}" stroke="{color}" stroke-width="0.8" opacity="{fmt(label_op * .7)}" />')
        elems.append(
            f'<path d="M {fmt(x + w * .92)} {fmt(arrow_y)} L {fmt(x + w * .92 - 8)} {fmt(arrow_y - 4)} L {fmt(x + w * .92 - 8)} {fmt(arrow_y + 4)} Z" fill="{color}" opacity="{fmt(label_op * .7)}" />')
        elems.append(
            f'<text x="{fmt(x + w * .45)}" y="{fmt(arrow_y + 18)}" font-size="12" font-family="Inter, Arial, sans-serif" fill="{color}" opacity="{fmt(label_op * .65)}">time</text>')
        all_pts.append((x + w, arrow_y + 18))
    plot_rect = polyline_bounds(all_pts, 18)
    group = f'<g data-motif-type="time_series_stack" data-shape-mode="{wave_mode}">{"".join(elems)}</g>'
    group = group_with_rotation(
        group, plot_rect, rotation_for(builder, "traces"))
    builder.add("time_series_stack", region_name, group, plot_rect, 24)


def add_voxel_fragment(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    cols, rows = rng.randint(12, 28), rng.randint(8, 18)
    w = (rect[2] - rect[0]) * rng.uniform(0.30, 0.60)
    h = (rect[3] - rect[1]) * rng.uniform(0.22, 0.48)
    x = rng.uniform(rect[0] + 12, rect[2] - w - 12)
    y = rng.uniform(rect[1] + 10, rect[3] - h - 10)
    cw, ch = w / cols, h / rows
    cx, cy = x + w / 2, y + h / 2
    shape_mode = weighted_choice(
        rng, [("blob", 1.0), ("crescent", 0.45), ("ragged_sheet", 0.75), ("islands", 0.60)])
    elems: List[str] = []
    for rr in range(rows):
        for cc in range(cols):
            px, py = x + cc * cw, y + rr * ch
            nx, ny = (px + cw / 2 - cx) / (w / 2), (py + ch / 2 - cy) / (h / 2)
            field = math.exp(-2.2 * (nx * nx + ny * ny)) + .22 * \
                math.sin(3 * nx) * math.cos(4 * ny) + rng.uniform(-.08, .08)
            if shape_mode == "crescent":
                field -= 0.62 * \
                    math.exp(-4.0 * ((nx - .25) ** 2 + (ny + .05) ** 2))
            elif shape_mode == "ragged_sheet":
                field += rng.uniform(-.25, .18)
            elif shape_mode == "islands":
                field = max(
                    math.exp(-6 * ((nx - .35) ** 2 + (ny - .2) ** 2)),
                    math.exp(-7 * ((nx + .30) ** 2 + (ny + .25) ** 2)),
                    math.exp(-8 * ((nx - .05) ** 2 + (ny + .45) ** 2)),
                ) + rng.uniform(-.08, .10)
            if field < .08 and rng.random() < .70:
                continue
            fill = COLORS[weighted_choice(
                rng, [("gray", 1.8), ("blue_soft", 1.0), ("indigo_soft", .9), ("violet_soft", .7)])]
            op = clamp(opacity_for(rng, "voxel_fragment", role) *
                       (.45 + .85 * clamp(field + .25, 0, 1)), .06, .42)
            elems.append(
                f'<rect x="{fmt(px)}" y="{fmt(py)}" width="{fmt(cw - .8)}" height="{fmt(ch - .8)}" fill="{fill}" opacity="{fmt(op)}" rx="{fmt(rng.uniform(.6, 2.5))}" />')
    plot_rect = (x, y, x + w, y + h)
    group = f'<g data-motif-type="voxel_fragment" data-shape-mode="{shape_mode}">{"".join(elems)}</g>'
    group = group_with_rotation(
        group, plot_rect, rotation_for(builder, "voxel"))
    builder.add("voxel_fragment", region_name, group, plot_rect, 16)


def add_event_raster_fragment(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    w = (rect[2] - rect[0]) * rng.uniform(.25, .54)
    rows, gap = rng.randint(3, 8), rng.uniform(16, 30)
    x = rng.uniform(rect[0] + 8, rect[2] - w - 8)
    y = rng.uniform(rect[1] + 16, rect[3] - gap * rows - 16)
    color = color_for(rng, "event_raster_fragment", role)
    base = opacity_for(rng, "event_raster_fragment", role)
    mode = weighted_choice(
        rng, [("ticks", 1.0), ("dots", 0.7), ("mixed", 1.2), ("bursty", 0.7)])
    elems: List[str] = []
    pts: List[Point] = []
    for row in range(rows):
        yy = y + row * gap
        if one_of(builder, 0.55):
            elems.append(
                f'<line x1="{fmt(x)}" y1="{fmt(yy)}" x2="{fmt(x + w)}" y2="{fmt(yy)}" stroke="{color}" stroke-width="0.6" opacity="{fmt(base * .25)}" />')
        n_events = rng.randint(6, 14)
        if mode == "bursty":
            center = rng.uniform(0.25, 0.80)
            events = [x + w * clamp(rng.gauss(center, 0.12), 0, 1)
                      for _ in range(n_events)]
        else:
            events = [x + rng.uniform(0, w) for _ in range(n_events)]
        for ex in sorted(events):
            op = clamp(base * rng.uniform(.55, 1.08), .06, .40)
            draw_dot = mode == "dots" or (
                mode == "mixed" and rng.random() < .45)
            if draw_dot:
                elems.append(
                    f'<circle cx="{fmt(ex)}" cy="{fmt(yy)}" r="{fmt(rng.uniform(.9, 2.2))}" fill="{color}" opacity="{fmt(op)}" />')
            else:
                y2 = yy + rng.uniform(5, 15)
                elems.append(
                    f'<line x1="{fmt(ex)}" y1="{fmt(yy)}" x2="{fmt(ex)}" y2="{fmt(y2)}" stroke="{color}" stroke-width="{fmt(rng.uniform(.7, 1.3))}" stroke-linecap="round" opacity="{fmt(op)}" />')
            pts.append((ex, yy))
    if pts:
        plot_rect = polyline_bounds(pts, 10)
        group = f'<g data-motif-type="event_raster_fragment" data-shape-mode="{mode}">{"".join(elems)}</g>'
        group = group_with_rotation(
            group, plot_rect, rotation_for(builder, "raster"))
        builder.add("event_raster_fragment", region_name, group, plot_rect, 22)


def add_design_matrix_fragment(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    cols, rows = rng.randint(4, 9), rng.randint(10, 24)
    w = (rect[2] - rect[0]) * rng.uniform(.12, .28)
    h = (rect[3] - rect[1]) * rng.uniform(.22, .48)
    x = rng.uniform(rect[0] + 10, rect[2] - w - 10)
    y = rng.uniform(rect[1] + 10, rect[3] - h - 10)
    cw, ch = w / cols, h / rows
    base = opacity_for(rng, "design_matrix_fragment", role)
    shape_mode = weighted_choice(rng, [(
        "rectangular", 0.9), ("ragged", 0.7), ("columns_only", 0.55), ("event_sparse", 0.65)])
    elems: List[str] = []
    for cc in range(cols):
        mode = weighted_choice(
            rng, [("event", 1.0), ("sin", 1.0), ("ramp", .8), ("noise", .8)])
        for rr in range(rows):
            if shape_mode == "ragged" and rng.random() < 0.18:
                continue
            if shape_mode == "columns_only" and cc % 2 == 1 and rng.random() < 0.74:
                continue
            if shape_mode == "event_sparse" and rng.random() < 0.50:
                continue
            if mode == "event":
                a = base * (1.1 if rng.random() < .14 else .20)
            elif mode == "sin":
                a = base * (.20 + .80 * (.5 + .5 * math.sin(rr /
                            rows * math.pi * rng.uniform(1.2, 3.2) + cc)))
            elif mode == "ramp":
                a = base * (.18 + .82 * rr / max(1, rows - 1))
            else:
                a = base * rng.uniform(.10, .90)
            if rng.random() < .10:
                a *= .2
            fill = COLORS[weighted_choice(
                rng, [("gray", 1.5), ("blue_soft", 1.0), ("indigo_soft", 1.0), ("violet_soft", .8)])]
            elems.append(
                f'<rect x="{fmt(x + cc * cw)}" y="{fmt(y + rr * ch)}" width="{fmt(cw - .8)}" height="{fmt(ch - .8)}" fill="{fill}" opacity="{fmt(clamp(a, .04, .42))}" rx="{fmt(rng.uniform(.6, 1.8))}" />')
    plot_rect = (x, y, x + w, y + h)
    group = f'<g data-motif-type="design_matrix_fragment" data-shape-mode="{shape_mode}">{"".join(elems)}</g>'
    group = group_with_rotation(
        group, plot_rect, rotation_for(builder, "matrix"))
    builder.add("design_matrix_fragment", region_name, group, plot_rect, 16)


def add_belief_update_curve(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    w = (rect[2] - rect[0]) * rng.uniform(.24, .52)
    h = (rect[3] - rect[1]) * rng.uniform(.08, .22)
    x0 = rng.uniform(rect[0] + 12, rect[2] - w - 12)
    y0 = rng.uniform(rect[1] + h + 12, rect[3] - h - 12)
    mode = weighted_choice(
        rng, [("sigmoid", 1.0), ("step", 0.55), ("decay", 0.55), ("oscillatory", 0.45)])
    pts: List[Point] = []
    n = rng.randint(7, 12)
    for i in range(n):
        t = i / max(1, n - 1)
        if mode == "sigmoid":
            val = 1 / (1 + math.exp(-8 * (t - .5))) - .5
        elif mode == "step":
            val = -0.35 if t < rng.uniform(.35, .55) else 0.35
        elif mode == "decay":
            val = 0.6 * math.exp(-3 * t) - 0.3
        else:
            val = 0.35 * math.sin(t * 2 * math.pi * rng.uniform(1.0, 2.0))
        pts.append((x0 + w * t, y0 - h * val + rng.uniform(-h * .06, h * .06)))
    color = color_for(rng, "belief_update_curve", role)
    op = opacity_for(rng, "belief_update_curve", role)
    elems = [
        f'<path d="{path_from_points(pts)}" fill="none" stroke="{color}" stroke-width="{fmt(rng.uniform(0.9, 1.8))}" stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(op)}" />']
    for npt in rng.sample(pts[1:-1], k=min(len(pts) - 2, rng.randint(1, 4))):
        elems.append(
            f'<circle cx="{fmt(npt[0])}" cy="{fmt(npt[1])}" r="{fmt(rng.uniform(1.6, 3.2))}" fill="{color}" opacity="{fmt(op * .72)}" />')
    builder.add("belief_update_curve", region_name,
                f'<g data-motif-type="belief_update_curve" data-shape-mode="{mode}">{"".join(elems)}</g>', polyline_bounds(pts, 16), 20)


def add_prediction_error_pulses(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    w = (rect[2] - rect[0]) * rng.uniform(.24, .52)
    x0 = rng.uniform(rect[0] + 12, rect[2] - w - 12)
    y0 = rng.uniform(rect[1] + 24, rect[3] - 24)
    color = color_for(rng, "prediction_error_pulses", role)
    op = opacity_for(rng, "prediction_error_pulses", role)
    elems = [
        f'<line x1="{fmt(x0)}" y1="{fmt(y0)}" x2="{fmt(x0 + w)}" y2="{fmt(y0)}" stroke="{color}" stroke-width="0.8" opacity="{fmt(op * .30)}" />']
    pts = [(x0, y0), (x0 + w, y0)]
    n = rng.randint(6, 15)
    signed_bias = rng.uniform(-0.25, 0.25)
    for i in range(n):
        t = i / max(1, n - 1)
        x = x0 + w * t + rng.uniform(-4, 4)
        direction = -1 if rng.random() < 0.5 + signed_bias else 1
        y2 = y0 + direction * rng.uniform(8, 42)
        pts.append((x, y2))
        elems.append(f'<line x1="{fmt(x)}" y1="{fmt(y0)}" x2="{fmt(x)}" y2="{fmt(y2)}" stroke="{color}" stroke-width="{fmt(rng.uniform(0.8, 1.6))}" stroke-linecap="round" opacity="{fmt(op * rng.uniform(.55, 1.02))}" />')
    builder.add("prediction_error_pulses", region_name,
                f'<g data-motif-type="prediction_error_pulses">{"".join(elems)}</g>', polyline_bounds(pts, 16), 20)


def add_posterior_density_ridge(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL, ridges: int = 3) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    w = (rect[2] - rect[0]) * rng.uniform(.20, .44)
    h = (rect[3] - rect[1]) * rng.uniform(.06, .16)
    x0 = rng.uniform(rect[0] + 12, rect[2] - w - 12)
    y0 = rng.uniform(rect[1] + 30, rect[3] - h * ridges - 24)
    color = color_for(rng, "posterior_density_ridge", role)
    op = opacity_for(rng, "posterior_density_ridge", role)
    mode = weighted_choice(
        rng, [("single_peak", 1.0), ("double_peak", 0.55), ("skewed", 0.55)])
    elems: List[str] = []
    boxes: List[Rect] = []
    for r in range(ridges):
        base = y0 + r * h * rng.uniform(.65, .96)
        center, spread = rng.uniform(.32, .68), rng.uniform(.025, .075)
        pts: List[Point] = []
        for i in range(14):
            t = i / 13
            if mode == "double_peak":
                dens = math.exp(-((t - center) ** 2) / spread) + 0.65 * \
                    math.exp(-((t - rng.uniform(.55, .82)) ** 2) /
                             (spread * 0.8))
            elif mode == "skewed":
                dens = math.exp(-((t - center) ** 2) /
                                spread) * (0.55 + 1.1 * t)
            else:
                dens = math.exp(-((t - center) ** 2) / spread)
            pts.append((x0 + w * t, base - dens * h *
                       rng.uniform(.42, .82) + rng.uniform(-2, 2)))
        closed = pts + [(x0 + w, base + 5), (x0, base + 5)]
        elems.append(
            f'<path d="{path_from_points(closed)} Z" fill="{color}" opacity="{fmt(op * .20)}" />')
        elems.append(
            f'<path d="{path_from_points(pts)}" fill="none" stroke="{color}" stroke-width="{fmt(rng.uniform(.7, 1.3))}" stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(op)}" />')
        boxes.append(polyline_bounds(closed, 8))
    builder.add("posterior_density_ridge", region_name,
                f'<g data-motif-type="posterior_density_ridge" data-shape-mode="{mode}">{"".join(elems)}</g>', rect_union(boxes), 18)


def add_topography_fragment(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL, rings: int = 5) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    c = sample_point(rng, rect)
    rx0 = (rect[2] - rect[0]) * rng.uniform(.06, .16)
    ry0 = (rect[3] - rect[1]) * rng.uniform(.04, .13)
    color = color_for(rng, "density_contours", role)
    op = opacity_for(rng, "density_contours", role)
    elems: List[str] = []
    all_pts: List[Point] = []
    for ring in range(rings):
        t = 1 - ring / max(1, rings - 1)
        pts: List[Point] = []
        for i in range(18):
            a = 2 * math.pi * i / 18 + rng.uniform(0, math.pi)
            rough = 1 + .11 * math.sin(3 * a) + rng.uniform(-.06, .06)
            p = (c[0] + math.cos(a) * rx0 * (0.36 + .72 * t) * rough,
                 c[1] + math.sin(a) * ry0 * (0.36 + .72 * t) * rough)
            pts.append(p)
            all_pts.append(p)
        pts.append(pts[0])
        elems.append(f'<path d="{path_from_points(pts)} Z" fill="none" stroke="{color}" stroke-width="{fmt(rng.uniform(.6, 1.2))}" stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(op * (.50 + .38 * t))}" />')
    builder.add("topography_fragment", region_name,
                f'<g data-motif-type="topography_fragment">{"".join(elems)}</g>', polyline_bounds(all_pts, 12), 22)


def add_scan_echo(builder: Builder, region_name: str, role: str = ROLE_STRUCTURAL) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    color = color_for(rng, "voxel_fragment", role)
    op = opacity_for(rng, "voxel_fragment", role)
    elems: List[str] = []
    boxes: List[Rect] = []
    for _ in range(rng.randint(3, 9)):
        w = (rect[2] - rect[0]) * rng.uniform(.026, .075)
        h = (rect[3] - rect[1]) * rng.uniform(.022, .070)
        x = rng.uniform(rect[0] + 8, rect[2] - w - 8)
        y = rng.uniform(rect[1] + 8, rect[3] - h - 8)
        cx, cy = x + w / 2, y + h / 2
        elems.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}" rx="{fmt(rng.uniform(3, 11))}" fill="{color}" opacity="{fmt(op * rng.uniform(.40, .95))}" transform="rotate({fmt(rng.uniform(-16, 16))} {fmt(cx)} {fmt(cy)})" />')
        boxes.append((x, y, x + w, y + h))
    builder.add("scan_echo", region_name,
                f'<g data-motif-type="scan_echo">{"".join(elems)}</g>', rect_union(boxes), 18)


def add_state_space_label(builder: Builder, region_name: str, role: str = ROLE_AMBIENT) -> None:
    rect = builder.region(region_name).bounds
    rng = builder.rng
    color = color_for(rng, "state_space_label", role)
    op = clamp(opacity_for(rng, "state_space_label", role) * 0.75, 0.08, 0.32)
    x, y = sample_point(rng, rect, (1.3, 1.6), (1.2, 1.8))
    n = rng.randint(5, 9)
    dots = []
    for i in range(n):
        dots.append(
            f'<circle cx="{fmt(x + i * 14)}" cy="{fmt(y + 22)}" r="{fmt(rng.uniform(2.0, 3.4))}" fill="{color}" opacity="{fmt(op * rng.uniform(.65, 1.2))}" />')
    elems = [
        f'<text x="{fmt(x)}" y="{fmt(y)}" font-size="15" font-family="Inter, Arial, sans-serif" fill="{color}" opacity="{fmt(op)}">state space</text>', *dots]
    builder.add("state_space_label", region_name,
                f'<g data-motif-type="state_space_label">{"".join(elems)}</g>', (x, y - 16, x + n * 14 + 8, y + 30), 8)


# -----------------------------------------------------------------------------
# Probabilistic scene grammar
# -----------------------------------------------------------------------------


MOTIF_PALETTES: Dict[str, Sequence[MotifSpec]] = {
    "minimal": [
        MotifSpec("ambient_dot_grid", 0.55, (0, 1), [
                  ("left_outer", 1.0), ("left_middle", 0.7), ("right_lower", 0.45)], [(ROLE_AMBIENT, 1.0)]),
        MotifSpec("density_contours", 0.75, (1, 2), [("center_bridge", 1.2), ("left_upper", 0.8), (
            "right_middle", 0.8), ("right_lower", 0.45)], [(ROLE_AMBIENT, 0.8), (ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("flow_streamlines", 0.82, (1, 2), [("center_bridge", 1.3), ("right_middle", 1.2), (
            "left_middle", 0.45)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.5)]),
        MotifSpec("vector_field", 0.72, (0, 2), [("center_bridge", 1.2), ("right_middle", 1.2), (
            "left_middle", 0.55)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.6)]),
        MotifSpec("posterior_cloud", 0.82, (1, 2), [("right_middle", 1.2), ("center_bridge", 1.1), (
            "left_middle", 0.55)], [(ROLE_ANCHOR, 1.0), (ROLE_STRUCTURAL, 0.6)]),
        MotifSpec("latent_trajectory", 0.78, (1, 2), [("right_middle", 1.2), ("center_bridge", 1.2), (
            "left_middle", 0.55)], [(ROLE_ANCHOR, 1.0), (ROLE_STRUCTURAL, 0.7)]),
        MotifSpec("connectivity_matrix", 0.28, (0, 1), [("right_upper", 1.0), ("right_middle", 0.8), (
            "right_lower", 0.7), ("left_middle", 0.35)], [(ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("voxel_fragment", 0.36, (0, 1), [("right_lower", 1.0), ("right_middle", 0.8), (
            "center_bridge", 0.55), ("left_middle", 0.45)], [(ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("time_series_stack", 0.36, (0, 1), [("right_middle", 1.0), ("right_upper", 0.8), (
            "right_lower", 0.8), ("left_middle", 0.55)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.5)]),
        MotifSpec("latent_axes", 0.28, (0, 1), [("center_bridge", 1.0), ("right_lower", 0.75), (
            "left_middle", 0.55)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.6)]),
        MotifSpec("posterior_density_ridge", 0.42, (0, 2), [("left_outer", 1.0), ("left_upper", 0.7), (
            "right_lower", 0.75), ("center_bridge", 0.55)], [(ROLE_AMBIENT, 0.8), (ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("event_raster_fragment", 0.24, (0, 1), [("left_middle", 1.0), ("center_bridge", 0.8), (
            "right_middle", 0.7), ("right_lower", 0.6)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.6)]),
        MotifSpec("state_space_label", 0.26, (0, 1), [("left_upper", 0.9), ("center_bridge", 0.8), (
            "right_upper", 0.65), ("left_middle", 0.45)], [(ROLE_AMBIENT, 1.0), (ROLE_STRUCTURAL, 0.5)]),
    ],
    "spacefill": [
        MotifSpec("ambient_dot_grid", 0.75, (0, 2), [
                  ("left_outer", 1.0), ("left_middle", 0.8), ("right_lower", 0.5)], [(ROLE_AMBIENT, 1.0)]),
        MotifSpec("density_contours", 0.88, (1, 3), [("center_bridge", 1.2), ("left_upper", 0.9), (
            "right_middle", 0.9), ("right_lower", 0.65)], [(ROLE_AMBIENT, 0.7), (ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("flow_streamlines", 0.92, (1, 2), [("center_bridge", 1.2), ("right_middle", 1.2), (
            "left_middle", 0.55)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.5)]),
        MotifSpec("vector_field", 0.82, (1, 2), [("center_bridge", 1.2), ("right_middle", 1.2), (
            "left_middle", 0.55)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.6)]),
        MotifSpec("posterior_cloud", 0.90, (1, 3), [("right_middle", 1.2), ("center_bridge", 1.1), (
            "left_middle", 0.55)], [(ROLE_ANCHOR, 1.0), (ROLE_STRUCTURAL, 0.7)]),
        MotifSpec("latent_trajectory", 0.86, (1, 2), [("right_middle", 1.2), ("center_bridge", 1.2), (
            "left_middle", 0.55)], [(ROLE_ANCHOR, 1.0), (ROLE_STRUCTURAL, 0.7)]),
        MotifSpec("connectivity_matrix", 0.42, (0, 2), [("right_upper", 1.0), ("right_middle", 0.9), (
            "right_lower", 0.7), ("left_middle", 0.45)], [(ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("voxel_fragment", 0.50, (0, 2), [("right_lower", 1.0), ("right_middle", 0.8), (
            "center_bridge", 0.55), ("left_middle", 0.45)], [(ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("time_series_stack", 0.50, (0, 2), [("right_middle", 1.0), ("right_upper", 0.8), (
            "right_lower", 0.8), ("left_middle", 0.55)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.5)]),
        MotifSpec("latent_axes", 0.36, (0, 1), [("center_bridge", 1.0), ("right_lower", 0.8), (
            "left_middle", 0.6)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.6)]),
        MotifSpec("posterior_density_ridge", 0.55, (0, 3), [("left_outer", 1.0), ("left_upper", 0.7), (
            "right_lower", 0.75), ("center_bridge", 0.55)], [(ROLE_AMBIENT, 0.8), (ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("event_raster_fragment", 0.36, (0, 2), [("left_middle", 1.0), ("center_bridge", 0.8), (
            "right_middle", 0.7), ("right_lower", 0.6)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.6)]),
        MotifSpec("design_matrix_fragment", 0.28, (0, 1), [("right_middle", 0.9), (
            "right_lower", 0.8), ("center_bridge", 0.7), ("left_middle", 0.45)], [(ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("state_space_label", 0.34, (0, 1), [("left_upper", 0.9), ("center_bridge", 0.8), (
            "right_upper", 0.65), ("left_middle", 0.45)], [(ROLE_AMBIENT, 1.0), (ROLE_STRUCTURAL, 0.5)]),
    ],
    "maximal": [
        MotifSpec("ambient_dot_grid", 0.90, (1, 3), [("left_outer", 1.0), ("left_middle", 0.9), (
            "right_lower", 0.65), ("right_upper", 0.4)], [(ROLE_AMBIENT, 1.0)]),
        MotifSpec("density_contours", 0.95, (2, 4), [("center_bridge", 1.2), ("left_upper", 0.9), ("right_middle", 0.9), (
            "right_lower", 0.7), ("left_middle", 0.55)], [(ROLE_AMBIENT, 0.7), (ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("flow_streamlines", 0.96, (1, 3), [("center_bridge", 1.2), ("right_middle", 1.2), (
            "left_middle", 0.65)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.5)]),
        MotifSpec("vector_field", 0.90, (1, 3), [("center_bridge", 1.2), ("right_middle", 1.2), (
            "left_middle", 0.65), ("right_lower", 0.55)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.6)]),
        MotifSpec("posterior_cloud", 0.94, (1, 3), [("right_middle", 1.2), ("center_bridge", 1.1), (
            "left_middle", 0.65), ("right_lower", 0.55)], [(ROLE_ANCHOR, 1.0), (ROLE_STRUCTURAL, 0.8)]),
        MotifSpec("latent_trajectory", 0.92, (1, 3), [("right_middle", 1.2), ("center_bridge", 1.2), (
            "left_middle", 0.65), ("right_lower", 0.55)], [(ROLE_ANCHOR, 1.0), (ROLE_STRUCTURAL, 0.8)]),
        MotifSpec("connectivity_matrix", 0.50, (0, 2), [("right_upper", 1.0), ("right_middle", 0.9), (
            "right_lower", 0.8), ("left_middle", 0.55)], [(ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("voxel_fragment", 0.62, (0, 2), [("right_lower", 1.0), ("right_middle", 0.85), (
            "center_bridge", 0.6), ("left_middle", 0.55)], [(ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("time_series_stack", 0.62, (0, 2), [("right_middle", 1.0), ("right_upper", 0.8), (
            "right_lower", 0.8), ("left_middle", 0.65)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.5)]),
        MotifSpec("latent_axes", 0.50, (0, 2), [("center_bridge", 1.0), ("right_lower", 0.8), (
            "left_middle", 0.7), ("right_upper", 0.45)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.6)]),
        MotifSpec("posterior_density_ridge", 0.72, (0, 4), [("left_outer", 1.0), ("left_upper", 0.7), (
            "right_lower", 0.8), ("center_bridge", 0.6)], [(ROLE_AMBIENT, 0.8), (ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("event_raster_fragment", 0.50, (0, 2), [("left_middle", 1.0), ("center_bridge", 0.8), (
            "right_middle", 0.8), ("right_lower", 0.7)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.6)]),
        MotifSpec("design_matrix_fragment", 0.42, (0, 2), [("right_middle", 0.9), (
            "right_lower", 0.8), ("center_bridge", 0.7), ("left_middle", 0.55)], [(ROLE_STRUCTURAL, 1.0)]),
        MotifSpec("prediction_error_pulses", 0.42, (0, 2), [("left_middle", 0.9), (
            "right_lower", 0.8), ("center_bridge", 0.6)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.5)]),
        MotifSpec("belief_update_curve", 0.42, (0, 2), [("left_upper", 0.9), ("left_middle", 0.75), (
            "center_bridge", 0.55), ("right_lower", 0.45)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.5)]),
        MotifSpec("topography_fragment", 0.38, (0, 2), [("left_middle", 0.9), ("right_lower", 0.8), (
            "center_bridge", 0.55)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.5)]),
        MotifSpec("scan_echo", 0.30, (0, 1), [("right_lower", 0.9), ("right_middle", 0.75), (
            "center_bridge", 0.5), ("left_middle", 0.35)], [(ROLE_STRUCTURAL, 1.0), (ROLE_AMBIENT, 0.4)]),
        MotifSpec("state_space_label", 0.42, (0, 1), [("left_upper", 0.9), ("center_bridge", 0.8), (
            "right_upper", 0.65), ("left_middle", 0.45)], [(ROLE_AMBIENT, 1.0), (ROLE_STRUCTURAL, 0.5)]),
    ],
}


def add_motif_from_spec(builder: Builder, spec: MotifSpec) -> None:
    rng = builder.rng
    if not one_of(builder, spec.p):
        return
    count = rng.randint(spec.count_range[0], spec.count_range[1])
    if count <= 0:
        return
    for _ in range(count):
        region = choose_region(builder, family=spec.name,
                               candidates=spec.region_weights, avoid_reuse=False)
        role = weighted_choice(rng, spec.role_weights)
        if spec.name == "ambient_dot_grid":
            add_ambient_dot_grid(builder, region, role, cols=rng.randint(
                7, 24), rows=rng.randint(5, 16))
        elif spec.name == "density_contours":
            add_density_contours(builder, region, role,
                                 bands=rng.randint(3, 8))
        elif spec.name == "flow_streamlines":
            add_flow_streamlines(builder, region, role,
                                 lines=rng.randint(6, 24))
        elif spec.name == "vector_field":
            add_vector_field(builder, region, role, cols=rng.randint(
                8, 20), rows=rng.randint(6, 13))
        elif spec.name == "posterior_cloud":
            add_posterior_cloud(builder, region, role,
                                count=rng.randint(90, 520))
        elif spec.name == "latent_trajectory":
            add_latent_trajectory(builder, region, role,
                                  multiplicity=rng.randint(1, 3))
        elif spec.name == "connectivity_matrix":
            add_connectivity_matrix(builder, region, role)
            if one_of(builder, 0.35):
                add_scalar_legend(builder, region, role)
        elif spec.name == "voxel_fragment":
            add_voxel_fragment(builder, region, role)
        elif spec.name == "time_series_stack":
            add_time_series_stack(builder, region, role,
                                  rows=rng.randint(3, 8))
        elif spec.name == "latent_axes":
            add_latent_axes(builder, region, role)
        elif spec.name == "posterior_density_ridge":
            add_posterior_density_ridge(
                builder, region, role, ridges=rng.randint(1, 5))
        elif spec.name == "event_raster_fragment":
            add_event_raster_fragment(builder, region, role)
        elif spec.name == "design_matrix_fragment":
            add_design_matrix_fragment(builder, region, role)
        elif spec.name == "prediction_error_pulses":
            add_prediction_error_pulses(builder, region, role)
        elif spec.name == "belief_update_curve":
            add_belief_update_curve(builder, region, role)
        elif spec.name == "topography_fragment":
            add_topography_fragment(
                builder, region, role, rings=rng.randint(3, 8))
        elif spec.name == "scan_echo":
            add_scan_echo(builder, region, role)
        elif spec.name == "state_space_label":
            add_state_space_label(builder, region, role)


def compose(builder: Builder) -> None:
    palette = MOTIF_PALETTES[builder.variant]
    specs = list(palette)
    builder.rng.shuffle(specs)
    background_first = {"ambient_dot_grid", "density_contours",
                        "flow_streamlines", "vector_field", "posterior_cloud"}
    foreground_late = {"latent_trajectory", "connectivity_matrix", "time_series_stack",
                       "event_raster_fragment", "latent_axes", "design_matrix_fragment", "state_space_label"}
    for spec in [s for s in specs if s.name in background_first]:
        add_motif_from_spec(builder, spec)
    for spec in [s for s in specs if s.name not in background_first and s.name not in foreground_late]:
        add_motif_from_spec(builder, spec)
    for spec in [s for s in specs if s.name in foreground_late]:
        add_motif_from_spec(builder, spec)
    if builder.stats.motif_counts.get("posterior_cloud", 0) == 0 and builder.stats.motif_counts.get("latent_trajectory", 0) == 0:
        region = weighted_choice(builder.rng, [(
            "center_bridge", 1.0), ("right_middle", 1.0), ("left_middle", 0.5)])
        add_posterior_cloud(builder, region, ROLE_ANCHOR,
                            count=builder.rng.randint(160, 340))
    if builder.stats.motif_counts.get("flow_streamlines", 0) == 0 and builder.stats.motif_counts.get("vector_field", 0) == 0:
        region = weighted_choice(builder.rng, [(
            "center_bridge", 1.0), ("right_middle", 1.0), ("left_middle", 0.5)])
        add_flow_streamlines(builder, region, ROLE_STRUCTURAL,
                             lines=builder.rng.randint(8, 16))


# -----------------------------------------------------------------------------
# Quality checks and rendering
# -----------------------------------------------------------------------------


def coverage_report(builder: Builder) -> None:
    for name, region in builder.regions.items():
        builder.stats.region_coverage[name] = round(
            builder.coverage.fraction_for_rect(region.bounds), 4)
    builder.stats.overall_coverage = round(
        builder.coverage.overall_fraction(), 4)


def generation_is_acceptable(builder: Builder) -> bool:
    coverage_report(builder)
    counts = builder.stats.motif_counts
    has_dynamics = counts.get("flow_streamlines", 0) + counts.get(
        "vector_field", 0) + counts.get("latent_trajectory", 0) >= 1
    has_distribution = counts.get("posterior_cloud", 0) + counts.get(
        "density_contours", 0) + counts.get("posterior_density_ridge", 0) >= 1
    has_diagnostic = (
        counts.get("connectivity_matrix", 0)
        + counts.get("voxel_fragment", 0)
        + counts.get("time_series_stack", 0)
        + counts.get("event_raster_fragment", 0)
        + counts.get("design_matrix_fragment", 0)
        + counts.get("latent_axes", 0)
    ) >= 1
    if not has_dynamics or not has_distribution:
        return False
    if builder.variant in {"spacefill", "maximal"} and not has_diagnostic:
        return False
    if builder.variant == "minimal":
        return builder.stats.overall_coverage >= 0.07
    if builder.variant == "spacefill":
        return builder.stats.overall_coverage >= 0.12
    return builder.stats.overall_coverage >= 0.17


def render_svg(builder: Builder) -> str:
    bg_group = '<g class="neuro-background">' + \
        "".join(builder.elements) + "</g>"
    debug = ""
    if builder.debug_overlay:
        boxes: List[str] = []
        for name, region in builder.regions.items():
            fill, stroke = REGION_DEBUG_STYLES[name]
            x1, y1, x2, y2 = region.bounds
            boxes.append(
                f'<rect x="{fmt(x1)}" y="{fmt(y1)}" width="{fmt(x2 - x1)}" height="{fmt(y2 - y1)}" fill="{fill}" stroke="{stroke}" stroke-width="1.4" stroke-dasharray="10 8" />')
            boxes.append(
                f'<text x="{fmt(x1 + 12)}" y="{fmt(y1 + 18)}" font-size="16" font-family="Inter, Arial, sans-serif" fill="{stroke}">{name}</text>')
        debug = '<g class="debug-regions">' + \
            "".join(boxes + builder.debug_elements) + "</g>"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{builder.width}" height="{builder.height}" viewBox="0 0 {builder.width} {builder.height}" fill="none">
{bg_group}
{debug}
</svg>'''


def generate_candidate(width: int, height: int, variant: str, seed: int, debug_overlay: bool) -> Builder:
    builder = Builder(width, height, seed, variant, debug_overlay)
    compose(builder)
    coverage_report(builder)
    return builder


def generate_best(width: int, height: int, variant: str, seed: int, debug_overlay: bool, max_attempts: int = 24) -> Builder:
    best: Optional[Builder] = None
    best_score = -1.0
    weights = {
        "left_outer": 0.08,
        "left_middle": 0.12,
        "center_bridge": 0.24,
        "right_upper": 0.09,
        "right_middle": 0.24,
        "right_lower": 0.11,
        "left_upper": 0.06,
    }
    for attempt in range(max_attempts):
        candidate_seed = seed + attempt * 9973
        builder = generate_candidate(
            width, height, variant, candidate_seed, debug_overlay)
        score = builder.stats.overall_coverage + \
            sum(builder.stats.region_coverage.get(
                k, 0) * w for k, w in weights.items())
        builder.stats.attempts = attempt + 1
        if generation_is_acceptable(builder):
            return builder
        if score > best_score:
            best = builder
            best_score = score
    assert best is not None
    return best


def motif_presence_classes(builder: Builder) -> Dict[str, bool]:
    c = builder.stats.motif_counts
    return {
        "has_matrix": c.get("connectivity_matrix", 0) > 0,
        "has_trial_traces": c.get("time_series_stack", 0) > 0,
        "has_axes": c.get("latent_axes", 0) > 0,
        "has_state_space_label": c.get("state_space_label", 0) > 0,
        "has_distribution_heavy": c.get("posterior_cloud", 0) + c.get("density_contours", 0) + c.get("posterior_density_ridge", 0) >= 3,
        "has_diagnostic_texture": c.get("connectivity_matrix", 0) + c.get("voxel_fragment", 0) + c.get("time_series_stack", 0) + c.get("event_raster_fragment", 0) + c.get("design_matrix_fragment", 0) >= 1,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate probabilistic computational-neuroscience SVG backgrounds.")
    parser.add_argument("--variant", default=DEFAULT_VARIANT,
                        choices=["minimal", "spacefill", "maximal"])
    parser.add_argument("--seed", type=int, default=10)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stats-output", type=Path)
    parser.add_argument("--debug-overlay", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=24)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    builder = generate_best(args.width, args.height, args.variant,
                            args.seed, args.debug_overlay, args.max_attempts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_svg(builder), encoding="utf-8")
    if args.stats_output:
        args.stats_output.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "variant": args.variant,
            "requested_seed": args.seed,
            "chosen_seed": builder.seed,
            "attempts": builder.stats.attempts,
            "motif_counts": builder.stats.motif_counts,
            "motif_presence_classes": motif_presence_classes(builder),
            "region_coverage": builder.stats.region_coverage,
            "overall_coverage": builder.stats.overall_coverage,
        }
        args.stats_output.write_text(json.dumps(
            payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
