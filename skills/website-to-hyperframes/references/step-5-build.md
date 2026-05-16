# Step 5: Build Compositions

**Captions rule — read before building anything:** Never create `compositions/captions.html` with an empty transcript (`const script = []`). If the VO/transcript step was skipped or failed, do not create a captions composition at all. An empty captions file silently does nothing and wastes a track slot. Only create it when `transcript.json` has real word timestamps.

**Captions stacking bug:** Every caption word group must start with `opacity: 0` (or `visibility: hidden`) and be positioned `position: absolute`. Never show more than one group at a time — GSAP controls visibility sequentially. If multiple groups are visible simultaneously it means either (a) the initial CSS state isn't hidden, or (b) a group's exit tween is missing before the next group's entrance fires. After building captions.html, take a snapshot at 3–4 timestamps mid-narration and verify only one word group is visible per frame.

**Before building, verify you have:**

- **STORYBOARD.md** — the beat-by-beat plan. Re-read it now if you don't remember every beat's concept, assets, and techniques.
- **DESIGN.md** — if you need to check a specific value (color, font, component style) you can't recall, look it up. Don't re-read the whole file.
- **`capture/extracted/asset-descriptions.md`** — when the storyboard assigns an asset to a beat, check the description to understand what it shows. Re-read this file if you can't recall the asset inventory.
- **transcript.json** — word-level timestamps that drive scene durations.

Load the `hyperframes` skill — it has the rules for data attributes, timeline contracts, deterministic rendering, and layout. Read it now if you haven't already this session.

**For capabilities.md and techniques.md:** read the Table of Contents to orient yourself, then go deep only on the sections your storyboard actually calls for. You don't need to re-read sections for animation engines, registry blocks, or techniques that none of your beats use.

---

## 1. Copy SFX to project

```bash
cp -r skills/website-to-hyperframes/assets/sfx/ <project-dir>/sfx/
# If skill is installed elsewhere:
find . -path "*/website-to-hyperframes/assets/sfx" -exec cp -r {} <project-dir>/sfx/ \;
```

## 2. Build the root index.html

Create `index.html` yourself. This is the orchestrator — it holds beat slots, narration audio, SFX, and shader transitions (if any).

**Critical CSS — every beat must overlap in the same frame:**

```css
.scene {
  position: absolute;
  top: 0;
  left: 0;
  width: 1920px;
  height: 1080px;
  overflow: hidden;
}
```

**Beat structure:**

```html
<div
  id="root"
  data-composition-id="main"
  data-start="0"
  data-duration="TOTAL"
  data-width="1920"
  data-height="1080"
>
  <div
    id="beat-1"
    class="scene"
    data-composition-id="beat-1-hook"
    data-composition-src="compositions/beat-1-hook.html"
    data-start="0"
    data-duration="5.5"
    data-track-index="1"
    data-width="1920"
    data-height="1080"
  ></div>

  <!-- more beats... -->

  <audio
    id="narration"
    src="narration.wav"
    data-start="0"
    data-duration="NARRATION_LENGTH"
    data-track-index="0"
    data-volume="1"
  ></audio>

  <!-- SFX on content moments, NOT on shader transitions -->
  <audio
    id="sfx-impact"
    src="sfx/impact-bass-1.mp3"
    data-start="0.3"
    data-duration="2.1"
    data-track-index="41"
    data-volume="0.35"
  ></audio>
</div>
```

SFX were assigned in the storyboard (Step 3) — implement exactly what STORYBOARD.md specifies. Each SFX entry has a file, trigger time, and volume. Wire each one as an `<audio>` element with the exact `data-start`, `data-duration`, and `data-volume` from the storyboard. Do not add, remove, or substitute SFX beyond what the storyboard says.

**Shader transitions**

If the storyboard specifies shader transitions, copy the local shader-transitions build into the project and reference it directly — the CDN version is behind the local build and doesn't support CSS crossfade mixing:

```bash
cp packages/shader-transitions/dist/index.global.js <project-dir>/hyper-shader-local.js
```

Then in `index.html` use the local file:

```html
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<script src="hyper-shader-local.js"></script>
```

Call `HyperShader.init()` as documented. Read [the shader transitions section in the main hyperframes skill](../../hyperframes/references/transitions.md) for the full API. Key rule: `scenes.length === transitions.length + 1`.

