#!/usr/bin/env node
// captions.mjs — build the captions sub-composition from STORYBOARD + audio_meta.
//
// One mode: `build`. Reads STORYBOARD.md (frame order + durations → cumulative
// frame starts) + audio_meta.json (voices[].words, frame-relative) → absolute-
// timed caption groups → writes:
//   compositions/captions.html  — a self-contained sub-composition the index
//        assembler mounts on its captions track (data-composition-id="captions").
//   caption_groups.json         — the computed groups (debug / inspection / --out).
//   caption-overrides.json      — an empty `[]` shim (silences the captions runtime's
//        validate-time fetch; only written when captions.html is).
// No narration / no words → legal skip: nothing written, assemble-index then omits
// the captions track (it keys off compositions/captions.html existence).
//
//   node captions.mjs build --storyboard ./STORYBOARD.md --audio-meta ./audio_meta.json --hyperframes . --out ./caption_groups.json
//
// CAPTION LOOK — two sources, picked automatically:
//   1. PRESET SKIN (preferred). If a project-local `caption-skin.html` exists (Step 2
//      copies the chosen frame-preset's skin into the project), it is the caption look.
//      It is a brand-token-strict skin with three reserved holes; this script fills them
//      and wraps the result in a <template> for the engine:
//        - `var GROUPS = [];`            → the computed caption groups
//        - `var DURATION = 0;` + data-duration="0" (and data-width/height="0") → real values
//        - `<style data-brand-tokens></style>` → :root tokens derived from the project's
//          frame.md (colors + fonts), mapped to a fixed semantic vocab every skin shares:
//          --cap-ink / --cap-canvas / --cap-accent / --cap-accent-2 / --font-display /
//          --font-body, plus --cap-band-top / --cap-band-height (the keep-out band).
//      So the brand-token overlay from Step 2 flows into the captions automatically.
//   2. DEFAULT (fallback). No skin file → the built-in Roboto/black pill (buildCaptionsHtml).
//
// Grouping mirrors the proven heuristics (frame boundary · sentence-end punct ·
// silence gap · density-aware word cap); word timings come inline from audio_meta.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { parseStoryboard } from "./lib/storyboard.mjs";
import { captionBand, parseFormat } from "./lib/dimensions.mjs";

const flag = (argv, name, def) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : def;
};
const r3 = (x) => Number(x.toFixed(3));

// ── grouping params ───────────────────────────────────────────────────────────
const SILENCE_GAP = 0.18; // s of silence between words → split
const TAIL_PAD = 0.12; // s the group lingers after its last word
const SENT_END = /[.?!,;:—]$/;
const DENSITY_WINDOW = 1.0; // s window for words/sec density
function wordCap(density) {
  return density > 3.5 ? 2 : density > 2.5 ? 3 : 4;
}

