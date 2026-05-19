# Video Composition

Video frames are not web pages. These rules apply to every composition regardless of brand, style, or design.md.

## design.md Is Brand, Not Layout

design.md defines what the brand looks like: colors, fonts, personality, constraints. It does NOT define how to compose a video frame. Use brand colors at video-appropriate intensity — not at web-UI opacity.

**Strict from design.md:** hex values (including background color), font families, weight relationships, Do's and Don'ts. If the user chose a light canvas, use a light canvas. If they chose dark, use dark. Do not override their palette.

**Adapt for video:** type sizes, spacing, decorative opacity, border weight, component treatments. A web UI card at `border: 1px solid #e2e3e6` with `box-shadow: 0 2px 4px rgba(0,0,0,0.06)` is invisible on video. The brand color is sacred; the application is yours.

## Density

Density is a creative choice, not a minimum. A single number filling the frame can be more powerful than 10 elements competing for attention. An empty frame with one element appearing creates tension a busy frame can't.

Think in layers, not counts:

- **Background** — texture, color, atmosphere. Can be a solid color if that serves the scene.
- **Content** — the actual message. Could be one word or a data table.
- **Accents** — structural elements that guide the eye. Optional — not every scene needs them.

The default failure mode is too sparse (flat background, centered text, no depth). But the overcorrection — cramming decoratives into every frame — is equally bad. Match density to the scene's emotional beat: high-energy scenes earn more elements; contemplative moments earn fewer.

## Color Presence

Muted is fine. Flat is not. Every scene should have at least one color that pulls the eye.

- Brand accent should be VISIBLE — not a 5% opacity glow lost in compression. 15-25% for atmospheric, full saturation for focal elements.
- **Light canvases work differently than dark.** On dark: accent glows pop naturally. On light: use bolder borders (2px+ solid), stronger structural elements (rules, dividers), and full-saturation accent hits. Light backgrounds need texture (subtle grain, patterns) to avoid the "blank slide" feel. Don't switch to dark — make light cinematic.
- Tint neutrals toward the brand hue. Dead gray reads as undesigned.

## Scale

Web sizes are invisible on video. Everything scales up.

| Element            | Web     | Video    |
| ------------------ | ------- | -------- |
| Headlines          | 32-48px | 64-120px |
| Body text          | 14-16px | 28-42px  |
| Labels             | 12px    | 18-24px  |
| Decorative opacity | 3-8%    | 12-25%   |
| Borders            | 1px     | 2-4px    |
| Padding            | 16-32px | 60-140px |

If you're writing a font-size under 24px in a video composition, justify it. If you're writing decorative opacity under 10%, it's invisible.

## Motion Intensity

Subtle reads as static at 30fps. Err toward more movement than feels safe.

- Decorative elements usually need ambient motion: breathe, drift, pulse, orbit. But deliberate stillness after motion is powerful — don't animate something just because it exists.
- Vary motion per scene — don't repeat the same ambient pattern.
- Scene entrances should use 3+ different eases and directions. If every element enters from `y: 30, opacity: 0`, the scene has no choreography.

## Frame Composition

- **Focal hierarchy.** The eye needs to know where to land first. Sometimes that's two competing elements; sometimes it's one dominating element with nothing else. Both work — what doesn't work is everything at equal weight.
- **Use the frame.** Content can fill 80% of the width or occupy one corner — both are valid compositions. What looks broken is content floating in the center with equal margins on all sides, the default web layout.
- **Anchor to edges.** Pin content to left/top or right/bottom. Centered-and-floating is a web layout pattern.
- **Split frames.** Data panel left, content right. Top bar with metadata, full-width below. Zone-based layouts over centered stacks.
- **Structural elements.** Rules, dividers, border panels. They create visual paths and animate well (`scaleX: 0` → `1`).
