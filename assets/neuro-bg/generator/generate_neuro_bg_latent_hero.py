#!/usr/bin/env python3
"""Generate deterministic computational-neuroscience SVG background candidates."""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


Point = Tuple[float, float]
Rect = Tuple[float, float, float, float]

DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 900

ROLE_AMBIENT = "ambient"
ROLE_STRUCTURAL = "structural"
ROLE_ANCHOR = "anchor"


@dataclass(frozen=True)
class Zone:
    name: str
    bounds: Rect
    opacity_range: Tuple[float, float]


@dataclass(frozen=True)
class Preset:
    contour_fields: int
    posterior_clouds: int
    latent_trajectories: int
    matrix_fragments: int
    projected_axes: int
    scan_echoes: int
    belief_curves: int
    prediction_error_pulses: int
    time_series_stacks: int
    event_rasters: int
    design_matrix_fragments: int
    posterior_density_ridges: int
    model_comparison_intervals: int
    state_transition_mini_graphs: int
    topography_fragments: int
    ambient_dots: int
    ambient_contours: int
    anchor_intensity: float
    conservative_left: bool = False


@dataclass
class DebugRecord:
    motif_type: str
    zone: str
    role: str
    rect: Rect
    center: Point
    opacity_class: str


@dataclass
class GenerationStats:
    motif_counts: Dict[str, int] = field(default_factory=dict)
    zone_occupancy: Dict[str, int] = field(default_factory=dict)

    def bump(self, motif_type: str, point: Point) -> None:
        self.motif_counts[motif_type] = self.motif_counts.get(motif_type, 0) + 1
        for zone_name, rect in OCCUPANCY_RECTS.items():
            if point_in_rect(point, rect):
                self.zone_occupancy[zone_name] = self.zone_occupancy.get(zone_name, 0) + 1


ZONE_DEFINITIONS: Dict[str, Zone] = {
    "left_title": Zone("left_title", (34.0, 24.0, 430.0, 228.0), (0.12, 0.3)),
    "central_bridge": Zone("central_bridge", (570.0, 112.0, 818.0, 560.0), (0.18, 0.42)),
    "right_anchor": Zone("right_anchor", (760.0, 54.0, 1170.0, 716.0), (0.24, 0.56)),
    "lower_echo": Zone("lower_echo", (84.0, 706.0, 1018.0, 860.0), (0.12, 0.28)),
    "left_field": Zone("left_field", (0.0, 72.0, 720.0, 690.0), (0.1, 0.32)),
}

LEFT_HALF_RECT: Rect = (0.0, 0.0, 600.0, 900.0)
TITLE_ZONE_RECT: Rect = (48.0, 54.0, 602.0, 236.0)
PROSE_ZONE_RECT: Rect = (84.0, 224.0, 610.0, 672.0)
RIGHT_SIDEBAR_ZONE_RECT: Rect = (676.0, 0.0, 1200.0, 716.0)
LATEST_POSTS_ZONE_RECT: Rect = (92.0, 724.0, 846.0, 860.0)
LEFT_OUTER_MARGIN_RECT: Rect = (0.0, 96.0, 148.0, 690.0)
LEFT_TOP_BAND_RECT: Rect = (0.0, 72.0, 336.0, 234.0)
LEFT_TOP_WHITESPACE_RECT: Rect = (0.0, 72.0, 228.0, 134.0)
LEFT_OUTER_LOWER_RECT: Rect = (0.0, 248.0, 168.0, 690.0)
LEFT_BRIDGE_RECT: Rect = (470.0, 136.0, 718.0, 548.0)

OCCUPANCY_RECTS: Dict[str, Rect] = {
    "left_half": LEFT_HALF_RECT,
    "title_zone": TITLE_ZONE_RECT,
    "prose_zone": PROSE_ZONE_RECT,
    "right_sidebar_zone": RIGHT_SIDEBAR_ZONE_RECT,
    "latest_posts_zone": LATEST_POSTS_ZONE_RECT,
}

HARD_KEEP_OUT_RECTS: Tuple[Rect, ...] = (
    (92.0, 88.0, 548.0, 198.0),
    (102.0, 252.0, 580.0, 646.0),
    (112.0, 742.0, 804.0, 854.0),
    (438.0, 104.0, 566.0, 228.0),
)

SOFT_KEEP_OUT_RECTS: Tuple[Rect, ...] = (
    (48.0, 54.0, 602.0, 236.0),
    (84.0, 224.0, 610.0, 672.0),
    (92.0, 724.0, 846.0, 860.0),
    (422.0, 92.0, 590.0, 246.0),
)

RIGHT_ANCHOR_SAFE_POLYGON: Tuple[Point, ...] = (
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
)

DEBUG_ZONE_STYLES = {
    "left_title": {"fill": "rgba(63, 111, 214, 0.08)", "stroke": "rgba(63, 111, 214, 0.72)"},
    "central_bridge": {"fill": "rgba(79, 157, 104, 0.08)", "stroke": "rgba(79, 157, 104, 0.72)"},
    "right_anchor": {"fill": "rgba(168, 98, 201, 0.08)", "stroke": "rgba(168, 98, 201, 0.72)"},
    "lower_echo": {"fill": "rgba(214, 146, 70, 0.08)", "stroke": "rgba(214, 146, 70, 0.72)"},
    "left_field": {"fill": "rgba(58, 154, 166, 0.05)", "stroke": "rgba(58, 154, 166, 0.74)"},
}

DEBUG_MOTIF_COLORS = {
    "contour_field": "rgba(88, 103, 188, 0.8)",
    "vector_field": "rgba(88, 103, 188, 0.72)",
    "posterior_cloud": "rgba(81, 70, 166, 0.8)",
    "latent_trajectory": "rgba(22, 92, 138, 0.84)",
    "matrix_fragment": "rgba(95, 104, 120, 0.84)",
    "projected_axes": "rgba(79, 157, 104, 0.82)",
    "scan_echo": "rgba(177, 127, 58, 0.84)",
    "belief_update_curve": "rgba(112, 104, 200, 0.84)",
    "prediction_error_pulses": "rgba(99, 119, 176, 0.84)",
    "time_series_stack": "rgba(127, 133, 158, 0.84)",
    "event_raster_fragment": "rgba(126, 138, 164, 0.84)",
    "design_matrix_fragment": "rgba(148, 134, 216, 0.84)",
    "posterior_density_ridge": "rgba(140, 146, 184, 0.84)",
    "model_comparison_interval": "rgba(90, 100, 126, 0.84)",
    "state_transition_mini_graph": "rgba(98, 112, 168, 0.84)",
    "topography_fragment": "rgba(113, 123, 188, 0.84)",
    "ambient_dots": "rgba(126, 138, 164, 0.8)",
}

ROLE_DASH = {
    ROLE_AMBIENT: "3 4",
    ROLE_STRUCTURAL: "6 5",
    ROLE_ANCHOR: "10 6",
}

FALLBACK_COLORS = {
    "ink_strong": "rgba(20, 20, 24, 0.52)",
    "ink": "rgba(56, 58, 68, 0.32)",
    "ink_soft": "rgba(94, 98, 114, 0.18)",
    "gray": "rgba(108, 112, 126, 0.22)",
    "gray_soft": "rgba(138, 144, 158, 0.12)",
    "indigo": "rgba(92, 98, 176, 0.3)",
    "indigo_soft": "rgba(120, 126, 208, 0.18)",
    "violet": "rgba(126, 110, 194, 0.28)",
    "violet_soft": "rgba(180, 168, 228, 0.14)",
    "accent": "rgba(90, 118, 178, 0.34)",
    "white_soft": "rgba(255, 255, 255, 0.08)",
}

VARIANT_PRESETS = {
    "sparse": Preset(10, 1, 1, 1, 1, 1, 3, 2, 2, 2, 0, 1, 1, 1, 2, 18, 10, 1.12, True),
    "balanced": Preset(14, 2, 1, 2, 1, 2, 4, 3, 3, 2, 1, 2, 2, 2, 4, 24, 13, 1.3),
    "dense": Preset(18, 2, 2, 2, 2, 2, 5, 4, 4, 3, 1, 2, 2, 2, 5, 28, 18, 1.42),
    "rich": Preset(20, 2, 2, 2, 2, 2, 6, 4, 4, 3, 2, 3, 2, 2, 6, 16, 22, 1.48),
    "composite": Preset(20, 2, 2, 2, 2, 2, 6, 4, 4, 3, 2, 3, 2, 2, 6, 16, 22, 1.48),
    "rich_sparse": Preset(12, 1, 1, 1, 1, 1, 4, 2, 2, 2, 1, 2, 1, 1, 3, 10, 12, 1.24, True),
    # Latent-dynamics-first website hero. The hierarchy is intentional:
    # trajectories/cloud/flow dominate; diagnostic fragments remain secondary.
    "latent_hero": Preset(10, 3, 2, 2, 1, 1, 2, 1, 2, 1, 1, 2, 0, 0, 1, 18, 8, 1.55, True),
}


