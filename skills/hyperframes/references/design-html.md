# Reading DESIGN.html

DESIGN.html is a self-contained design system document exported from the design picker. It is both human-viewable (opens in a browser as a styled page) and agent-parseable (all data is in the visible HTML source). There are no hidden data layers — everything the agent needs is rendered content.

## Structure

The file has 7 content sections, each with a stable `id`:

| Section    | ID            | What it contains                                       |
| ---------- | ------------- | ------------------------------------------------------ |
| Palette    | `#palette`    | 4 color swatches with hex values and role names        |
| Typography | `#type`       | Font specimens with family names and weights           |
| Surface    | `#surface`    | Corner radius, padding, gap, elevation, density values |
| Motion     | `#motion`     | Easing function name/value, duration defaults          |
| Background | `#background` | Shader preset config, GLSL source, live preview        |
| Guidelines | `#guidelines` | Do/don't rules as `<li>` items                         |
| Templates  | `#templates`  | Slide type gallery with HTML skeletons                 |

## Extracting the palette

The `:root` block in `<style id="ds-tokens">` defines the 4-role palette:

```css
:root {
  --primary: #f0ece5; /* text on dark surfaces */
  --secondary: #111111; /* canvas / background */
  --tertiary: #282826; /* muted / borders */
  --accent: #e85d26; /* signal — reserved for one focal element per frame */
}
```

Use these exact hex values. The palette section also shows human-readable names and usage descriptions in the swatch cards.

**Mapping to template CSS:** Template slide CSS uses `--tp-primary`, `--tp-secondary`, `--tp-tertiary`, `--tp-accent` which resolve to the same values. When writing compositions, set these in your `:root`.

## Extracting typography

The type specimen section shows the font families and weights. Extract from the `<link>` tag in `<head>`:

```html
<link
  href="https://fonts.googleapis.com/css2?family=Barlow:wght@400;700;800;900&family=IBM+Plex+Mono:wght@300;500&display=swap"
/>
```

The specimen rows show each scale level (Display, H1, H2, Lead, Body, Label) with the font family, weight, and size.

## Extracting surface tokens

The surface section has a token list with values for:

- **Corners** — border-radius value (e.g., `4px`, `0px`, `12px`)
- **Padding** — content padding
- **Gap** — spacing between elements
- **Elevation** — shadow treatment (`Flat`, `Subtle`, `Layered`)
- **Density** — content density level and description

## Extracting motion

The motion section has two panels:

1. **Easing** — name, description, and the easing value (GSAP string or cubic-bezier)
2. **Duration** — default durations for slides and element entrances

Use the easing value directly in GSAP timelines: `gsap.to(el, { ease: "power3.out" })`.

## Extracting the shader background

The background section contains everything needed to reproduce the animated shader:

1. **Config JSON** — in a `<details>` block, contains geometry type, density, speed, strength, colors, camera position, rotation, grain settings
2. **Vertex shader GLSL** — in `<pre id="vtx-src">`
3. **Fragment shader GLSL** — in `<pre id="frg-src">`

### Static usage (non-HyperFrames)

1. Copy the `<canvas id="design-bg">` element
2. Copy the `<script type="module">` at the bottom of the file (the shader renderer)
3. The renderer reads colors from CSS variables `--secondary`, `--accent`, `--tertiary` — set those in your composition's `:root`

The shader renders behind all content at `z-index:-2`. The `#bg-veil` div provides a gradient fade at `z-index:-1`.

### HyperFrames adaptation (required for rendered video)

The DESIGN.html shader uses `requestAnimationFrame` and ES module imports. Both break the HyperFrames capture engine — rAF runs on wallclock time (not seekable), and ES module import may not resolve in the headless capture context. Port the shader using this pattern:

**1. Replace ES module imports with UMD script tags:**

```html
<script src="https://cdn.jsdelivr.net/npm/three@0.167.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.167.0/examples/js/postprocessing/EffectComposer.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.167.0/examples/js/postprocessing/RenderPass.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.167.0/examples/js/postprocessing/ShaderPass.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.167.0/examples/js/postprocessing/HalftonePass.js"></script>
```

Load these BEFORE GSAP and BEFORE your composition script.

**2. Place the canvas inside the composition container, not on body:**

