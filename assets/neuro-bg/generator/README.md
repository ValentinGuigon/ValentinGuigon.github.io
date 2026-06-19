# Neuro Background SVG Generator

This generator creates static SVG background candidates that match the site's existing computational-neuroscience art direction without changing the live `neuro_background` component or any page layout.

It preserves the current background grammar:

- contour/vector-field curves
- posterior-like dot clouds
- restrained latent-state trajectories with sparse nodes
- small matrix/grid fragments

It also preserves the current composition rules:

- right-weighted density
- low density over the left reading column
- safe bounds derived from the current clipped `1200x900` background region
- existing `sparse`, `balanced`, and `dense` variant names

## Generate One Asset

From the repo root, run:

```bash
python assets/neuro-bg/generator/generate_neuro_bg.py --variant balanced --seed 1 --output assets/neuro-bg/generated/about-balanced-seed-001.svg
```

If `python` is not on your PATH in this environment, use the Python launcher instead:

```powershell
py assets/neuro-bg/generator/generate_neuro_bg.py --variant balanced --seed 1 --output assets/neuro-bg/generated/about-balanced-seed-001.svg
```

## Generate Multiple Seeds

PowerShell example:

```powershell
foreach ($seed in 1..3) {
  $name = ('assets/neuro-bg/generated/about-balanced-seed-{0:d3}.svg' -f $seed)
  py assets/neuro-bg/generator/generate_neuro_bg.py --variant balanced --seed $seed --output $name
}
```

You can also switch presets while keeping the same seed:

```powershell
py assets/neuro-bg/generator/generate_neuro_bg.py --variant sparse --seed 1 --output assets/neuro-bg/generated/about-sparse-seed-001.svg
py assets/neuro-bg/generator/generate_neuro_bg.py --variant balanced --seed 1 --output assets/neuro-bg/generated/about-balanced-seed-001.svg
py assets/neuro-bg/generator/generate_neuro_bg.py --variant dense --seed 1 --output assets/neuro-bg/generated/projects-dense-seed-001.svg
```

## Parameters

- `--variant`: `sparse`, `balanced`, or `dense`
- `--seed`: deterministic random seed
- `--output`: output SVG path
- `--width`: rendered width attribute, default `1200`
- `--height`: rendered height attribute, default `900`

The generator keeps the current `viewBox="0 0 1200 900"` coordinate system while allowing different rendered width/height attributes.

## Where Files Are Saved

Generated SVGs should be saved under:

```text
assets/neuro-bg/generated/
```

The generator directory itself lives at:

```text
assets/neuro-bg/generator/
```

## How To Choose A Generated Asset For A Page

This pass does not wire generated assets into production automatically.

Recommended review flow:

1. Generate several seeds for the page and density preset you want to test.
2. Review the SVGs visually in both light and dark mode contexts.
3. Pick one candidate that preserves the existing editorial balance and safe reading area.
4. In a later bounded pass, decide whether and how to map the selected SVG into the current background system.

Current page-to-variant examples in the repo:

- home/about uses `balanced`
- projects uses `dense`

## Visual Review Rule

Generated assets must be visually reviewed before replacing any production background asset or before changing the current `neuro_background` include.

This generator is for reproducible candidate creation only. The current site appearance should remain unchanged until a later manual-selection pass approves a specific SVG.