**Critical: beat host divs must have sequential `data-start` and matching `data-duration`.** Do NOT set `data-start="0"` and `data-duration="[total_video_length]"` on all beats. The render engine seeks each beat's sub-composition timeline to `global_time - beat.data_start`. If `data-start=0` on all beats, each beat's internal timeline is seeked to the GLOBAL time — at global t=10s, a beat whose GSAP timeline lasts 5.5s is seeked to t=10, past its end. The engine makes the sub-composition invisible once its timeline is exhausted. All beats go blank as soon as their individual GSAP timelines end.

Correct pattern — `data-start` at the transition point, `data-duration` equal to the beat's GSAP timeline length, all on the same `data-track-index`:

```html
<!-- Beat 2: HyperShader transition into it starts at t=4.0 -->
<!-- Beat 2's GSAP timeline spans 5.5s (BEAT=5.5 constant in the composition) -->
<div
  id="beat-2"
  class="scene"
  data-composition-id="beat-2-features"
  data-composition-src="compositions/beat-2-features.html"
  data-start="4.0"
  data-duration="5.5"
  data-track-index="1"
  data-width="1920"
  data-height="1080"
></div>
```

All beats should use `data-track-index="1"`. HyperShader manages which scene is visible via opacity — the track system just needs sequential non-conflicting time ranges.

**Font handling:** Common fonts are auto-resolved by the renderer: use `"Inter"` (not `"Inter Variable"` — the compiler only maps the base name), `"Roboto"`, `"JetBrains Mono"`, `"Poppins"`. If a composition uses `"Inter Variable"` it will log compiler warnings and may fall back incorrectly — always use `"Inter"`. Only brand-specific fonts (GT Walsheim, Aeonik, etc.) need `@font-face`. Check `capture/assets/fonts/` — hashed filenames are Google Fonts subsets that auto-resolve; recognizable filenames (e.g. `BrandSans-Bold.woff2`) are brand fonts that need `@font-face` declarations.

**Brand font @font-face:** If the storyboard's BRAND VALUES lists a brand-specific font with a path in `capture/assets/fonts/`, add the `@font-face` block at the top of each composition that uses it — sub-agents won't do this unless you tell them explicitly. Paste the exact `@font-face` declaration in the sub-agent prompt's BRAND VALUES section. Without this, every composition falls back to `system-ui` and the brand typeface never loads.

**⚠ ASSET PATHS — most common sub-agent mistake (5+ agents per run):** All asset paths in compositions must be relative to the **PROJECT ROOT**, not to the composition file. `compositions/beat-N.html` lives one directory deep, but paths must be written as if from the root.

- ✅ `capture/assets/hero.png`
- ❌ `../capture/assets/hero.png`

The Studio preview server rewrites base URLs to the project root — `../` paths that seem to work locally will 404 in preview and in renders. Add this verbatim to every sub-agent prompt's RULES section.

## 3. Build each composition — USE SUB-AGENTS

**Before dispatching, re-read DESIGN.md and STORYBOARD.md.** You wrote these files earlier in the session and you think you remember them. You don't — not the exact hex values, not the specific font families, not the button border-radius, not the Do's/Don'ts. Re-read them now so you can paste accurate brand rules and beat specs into each sub-agent prompt.

**If your runtime supports parallel sub-agents** (Claude Code, Cursor, most agent frameworks): dispatch one sub-agent per beat — 3 to 4× faster than building sequentially. For 3+ beats, always dispatch in parallel. For 1–2 beats, sequential is fine.

**If your runtime does not support parallel sub-agents** (some Codex setups, serial-only models): build sequentially using the same context-packing template below. The template gives each build pass the same context a sub-agent would get — paste prev/this/next beat + brand values — so output quality is the same, just slower.

In either case, use the template. Do not skip it and build from memory.

Each sub-agent gets the full context it needs to build independently. Paste the COMPLETE storyboard sections — don't summarize or extract pieces. **Also paste the brand values inline** — do not tell sub-agents to re-read DESIGN.md in full. You already have DESIGN.md in context; extract the relevant values and paste them directly. This cuts each sub-agent's startup time by 30-40%.

