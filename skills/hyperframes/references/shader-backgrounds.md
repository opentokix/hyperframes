# Shader Backgrounds

WebGL fragment shaders as living, breathing scene backgrounds. Each composition can have a contextual shader that renders behind the content.

## Noise Library

Include this in every shader. It provides gradient noise (no grid artifacts), FBM, and domain warping.

```glsl
precision highp float;
uniform float u_time;
uniform vec2 u_res;

vec2 h2(vec2 p) {
  p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
  return -1.0 + 2.0 * fract(sin(p) * 43758.5453);
}

float gn(vec2 p) {
  vec2 i = floor(p), f = fract(p);
  vec2 u = f*f*f*(f*(f*6.0-15.0)+10.0); // quintic smoothstep
  return mix(
    mix(dot(h2(i), f), dot(h2(i+vec2(1,0)), f-vec2(1,0)), u.x),
    mix(dot(h2(i+vec2(0,1)), f-vec2(0,1)), dot(h2(i+vec2(1,1)), f-vec2(1,1)), u.x),
    u.y
  );
}

// FBM with rotated octaves — prevents directional banding
float fbm(vec2 p) {
  float v = 0.0, a = 0.5;
  mat2 r = mat2(0.8, 0.6, -0.6, 0.8);
  for (int i = 0; i < 6; i++) { v += a * gn(p); p = r * p * 2.0 + vec2(1.7, 9.2); a *= 0.5; }
  return v;
}

// Lighter FBM for secondary detail
float fbm4(vec2 p) {
  float v = 0.0, a = 0.5;
  mat2 r = mat2(0.8, 0.6, -0.6, 0.8);
  for (int i = 0; i < 4; i++) { v += a * gn(p); p = r * p * 2.0 + vec2(1.7, 9.2); a *= 0.5; }
  return v;
}
```

## Domain Warping

The single most important technique for natural-looking shaders. Feed noise into noise:

```glsl
// Single warp — organic but recognizable as noise
vec2 q = vec2(fbm(uv * 2.0 + vec2(t * 0.3, t * 0.1)),
              fbm(uv * 2.0 + vec2(t * 0.1, t * 0.4) + 5.0));
float f = fbm(uv * 1.5 + q * 1.5);

// Double warp — painterly, flowing, no visible noise pattern
vec2 q = vec2(fbm(uv * 2.0 + vec2(t * 0.3, t * 0.1)),
              fbm(uv * 2.0 + vec2(t * 0.1, t * 0.4) + 5.0));
vec2 r = vec2(fbm(uv * 3.0 + q * 3.0 + vec2(1.7, t * 0.15)),
              fbm(uv * 3.0 + q * 3.0 + vec2(8.3, t * 0.2)));
float f = fbm(uv * 2.0 + r * 1.5);

// Triple warp — truly organic, like real fluid dynamics
vec2 q = ...; // as above
vec2 r = ...; // as above
vec2 s = vec2(fbm(uv * 1.0 + r * 2.0 + vec2(3.1, t * 0.05)),
              fbm(uv * 1.0 + r * 2.0 + vec2(6.7, t * 0.03)));
float f = fbm(uv * 1.5 + s * 1.5);
```

## Shader Patterns by Context

### Warm / Travel / Lifestyle

**Gradient Mesh** — flowing color blobs:

```glsl
// 5 blobs with gaussian falloff, noise-warped edges
vec2 c1 = vec2(0.3 + sin(t*0.7)*0.15, 0.7 + cos(t*0.5)*0.12);
float w1 = exp(-pow(length(uv - c1 + warp) * 2.5, 2.0));
// ... repeat for each blob, weighted blend of colors
col = (color1*w1 + color2*w2 + ...) / (w1+w2+...+0.001);
```

**Warm Caustics** — golden light on cream:

```glsl
// Double domain warp, then map to warm palette
float c = smoothstep(0.2, 0.8, f * 0.5 + 0.5);
vec3 col = mix(cream, gold, pow(c, 2.0) * 0.3);
```

**Sunset Horizon** — sky gradient + clouds + water reflection. Use 5+ color stops for the sky, FBM clouds with bottom-lit coloring, water below with noise-broken sun reflection.

### Medical / Emergency / PSA

**Biohazard Pulse** — expanding rings from center:

```glsl
for (int i = 0; i < 3; i++) {
  float phase = fract(t * 0.3 + float(i) * 0.33);
  float ring = abs(dist - phase * 0.7) * 30.0;
  col += dangerColor * exp(-ring*ring) * (1.0 - phase) * 0.4;
}
```

**Clinical Sterile** — bright white + scan line + faint grid:

```glsl
float scanY = fract(t * 0.04);
float scan = exp(-abs(uv.y - scanY) * 100.0) * 0.08;
float grid = max(
  smoothstep(0.49, 0.5, fract(uv.x * 60.0)),
  smoothstep(0.49, 0.5, fract(uv.y * 35.0))
);
```

**Microscopic** — floating particles with membrane rings:

```glsl
float cell = exp(-pd*pd/(size*size)) * 0.2;
float membrane = exp(-pow(abs(pd-size)*40.0, 2.0)) * 0.15;
```

**Respiratory** — breathing cycle with UV warp:

```glsl
float breath = sin(t * 0.8) * 0.5 + 0.5;
vec2 dir = uv - center;
vec2 warped = center + dir * (1.0 + breath * 0.04 * exp(-length(dir) * 2.0));
```

### Tech / Data / Product

**Data Grid** — subtle flowing grid with accent-colored intersections. Use `fract()` for grid lines, noise for line brightness variation.

**Terminal Glow** — dark base with green/blue accent scan. Monospace character rain (use noise thresholds to place bright dots in grid positions).

### Industrial / Manufacturing

**Heat Distortion** — UV warp increasing toward bottom:

```glsl
float heat = pow(1.0 - uv.y, 1.5);
warped.x += sin(uv.y * 30.0 + t * 8.0) * 0.003 * heat;
```

**Warning Stripe** — diagonal hazard bands at edges:

```glsl
float stripe = sin((uv.x + uv.y) * 40.0) > 0.3 ? 1.0 : 0.0;
float bandMask = max(smoothstep(0.88, 0.92, uv.y), smoothstep(0.12, 0.08, uv.y));
```

## Integration

### In the picker

Each architecture's `preview_frames` can include a `<canvas>` element with inline GLSL. The canvas renders behind the frame content. Use the picker's accent color as a uniform.

### In the composition

The design.md `## Background` section describes the shader for the composition agent to implement. Include:

- Effect name and visual description
- Key GLSL techniques used (domain warp level, pattern type)
- Color palette mapping (which design.md colors map to which shader roles)
- Movement speed and character
- How the shader integrates with content (behind, overlay, mask)

### In rendering

Shaders use `u_time` as their only time input — compatible with GSAP timeline seeking. The capture engine advances `u_time` per frame for deterministic output. No `Math.random()`, no `Date.now()`.