```html
<div
  id="root"
  data-composition-id="main"
  data-width="1920"
  data-height="1080"
  data-start="0"
  data-duration="30"
>
  <canvas
    id="shader-bg"
    style="position:absolute;inset:0;width:1920px;height:1080px;z-index:0;pointer-events:none;"
  ></canvas>
  <div
    id="bg-veil"
    style="position:absolute;inset:0;z-index:1;pointer-events:none;background:radial-gradient(ellipse at 40% 30%,transparent 0%,var(--secondary) 70%);"
  ></div>
  <!-- scenes at z-index:2+ -->
</div>
```

**3. Drive the time uniform from the GSAP timeline, not rAF:**

```javascript
// --- Shader setup (runs once at page load, outside timeline) ---
var canvas = document.getElementById("shader-bg");
var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
renderer.setSize(1920, 1080);

var scene3d = new THREE.Scene();
var cam = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 100);
// Copy camera position from DESIGN.html config JSON
cam.position.set(0.718, 1.505, -4.072);
cam.lookAt(0, 0, 0);

scene3d.add(new THREE.AmbientLight(0xffffff, 0.6));
var dl = new THREE.DirectionalLight(0xffffff, 0.8);
dl.position.set(5, 5, 5);
scene3d.add(dl);

// Copy uniforms from DESIGN.html — colors, speed, density, strength, rendering
var uniforms = {
  uTime: { value: 0 },
  uSpeed: { value: 0.2 }, // from config JSON
  uDensity: { value: 1.2 },
  uStrength: { value: 3.4 },
  uColor1: { value: new THREE.Color("#111111") }, // --secondary
  uColor2: { value: new THREE.Color("#E15A2E") }, // --accent
  uColor3: { value: new THREE.Color("#112D54") }, // --tertiary
  uBrightness: { value: 2 },
  uContrast: { value: 1.45 },
  uSaturation: { value: 0.45 },
};

// Copy vertex + fragment shader source from <pre id="vtx-src"> and <pre id="frg-src">
var mat = new THREE.ShaderMaterial({
  vertexShader: VTX_SOURCE, // string from DESIGN.html
  fragmentShader: FRG_SOURCE, // string from DESIGN.html
  uniforms: uniforms,
  side: THREE.DoubleSide,
});

// Copy geometry type + transforms from config JSON
var mesh = new THREE.Mesh(new THREE.PlaneGeometry(10, 10, 128, 128), mat);
mesh.rotation.set(0.785, 0, 0); // from config rotation
mesh.position.set(0, 0.9, -0.3); // from config position
scene3d.add(mesh);

// Copy post-processing from config JSON (grain section)
var composer = new THREE.EffectComposer(renderer);
composer.addPass(new THREE.RenderPass(scene3d, cam));
composer.addPass(
  new THREE.HalftonePass(1920, 1080, {
    shape: 1,
    radius: 4.5,
    scatter: 1,
    blending: 0.35,
    blendingMode: 1,
    greyscale: false,
    rotateR: Math.PI / 12,
    rotateG: Math.PI / 6,
    rotateB: Math.PI / 4,
  }),
);

// --- Timeline-driven render (seekable, deterministic) ---
var shaderProxy = { time: 0 };
tl.to(
  shaderProxy,
  {
    time: 30, // match composition duration
    duration: 30,
    ease: "none",
    onUpdate: function () {
      uniforms.uTime.value = shaderProxy.time;
      composer.render();
    },
  },
  0,
);
```

**Key rules:**

- Never use `requestAnimationFrame` for the render loop. The capture engine seeks the timeline to arbitrary positions — rAF runs on wallclock and produces frozen or wrong frames.
- Initialize the renderer, scene, and composer OUTSIDE the timeline — synchronously at page load. Only the `uTime` update and `composer.render()` call go inside `onUpdate`.
- Match `shaderProxy.time` duration to `data-duration` on the root composition element.
- Copy ALL config values from the DESIGN.html — camera position, mesh rotation/position, uniform values, grain settings. Don't approximate.
- The canvas must be inside the composition container (`data-composition-id` div), not on `<body>`. The capture engine only captures elements within the composition bounds.
- UMD builds use `THREE.*` globals — `THREE.EffectComposer`, `THREE.RenderPass`, `THREE.HalftonePass`. The ES module versions use named imports from subpaths. If a post-processing pass is missing from the UMD examples directory, check Three.js docs for the correct path.

### What to extract from each DESIGN.html section