def fmt(value: float) -> str:
    text = f"{value:.2f}"
    return text.rstrip("0").rstrip(".")


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def weighted_choice(rng: random.Random, weighted_items: Sequence[Tuple[str, float]]) -> str:
    total = sum(weight for _, weight in weighted_items)
    threshold = rng.uniform(0.0, total)
    cursor = 0.0
    for item, weight in weighted_items:
        cursor += weight
        if threshold <= cursor:
            return item
    return weighted_items[-1][0]


def var_color(name: str) -> str:
    token_map = {
        "ink_strong": "--neuro-bg-ink-strong",
        "ink": "--neuro-bg-ink",
        "ink_soft": "--neuro-bg-ink-soft",
        "gray": "--neuro-bg-gray",
        "gray_soft": "--neuro-bg-gray-soft",
        "indigo": "--neuro-bg-indigo",
        "indigo_soft": "--neuro-bg-indigo-soft",
        "violet": "--neuro-bg-violet",
        "violet_soft": "--neuro-bg-violet-soft",
        "accent": "--neuro-bg-accent",
        "white_soft": "--neuro-white-soft",
    }
    return f"var({token_map[name]}, {FALLBACK_COLORS[name]})"


def zone_opacity(zone_name: str, rng: random.Random, intensity: float = 1.0) -> float:
    low, high = ZONE_DEFINITIONS[zone_name].opacity_range
    return clamp(rng.uniform(low, high) * intensity, 0.02, 0.65)


def point_in_rect(point: Point, rect: Rect) -> bool:
    x, y = point
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2


def point_in_any_rect(point: Point, rects: Sequence[Rect]) -> bool:
    return any(point_in_rect(point, rect) for rect in rects)


def rect_intersects_any(rect: Rect, rects: Sequence[Rect]) -> bool:
    x1, y1, x2, y2 = rect
    for ox1, oy1, ox2, oy2 in rects:
        if not (x2 < ox1 or ox2 < x1 or y2 < oy1 or oy2 < y1):
            return True
    return False


def rect_center(rect: Rect) -> Point:
    x1, y1, x2, y2 = rect
    return ((x1 + x2) * 0.5, (y1 + y2) * 0.5)


def rect_distance(point: Point, rect: Rect) -> float:
    x, y = point
    x1, y1, x2, y2 = rect
    dx = max(x1 - x, 0.0, x - x2)
    dy = max(y1 - y, 0.0, y - y2)
    return math.hypot(dx, dy)


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    x, y = point
    inside = False
    for idx in range(len(polygon)):
        x1, y1 = polygon[idx]
        x2, y2 = polygon[(idx + 1) % len(polygon)]
        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-9) + x1
        )
        if intersects:
            inside = not inside
    return inside


def path_from_points(points: Sequence[Point]) -> str:
    start = points[0]
    parts = [f"M {fmt(start[0])} {fmt(start[1])}"]
    for idx in range(len(points) - 1):
        p0 = points[idx - 1] if idx > 0 else points[idx]
        p1 = points[idx]
        p2 = points[idx + 1]
        p3 = points[idx + 2] if idx + 2 < len(points) else p2
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        parts.append(
            "C "
            f"{fmt(c1x)} {fmt(c1y)}, "
            f"{fmt(c2x)} {fmt(c2y)}, "
            f"{fmt(p2[0])} {fmt(p2[1])}"
        )
    return " ".join(parts)


def path_from_segments(points: Sequence[Point]) -> str:
    parts = [f"M {fmt(points[0][0])} {fmt(points[0][1])}"]
    parts.extend(f"L {fmt(x)} {fmt(y)}" for x, y in points[1:])
    return " ".join(parts)


def polyline_bounds(points: Sequence[Point], pad: float = 0.0) -> Rect:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def polyline_center(points: Sequence[Point]) -> Point:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def zone_center(zone_name: str, x_bias: float = 0.5, y_bias: float = 0.5) -> Point:
    x1, y1, x2, y2 = ZONE_DEFINITIONS[zone_name].bounds
    return (lerp(x1, x2, x_bias), lerp(y1, y2, y_bias))


def choose_color_role(rng: random.Random, role: str, family: str) -> str:
    if family == "curve":
        choices = {
            ROLE_AMBIENT: [("gray_soft", 2.2), ("violet_soft", 1.7), ("indigo_soft", 1.6), ("gray", 0.8)],
            ROLE_STRUCTURAL: [("gray", 2.0), ("indigo_soft", 1.8), ("violet", 1.2), ("ink_soft", 1.0)],
            ROLE_ANCHOR: [("indigo", 2.0), ("violet", 1.5), ("ink", 1.2), ("accent", 1.0)],
        }
    elif family == "dot":
        choices = {
            ROLE_AMBIENT: [("gray_soft", 2.4), ("violet_soft", 1.7), ("indigo_soft", 1.2), ("white_soft", 0.6)],
            ROLE_STRUCTURAL: [("gray", 1.8), ("indigo_soft", 1.4), ("violet", 1.1), ("accent", 0.8)],
            ROLE_ANCHOR: [("accent", 1.6), ("violet", 1.4), ("indigo", 1.2), ("ink", 0.8)],
        }
    elif family == "fill":
        choices = {
            ROLE_AMBIENT: [("gray_soft", 2.3), ("violet_soft", 1.8), ("indigo_soft", 1.4)],
            ROLE_STRUCTURAL: [("gray_soft", 1.5), ("violet_soft", 1.4), ("indigo_soft", 1.2), ("gray", 0.8)],
            ROLE_ANCHOR: [("gray", 1.2), ("indigo_soft", 1.1), ("violet_soft", 1.0)],
        }
    else:
        choices = {
            ROLE_AMBIENT: [("gray_soft", 2.0), ("indigo_soft", 1.4)],
            ROLE_STRUCTURAL: [("gray", 1.8), ("indigo_soft", 1.4), ("violet", 1.1)],
            ROLE_ANCHOR: [("ink", 1.5), ("indigo", 1.3), ("violet", 1.0)],
        }
    return weighted_choice(rng, choices[role])


def opacity_class(opacity: float) -> str:
    if opacity < 0.12:
        return "faint"
    if opacity < 0.28:
        return "soft"
    if opacity < 0.46:
        return "medium"
    return "strong"


def ambient_soft_factor(point: Point) -> float:
    if not point_in_rect(point, ZONE_DEFINITIONS["left_field"].bounds):
        return 0.0
    x, y = point
    x1, y1, x2, y2 = ZONE_DEFINITIONS["left_field"].bounds
    edge_fade = min(
        clamp((x - x1) / 90.0, 0.0, 1.0),
        clamp((x2 - x) / 110.0, 0.0, 1.0),
        clamp((y - y1) / 50.0, 0.0, 1.0),
        clamp((y2 - y) / 70.0, 0.0, 1.0),
    )
    emphasis = 0.0
    for center, sigma_x, sigma_y, weight in (
        ((52.0, 148.0), 84.0, 82.0, 1.18),
        ((162.0, 126.0), 152.0, 74.0, 1.06),
        ((76.0, 402.0), 102.0, 176.0, 0.94),
        ((548.0, 322.0), 136.0, 142.0, 1.02),
        ((662.0, 246.0), 84.0, 136.0, 0.86),
    ):
        dx = (x - center[0]) / sigma_x
        dy = (y - center[1]) / sigma_y
        emphasis = max(emphasis, weight * math.exp(-0.5 * (dx * dx + dy * dy)))

    softness = 1.0
    for rect in SOFT_KEEP_OUT_RECTS:
        distance = rect_distance(point, rect)
        if point_in_rect(point, rect):
            softness *= 0.22
        elif distance < 22.0:
            softness *= lerp(0.28, 1.0, distance / 22.0)
        elif distance < 64.0:
            softness *= lerp(0.58, 1.0, (distance - 22.0) / 42.0)

    if point_in_rect(point, LEFT_OUTER_MARGIN_RECT):
        softness *= 1.12
    if point_in_rect(point, LEFT_TOP_BAND_RECT):
        softness *= 0.94
    if point_in_rect(point, LEFT_BRIDGE_RECT):
        softness *= 1.05
    if point_in_rect(point, TITLE_ZONE_RECT):
        softness *= 0.62

    return clamp(0.18 + emphasis * edge_fade * softness, 0.0, 1.0)


def sample_point_in_rect(
    rng: random.Random,
    rect: Rect,
    avoid: Sequence[Rect] = HARD_KEEP_OUT_RECTS,
    require_right_safe: bool = False,
    edge_bias: Tuple[float, float] | None = None,
) -> Point:
    x1, y1, x2, y2 = rect
    for _ in range(5000):
        x = lerp(x1, x2, rng.betavariate(*edge_bias)) if edge_bias else rng.uniform(x1, x2)
        y = rng.uniform(y1, y2)
        point = (x, y)
        if point_in_any_rect(point, avoid):
            continue
        if require_right_safe and not point_in_polygon(point, RIGHT_ANCHOR_SAFE_POLYGON):
            continue
        return point
    raise RuntimeError(f"Could not sample point in rect {rect}")


