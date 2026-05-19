# Section 07 — HTML in Canvas

Compositions that draw to `<canvas>` — WebGL fragment shaders, Canvas 2D procedural art, HTML-in-canvas VFX patterns. The category that makes HyperFrames distinct from a slideshow tool.

**When to study this section:** any beat where you want generative texture, organic motion that CSS can't do, or cinematic VFX over composed HTML.

---

## Scenes

| Scene | Duration | Technique | Why study |
|-------|----------|-----------|-----------|
| [`scene-01-webgl-shader/`](scene-01-webgl-shader/) | 1.2s | WebGL fragment shader with domain-warp FBM noise + cosine palette. Canvas 2D fallback (animated multi-stop radial + linear iridescent sweep) for headless / no-WebGL contexts. | The pattern for shader-based generative art with a graceful fallback. Both branches present so the scene renders even when WebGL isn't available. |
| [`scene-02-canvas-ascii/`](scene-02-canvas-ascii/) | 3.9s | Canvas 2D ASCII art with procedural hash-noise + BFS depth mapping + lightning strikes + 5×5 bitmap font rendering. Lightning bolts strike across the frame revealing "THE END" in amber ASCII glyphs with "GO MAKE SOMETHING" subtext. | Demonstrates Canvas 2D for headless rendering — no WebGL needed. **Important pattern**: uses `gsap.ticker.add()` reading `tl.time()` to drive `renderAtTime()` instead of `tl.to(proxy, { onUpdate: render })` — the proxy+onUpdate pattern does NOT fire under `tl.seek()` which the snapshot/render CLI uses. |

---

## QC log

- scene-01: **PASS** — 6 frames; vibrant iridescent domain-warp pattern with magenta/cyan/lime/orange swirls. WebGL branch fired in snapshot run (Canvas 2D fallback ready if needed). Lifted from `launch-video/compositions/flex-shader.html`; Canvas 2D fallback upgraded from static gradient to animated so it's a good pattern to copy.
- scene-02: **PASS** — 6 frames; black startup → small lightning impact (amber ASCII glyphs scattered) → black gap → full "THE END" gold ASCII bitmap + "GO MAKE SOMETHING" subtext → final hold. Lifted from `launch-video/compositions/canvas-close.html` (525 lines). **Key fix during conversion:** original source used `tl.to(proxy, { onUpdate: render })` to drive canvas rendering, which does NOT fire under `tl.seek()`. Refactored to `gsap.ticker.add()` reading `tl.time()` each frame. This is the reliable pattern for canvas-render-by-time scenes under HyperFrames' seekable engine. Rebranded HYPERFRAMES → THE END (also bumped MAIN_SCALE 2→3 since the new string is shorter).
