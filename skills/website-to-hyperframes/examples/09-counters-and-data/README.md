# Section 09 — Counters and Data

Scenes that visualize numbers, timelines, and pipelines. The counter pattern (deterministic `tl.set(textContent)` at evenly-spaced timestamps) is mandatory for any counter animation in a HyperFrames composition — `onUpdate` callbacks do not fire reliably during snapshot/render seek.

**When to study this section:** any beat with stats, growth claims, pipeline/flow diagrams, educational explainers, or timelines.

---

## Scenes

| Scene | Duration | Technique | Why study |
|-------|----------|-----------|-----------|
| [`scene-01-timeline-diagram/`](scene-01-timeline-diagram/) | 8.5s | Editorial cream/parchment background. Build phases: eyebrow "anatomy of a composition" → div rectangle + timeline axis with tick marks → second div docks beside the first → div changes to styled state → SVG easing curve draws + teal slider dot follows it via MotionPath → camera zooms onto curve → exit blur. | Cinematic educational viz. Demonstrates how to BUILD a diagram on screen, not just present it. SVG path drawing + MotionPath + camera zoom + multi-phase staging. |
| [`scene-02-pipeline-diagram/`](scene-02-pipeline-diagram/) | 10.7s | Vertical scroll-pan camera through a 4-step pipeline: Agent (writes HTML) → Renderer (captures every frame) → MP4 output → Deterministic proof (identical card stacks split apart with green check badge). SVG dashed flow connectors with orange pip markers slide between stages. | Demonstrates pipeline/flow-diagram beat: scroll-pan motion + SVG connector draw + icon choreography + payoff with side-by-side cards proving determinism. |

---

## QC log

- scene-01: **PASS** — 6 frames; lifted from `launch-video/compositions/anatomy.html` (488 lines). Frame 5 captures the curve+slider zoom moment perfectly. Frame 6 shows clean exit blur. All technique labels preserved (`anatomy of a composition`, `<div>`, `start: 0`, `duration: 5`, `power2.out`).
- scene-02: **PASS** — 6 frames; lifted from `launch-video/compositions/engine.html` (409 lines). Frames 2-5 progress vertically through the Agent → flow connector → Deterministic block stages. Card-split at frame 5 with "Identical output, every time." badge visible. Source used generic Agent/Renderer/MP4 labels so no rebranding needed.