def sample_point_near(
    rng: random.Random,
    center: Point,
    rect: Rect,
    sigma_x: float,
    sigma_y: float,
    avoid: Sequence[Rect] = HARD_KEEP_OUT_RECTS,
    require_right_safe: bool = False,
) -> Point:
    x1, y1, x2, y2 = rect
    for _ in range(4000):
        point = (
            clamp(rng.gauss(center[0], sigma_x), x1, x2),
            clamp(rng.gauss(center[1], sigma_y), y1, y2),
        )
        if point_in_any_rect(point, avoid):
            continue
        if require_right_safe and not point_in_polygon(point, RIGHT_ANCHOR_SAFE_POLYGON):
            continue
        return point
    return sample_point_in_rect(rng, rect, avoid=avoid, require_right_safe=require_right_safe)


def sample_left_field_point(rng: random.Random) -> Point:
    for _ in range(6000):
        target_rect = weighted_choice(
            rng,
            [
                ("outer", 2.3),
                ("top", 1.15),
                ("top_whitespace", 0.9),
                ("outer_lower", 1.5),
                ("bridge", 1.5),
                ("full", 1.2),
            ],
        )
        rect = {
            "outer": LEFT_OUTER_MARGIN_RECT,
            "top": LEFT_TOP_BAND_RECT,
            "top_whitespace": LEFT_TOP_WHITESPACE_RECT,
            "outer_lower": LEFT_OUTER_LOWER_RECT,
            "bridge": LEFT_BRIDGE_RECT,
            "full": ZONE_DEFINITIONS["left_field"].bounds,
        }[target_rect]
        x = lerp(rect[0], rect[2], rng.betavariate(1.1, 1.35 if target_rect != "bridge" else 1.2))
        y = lerp(rect[1], rect[3], rng.betavariate(1.08, 1.28))
        point = (x, y)
        if point_in_any_rect(point, HARD_KEEP_OUT_RECTS):
            continue
        strength = ambient_soft_factor(point)
        if strength <= 0.0:
            continue
        if rng.random() <= clamp(strength * 1.26, 0.08, 1.0):
            return point
    return zone_center("left_title", 0.24, 0.38)


class Builder:
    def __init__(self, variant: str, seed: int):
        self.variant = variant
        self.seed = seed
        self.preset = VARIANT_PRESETS[variant]
        self.rng = random.Random(seed)
        self.stats = GenerationStats()
        self.debug_records: List[DebugRecord] = []
        self.groups: Dict[str, List[str]] = {
            "field": [],
            "fragments": [],
            "trajectory": [],
            "cloud": [],
        }
        self.trajectory_centers: List[Point] = []

    def add(
        self,
        group: str,
        motif_type: str,
        zone: str,
        role: str,
        rect: Rect,
        element: str,
        point: Point | None = None,
        opacity: float = 0.16,
    ) -> None:
        self.groups[group].append(element)
        center = point or rect_center(rect)
        self.stats.bump(motif_type, center)
        self.debug_records.append(
            DebugRecord(
                motif_type=motif_type,
                zone=zone,
                role=role,
                rect=rect,
                center=center,
                opacity_class=opacity_class(opacity),
            )
        )

    def motif_group(self, motif_type: str) -> str:
        if motif_type in {"latent_trajectory"}:
            return "trajectory"
        if motif_type in {"posterior_cloud", "ambient_dots"}:
            return "cloud"
        if motif_type in {"matrix_fragment", "scan_echo", "design_matrix_fragment"}:
            return "fragments"
        return "field"


def role_intensity(role: str, preset: Preset) -> float:
    base = {ROLE_AMBIENT: 0.78, ROLE_STRUCTURAL: 1.0, ROLE_ANCHOR: preset.anchor_intensity}
    return base[role]


def ambient_curve_points(rng: random.Random) -> List[Point]:
    start = sample_left_field_point(rng)
    end = sample_left_field_point(rng)
    if abs(end[0] - start[0]) < 140.0:
        end = (clamp(end[0] + rng.uniform(140.0, 260.0), 0.0, 720.0), end[1])
    return [
        start,
        (
            lerp(start[0], end[0], 0.28) + rng.uniform(-34.0, 34.0),
            lerp(start[1], end[1], 0.26) + rng.uniform(-44.0, 26.0),
        ),
        (
            lerp(start[0], end[0], 0.63) + rng.uniform(-28.0, 28.0),
            lerp(start[1], end[1], 0.7) + rng.uniform(-24.0, 38.0),
        ),
        end,
    ]


def add_contour_field(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    if zone == "left_field":
        points = ambient_curve_points(rng)
    else:
        x1, y1, x2, y2 = ZONE_DEFINITIONS[zone].bounds
        horizontal = zone != "right_anchor" or rng.random() < 0.58
        if horizontal:
            base_y = rng.uniform(y1 + 18.0, y2 - 18.0)
            points = [
                (x1 + rng.uniform(-18.0, 12.0), base_y + rng.uniform(-14.0, 14.0)),
                (lerp(x1, x2, 0.26), base_y + rng.uniform(-62.0, 44.0)),
                (lerp(x1, x2, 0.58), base_y + rng.uniform(-54.0, 56.0)),
                (x2 + rng.uniform(-16.0, 16.0), base_y + rng.uniform(-16.0, 18.0)),
            ]
        else:
            base_x = rng.uniform(x1 + 24.0, x2 - 38.0)
            points = [
                (base_x + rng.uniform(-14.0, 14.0), y1),
                (base_x + rng.uniform(16.0, 56.0), lerp(y1, y2, 0.28)),
                (base_x + rng.uniform(-24.0, 28.0), lerp(y1, y2, 0.62)),
                (base_x + rng.uniform(-18.0, 18.0), y2),
            ]
    bounds = polyline_bounds(points, pad=5.0)
    width_low, width_high = ((0.4, 0.9) if role == ROLE_AMBIENT else (0.6, 1.2) if role == ROLE_STRUCTURAL else (1.2, 1.8))
    opacity = zone_opacity(zone if zone != "left_field" else "left_title", rng, role_intensity(role, builder.preset))
    if zone == "left_field":
        opacity = clamp(0.24 + ambient_soft_factor(polyline_center(points)) * rng.uniform(0.16, 0.34), 0.24, 0.58)
    color = choose_color_role(rng, role, "curve")
    element = (
        f'<path class="neuro-background__motif neuro-background__motif--contour-field" '
        f'data-motif-type="contour_field" data-zone="{zone}" data-role="{role}" data-opacity-class="{opacity_class(opacity)}" '
        f'd="{path_from_points(points)}" fill="none" stroke="{var_color(color)}" stroke-width="{fmt(rng.uniform(width_low, width_high))}" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(opacity)}" />'
    )
    builder.add(builder.motif_group("contour_field"), "contour_field", zone, role, bounds, element, polyline_center(points), opacity)


def build_main_trajectory_points(rng: random.Random, variant: str, index: int) -> List[Point]:
    base = [
        (506.0, 446.0),
        (616.0, 420.0),
        (734.0, 388.0),
        (846.0, 344.0),
        (964.0, 278.0),
        (1084.0, 194.0),
    ]
    if variant in {"dense", "rich", "composite", "latent_hero"} and index == 1:
        base = [
            (586.0, 522.0),
            (674.0, 506.0),
            (780.0, 472.0),
            (896.0, 424.0),
            (1018.0, 364.0),
            (1128.0, 298.0),
        ]
    return [(x + rng.uniform(-14.0, 14.0), y + rng.uniform(-22.0, 22.0)) for x, y in base]


def add_vector_field(builder: Builder, zone: str = "right_anchor", role: str = ROLE_STRUCTURAL) -> None:
    """Add a sparse phase-portrait layer behind the latent trajectory.

    This is deliberately different from contour fields. Contours imply density or
    topology; the vector field implies a local transition rule in latent space.
    """
    rng = builder.rng
    x1, y1, x2, y2 = ZONE_DEFINITIONS[zone].bounds

    cols = 16 if zone == "right_anchor" else 10
    rows = 11 if zone == "right_anchor" else 7
    jitter = 6.0
    pieces: List[str] = []
    points: List[Point] = []

    # Zone-specific visual centers keep the field aligned with existing layout.
    if zone == "right_anchor":
        center_x, center_y = 940.0, 360.0
        scale_x, scale_y = 260.0, 210.0
    else:
        center_x, center_y = rect_center(ZONE_DEFINITIONS[zone].bounds)
        scale_x = max(140.0, (x2 - x1) * 0.45)
        scale_y = max(120.0, (y2 - y1) * 0.45)

    for row in range(rows):
        for col in range(cols):
            x = lerp(x1 + 24.0, x2 - 24.0, col / max(1, cols - 1)) + rng.uniform(-jitter, jitter)
            y = lerp(y1 + 36.0, y2 - 42.0, row / max(1, rows - 1)) + rng.uniform(-jitter, jitter)
            point = (x, y)

            if point_in_any_rect(point, HARD_KEEP_OUT_RECTS):
                continue
            if zone == "right_anchor" and not point_in_polygon(point, RIGHT_ANCHOR_SAFE_POLYGON):
                continue

            nx = (x - center_x) / scale_x
            ny = (y - center_y) / scale_y

            # A compact nonlinear phase portrait: weak rotation, contraction,
            # and sinusoidal local structure. It reads as a latent transition
            # field without requiring a literal model object.
            u = -0.55 * ny + 0.24 * math.sin(2.2 * nx)
            v = 0.42 * nx - 0.18 * ny + 0.16 * math.cos(1.8 * ny)
            norm = math.hypot(u, v) or 1.0
            u /= norm
            v /= norm

            length = rng.uniform(10.0, 22.0 if zone == "right_anchor" else 17.0)
            x_end = x + u * length
            y_end = y + v * length

            angle = math.atan2(v, u)
            head = rng.uniform(2.2, 3.6)
            left = (
                x_end - head * math.cos(angle - 0.55),
                y_end - head * math.sin(angle - 0.55),
            )
            right = (
                x_end - head * math.cos(angle + 0.55),
                y_end - head * math.sin(angle + 0.55),
            )

            opacity = rng.uniform(0.14, 0.32 if role != ROLE_ANCHOR else 0.38)
            stroke = var_color(choose_color_role(rng, role, "curve"))
            stroke_width = rng.uniform(0.45, 0.8 if role != ROLE_ANCHOR else 0.95)

            pieces.append(
                f'<line x1="{fmt(x)}" y1="{fmt(y)}" x2="{fmt(x_end)}" y2="{fmt(y_end)}" '
                f'stroke="{stroke}" stroke-width="{fmt(stroke_width)}" '
                f'stroke-linecap="round" opacity="{fmt(opacity)}" />'
            )
            pieces.append(
                f'<path d="M {fmt(x_end)} {fmt(y_end)} L {fmt(left[0])} {fmt(left[1])} '
                f'L {fmt(right[0])} {fmt(right[1])} Z" fill="{stroke}" opacity="{fmt(opacity * 0.85)}" />'
            )
            points.extend([point, (x_end, y_end)])

    if not points:
        return

    bounds = polyline_bounds(points, pad=8.0)
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--vector-field" '
        f'data-motif-type="vector_field" data-zone="{zone}" data-role="{role}" data-opacity-class="soft">'
        + "".join(pieces)
        + "</g>"
    )
    builder.add("field", "vector_field", zone, role, bounds, group, rect_center(bounds), 0.22)

