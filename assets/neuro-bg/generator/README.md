# Neuro Background SVG Generator

This generator produces deterministic review-only SVG background candidates for the fixed `1200x900` neuro-background viewport.

It does not change the live `neuro_background` include, page layout, page copy, navigation, or production asset wiring.

## Composition Model

Each generated SVG preserves the same fixed-page geometry and keep-out logic used by the current about-page background:

- `left_title`: faint ambient scientific fragments only
- `central_bridge`: medium-contrast structural fragments
- `right_anchor`: the strongest restrained anchor zone
- `lower_echo`: sparse post-divider continuation
- `left_field`: extra ambient left-edge field for the about-page reading side

The generator now treats motif selection as a role-aware library instead of a single cloud-plus-curve recipe.

Roles:

- `ambient`: very low contrast, safe near text when placement clears the hard keep-outs
- `structural`: medium contrast, intended for whitespace, bridge regions, and margins
- `anchor`: restrained high-contrast motifs, concentrated on the right side or outer edges

## Motif Library

Existing motif families retained:

- `contour_field`
- `posterior_cloud`
- `latent_trajectory`
- `matrix_fragment`
- `projected_axes`
- `scan_echo`

New plot-derived motif families:

- `topography_fragment`
- `belief_update_curve`
- `prediction_error_pulses`
- `time_series_stack`
- `event_raster_fragment`
- `design_matrix_fragment`
- `posterior_density_ridge`
- `model_comparison_interval`
- `state_transition_mini_graph`

All motifs are text-free. The generator does not emit labels, axes text, equations, or fake annotations.

## Tonal Palette

The output uses restrained CSS-variable-driven color roles with fallbacks:

- `--neuro-bg-ink-strong`
- `--neuro-bg-ink`
- `--neuro-bg-ink-soft`
- `--neuro-bg-gray`
- `--neuro-bg-gray-soft`
- `--neuro-bg-indigo`
- `--neuro-bg-indigo-soft`
- `--neuro-bg-violet`
- `--neuro-bg-violet-soft`
- `--neuro-bg-accent`

If those variables are not yet defined in production CSS, the SVG falls back to internal gray / indigo / violet values.

## Variants

Supported variants:

- `sparse`
- `balanced`
- `dense`
- `rich`
- `composite`
- `rich_sparse`

`rich` and `composite` are equivalent rich-library presets. `rich_sparse` is the conservative left-field version for review.

## Generate One Asset

From the repo root:

```powershell
py assets/neuro-bg/generator/generate_neuro_bg.py --variant rich --seed 10 --output assets/neuro-bg/generated/about-rich-leftfield-seed-010.svg
```

If `python` is preferred:

```bash
python assets/neuro-bg/generator/generate_neuro_bg.py --variant rich --seed 10 --output assets/neuro-bg/generated/about-rich-leftfield-seed-010.svg
```

## Parameters

- `--variant`: one of the presets listed above
- `--seed`: deterministic seed
- `--output`: output SVG path
- `--width`: rendered width attribute, default `1200`
- `--height`: rendered height attribute, default `900`
- `--fragment`: emit only the interior SVG markup for host-SVG inclusion workflows
- `--debug-overlay`: add review-only overlays for zones, keep-outs, and motif-class bounds
- `--stats-output`: optional JSON file with deterministic motif and zone-occupancy counts

Generated SVGs preserve:

- `viewBox="0 0 1200 900"`
- `preserveAspectRatio="xMidYMid meet"`

## Review Set For This Pass

```powershell
py assets/neuro-bg/generator/generate_neuro_bg.py --variant rich --seed 10 --output assets/neuro-bg/generated/about-rich-leftfield-seed-010.svg --stats-output assets/neuro-bg/generated/about-rich-leftfield-seed-010.json
py assets/neuro-bg/generator/generate_neuro_bg.py --variant rich --seed 11 --output assets/neuro-bg/generated/about-rich-leftfield-seed-011.svg --stats-output assets/neuro-bg/generated/about-rich-leftfield-seed-011.json
py assets/neuro-bg/generator/generate_neuro_bg.py --variant rich --seed 12 --output assets/neuro-bg/generated/about-rich-leftfield-seed-012.svg --stats-output assets/neuro-bg/generated/about-rich-leftfield-seed-012.json
py assets/neuro-bg/generator/generate_neuro_bg.py --variant rich --seed 10 --debug-overlay --output assets/neuro-bg/generated/about-rich-leftfield-seed-010-debug.svg --stats-output assets/neuro-bg/generated/about-rich-leftfield-seed-010-debug.json
py assets/neuro-bg/generator/generate_neuro_bg.py --variant rich_sparse --seed 10 --output assets/neuro-bg/generated/about-rich-sparse-leftfield-seed-010.svg --stats-output assets/neuro-bg/generated/about-rich-sparse-leftfield-seed-010.json
```

## Debug Overlay

Debug mode is class-aware now.

It shows:

- composition zones
- hard and soft keep-outs
- the right-anchor safe polygon
- motif bounds
- motif centers
- motif-class color coding
- role-specific dash patterns

The overlay does not use SVG `<text>` labels. Visual inspection is done through motif-class color and role pattern differences.

Each emitted motif also carries internal metadata attributes:

- `data-motif-type`
- `data-zone`
- `data-role`
- `data-opacity-class`

## Save Location

Store review candidates in:

```text
assets/neuro-bg/generated/
```

The generator itself lives in:

```text
assets/neuro-bg/generator/
```

## Visual Review Rule

Generated assets remain manual-review candidates only.

Review flow:

1. Generate several seeds for the target preset.
2. Inspect them in both light and dark themes.
3. Check that the left side shows multiple faint scientific fragments rather than one cloud-plus-curve pair or sparse isolated dots.
4. Confirm that stronger anchors stay out of the title and prose keep-outs.
5. Prefer candidates with visible topographical contours, stacked traces, and structural fragments over candidates dominated by single circles.
6. Use the debug overlay when needed to inspect motif diversity by class and zone.
7. Select any production replacement in a later bounded pass only after manual review.

This pass does not wire any newly generated SVG into production automatically.