function runBuild(argv) {
  const skip = (reason) => {
    console.log(`captions: skipped (${reason})`);
    process.exit(0);
  };
  const die = (m) => {
    console.error(`✗ captions build: ${m}`);
    process.exit(1);
  };

  const hyperframesDir = resolve(flag(argv, "hyperframes", "."));
  const storyboardPath = resolve(flag(argv, "storyboard", join(hyperframesDir, "STORYBOARD.md")));
  const audioMetaPath = resolve(flag(argv, "audio-meta", join(hyperframesDir, "audio_meta.json")));
  const outPath = resolve(flag(argv, "out", join(hyperframesDir, "caption_groups.json")));
  const htmlPath = join(hyperframesDir, "compositions/captions.html");
  const overridesPath = join(hyperframesDir, "caption-overrides.json");
  const skinPath = resolve(flag(argv, "skin", join(hyperframesDir, "caption-skin.html")));
  const framePath = resolve(flag(argv, "frame", join(hyperframesDir, "frame.md")));

  if (!existsSync(storyboardPath)) die(`STORYBOARD.md not found at ${storyboardPath}`);
  const manifest = parseStoryboard(readFileSync(storyboardPath, "utf8"));
  const { width: W, height: H } = parseFormat(manifest.globals.format);

  if (!existsSync(audioMetaPath)) skip("no audio_meta.json (silent film)");
  const meta = JSON.parse(readFileSync(audioMetaPath, "utf8"));
  if (!Array.isArray(meta.voices) || meta.voices.length === 0) skip("no narration");

  // cumulative frame starts (by frame number) + total duration, from STORYBOARD.
  const startByFrame = new Map();
  let acc = 0;
  for (const f of manifest.frames) {
    if (f.number != null) startByFrame.set(f.number, acc);
    acc += Number.isFinite(f.durationSeconds) ? f.durationSeconds : 0;
  }
  const total = r3(acc);

  // absolute word stream: frame start + frame-relative word timing.
  const words = [];
  for (const v of meta.voices) {
    const base = startByFrame.get(v.frame);
    if (base == null || !Array.isArray(v.words)) continue;
    for (const w of v.words) {
      const text = String(w.text ?? "").trim();
      if (!text || /^[.?!,;:—–-]+$/.test(text)) continue; // drop empties + bare punctuation
      if (!isFinite(w.start) || !isFinite(w.end)) continue;
      words.push({ text, start: r3(base + w.start), end: r3(base + w.end), frame: v.frame });
    }
  }
  words.sort((a, b) => a.start - b.start);
  if (words.length === 0) skip("no usable words");

  // density at i = words whose start falls within [w.start, w.start + WINDOW).
  const densityAt = (i) => {
    const t0 = words[i].start;
    let n = 0;
    for (let j = i; j < words.length && words[j].start < t0 + DENSITY_WINDOW; j++) n++;
    return n / DENSITY_WINDOW;
  };

  // group: split on frame change / silence gap / word cap; always flush after a
  // sentence-ending word.
  const groups = [];
  let cur = null;
  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    const prev = cur && cur.words[cur.words.length - 1];
    const crossFrame = cur && w.frame !== cur.frame;
    const gap = prev && w.start - prev.end > SILENCE_GAP;
    const full = cur && cur.words.length >= cur.cap;
    if (!cur || crossFrame || gap || full) {
      if (cur) groups.push(cur);
      cur = { frame: w.frame, cap: wordCap(densityAt(i)), words: [] };
    }
    cur.words.push(w);
    if (SENT_END.test(w.text)) {
      groups.push(cur);
      cur = null;
    }
  }
  if (cur) groups.push(cur);

  // finalize: ids, start/end (tail-padded, clamped < next group's start), text.
  const finalized = groups.map((g, gi) => {
    const first = g.words[0];
    const last = g.words[g.words.length - 1];
    const next = groups[gi + 1];
    let end = r3(last.end + TAIL_PAD);
    if (next && next.words[0].start < end) end = r3(next.words[0].start);
    return {
      id: `caption-group-${gi}`,
      frame: g.frame,
      start: r3(first.start),
      end,
      text: g.words.map((w) => w.text).join(" "),
      words: g.words.map((w, wi) => ({
        id: `caption-word-${gi}-${wi}`,
        text: w.text,
        start: r3(w.start),
        end: r3(w.end),
      })),
    };
  });

  // ── write caption_groups.json ──
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(
    outPath,
    JSON.stringify({ total_duration_s: total, width: W, height: H, groups: finalized }, null, 2),
  );

  // ── write compositions/captions.html (preset skin if present, else default) ──
  mkdirSync(dirname(htmlPath), { recursive: true });
  let source;
  if (existsSync(skinPath)) {
    const tokens = frameTokensCss(framePath, H);
    writeFileSync(htmlPath, buildFromSkin(readFileSync(skinPath, "utf8"), finalized, total, W, H, tokens, die));
    source = `preset skin (${skinPath.replace(hyperframesDir + "/", "")})`;
  } else {
    writeFileSync(htmlPath, buildCaptionsHtml(finalized, total, W, H));
    source = "default (built-in pill)";
  }

  // ── write caption-overrides.json shim ──
  if (!existsSync(overridesPath)) writeFileSync(overridesPath, "[]\n");

  console.log(
    `✓ captions build: ${finalized.length} group(s) from ${words.length} words → compositions/captions.html (total ${total}s) · skin: ${source}`,
  );
}