def add_latent_trajectory(builder: Builder, index: int) -> None:
    rng = builder.rng
    role = ROLE_ANCHOR if index == 0 else ROLE_STRUCTURAL
    points = build_main_trajectory_points(rng, builder.variant, index)
    path = path_from_points(points)
    opacity = clamp(rng.uniform(0.5, 0.84) * role_intensity(role, builder.preset), 0.5, 0.9)
    stroke_width = rng.uniform(1.2, 2.4) if role == ROLE_ANCHOR else rng.uniform(0.9, 1.5)
    color = choose_color_role(rng, role, "curve")
    dash = "" if index == 0 else ' stroke-dasharray="8 10"'
    element = (
        f'<path class="neuro-background__motif neuro-background__motif--latent-trajectory" '
        f'data-motif-type="latent_trajectory" data-zone="right_anchor" data-role="{role}" data-opacity-class="{opacity_class(opacity)}" '
        f'd="{path}" fill="none" stroke="{var_color(color)}" stroke-width="{fmt(stroke_width)}" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(opacity)}"{dash} />'
    )
    bounds = polyline_bounds(points, pad=stroke_width * 2.0)
    builder.add("trajectory", "latent_trajectory", "right_anchor", role, bounds, element, polyline_center(points), opacity)
    builder.trajectory_centers.append(polyline_center(points))

    node_count = 5 if index == 0 else 3
    node_markup: List[str] = []
    for node_index in range(node_count):
        point = points[min(len(points) - 1, node_index + (0 if index == 0 else 1))]
        radius = rng.uniform(2.0, 5.0) if index == 0 else rng.uniform(1.4, 2.8)
        node_opacity = clamp(opacity * rng.uniform(0.7, 1.0), 0.3, 0.65)
        node_markup.append(
            f'<circle cx="{fmt(point[0])}" cy="{fmt(point[1])}" r="{fmt(radius)}" fill="{var_color(choose_color_role(rng, role, "dot"))}" opacity="{fmt(node_opacity)}" />'
        )
    node_group = (
        f'<g class="neuro-background__motif neuro-background__motif--trajectory-nodes" '
        f'data-motif-type="latent_trajectory" data-zone="right_anchor" data-role="{role}" data-opacity-class="{opacity_class(opacity)}">'
        + "".join(node_markup)
        + "</g>"
    )
    builder.add("cloud", "latent_trajectory", "right_anchor", role, bounds, node_group, polyline_center(points), opacity)


def add_posterior_cloud(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    rect = ZONE_DEFINITIONS[zone].bounds
    center = (
        builder.trajectory_centers[min(len(builder.trajectory_centers) - 1, rng.randrange(len(builder.trajectory_centers)))]
        if builder.trajectory_centers and zone == "right_anchor"
        else zone_center(zone, rng.uniform(0.22, 0.78), rng.uniform(0.2, 0.78))
    )
    sigma_x = 32.0 if role == ROLE_ANCHOR else 26.0
    sigma_y = 24.0 if role == ROLE_ANCHOR else 18.0
    dot_count = rng.randint(30, 48) if role == ROLE_ANCHOR else rng.randint(14, 26) if zone != "left_title" else rng.randint(6, 12)
    points: List[Point] = []
    dots: List[str] = []
    for _ in range(dot_count):
        point = sample_point_near(
            rng,
            center,
            rect,
            sigma_x=sigma_x,
            sigma_y=sigma_y,
            avoid=HARD_KEEP_OUT_RECTS if role != ROLE_AMBIENT else HARD_KEEP_OUT_RECTS,
            require_right_safe=(zone == "right_anchor"),
        )
        if zone == "left_title":
            strength = ambient_soft_factor(point)
            if strength < 0.18:
                continue
            opacity = clamp(0.24 + strength * rng.uniform(0.12, 0.28), 0.24, 0.56)
            radius = rng.uniform(0.7, 1.6)
        else:
            opacity = clamp(zone_opacity(zone, rng, role_intensity(role, builder.preset) * 1.55), 0.24, 0.72 if role != ROLE_ANCHOR else 0.82)
            radius = rng.uniform(0.8, 1.7 if role != ROLE_ANCHOR else 2.0)
        points.append(point)
        dots.append(
            f'<circle cx="{fmt(point[0])}" cy="{fmt(point[1])}" r="{fmt(radius)}" fill="{var_color(choose_color_role(rng, role, "dot"))}" opacity="{fmt(opacity)}" />'
        )
    if not points:
        return
    bounds = polyline_bounds(points, pad=6.0)
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--posterior-cloud" '
        f'data-motif-type="posterior_cloud" data-zone="{zone}" data-role="{role}" data-opacity-class="soft">'
        + "".join(dots)
        + "</g>"
    )
    builder.add("cloud", "posterior_cloud", zone, role, bounds, group, rect_center(bounds), 0.18 if role == ROLE_AMBIENT else 0.28)


def add_matrix_fragment(builder: Builder, zone: str, role: str, design: bool = False) -> None:
    rng = builder.rng
    motif_type = "design_matrix_fragment" if design else "matrix_fragment"
    rect = ZONE_DEFINITIONS[zone].bounds
    cols = rng.randint(4, 7) if not design else rng.randint(4, 6)
    rows = rng.randint(3, 5) if not design else rng.randint(8, 13)
    cell_w = rng.uniform(10.0, 18.0) if not design else rng.uniform(8.0, 13.0)
    cell_h = rng.uniform(8.0, 16.0) if not design else rng.uniform(6.0, 10.0)
    gap = rng.uniform(4.0, 6.0) if not design else rng.uniform(2.0, 4.0)
    width = cols * cell_w + (cols - 1) * gap
    height = rows * cell_h + (rows - 1) * gap
    anchor = sample_point_in_rect(
        rng,
        rect,
        avoid=HARD_KEEP_OUT_RECTS,
        require_right_safe=(zone == "right_anchor"),
    )
    anchor = (
        clamp(anchor[0], rect[0], rect[2] - width - 2.0),
        clamp(anchor[1], rect[1], rect[3] - height - 2.0),
    )
    bounds = (anchor[0], anchor[1], anchor[0] + width, anchor[1] + height)
    if rect_intersects_any(bounds, HARD_KEEP_OUT_RECTS):
        return
    cells: List[str] = []
    max_cell_opacity = 0.45 if design else 0.3
    for row in range(rows):
        for col in range(cols):
            if rng.random() < (0.32 if not design else 0.42):
                continue
            x = anchor[0] + col * (cell_w + gap)
            y = anchor[1] + row * (cell_h + gap)
            accent = rng.random() < (0.08 if design else 0.05)
            opacity = rng.uniform(0.22, max_cell_opacity if accent else min(0.42, max_cell_opacity))
            fill_role = "accent" if accent else choose_color_role(rng, role, "fill")
            cells.append(
                f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(cell_w)}" height="{fmt(cell_h)}" rx="{fmt(max(0.8, cell_h * 0.22))}" '
                f'fill="{var_color(fill_role)}" opacity="{fmt(opacity)}" />'
            )
    if not cells:
        return
    group_class = "design-matrix" if design else "matrix-fragment"
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--{group_class}" '
        f'data-motif-type="{motif_type}" data-zone="{zone}" data-role="{role}" data-opacity-class="soft">'
        + "".join(cells)
        + "</g>"
    )
    builder.add("fragments", motif_type, zone, role, bounds, group, rect_center(bounds), 0.22)