```
Build the composition for Beat N. Save to compositions/beat-N-name.html.

═══ PREVIOUS BEAT (Beat N-1) ═══
[paste the FULL previous beat section from STORYBOARD.md — concept, VO,
visual description, animation sequence, SFX, everything. The sub-agent
needs to see what was just on screen to build a matching entrance.]

═══ THIS BEAT (Beat N) ═══
[paste the FULL beat section from STORYBOARD.md — concept, VO, visual
description with all animation sequences/timings/CSS values, SFX cues,
techniques referenced. This IS the build spec.]

═══ NEXT BEAT (Beat N+1) ═══
[paste the FULL next beat section from STORYBOARD.md — so the sub-agent
knows what's coming and can build an exit that sets it up.]

═══ BRAND VALUES (from DESIGN.md — use these exactly) ═══
Colors:
  --bg:        #[hex]   primary background
  --fg:        #[hex]   primary text
  --accent:    #[hex]   CTA / highlights
  --surface:   #[hex]   card / panel backgrounds
  [add 2-3 more if used in this beat]

Fonts:
  Headlines: [font family], [weight]
  Body:      [font family], [weight]
  [brand-specific font path if needed: capture/assets/fonts/Brand.woff2]

Key component styles for this beat:
  [paste 3-5 relevant lines from DESIGN.md for components this beat uses,
   e.g. button radius, card shadow, heading letter-spacing]

Do NOT read DESIGN.md. The values above are everything you need.

═══ CAPTURED ASSETS FOR THIS BEAT ═══
[Paste the ACTUAL file paths from capture/extracted/asset-descriptions.md for
every asset assigned to this beat. Include the one-line description so the
sub-agent knows what each file shows. Format:

- capture/assets/hero-dashboard.png — full-bleed product dashboard screenshot, dark theme
- capture/assets/logo.svg — brand wordmark, white on transparent
- capture/assets/feature-card.jpg — feature comparison grid, 3 columns

DO NOT just say "see asset-descriptions.md". Paste the relevant entries here.
The sub-agent has ZERO context — if you don't paste the path, it will build
CSS recreations instead of using the real captured assets.

If you don't know which assets to assign yet, read capture/extracted/asset-descriptions.md
NOW (before dispatching) and decide. Then paste the relevant ones here.]

═══ IMPORTANT: YOU START WITH ZERO CONTEXT ═══
You have no knowledge of HyperFrames, GSAP, or this project. Before writing
ANY code, read these — targeted reads only, not full files:

1. Load the `hyperframes` skill — data attributes, timeline contracts,
   deterministic rendering rules (this is non-negotiable, read the whole skill)
2. capabilities.md — read the Table of Contents first (lines 1-40), then
   read ONLY the sections relevant to this beat's techniques:
   [paste the section names/line ranges from capabilities.md that apply,
    e.g. "Section 3: Canvas 2D (lines 89-134)" or "Section 7: Shader Transitions"]
3. techniques.md — read ONLY the techniques this beat uses:
   [paste the technique names/line ranges from techniques.md that apply,
    e.g. "Technique 4: Kinetic Typography (lines 156-210)"]
4. If this beat uses HTML-in-Canvas/WebGL: read html-in-canvas-patterns.md in full
5. If this beat uses screenshots: VIEW them before placing text on them

Brand values are in the BRAND VALUES section above — no need to read DESIGN.md.

═══ RULES ═══
- SCRIPT PLACEMENT: scripts MUST be inside the <template> element, not after </template>. The <template> content is inert until HyperFrames injects it — scripts outside see no DOM, every querySelector returns null, GSAP silently does nothing. This is the single most common cause of "all compositions completely static."
- STYLE PLACEMENT: CSS <style> blocks inside <template> elements are unreliable after injection. Use inline style="" attributes on elements, or set backgrounds/colors on the host divs in index.html instead.
- DATA-START: never set data-start="0" on all beat host divs. Each beat's GSAP timeline is seeked to global_time - data_start. With all data-start=0, a beat with a 5.5s GSAP timeline is seeked to t=10 at global t=10 — past its end, engine marks it invisible. Set each beat's data-start to its HyperShader transition point. data-duration = beat's GSAP timeline length. All beats on data-track-index="1".
- HYPERSHADER TIMELINE: never pass `timeline: tl` to HyperShader.init(). Let HyperShader create the timeline. Add all tweens to the returned tl AFTER init(). Passing an existing timeline breaks the scrubber and pre-warming.
- PROXY+ONUPDATE: never use `tl.fromTo(proxy, {}, {val, onUpdate: () => el.textContent = proxy.val})` for counter animations. The onUpdate callback doesn't fire when the render engine seeks directly to a time. Use discrete tl.set(el, {textContent: value}, timestamp) calls instead.
- SHADER NAMES: before writing any shader name in HyperShader.init(), run `ls registry/blocks/` to see what's installed. Don't guess shader names from memory.
- ASSET PATHS: always project-root-relative. capture/assets/file.png ✅  ../capture/assets/file.png ❌
- FONTS: if brand fonts are listed above with a capture/assets/fonts/ path, add @font-face at the top of your CSS. Without it everything falls back to system-ui.
- QUERYSELECTOR: never use document.querySelector("#host #child") — the host isn't in main DOM at script time. Use document.getElementById("child") with null guards. Never call .getTotalLength() or any DOM method without a null check first — one uncaught TypeError crashes the entire beat script before the timeline registers.
- If you want to place text over a screenshot: VIEW it first
- Use captured screenshots at full size, NOT CSS recreations unless you
  can recreate something almost pixel perfect
- Register timeline: window.__timelines["beat-N-name"] = tl
- No Math.random, no repeat:-1, no callbacks, no RAF
- Use tl.fromTo() not tl.from() for entrance animations
- No CSS transform for centering — use flexbox
- Never stack two transform tweens on same element
```