| Source in DESIGN.html                            | What to copy                     | Where it goes in composition                       |
| ------------------------------------------------ | -------------------------------- | -------------------------------------------------- |
| Config JSON `"colors"` array                     | 3 hex values                     | `uColor1`, `uColor2`, `uColor3` uniforms           |
| Config JSON `"density"`, `"speed"`, `"strength"` | Float values                     | `uDensity`, `uSpeed`, `uStrength` uniforms         |
| Config JSON `"camera"`                           | distance, azimuth, polar, zoom   | `cam.position.set(...)`, `cam.zoom`                |
| Config JSON `"position"`, `"rotation"`           | Array values                     | `mesh.position.set(...)`, `mesh.rotation.set(...)` |
| Config JSON `"rendering"`                        | brightness, contrast, saturation | `uBrightness`, `uContrast`, `uSaturation` uniforms |
| Config JSON `"grain"`                            | radius, scatter, blending        | `HalftonePass` options                             |
| `<pre id="vtx-src">`                             | Full GLSL string                 | `vertexShader` in ShaderMaterial                   |
| `<pre id="frg-src">`                             | Full GLSL string                 | `fragmentShader` in ShaderMaterial                 |

## Extracting guidelines

The guidelines section has two `<ul>` lists:

- **Do** — rules to follow (accent usage, corner consistency, font weights, etc.)
- **Don't** — constraints (no second accent color, no body text under 24px, etc.)

These are hard constraints. Violating them breaks the design system's coherence.

## Extracting slide skeletons

The templates section contains a `<template id="tmpl-source">` element with the slide gallery. Each slide type is wrapped in a `.tmpl` card:

```html
<div class="tmpl">
  <div class="tmpl-thumb">
    <div class="scale-wrap">
      <div class="ds-slide-frame">
        <section class="slide slide--cover orange">
          <!-- slide skeleton HTML -->
        </section>
      </div>
    </div>
  </div>
  <div class="tmpl-foot">
    <span class="name">slide--cover</span><span class="idx">01 / 16</span>
  </div>
</div>
```

The skeleton HTML inside `.ds-slide-frame` shows the layout structure with content placeholders:

- `{{headline}}` — primary heading text
- `{{body}}` — paragraph/description text
- `{{label}}` — small chrome text (kickers, captions, metadata)
- `{{number}}` — numeric values (stats, dates, counts)
- `{{text}}` — generic short text

**How to use skeletons:** Each skeleton is a slide type you can instantiate in your composition. Replace the `{{placeholder}}` tokens with real content. Keep the class names and DOM structure — they're styled by the template CSS in `<style id="template-css">`.

The template CSS is scoped under `.ds-slide-frame` in the design document. When using skeletons in a composition, strip the `.ds-slide-frame` prefix from selectors or wrap your slides in a `.ds-slide-frame` container.

## Slide theme classes

Slides use theme classes for background/text color:

- `.dark` — dark background (`--secondary`), light text (`--primary`)
- `.light` — light background (`--primary`), dark text (`--secondary`)
- `.orange` — accent background (`--accent`), dark text

Apply the appropriate class to each `<section class="slide ...">` element.

## Composition workflow

1. Read DESIGN.html
2. **Extract template CSS separately from page chrome** — read the Design HTML Template Extraction section below for the full extraction process. The page has TWO design systems: the showcase chrome and the slide templates. Build from the templates, not the chrome.
3. Set `:root` with palette values from `<style id="ds-tokens">`
4. Load the fonts from the **template CSS** (not the page `<link>` tags — they may differ)
5. Pick slide types from the template gallery for your composition's scenes
6. Replace `{{placeholder}}` tokens with real content
7. Apply the easing from the motion section to your GSAP timeline
8. If a `#background` shader section exists, port it into the composition using the GSAP-proxy pattern described in "Extracting the shader background > HyperFrames adaptation" above. Place the canvas at `z-index:0` inside the composition container, scenes above it. Do NOT skip this — the shader is a core visual element of the design system, not optional decoration.
9. Follow the guidelines section constraints throughout

---

## Design HTML Template Extraction

A design.html with embedded templates contains TWO separate design systems. Mix them up and the output looks nothing like the reference. This guide prevents that.

### The Two Systems

Every design.html with a template gallery has:

| Layer               | What it is                                                                       | Where it lives                                                                             | Fonts                                                 | Use for                                           |
| ------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------- | ------------------------------------------------- |
| **Page chrome**     | The design system document itself — headers, swatches, specimen rows, rules grid | `<style id="ds-tokens">`, `:root` block, main `<style>`                                    | Loaded in `<link>` tags                               | Reading palette values, understanding constraints |
| **Slide templates** | The actual video/slide frames — the things the user SEES and wants reproduced    | `<style id="template-css">` or similar scoped block, `<template>` elements or gallery HTML | Referenced in template CSS (often NOT loaded — check) | Building the composition                          |

**The templates are the product. The page chrome is the packaging.** Build from the templates.

### Extraction Order

#### 1. Find the template CSS

Look for a scoped style block — `<style id="template-css">`, a class-scoped namespace like `.ds-slide-frame`, or similar. This is the CSS that styles the actual slides, not the document page.

#### 2. Resolve the color chain

Template CSS often uses `var()` references back to `:root` tokens:

```
:root → --primary:#1C2B33
template → --tp-primary: var(--primary)
template → --black: var(--tp-primary)
```

Trace every variable to its resolved hex. Check for override blocks like `.slide.dark { background: #F7B928 !important }` — these remap what "dark" and "light" mean in this specific system. The names often lie after remapping.

#### 3. Identify the template font stack

Template CSS declares its own `font-family` values per element. These are often DIFFERENT from the page's `<link>` loaded fonts:

```css
/* Page loads: "Big Shoulders Stencil Display" */
/* Template CSS uses: "Stardos Stencil", "Barlow Condensed" */
```

Use the fonts from the template CSS. If they're Google Fonts, the HyperFrames compiler auto-embeds them. If they're not loaded in the HTML and not on Google Fonts, warn and fall back.

#### 4. Catalog available templates

List every slide type with its class name, layout pattern, and content slots:

```
s-cover   — hero headline, super label, lockup row, decorative shape
s-agenda  — 4-item grid with SVG shapes, numbered items
s-princ   — 4 colored cards (c1-c4) with number, title, description
s-sec     — big section number, label, h2 heading (dark variant)
s-stats   — 3 stat blocks with big numbers (dark variant)
s-quote   — large quote panel with attribution
s-cta     — two-pane layout (left headline, right steps)
```

#### 5. Map scenes to templates

For each scene in the composition, pick the template type that best fits the content. Adapt content into the template's HTML structure — don't invent new structures.

```
Scene 1 (brand intro)     → s-cover
Scene 2 (section break)   → s-sec
Scene 3 (product pillars) → s-princ
Scene 4 (impact stats)    → s-stats
Scene 5 (CTA)             → s-cta
```

#### 6. Build scenes using template HTML

Wrap each template slide in the scene management structure:

```html
<div id="scene1" class="scene">
  <div class="ds-slide-frame">
    <section class="slide s-cover">
      <!-- exact template HTML structure, content swapped -->
    </section>
  </div>
</div>
```

Keep class names, element hierarchy, and nesting exactly as they appear in the template. Swap only text content and color-class assignments (like c1/c2/c3/c4).

#### 7. Include template CSS in composition

Copy the full template CSS block into the composition's `<style>`. Include the `:root` tokens it depends on. Don't cherry-pick — missing a selector breaks a layout.

### What Goes Wrong Without This

| Mistake                                           | Symptom                                                                              |
| ------------------------------------------------- | ------------------------------------------------------------------------------------ |
| Extract only tokens, rebuild layouts from scratch | Output looks generic, nothing like the templates                                     |
| Use page chrome fonts instead of template fonts   | Wrong typeface in every headline                                                     |
| Miss `.slide.dark` overrides                      | "Dark" scenes use wrong background color                                             |
| Invent card/panel structures                      | Rounded corners where templates use sharp (or vice versa)                            |
| Skip template CSS, write own                      | Element spacing, font sizes, layout grids all wrong                                  |
| Use 3 cards when template has 4                   | Breaks the grid, gaps look wrong                                                     |
| Skip the shader background                        | Flat solid backgrounds instead of the animated depth layer the design system defines |

### Integration with HyperFrames Skill

This guide runs during Step 1 (Design system) of the hyperframes workflow. When a DESIGN.html with templates is detected:

1. Replace the "read design.md" path with template extraction (this guide)
2. Check for a `#background` shader section — if present, extract and port it using the GSAP-proxy pattern
3. Continue to Step 2 (prompt expansion) — but scene beats must map to specific template types
4. Continue to Step 3 (build) — each scene uses template HTML structures, the template CSS, and the ported shader background