def add_projected_axes(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    rect = ZONE_DEFINITIONS[zone].bounds
    origin = sample_point_in_rect(rng, rect, avoid=HARD_KEEP_OUT_RECTS, require_right_safe=(zone == "right_anchor"))
    if zone == "lower_echo":
        origin = (origin[0], clamp(origin[1], rect[1] + 20.0, rect[1] + 56.0))
    lines: List[str] = []
    points = [origin]
    for angle in (-0.85, 0.0, 0.82):
        length = rng.uniform(34.0, 86.0)
        x2 = origin[0] + math.cos(angle) * length
        y2 = origin[1] + math.sin(angle) * length
        points.append((x2, y2))
        opacity = rng.uniform(0.24, 0.46 if role != ROLE_ANCHOR else 0.56)
        lines.append(
            f'<line x1="{fmt(origin[0])}" y1="{fmt(origin[1])}" x2="{fmt(x2)}" y2="{fmt(y2)}" '
            f'stroke="{var_color(choose_color_role(rng, role, "curve"))}" stroke-width="{fmt(rng.uniform(0.6, 1.2))}" '
            f'stroke-linecap="round" opacity="{fmt(opacity)}" />'
        )
    bounds = polyline_bounds(points, pad=6.0)
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--projected-axes" '
        f'data-motif-type="projected_axes" data-zone="{zone}" data-role="{role}" data-opacity-class="soft">'
        + "".join(lines)
        + "</g>"
    )
    builder.add("field", "projected_axes", zone, role, bounds, group, origin, 0.18)


def add_topography_fragment(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    rect = ZONE_DEFINITIONS[zone].bounds
    if zone == "left_field":
        center = sample_left_field_point(rng)
    else:
        center = sample_point_in_rect(rng, rect, avoid=HARD_KEEP_OUT_RECTS, require_right_safe=(zone == "right_anchor"))
    rings = rng.randint(4, 7)
    angle_steps = 12
    ring_paths: List[str] = []
    all_points: List[Point] = []
    if zone == "left_field":
        base_rx = rng.uniform(22.0, 44.0)
        base_ry = rng.uniform(16.0, 36.0)
    else:
        base_rx = rng.uniform(28.0, 64.0)
        base_ry = rng.uniform(20.0, 52.0)
    for ring in range(rings):
        t = 1.0 - ring / max(1, rings - 1)
        rx = base_rx * (0.32 + 0.68 * t)
        ry = base_ry * (0.32 + 0.68 * t)
        points: List[Point] = []
        for idx in range(angle_steps):
            angle = (math.pi * 2.0 * idx / angle_steps) + rng.uniform(-0.08, 0.08)
            radial_jitter = 1.0 + rng.uniform(-0.12, 0.12)
            x = center[0] + math.cos(angle) * rx * radial_jitter
            y = center[1] + math.sin(angle) * ry * radial_jitter
            points.append((x, y))
            all_points.append((x, y))
        points.append(points[0])
        if zone == "left_field":
            strength = ambient_soft_factor(center)
            opacity = clamp(0.22 + strength * rng.uniform(0.14, 0.3) + t * 0.08, 0.22, 0.52)
        else:
            opacity = clamp(rng.uniform(0.24, 0.4) + t * 0.14, 0.24, 0.58 if role != ROLE_ANCHOR else 0.72)
        width = rng.uniform(0.7, 1.0 if role == ROLE_AMBIENT else 1.35)
        ring_paths.append(
            f'<path d="{path_from_points(points)} Z" fill="none" stroke="{var_color(choose_color_role(rng, role, "curve"))}" '
            f'stroke-width="{fmt(width)}" stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(opacity)}" />'
        )
    if rng.random() < 0.7:
        fill_opacity = rng.uniform(0.08, 0.18 if zone != "left_field" else 0.14)
        fill_points = all_points[:angle_steps] + [all_points[0]]
        ring_paths.insert(
            0,
            f'<path d="{path_from_points(fill_points)} Z" fill="{var_color(choose_color_role(rng, role, "fill"))}" opacity="{fmt(fill_opacity)}" />',
        )
    bounds = polyline_bounds(all_points, pad=8.0)
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--topography-fragment" '
        f'data-motif-type="topography_fragment" data-zone="{zone}" data-role="{role}" data-opacity-class="medium">'
        + "".join(ring_paths)
        + "</g>"
    )
    builder.add("field", "topography_fragment", zone, role, bounds, group, center, 0.24)


def add_scan_echo(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    rect = ZONE_DEFINITIONS[zone].bounds
    group_bounds: List[Rect] = []
    pieces: List[str] = []
    count = rng.randint(4, 8)
    for _ in range(count):
        width = rng.uniform(16.0, 42.0)
        height = rng.uniform(12.0, 34.0)
        x, y = sample_point_in_rect(rng, rect, avoid=HARD_KEEP_OUT_RECTS, require_right_safe=(zone == "right_anchor"))
        x = clamp(x, rect[0], rect[2] - width)
        y = clamp(y, rect[1], rect[3] - height)
        piece_rect = (x, y, x + width, y + height)
        group_bounds.append(piece_rect)
        pieces.append(
            f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(width)}" height="{fmt(height)}" rx="{fmt(rng.uniform(2.0, 8.0))}" '
            f'fill="{var_color(choose_color_role(rng, role, "fill"))}" opacity="{fmt(rng.uniform(0.24, 0.48 if role != ROLE_ANCHOR else 0.58))}" '
            f'transform="rotate({fmt(rng.uniform(-18.0, 18.0))} {fmt(x + width * 0.5)} {fmt(y + height * 0.5)})" />'
        )
    if not group_bounds:
        return
    bounds = (
        min(b[0] for b in group_bounds),
        min(b[1] for b in group_bounds),
        max(b[2] for b in group_bounds),
        max(b[3] for b in group_bounds),
    )
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--scan-echo" '
        f'data-motif-type="scan_echo" data-zone="{zone}" data-role="{role}" data-opacity-class="soft">'
        + "".join(pieces)
        + "</g>"
    )
    builder.add("fragments", "scan_echo", zone, role, bounds, group, rect_center(bounds), 0.2)


def add_belief_update_curve(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    if zone == "left_title":
        start = sample_left_field_point(rng)
        start = (clamp(start[0], 0.0, 280.0), clamp(start[1], 90.0, 220.0))
        width = rng.uniform(150.0, 260.0)
    else:
        rect = ZONE_DEFINITIONS[zone].bounds
        start = sample_point_in_rect(rng, rect, avoid=HARD_KEEP_OUT_RECTS, require_right_safe=(zone == "right_anchor"))
        width = rng.uniform(120.0, 240.0)
    step_like = rng.random() < 0.45
    points: List[Point] = []
    base_y = start[1]
    current = start[0]
    for idx in range(rng.randint(5, 8)):
        x = current + width / rng.randint(5, 8)
        if step_like:
            y = base_y + math.tanh((idx - 2.0) / 1.35) * rng.uniform(8.0, 28.0)
        else:
            y = base_y + math.sin(idx / 1.3) * rng.uniform(10.0, 24.0) + idx * rng.uniform(-2.0, 3.0)
        points.append((current, y))
        current = x
    points.append((min(current, 1160.0), points[-1][1] + rng.uniform(-8.0, 8.0)))
    opacity = clamp(
        (0.28 if role == ROLE_AMBIENT else 0.38 if role == ROLE_STRUCTURAL else 0.5)
        + rng.uniform(0.04, 0.18),
        0.28,
        0.6 if role != ROLE_ANCHOR else 0.72,
    )
    stroke_width = rng.uniform(0.6, 1.0) if role == ROLE_AMBIENT else rng.uniform(0.8, 1.4)
    elements = [
        f'<path d="{path_from_points(points)}" fill="none" stroke="{var_color(choose_color_role(rng, role, "curve"))}" '
        f'stroke-width="{fmt(stroke_width)}" stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(opacity)}" />'
    ]
    for point in rng.sample(points[1:-1], k=min(len(points) - 2, rng.randint(1, 3))):
        elements.append(
            f'<circle cx="{fmt(point[0])}" cy="{fmt(point[1])}" r="{fmt(rng.uniform(1.0, 2.2))}" fill="{var_color(choose_color_role(rng, role, "dot"))}" opacity="{fmt(clamp(opacity * 1.1, 0.12, 0.4))}" />'
        )
    bounds = polyline_bounds(points, pad=6.0)
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--belief-update-curve" '
        f'data-motif-type="belief_update_curve" data-zone="{zone}" data-role="{role}" data-opacity-class="{opacity_class(opacity)}">'
        + "".join(elements)
        + "</g>"
    )
    builder.add("field", "belief_update_curve", zone, role, bounds, group, polyline_center(points), opacity)