// ── preset-skin path ────────────────────────────────────────────────────────
// Fill the skin's three reserved holes + the root's 0-placeholders, then wrap the
// fragment in a <template> (the engine clones template contents only). One generic
// fill works for every preset's skin — no per-skin transform.
function buildFromSkin(skin, groups, total, W, H, tokens, die) {
  const fillOnce = (src, re, repl, label) => {
    const n = (src.match(re) || []).length;
    if (n !== 1) die(`caption-skin.html: expected exactly one ${label}, found ${n}`);
    return src.replace(re, () => repl);
  };
  let out = skin;
  out = fillOnce(out, /<style data-brand-tokens>\s*<\/style>/, `<style data-brand-tokens>\n${tokens}\n    </style>`, "<style data-brand-tokens></style> hole");
  out = fillOnce(out, /var GROUPS = \[\];/, `var GROUPS = ${JSON.stringify(groups)};`, "`var GROUPS = [];` hole");
  out = fillOnce(out, /var DURATION = 0;/, `var DURATION = ${total};`, "`var DURATION = 0;` hole");
  out = fillOnce(out, /data-duration="0"/, `data-duration="${total}"`, '`data-duration="0"` hole');
  out = fillOnce(out, /data-width="0"/, `data-width="${W}"`, '`data-width="0"` hole');
  out = fillOnce(out, /data-height="0"/, `data-height="${H}"`, '`data-height="0"` hole');
  return `<template id="captions-template">\n${out.trim()}\n</template>\n`;
}

// frame.md colors:/typography: → a :root token block, mapped to the fixed semantic
// vocab every preset skin references. Robust to per-preset key names: colors are
// matched by name, then by luminance. Brand-token overlay (Step 2) flows through
// because the values come from the project's frame.md. No frame.md → band vars only.
function frameTokensCss(framePath, H) {
  const band = captionBand(H);
  const out = [];
  if (existsSync(framePath)) {
    const md = readFileSync(framePath, "utf8");
    const colors = parseColors(md);
    for (const [k, v] of colors) out.push(`      --${k}: ${v};`); // raw, for completeness
    const sem = semanticColors(colors);
    if (sem.ink) out.push(`      --cap-ink: ${sem.ink};`);
    if (sem.canvas) out.push(`      --cap-canvas: ${sem.canvas};`);
    if (sem.accent) out.push(`      --cap-accent: ${sem.accent};`);
    if (sem.accent2) out.push(`      --cap-accent-2: ${sem.accent2};`);
    const { display, body } = parseFonts(md);
    if (display) out.push(`      --font-display: ${display}, system-ui, serif;`);
    if (body) out.push(`      --font-body: ${body}, system-ui, sans-serif;`);
  }
  out.push(`      --cap-band-top: ${band.bandTopY}px;`);
  out.push(`      --cap-band-height: ${band.bandHeight}px;`);
  return `      :root {\n${out.join("\n")}\n      }`;
}

// Collect `key: value` pairs under the top-level `colors:` block (until dedent).
function parseColors(md) {
  const out = [];
  let inBlock = false;
  for (const line of md.split(/\r?\n/)) {
    if (/^colors:\s*$/.test(line)) {
      inBlock = true;
      continue;
    }
    if (!inBlock) continue;
    if (/^\S/.test(line)) break; // dedent to a top-level key → end of block
    const m = line.match(/^\s+([\w-]+):\s*["']?(#[0-9a-fA-F]{3,8}|rgba?\([^)]*\)|[^"'#\s][^"'\n]*?)["']?\s*$/);
    if (m) out.push([m[1], m[2].trim()]);
  }
  return out;
}

// relative luminance of a #rrggbb (null for non-hex like rgba()).
function lum(v) {
  const m = /^#?([0-9a-fA-F]{6})$/.exec(String(v).trim());
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
}

// Map a preset's colors to the fixed semantic vocab. ink = a dark/ink-named color
// (else darkest); canvas = a paper/cream/white-named color (else lightest); accents
// = whatever's left, in declaration order.
function semanticColors(colors) {
  if (!colors.length) return {};
  const named = (re) => colors.find(([k]) => re.test(k));
  const hexes = colors.filter(([, v]) => lum(v) != null);
  const byLum = [...hexes].sort((a, b) => (lum(a[1]) ?? 1e9) - (lum(b[1]) ?? 1e9));
  const pick = (m, fallback) => (m ? m[1] : fallback ? fallback[1] : undefined);
  const ink = pick(named(/ink|black|charcoal|^text$|outline|noir/i), byLum[0] ?? colors[0]);
  const canvas = pick(
    named(/cream|paper|canvas|white|bg|ground|surface|base|sand|parchment|off-?white|bone/i),
    byLum[byLum.length - 1] ?? colors[colors.length - 1],
  );
  const accents = colors.map(([, v]) => v).filter((v) => v !== ink && v !== canvas);
  return { ink, canvas, accent: accents[0] ?? ink, accent2: accents[1] ?? accents[0] ?? ink };
}

// Collect role→fontFamily under the top-level `typography:` block; pick a display
// + body family from the usual role names.
function parseFonts(md) {
  const roles = {};
  let inBlock = false;
  for (const line of md.split(/\r?\n/)) {
    if (/^typography:\s*$/.test(line)) {
      inBlock = true;
      continue;
    }
    if (!inBlock) continue;
    if (/^\S/.test(line)) break;
    const m = line.match(/^\s+([\w-]+):\s*\{[^}]*fontFamily:\s*"([^"]+)"/);
    if (m) roles[m[1]] = m[2];
  }
  const q = (s) => (s ? `"${s}"` : null);
  const body = roles.body ?? roles.subtitle ?? Object.values(roles)[0];
  const display =
    roles.display ??
    roles.headline ??
    roles["card-headline"] ??
    roles["section-headline"] ??
    roles["quote-display"] ??
    body;
  return { display: q(display), body: q(body) };
}

