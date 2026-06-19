#!/usr/bin/env python3
"""Generate static SVG neuro background assets.

The generator matches the current site background grammar:
- faint contour/vector-field curves
- posterior-like dot clouds
- a restrained latent-state trajectory with sparse nodes
- small matrix/grid fragments

It is deterministic for a given seed and variant.
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


Point = Tuple[float, float]

DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 900

CLIP_PATH_D = (
    "M 676 0 L 1200 0 L 1200 708 L 1122 708 L 1048 698 L 960 700 "
    "L 868 690 L 788 660 L 726 608 L 694 532 L 682 424 L 678 286 L 676 136 Z"
)

SAFE_POLYGON: List[Point] = [
    (676.0, 0.0),
    (1200.0, 0.0),
    (1200.0, 708.0),
    (1122.0, 708.0),
    (1048.0, 698.0),
    (960.0, 700.0),
    (868.0, 690.0),
    (788.0, 660.0),
    (726.0, 608.0),
    (694.0, 532.0),
    (682.0, 424.0),
    (678.0, 286.0),
    (676.0, 136.0),
]

VARIANT_PRESETS = {
    "sparse": {
        "horizontal_contours": 5,
        "vertical_contours": 2,
        "dots": 58,
        "grid_clusters": 1,
        "grid_cells": (8, 12),
        "trajectory_nodes": 4,
        "secondary_trajectory": False,
        "trajectory_width": 1.75,
        "dot_radius": (0.9, 1.7),
    },
    "balanced": {
        "horizontal_contours": 7,
        "vertical_contours": 3,
        "dots": 96,
        "grid_clusters": 2,
        "grid_cells": (9, 14),
        "trajectory_nodes": 6,
        "secondary_trajectory": False,
        "trajectory_width": 2.0,
        "dot_radius": (0.9, 1.95),
    },
    "dense": {
        "horizontal_contours": 10,
        "vertical_contours": 5,
        "dots": 152,
        "grid_clusters": 3,
        "grid_cells": (12, 18),
        "trajectory_nodes": 7,
        "secondary_trajectory": True,
        "trajectory_width": 2.15,
        "dot_radius": (0.9, 2.0),
    },
}

FALLBACK_COLORS = {
    "line": "rgba(81, 70, 166, 0.12)",
    "line_soft": "rgba(81, 70, 166, 0.055)",
    "dot": "rgba(81, 70, 166, 0.18)",
    "dot_soft": "rgba(81, 70, 166, 0.075)",
    "grid": "rgba(81, 70, 166, 0.095)",
    "trajectory": "rgba(81, 70, 166, 0.34)",
}


def fmt(value: float) -> str:
    text = f"{value:.2f}"
    return text.rstrip("0").rstrip(".")


def var_color(name: str) -> str:
    if name == "line":
        return f"var(--neuro-bg-line, {FALLBACK_COLORS['line']})"
    if name == "line_soft":
        return f"var(--neuro-bg-line-soft, {FALLBACK_COLORS['line_soft']})"
    if name == "dot":
        return f"var(--neuro-bg-dot, {FALLBACK_COLORS['dot']})"
    if name == "dot_soft":
        return f"var(--neuro-bg-dot-soft, {FALLBACK_COLORS['dot_soft']})"
    if name == "grid":
        return f"var(--neuro-bg-grid, {FALLBACK_COLORS['grid']})"
    if name == "trajectory":
        return f"var(--neuro-bg-trajectory, {FALLBACK_COLORS['trajectory']})"
    raise ValueError(f"Unknown color token: {name}")


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    x, y = point
    inside = False
    count = len(polygon)
    for idx in range(count):
        x1, y1 = polygon[idx]
        x2, y2 = polygon[(idx + 1) % count]
        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-9) + x1
        )
        if intersects:
            inside = not inside
    return inside


def x_bounds_at_y(y: float, polygon: Sequence[Point]) -> Tuple[float, float]:
    xs: List[float] = []
    count = len(polygon)
    for idx in range(count):
        x1, y1 = polygon[idx]
        x2, y2 = polygon[(idx + 1) % count]
        if y1 == y2:
            if abs(y - y1) < 1e-6:
                xs.extend([x1, x2])
            continue
        if min(y1, y2) <= y <= max(y1, y2):
            t = (y - y1) / (y2 - y1)
            if 0.0 <= t <= 1.0:
                xs.append(x1 + t * (x2 - x1))
    xs.sort()
    if len(xs) < 2:
        raise ValueError(f"Could not derive safe x-bounds at y={y}")
    return xs[0], xs[-1]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sample_point(
    rng: random.Random,
    polygon: Sequence[Point],
    x_range: Tuple[float, float] | None = None,
    y_range: Tuple[float, float] | None = None,
) -> Point:
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    x_min, x_max = x_range or (min(xs), max(xs))
    y_min, y_max = y_range or (min(ys), max(ys))

    for _ in range(5000):
        y = rng.uniform(y_min, y_max)
        left, right = x_bounds_at_y(y, polygon)
        low = max(left, x_min)
        high = min(right, x_max)
        if high <= low:
            continue

        span = high - low
        # Beta skew keeps the left reading column quiet and biases the right.
        x = low + span * rng.betavariate(3.8, 1.6)
        if point_in_polygon((x, y), polygon):
            return x, y
    raise RuntimeError("Failed to sample a point inside the safe polygon")


def sample_point_near(
    rng: random.Random,
    center: Point,
    polygon: Sequence[Point],
    sigma_x: float,
    sigma_y: float,
) -> Point:
    for _ in range(3000):
        x = rng.gauss(center[0], sigma_x)
        y = rng.gauss(center[1], sigma_y)
        if point_in_polygon((x, y), polygon):
            return x, y
    return sample_point(rng, polygon)


def make_path(points: Sequence[Point]) -> str:
    if len(points) < 2:
        raise ValueError("Need at least two points for a path")
    start = points[0]
    segments = [f"M {fmt(start[0])} {fmt(start[1])}"]
    for idx in range(len(points) - 1):
        p0 = points[idx - 1] if idx > 0 else points[idx]
        p1 = points[idx]
        p2 = points[idx + 1]
        p3 = points[idx + 2] if idx + 2 < len(points) else p2
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        segments.append(
            "C "
            f"{fmt(c1x)} {fmt(c1y)}, "
            f"{fmt(c2x)} {fmt(c2y)}, "
            f"{fmt(p2[0])} {fmt(p2[1])}"
        )
    return " ".join(segments)


def trajectory_points(rng: random.Random, variant: str) -> List[Point]:
    base = {
        "sparse": [
            (726, 574),
            (792, 530),
            (864, 486),
            (934, 426),
            (992, 344),
            (1042, 262),
        ],
        "balanced": [
            (692, 594),
            (758, 536),
            (834, 486),
            (908, 440),
            (980, 366),
            (1040, 286),
            (1094, 204),
        ],
        "dense": [
            (670, 608),
            (736, 554),
            (808, 504),
            (882, 462),
            (952, 412),
            (1018, 324),
            (1072, 238),
            (1126, 168),
        ],
    }[variant]
    points: List[Point] = []
    for idx, (x, y) in enumerate(base):
        jitter_x = 0.0 if idx in (0, len(base) - 1) else rng.uniform(-10, 10)
        jitter_y = 0.0 if idx in (0, len(base) - 1) else rng.uniform(-14, 14)
        points.append((x + jitter_x, y + jitter_y))
    return points


def trajectory_elements(rng: random.Random, variant: str, preset: dict) -> Tuple[List[str], List[Point]]:
    points = trajectory_points(rng, variant)
    elements = [
        (
            f'<path d="{make_path(points)}" fill="none" '
            f'stroke="{var_color("trajectory")}" '
            f'stroke-width="{fmt(preset["trajectory_width"])}" '
            'stroke-linecap="round" stroke-linejoin="round" />'
        )
    ]

    if preset["secondary_trajectory"]:
        offset_points = [(x + 54, y + 28) for x, y in points[1:-1]]
        if len(offset_points) >= 2:
            secondary = [points[1]] + offset_points + [points[-2]]
            elements.append(
                (
                    f'<path d="{make_path(secondary)}" fill="none" '
                    f'stroke="{var_color("trajectory")}" stroke-width="1.42" '
                    'stroke-linecap="round" stroke-linejoin="round" opacity="0.42" />'
                )
            )

    node_count = min(preset["trajectory_nodes"], len(points) - 1)
    indices = [round(i) for i in [j * (len(points) - 2) / max(node_count - 1, 1) + 1 for j in range(node_count)]]
    node_elements = []
    for idx in indices:
        x, y = points[idx]
        radius = 3.4 + 1.0 * rng.random()
        opacity = 0.3 + 0.16 * rng.random()
        node_elements.append(
            f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(radius)}" fill="{var_color("trajectory")}" opacity="{fmt(opacity)}" />'
        )
    if node_elements:
        elements.append('<g class="neuro-background__nodes">' + "".join(node_elements) + "</g>")

    return elements, points


def contour_elements(rng: random.Random, variant: str, preset: dict) -> List[str]:
    elements: List[str] = []

    contour_ys = {
        "sparse": [90, 162, 246, 352, 476],
        "balanced": [74, 124, 182, 252, 330, 420, 520],
        "dense": [58, 102, 148, 198, 252, 314, 384, 454, 528, 604],
    }[variant]
    for idx, base_y in enumerate(contour_ys[: preset["horizontal_contours"]]):
        y = base_y + rng.uniform(-10, 10)
        left, right = x_bounds_at_y(y, SAFE_POLYGON)
        start_x = left + rng.uniform(10, 28)
        end_x = right - rng.uniform(10, 20)
        mid1_x = start_x + (end_x - start_x) * 0.32
        mid2_x = start_x + (end_x - start_x) * 0.7
        points = [
            (start_x, y + rng.uniform(-8, 8)),
            (mid1_x, y - rng.uniform(18, 34)),
            (mid2_x, y - rng.uniform(10, 26)),
            (end_x, y + rng.uniform(14, 30)),
        ]
        stroke = "line" if idx % 3 == 2 else "line_soft"
        width = 0.92 + 0.16 * rng.random()
        elements.append(
            f'<path d="{make_path(points)}" fill="none" stroke="{var_color(stroke)}" '
            f'stroke-width="{fmt(width)}" stroke-linecap="round" stroke-linejoin="round" />'
        )

    vertical_sets = {
        "sparse": [(856, 118), (980, 102)],
        "balanced": [(842, 106), (930, 92), (1018, 154)],
        "dense": [(818, 102), (884, 88), (950, 78), (1012, 98), (1072, 128)],
    }[variant]
    for idx, (x, start_y) in enumerate(vertical_sets[: preset["vertical_contours"]]):
        p1 = (x + rng.uniform(-8, 8), start_y)
        p2 = (x + rng.uniform(18, 28), start_y + 54 + rng.uniform(-8, 10))
        p3 = (x + rng.uniform(16, 26), start_y + 128 + rng.uniform(-12, 12))
        p4 = (x + rng.uniform(6, 20), start_y + 220 + rng.uniform(-16, 18))
        stroke = "line" if idx == max(0, preset["vertical_contours"] - 2) else "line_soft"
        width = 0.88 + 0.12 * rng.random()
        elements.append(
            f'<path d="{make_path([p1, p2, p3, p4])}" fill="none" stroke="{var_color(stroke)}" '
            f'stroke-width="{fmt(width)}" stroke-linecap="round" stroke-linejoin="round" />'
        )

    return elements


def dot_elements(
    rng: random.Random,
    variant: str,
    preset: dict,
    trajectory: Sequence[Point],
) -> List[str]:
    centers = list(trajectory[1:-1])
    if variant == "sparse":
        centers.extend([(890, 158), (980, 244)])
    elif variant == "balanced":
        centers.extend([(824, 148), (984, 204), (1056, 516)])
    else:
        centers.extend([(804, 132), (942, 194), (1068, 286), (1010, 612)])

    radius_low, radius_high = preset["dot_radius"]
    elements = []
    for idx in range(preset["dots"]):
        center = centers[idx % len(centers)]
        sigma_x = 34 + 20 * (idx % 3)
        sigma_y = 18 + 14 * ((idx + 1) % 3)
        x, y = sample_point_near(rng, center, SAFE_POLYGON, sigma_x, sigma_y)
        radius = rng.uniform(radius_low, radius_high)
        token = "dot" if idx % 2 else "dot_soft"
        elements.append(
            f'<circle cx="{fmt(x)}" cy="{fmt(y)}" r="{fmt(radius)}" fill="{var_color(token)}" />'
        )
    return elements


def grid_elements(rng: random.Random, variant: str, preset: dict) -> List[str]:
    anchors = {
        "sparse": [(986, 124)],
        "balanced": [(956, 96), (1036, 252)],
        "dense": [(944, 86), (1024, 238), (948, 520)],
    }[variant]
    elements = []
    for cluster_idx, anchor in enumerate(anchors[: preset["grid_clusters"]]):
        cells = rng.randint(*preset["grid_cells"])
        cols = 4 + (cluster_idx % 2)
        spacing = 18 + rng.uniform(-2, 4)
        start_x, start_y = anchor
        for idx in range(cells):
            row = idx // cols
            col = idx % cols
            x = start_x + col * spacing + rng.uniform(-2.8, 2.8)
            y = start_y + row * spacing * 0.82 + rng.uniform(-3.0, 3.0)
            size = 5 + (idx % 3)
            if not point_in_polygon((x + size / 2.0, y + size / 2.0), SAFE_POLYGON):
                continue
            elements.append(
                f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(size)}" height="{fmt(size)}" '
                f'rx="{fmt(max(1.0, size * 0.22))}" fill="{var_color("grid")}" />'
            )
    return elements


def build_svg(width: int, height: int, variant: str, seed: int) -> str:
    rng = random.Random(seed)
    preset = VARIANT_PRESETS[variant]

    trajectory_group, trajectory_points_list = trajectory_elements(rng, variant, preset)
    contour_group = contour_elements(rng, variant, preset)
    dot_group = dot_elements(rng, variant, preset, trajectory_points_list)
    grid_group = grid_elements(rng, variant, preset)

    field_opacity = {"sparse": "0.56", "balanced": "0.66", "dense": "0.76"}[variant]
    cloud_opacity = {"sparse": "0.22", "balanced": "0.52", "dense": "0.68"}[variant]
    trajectory_opacity = {"sparse": "0.36", "balanced": "0.64", "dense": "0.72"}[variant]
    fragment_opacity = {"sparse": "0.20", "balanced": "0.44", "dense": "0.56"}[variant]

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {DEFAULT_WIDTH} {DEFAULT_HEIGHT}" width="{width}" height="{height}" '
            f'preserveAspectRatio="xMidYMid slice" aria-hidden="true" role="presentation">'
        ),
        "  <defs>",
        f'    <clipPath id="neuro-bg-clip-{variant}-{seed}">',
        f'      <path d="{CLIP_PATH_D}" />',
        "    </clipPath>",
        "  </defs>",
        f'  <g clip-path="url(#neuro-bg-clip-{variant}-{seed})">',
        f'    <g class="neuro-background__field neuro-background__contours" opacity="{field_opacity}">',
        *[f"      {element}" for element in contour_group],
        "    </g>",
        f'    <g class="neuro-background__fragments neuro-background__grids" opacity="{fragment_opacity}">',
        *[f"      {element}" for element in grid_group],
        "    </g>",
        f'    <g class="neuro-background__trajectory" opacity="{trajectory_opacity}">',
        *[f"      {element}" for element in trajectory_group],
        "    </g>",
        f'    <g class="neuro-background__cloud neuro-background__dots" opacity="{cloud_opacity}">',
        *[f"      {element}" for element in dot_group],
        "    </g>",
        "  </g>",
        "</svg>",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate static SVG neuro background assets.")
    parser.add_argument(
        "--variant",
        choices=sorted(VARIANT_PRESETS.keys()),
        default="balanced",
        help="Density preset to generate.",
    )
    parser.add_argument("--seed", type=int, default=1, help="Deterministic random seed.")
    parser.add_argument(
        "--output",
        required=True,
        help="Output SVG path.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=DEFAULT_WIDTH,
        help="Rendered SVG width attribute in pixels.",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=DEFAULT_HEIGHT,
        help="Rendered SVG height attribute in pixels.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    svg = build_svg(
        width=args.width,
        height=args.height,
        variant=args.variant,
        seed=args.seed,
    )
    output_path.write_text(svg, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