def add_prediction_error_pulses(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    rect = ZONE_DEFINITIONS[zone].bounds
    if zone == "lower_echo":
        y = rng.uniform(rect[1] + 24.0, rect[1] + 66.0)
    else:
        y = rng.uniform(rect[1] + 40.0, rect[3] - 46.0)
    start_x = rng.uniform(rect[0] + 12.0, rect[2] - 220.0)
    end_x = min(rect[2] - 8.0, start_x + rng.uniform(140.0, 260.0))
    base_opacity = rng.uniform(0.26, 0.42 if role == ROLE_AMBIENT else 0.52)
    pieces = [
        f'<line x1="{fmt(start_x)}" y1="{fmt(y)}" x2="{fmt(end_x)}" y2="{fmt(y)}" stroke="{var_color("gray_soft")}" stroke-width="{fmt(rng.uniform(0.5, 0.9))}" opacity="{fmt(base_opacity)}" />'
    ]
    xs = [lerp(start_x, end_x, idx / (rng.randint(7, 10) - 1)) for idx in range(rng.randint(7, 10))]
    pulse_points = [(start_x, y), (end_x, y)]
    for x in xs:
        pulse_height = rng.uniform(6.0, 22.0 if role != ROLE_AMBIENT else 14.0)
        direction = -1.0 if rng.random() < 0.45 else 1.0
        y2 = y + pulse_height * direction
        pulse_points.append((x, y2))
        opacity = rng.uniform(0.28, 0.5 if role != ROLE_ANCHOR else 0.62)
        color_role = "accent" if rng.random() < 0.14 else choose_color_role(rng, role, "curve")
        pieces.append(
            f'<line x1="{fmt(x)}" y1="{fmt(y)}" x2="{fmt(x)}" y2="{fmt(y2)}" stroke="{var_color(color_role)}" '
            f'stroke-width="{fmt(rng.uniform(0.7, 1.2))}" stroke-linecap="round" opacity="{fmt(opacity)}" />'
        )
    bounds = polyline_bounds(pulse_points, pad=6.0)
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--prediction-error-pulses" '
        f'data-motif-type="prediction_error_pulses" data-zone="{zone}" data-role="{role}" data-opacity-class="{opacity_class(base_opacity)}">'
        + "".join(pieces)
        + "</g>"
    )
    builder.add("field", "prediction_error_pulses", zone, role, bounds, group, rect_center(bounds), max(base_opacity, 0.12))


def add_time_series_stack(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    rect = ZONE_DEFINITIONS[zone].bounds
    start_x = rng.uniform(rect[0] + 10.0, rect[2] - 240.0)
    width = rng.uniform(150.0, 260.0)
    rows = rng.randint(3, 6)
    start_y = rng.uniform(rect[1] + 16.0, rect[3] - 90.0)
    row_gap = rng.uniform(14.0, 22.0)
    pieces: List[str] = []
    bounds_list: List[Rect] = []
    for row in range(rows):
        points: List[Point] = []
        for idx in range(7):
            x = start_x + width * idx / 6.0
            y = start_y + row * row_gap + math.sin(idx * rng.uniform(0.72, 1.18) + row * 0.48) * rng.uniform(4.0, 10.0)
            y += rng.uniform(-2.0, 2.0)
            points.append((x, y))
        opacity = rng.uniform(0.28, 0.42 if role == ROLE_AMBIENT else 0.56)
        pieces.append(
            f'<path d="{path_from_points(points)}" fill="none" stroke="{var_color(choose_color_role(rng, role, "curve"))}" '
            f'stroke-width="{fmt(rng.uniform(0.6, 1.2 if role != ROLE_AMBIENT else 0.9))}" stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(opacity)}" />'
        )
        bounds_list.append(polyline_bounds(points, pad=4.0))
    bounds = (
        min(b[0] for b in bounds_list),
        min(b[1] for b in bounds_list),
        max(b[2] for b in bounds_list),
        max(b[3] for b in bounds_list),
    )
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--time-series-stack" '
        f'data-motif-type="time_series_stack" data-zone="{zone}" data-role="{role}" data-opacity-class="soft">'
        + "".join(pieces)
        + "</g>"
    )
    builder.add("field", "time_series_stack", zone, role, bounds, group, rect_center(bounds), 0.2)


def add_event_raster_fragment(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    rect = ZONE_DEFINITIONS[zone].bounds
    origin = sample_point_in_rect(rng, rect, avoid=HARD_KEEP_OUT_RECTS, require_right_safe=(zone == "right_anchor"))
    rows = rng.randint(3, 5)
    width = rng.uniform(120.0, 240.0)
    row_gap = rng.uniform(12.0, 18.0)
    markers: List[str] = []
    points: List[Point] = []
    for row in range(rows):
        row_y = origin[1] + row * row_gap
        events = sorted(origin[0] + rng.uniform(0.0, width) for _ in range(rng.randint(5, 9)))
        for event_x in events:
            use_dot = rng.random() < 0.35
            opacity = rng.uniform(0.28, 0.56 if role != ROLE_AMBIENT else 0.42)
            if use_dot:
                radius = rng.uniform(0.8, 1.6)
                markers.append(
                    f'<circle cx="{fmt(event_x)}" cy="{fmt(row_y)}" r="{fmt(radius)}" fill="{var_color(choose_color_role(rng, role, "dot"))}" opacity="{fmt(opacity)}" />'
                )
            else:
                y2 = row_y + rng.uniform(4.0, 10.0)
                markers.append(
                    f'<line x1="{fmt(event_x)}" y1="{fmt(row_y)}" x2="{fmt(event_x)}" y2="{fmt(y2)}" stroke="{var_color(choose_color_role(rng, role, "curve"))}" '
                    f'stroke-width="{fmt(rng.uniform(0.7, 1.1))}" stroke-linecap="round" opacity="{fmt(opacity)}" />'
                )
            points.append((event_x, row_y))
    if not points:
        return
    bounds = polyline_bounds(points, pad=8.0)
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--event-raster-fragment" '
        f'data-motif-type="event_raster_fragment" data-zone="{zone}" data-role="{role}" data-opacity-class="soft">'
        + "".join(markers)
        + "</g>"
    )
    builder.add("field", "event_raster_fragment", zone, role, bounds, group, rect_center(bounds), 0.18)


def add_posterior_density_ridge(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    rect = ZONE_DEFINITIONS[zone].bounds
    start_x = rng.uniform(rect[0] + 12.0, rect[2] - 180.0)
    width = rng.uniform(100.0, 180.0)
    base_y = rng.uniform(rect[1] + 18.0, rect[3] - 32.0)
    points: List[Point] = []
    for idx in range(8):
        t = idx / 7.0
        x = start_x + width * t
        y = base_y - math.exp(-((t - 0.48) ** 2) / rng.uniform(0.03, 0.08)) * rng.uniform(10.0, 28.0)
        y += rng.uniform(-2.0, 2.0)
        points.append((x, y))
    baseline = [(points[-1][0], base_y + 8.0), (points[0][0], base_y + 8.0)]
    fill_opacity = rng.uniform(0.12, 0.24)
    stroke_opacity = rng.uniform(0.3, 0.5)
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--posterior-density-ridge" '
        f'data-motif-type="posterior_density_ridge" data-zone="{zone}" data-role="{role}" data-opacity-class="{opacity_class(stroke_opacity)}">'
        f'<path d="{path_from_points(points + baseline)} Z" fill="{var_color(choose_color_role(rng, role, "fill"))}" opacity="{fmt(fill_opacity)}" />'
        f'<path d="{path_from_points(points)}" fill="none" stroke="{var_color(choose_color_role(rng, role, "curve"))}" stroke-width="{fmt(rng.uniform(0.6, 1.2))}" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(stroke_opacity)}" />'
        "</g>"
    )
    bounds = polyline_bounds(points + baseline, pad=4.0)
    builder.add("field", "posterior_density_ridge", zone, role, bounds, group, rect_center(bounds), stroke_opacity)