// ── default path (no preset skin) ─────────────────────────────────────────────
// Self-contained captions sub-composition. The <template> holds the band container
// + style AND the <script> (the HyperFrames loader only executes scripts INSIDE the
// cloned template — a sibling <script> after </template> never runs, so the timeline
// never registers and captions render blank). The script builds per-word spans and a
// paused, seek-safe GSAP timeline (opacity for group show/hide, a quick color tween
// per word for the karaoke highlight — no className flips, no JS state) and ends each
// group with a hard tl.set kill so an exit can't get stuck. gsap is loaded via CDN
// inside the template (matching the frame compositions). Band = captionBand(H).
function buildCaptionsHtml(groups, total, W, H) {
  const band = captionBand(H);
  const fs = Math.round(H * 0.038);
  const pad = Math.round(fs * 0.4);
  return `<template id="captions-template">
  <div
    data-composition-id="captions"
    data-width="${W}"
    data-height="${H}"
    data-duration="${total}"
    id="captions-root"
  >
    <div id="cap"></div>
  </div>
  <style>
    #captions-root {
      position: absolute;
      inset: 0;
      pointer-events: none;
    }
#cap {
      position: absolute;
      left: 0;
      right: 0;
      top: ${band.bandTopY}px;
      height: ${band.bandHeight}px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
.caption-group {
      position: absolute;
      max-width: 80%;
      padding: ${pad}px ${Math.round(pad * 1.8)}px;
      background: rgba(0, 0, 0, 0.72);
      border-radius: ${Math.round(fs * 0.3)}px;
      font-family: Roboto, sans-serif;
      font-weight: 700;
      font-size: ${fs}px;
      line-height: 1.25;
      text-align: center;
      color: #fff;
      opacity: 0;
    }
.caption-word {
      color: rgba(255, 255, 255, 0.55);
    }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
    (function () {
      var GROUPS = ${JSON.stringify(groups)};
      var cap = document.getElementById("cap");
      var tl = gsap.timeline({ paused: true });
      GROUPS.forEach(function (g) {
        var el = document.createElement("div");
        el.className = "caption-group";
        g.words.forEach(function (w) {
          var s = document.createElement("span");
          s.className = "caption-word";
          s.textContent = w.text + " ";
          el.appendChild(s);
        });
        cap.appendChild(el);
        tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.18, overwrite: "auto" }, g.start);
        tl.to(el, { opacity: 0, duration: 0.12, overwrite: "auto" }, g.end);
        tl.set(el, { opacity: 0, visibility: "hidden" }, g.end + 0.12); // deterministic hard kill
        g.words.forEach(function (w, i) {
          tl.to(el.children[i], { color: "#ffffff", duration: 0.06 }, w.start);
        });
      });
      tl.to({}, { duration: ${total} }, 0); // full-span anchor
      window.__timelines = window.__timelines || {};
      window.__timelines["captions"] = tl;
    })();
  </script>
</template>
`;
}

const sub = process.argv[2];
if (sub === "build" || sub === undefined) runBuild(process.argv.slice(sub === "build" ? 3 : 2));
else {
  console.error("usage: node captions.mjs build [--storyboard …] [--audio-meta …] [--hyperframes .]");
  process.exit(2);
}