The storyboard beat already contains everything — the concept, the visual choreography with exact timings, the CSS values, the SFX cues. The sub-agent's job is to translate that description into working HTML/CSS/GSAP, not to re-invent the creative direction. If you want, you can also paste any other relative and useful context to subagents if think it's good, why not.

### Per-composition process

For each beat:

**1. Read the storyboard beat.** The storyboard IS the build spec. It tells you what elements exist, how they enter, what they do during the beat, and how they exit. Follow it. If something in the storyboard isn't clear or seems impossible, research how to do it or ask — don't silently skip it.

**2. Build the static end-state first.** Position every element at its most visible moment. HTML+CSS only, no GSAP yet. The CSS position is the ground truth.

**3. Add the animation sequence.** Follow the storyboard's choreography — it specifies what happens and when. Use `tl.fromTo()` (not `tl.from()`) for entrances. Build the timeline in the order the storyboard describes.

**4. Add exit** (if CSS transition out). If shader transition — no exit animation needed.

**5. View the result.** After building, take a snapshot of this beat at different timestamps (where things are supposed to happen, animate, move and etc) and look at it from all angles, corners and positinos. Is the frame full and everything is exactly where it supposed to be? Are you sure??? Are elements readable? Does it match what the storyboard describes?

### Technical rules

- **No `repeat: -1`** — calculate exact repeats from beat duration
- **No `Math.random()`** — use a seeded PRNG
- **No bare `gsap.to()`** — all tweens on `tl`, never standalone
- **No full-screen dark linear gradients** — H.264 banding
- **Minimum fonts**: 80px+ headlines, 20px+ body
- **WCAG contrast on gradient backgrounds:** The contrast validator samples actual background pixels under the text element — if the background is a gradient image, darker parts of the image make the measured ratio _worse_ when you darken the text color, not better. Fix: either place text over a solid-color zone, or add `data-layout-ignore` attribute to decorative labels that don't need WCAG compliance. Don't blindly darken text color when the background isn't solid.

## 4. After all compositions are built — reconciliation check

Before moving to Step 6, run this sanity check:

```bash
# List every file in compositions/ and verify each one has a host div in index.html
ls compositions/
```

For every `.html` file in `compositions/`, confirm that `index.html` has a `data-composition-src="compositions/<filename>"` pointing to it. If any composition file is not referenced in `index.html`, add the missing host div now — an unreferenced composition is completely invisible at runtime.

**Captions stub rule:** Never create a `compositions/captions.html` with an empty transcript (`const script = [];`). If the VO/transcript step was skipped or failed, do not create the captions composition at all. An empty captions file that returns immediately is worse than no captions file — it silently does nothing and wastes a track slot.

Once all compositions are built and all `compositions/` files are wired into `index.html`, move to Step 6 (Validate & Deliver) for lint, validate, snapshots, and visual review.