def add_model_comparison_interval(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    rect = ZONE_DEFINITIONS[zone].bounds
    origin = sample_point_in_rect(rng, rect, avoid=HARD_KEEP_OUT_RECTS, require_right_safe=(zone == "right_anchor"))
    rows = rng.randint(3, 5)
    row_gap = rng.uniform(14.0, 20.0)
    pieces: List[str] = []
    points: List[Point] = []
    for row in range(rows):
        y = origin[1] + row * row_gap
        x1 = origin[0] + rng.uniform(0.0, 24.0)
        x2 = x1 + rng.uniform(36.0, 82.0)
        dot_x = lerp(x1, x2, rng.uniform(0.28, 0.72))
        opacity = rng.uniform(0.3, 0.52)
        color = choose_color_role(rng, role, "curve")
        pieces.append(
            f'<line x1="{fmt(x1)}" y1="{fmt(y)}" x2="{fmt(x2)}" y2="{fmt(y)}" stroke="{var_color(color)}" stroke-width="{fmt(rng.uniform(0.8, 1.2))}" stroke-linecap="round" opacity="{fmt(opacity)}" />'
        )
        pieces.append(
            f'<circle cx="{fmt(dot_x)}" cy="{fmt(y)}" r="{fmt(rng.uniform(1.2, 2.2))}" fill="{var_color(choose_color_role(rng, role, "dot"))}" opacity="{fmt(clamp(opacity * 1.15, 0.12, 0.35))}" />'
        )
        points.extend([(x1, y), (x2, y), (dot_x, y)])
    bounds = polyline_bounds(points, pad=6.0)
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--model-comparison-interval" '
        f'data-motif-type="model_comparison_interval" data-zone="{zone}" data-role="{role}" data-opacity-class="soft">'
        + "".join(pieces)
        + "</g>"
    )
    builder.add("field", "model_comparison_interval", zone, role, bounds, group, rect_center(bounds), 0.2)


def add_state_transition_mini_graph(builder: Builder, zone: str, role: str) -> None:
    rng = builder.rng
    rect = ZONE_DEFINITIONS[zone].bounds
    center = sample_point_in_rect(rng, rect, avoid=HARD_KEEP_OUT_RECTS, require_right_safe=(zone == "right_anchor"))
    node_count = rng.randint(3, 5)
    radius_x = rng.uniform(18.0, 46.0)
    radius_y = rng.uniform(14.0, 36.0)
    nodes: List[Point] = []
    for idx in range(node_count):
        angle = (math.pi * 2.0 * idx / node_count) + rng.uniform(-0.28, 0.28)
        nodes.append((center[0] + math.cos(angle) * radius_x, center[1] + math.sin(angle) * radius_y))
    pieces: List[str] = []
    for idx in range(node_count - 1):
        start, end = nodes[idx], nodes[idx + 1]
        pieces.append(
            f'<path d="{path_from_points([start, ((start[0] + end[0]) * 0.5 + rng.uniform(-10.0, 10.0), (start[1] + end[1]) * 0.5 + rng.uniform(-10.0, 10.0)), end])}" '
            f'fill="none" stroke="{var_color(choose_color_role(rng, role, "curve"))}" stroke-width="{fmt(rng.uniform(0.7, 1.2))}" stroke-linecap="round" stroke-linejoin="round" opacity="{fmt(rng.uniform(0.32, 0.5))}" />'
        )
    for node in nodes:
        pieces.append(
            f'<circle cx="{fmt(node[0])}" cy="{fmt(node[1])}" r="{fmt(rng.uniform(1.4, 3.0))}" fill="{var_color(choose_color_role(rng, role, "dot"))}" opacity="{fmt(rng.uniform(0.34, 0.56))}" />'
        )
    bounds = polyline_bounds(nodes, pad=14.0)
    group = (
        f'<g class="neuro-background__motif neuro-background__motif--state-transition-mini-graph" '
        f'data-motif-type="state_transition_mini_graph" data-zone="{zone}" data-role="{role}" data-opacity-class="soft">'
        + "".join(pieces)
        + "</g>"
    )
    builder.add("field", "state_transition_mini_graph", zone, role, bounds, group, center, 0.22)


def add_ambient_dots(builder: Builder) -> None:
    rng = builder.rng
    count = builder.preset.ambient_dots
    dots: List[str] = []
    points: List[Point] = []
    for _ in range(count):
        point = sample_left_field_point(rng)
        strength = ambient_soft_factor(point)
        radius = rng.uniform(0.6, 1.8)
        opacity = clamp(0.16 + strength * rng.uniform(0.06, 0.16), 0.16, 0.34)
        dots.append(
            f'<circle cx="{fmt(point[0])}" cy="{fmt(point[1])}" r="{fmt(radius)}" fill="{var_color(choose_color_role(rng, ROLE_AMBIENT, "dot"))}" opacity="{fmt(opacity)}" />'
        )
        points.append(point)
    if not points:
        return
    bounds = polyline_bounds(points, pad=3.0)
    group = (
        '<g class="neuro-background__motif neuro-background__motif--ambient-dots" '
        'data-motif-type="ambient_dots" data-zone="left_field" data-role="ambient" data-opacity-class="soft">'
        + "".join(dots)
        + "</g>"
    )
    builder.add("cloud", "ambient_dots", "left_field", ROLE_AMBIENT, bounds, group, rect_center(bounds), 0.16)


def populate(builder: Builder) -> None:
    preset = builder.preset

    for _ in range(preset.ambient_contours):
        add_contour_field(builder, "left_field", ROLE_AMBIENT)
    for zone in ("left_title", "central_bridge", "right_anchor", "lower_echo"):
        for _ in range(max(1, preset.contour_fields // 4)):
            add_contour_field(builder, zone, ROLE_AMBIENT if zone in {"left_title", "lower_echo"} else ROLE_STRUCTURAL)

    # True flow-field layer. It is drawn before trajectories so the trajectory
    # remains the visual anchor.
    add_vector_field(builder, "right_anchor", ROLE_STRUCTURAL)
    if builder.variant in {"dense", "rich", "composite", "latent_hero"}:
        add_vector_field(builder, "central_bridge", ROLE_AMBIENT)

    add_ambient_dots(builder)

    for index in range(preset.latent_trajectories):
        add_latent_trajectory(builder, index)

    posterior_plan = [
        ("left_title", ROLE_AMBIENT),
        ("central_bridge", ROLE_STRUCTURAL),
        ("right_anchor", ROLE_ANCHOR),
    ]
    for idx in range(preset.posterior_clouds):
        zone, role = posterior_plan[min(idx, len(posterior_plan) - 1)]
        if zone == "left_title" and not builder.preset.conservative_left and idx == 0:
            add_posterior_cloud(builder, zone, role)
        elif zone != "left_title":
            add_posterior_cloud(builder, zone, role)
        elif builder.preset.conservative_left:
            add_posterior_cloud(builder, "central_bridge", ROLE_AMBIENT)

    for idx in range(preset.matrix_fragments):
        add_matrix_fragment(builder, "right_anchor" if idx == 0 else "lower_echo", ROLE_STRUCTURAL)
    for idx in range(preset.design_matrix_fragments):
        zone = "right_anchor" if idx == 0 else "central_bridge"
        add_matrix_fragment(builder, zone, ROLE_STRUCTURAL, design=True)
    for idx in range(preset.projected_axes):
        add_projected_axes(builder, "lower_echo" if idx == 0 else "right_anchor", ROLE_STRUCTURAL)
    for idx in range(preset.scan_echoes):
        add_scan_echo(builder, "right_anchor", ROLE_STRUCTURAL if idx < preset.scan_echoes - 1 else ROLE_ANCHOR)
    topo_zones = ["left_field", "central_bridge", "right_anchor", "left_title"]
    for idx in range(preset.topography_fragments):
        zone = topo_zones[idx % len(topo_zones)]
        if zone == "left_title" and builder.preset.conservative_left:
            zone = "central_bridge"
        role = ROLE_AMBIENT if zone in {"left_title", "left_field"} else ROLE_STRUCTURAL if zone == "central_bridge" else ROLE_ANCHOR
        add_topography_fragment(builder, zone, role)

    belief_zones = ["left_field", "left_title", "central_bridge", "right_anchor", "central_bridge"]
    for idx in range(preset.belief_curves):
        zone = belief_zones[idx % len(belief_zones)]
        if zone == "left_field" and builder.preset.conservative_left:
            zone = "left_title"
        role = ROLE_AMBIENT if zone in {"left_title", "left_field"} else ROLE_ANCHOR if zone == "right_anchor" and idx == preset.belief_curves - 1 else ROLE_STRUCTURAL
        add_belief_update_curve(builder, zone, role)

    pulse_zones = ["central_bridge", "lower_echo", "right_anchor"]
    for idx in range(preset.prediction_error_pulses):
        zone = pulse_zones[idx % len(pulse_zones)]
        role = ROLE_AMBIENT if zone == "lower_echo" else ROLE_STRUCTURAL
        add_prediction_error_pulses(builder, zone, role)

    stack_zones = ["left_field", "central_bridge", "right_anchor", "left_title"]
    for idx in range(preset.time_series_stacks):
        zone = stack_zones[idx % len(stack_zones)]
        if zone in {"left_title", "left_field"} and builder.preset.conservative_left:
            zone = "central_bridge"
        role = ROLE_AMBIENT if zone in {"left_title", "left_field"} else ROLE_STRUCTURAL
        add_time_series_stack(builder, zone, role)

    raster_zones = ["lower_echo", "left_title", "right_anchor"]
    for idx in range(preset.event_rasters):
        zone = raster_zones[idx % len(raster_zones)]
        if zone == "left_title" and builder.preset.conservative_left:
            zone = "lower_echo"
        role = ROLE_AMBIENT if zone in {"left_title", "lower_echo"} else ROLE_STRUCTURAL
        add_event_raster_fragment(builder, zone, role)

    ridge_zones = ["central_bridge", "right_anchor"]
    for idx in range(preset.posterior_density_ridges):
        zone = ridge_zones[idx % len(ridge_zones)]
        add_posterior_density_ridge(builder, zone, ROLE_STRUCTURAL)

    interval_zones = ["right_anchor", "lower_echo"]
    for idx in range(preset.model_comparison_intervals):
        add_model_comparison_interval(builder, interval_zones[idx % len(interval_zones)], ROLE_STRUCTURAL)

    graph_zones = ["central_bridge", "right_anchor"]
    for idx in range(preset.state_transition_mini_graphs):
        add_state_transition_mini_graph(builder, graph_zones[idx % len(graph_zones)], ROLE_STRUCTURAL if idx == 0 else ROLE_ANCHOR)


def build_artifact(variant: str, seed: int, debug_overlay: bool = False) -> Tuple[GenerationStats, List[str], List[DebugRecord]]:
    builder = Builder(variant, seed)
    populate(builder)
    lines = [
        (
            f"  <!-- Variant={variant} seed={seed} motifs={sum(builder.stats.motif_counts.values())} "
            f"left_half={builder.stats.zone_occupancy.get('left_half', 0)} title_zone={builder.stats.zone_occupancy.get('title_zone', 0)} "
            f"prose_zone={builder.stats.zone_occupancy.get('prose_zone', 0)} right_sidebar_zone={builder.stats.zone_occupancy.get('right_sidebar_zone', 0)} "
            f"latest_posts_zone={builder.stats.zone_occupancy.get('latest_posts_zone', 0)} -->"
        ),
        '  <g class="neuro-background__field neuro-background__contours">',
        *[f"    {element}" for element in builder.groups["field"]],
        "  </g>",
        '  <g class="neuro-background__fragments neuro-background__grids">',
        *[f"    {element}" for element in builder.groups["fragments"]],
        "  </g>",
        '  <g class="neuro-background__trajectory">',
        *[f"    {element}" for element in builder.groups["trajectory"]],
        "  </g>",
        '  <g class="neuro-background__cloud neuro-background__dots">',
        *[f"    {element}" for element in builder.groups["cloud"]],
        "  </g>",
    ]
    if debug_overlay:
        lines.extend(build_debug_overlay(builder.debug_records))
    return builder.stats, lines, builder.debug_records


def build_art_markup(variant: str, seed: int, debug_overlay: bool = False) -> List[str]:
    _, lines, _ = build_artifact(variant, seed, debug_overlay=debug_overlay)
    return lines


def stats_payload(variant: str, seed: int) -> Dict[str, object]:
    stats, _, debug_records = build_artifact(variant, seed, debug_overlay=False)
    motif_zone_counts: Dict[str, int] = {}
    role_counts: Dict[str, int] = {}
    for record in debug_records:
        key = f"{record.motif_type}|{record.zone}"
        motif_zone_counts[key] = motif_zone_counts.get(key, 0) + 1
        role_counts[record.role] = role_counts.get(record.role, 0) + 1
    return {
        "variant": variant,
        "seed": seed,
        "motif_counts": stats.motif_counts,
        "zone_occupancy": stats.zone_occupancy,
        "motif_zone_counts": motif_zone_counts,
        "role_counts": role_counts,
    }


def build_debug_overlay(debug_records: Sequence[DebugRecord]) -> List[str]:
    overlay = [
        '  <g class="neuro-background__debug" aria-hidden="true">',
        '    <rect x="0.5" y="0.5" width="1199" height="899" fill="none" stroke="rgba(25, 25, 25, 0.48)" stroke-width="1" />',
    ]
    for zone_name, zone in ZONE_DEFINITIONS.items():
        x1, y1, x2, y2 = zone.bounds
        style = DEBUG_ZONE_STYLES[zone_name]
        overlay.append(
            f'    <rect x="{fmt(x1)}" y="{fmt(y1)}" width="{fmt(x2 - x1)}" height="{fmt(y2 - y1)}" rx="18" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="1.4" stroke-dasharray="10 8" />'
        )
    for x1, y1, x2, y2 in SOFT_KEEP_OUT_RECTS:
        overlay.append(
            f'    <rect x="{fmt(x1)}" y="{fmt(y1)}" width="{fmt(x2 - x1)}" height="{fmt(y2 - y1)}" rx="18" fill="rgba(236, 174, 61, 0.08)" stroke="rgba(236, 174, 61, 0.72)" stroke-width="1.1" stroke-dasharray="8 6" />'
        )
    for x1, y1, x2, y2 in HARD_KEEP_OUT_RECTS:
        overlay.append(
            f'    <rect x="{fmt(x1)}" y="{fmt(y1)}" width="{fmt(x2 - x1)}" height="{fmt(y2 - y1)}" rx="16" fill="rgba(196, 53, 64, 0.08)" stroke="rgba(196, 53, 64, 0.72)" stroke-width="1.2" stroke-dasharray="6 5" />'
        )
    polygon_path = " ".join(
        [f"M {fmt(RIGHT_ANCHOR_SAFE_POLYGON[0][0])} {fmt(RIGHT_ANCHOR_SAFE_POLYGON[0][1])}"]
        + [f"L {fmt(x)} {fmt(y)}" for x, y in RIGHT_ANCHOR_SAFE_POLYGON[1:]]
        + ["Z"]
    )
    overlay.append(
        f'    <path d="{polygon_path}" fill="rgba(132, 120, 245, 0.04)" stroke="rgba(132, 120, 245, 0.72)" stroke-width="1.4" stroke-dasharray="7 6" />'
    )
    for record in debug_records:
        x1, y1, x2, y2 = record.rect
        color = DEBUG_MOTIF_COLORS.get(record.motif_type, "rgba(110, 110, 110, 0.8)")
        overlay.append(
            f'    <rect x="{fmt(x1)}" y="{fmt(y1)}" width="{fmt(max(0.0, x2 - x1))}" height="{fmt(max(0.0, y2 - y1))}" '
            f'fill="none" stroke="{color}" stroke-width="{fmt(1.0 if record.role != ROLE_ANCHOR else 1.4)}" stroke-dasharray="{ROLE_DASH[record.role]}" opacity="0.84" />'
        )
        overlay.append(
            f'    <circle cx="{fmt(record.center[0])}" cy="{fmt(record.center[1])}" r="{fmt(2.2 if record.opacity_class != "strong" else 3.0)}" fill="{color}" opacity="0.88" />'
        )
    overlay.append("  </g>")
    return overlay


def build_svg(width: int, height: int, variant: str, seed: int, debug_overlay: bool = False) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {DEFAULT_WIDTH} {DEFAULT_HEIGHT}" '
            f'width="{width}" height="{height}" preserveAspectRatio="xMidYMid meet" '
            'aria-hidden="true" role="presentation">'
        ),
        *build_art_markup(variant, seed, debug_overlay=debug_overlay),
        "</svg>",
    ]
    return "\n".join(lines) + "\n"


def build_fragment(variant: str, seed: int, debug_overlay: bool = False) -> str:
    return "\n".join(build_art_markup(variant, seed, debug_overlay=debug_overlay)) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate static SVG neuro background assets.")
    parser.add_argument("--variant", choices=sorted(VARIANT_PRESETS.keys()), default="balanced")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output", required=True)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument(
        "--fragment",
        action="store_true",
        help="Emit SVG interior markup only for inclusion inside an existing host SVG.",
    )
    parser.add_argument(
        "--debug-overlay",
        action="store_true",
        help="Add review-only overlays for zones, keep-outs, and motif-class bounds.",
    )
    parser.add_argument(
        "--stats-output",
        help="Optional JSON path for deterministic motif and occupancy counts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    markup = (
        build_fragment(args.variant, args.seed, debug_overlay=args.debug_overlay)
        if args.fragment
        else build_svg(args.width, args.height, args.variant, args.seed, debug_overlay=args.debug_overlay)
    )
    output_path.write_text(markup, encoding="utf-8", newline="\n")
    if args.stats_output:
        stats_path = Path(args.stats_output)
        stats_path.parent.mkdir(parents=True, exist_ok=True)
        stats_path.write_text(json.dumps(stats_payload(args.variant, args.seed), indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
