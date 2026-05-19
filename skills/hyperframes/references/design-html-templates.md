# Design HTML Template Extraction

A design.html with embedded templates contains TWO separate design systems. Mix them up and the output looks nothing like the reference. This guide prevents that.

## The Two Systems

Every design.html with a template gallery has:

| Layer               | What it is                                                                       | Where it lives                                                                             | Fonts                                                 | Use for                                           |
| ------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ----------------------------------------------------- | ------------------------------------------------- |
| **Page chrome**     | The design system document itself — headers, swatches, specimen rows, rules grid | `<style id="ds-tokens">`, `:root` block, main `<style>`                                    | Loaded in `<link>` tags                               | Reading palette values, understanding constraints |
| **Slide templates** | The actual video/slide frames — the things the user SEES and wants reproduced    | `<style id="template-css">` or similar scoped block, `<template>` elements or gallery HTML | Referenced in template CSS (often NOT loaded — check) | Building the composition                          |

**The templates are the product. The page chrome is the packaging.** Build from the templates.

## Extraction Order

### 1. Find the template CSS

Look for a scoped style block — `<style id="template-css">`, a class-scoped namespace like `.ds-slide-frame`, or similar. This is the CSS that styles the actual slides, not the document page.

### 2. Resolve the color chain

Template CSS often uses `var()` references back to `:root` tokens:

```
:root → --primary:#1C2B33
template → --tp-primary: var(--primary)
template → --black: var(--tp-primary)
```

Trace every variable to its resolved hex. Check for override blocks like `.slide.dark { background: #F7B928 !important }` — these remap what "dark" and "light" mean in this specific system. The names often lie after remapping.

### 3. Identify the template font stack

Template CSS declares its own `font-family` values per element. These are often DIFFERENT from the page's `<link>` loaded fonts:

```css
/* Page loads: "Big Shoulders Stencil Display" */
/* Template CSS uses: "Stardos Stencil", "Barlow Condensed" */
```

Use the fonts from the template CSS. If they're Google Fonts, the HyperFrames compiler auto-embeds them. If they're not loaded in the HTML and not on Google Fonts, warn and fall back.

### 4. Catalog available templates

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

### 5. Map scenes to templates

For each scene in the composition, pick the template type that best fits the content. Adapt content into the template's HTML structure — don't invent new structures.

```
Scene 1 (brand intro)     → s-cover
Scene 2 (section break)   → s-sec
Scene 3 (product pillars) → s-princ
Scene 4 (impact stats)    → s-stats
Scene 5 (CTA)             → s-cta
```

### 6. Build scenes using template HTML

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

### 7. Include template CSS in composition

Copy the full template CSS block into the composition's `<style>`. Include the `:root` tokens it depends on. Don't cherry-pick — missing a selector breaks a layout.

## What Goes Wrong Without This

| Mistake                                           | Symptom                                                   |
| ------------------------------------------------- | --------------------------------------------------------- |
| Extract only tokens, rebuild layouts from scratch | Output looks generic, nothing like the templates          |
| Use page chrome fonts instead of template fonts   | Wrong typeface in every headline                          |
| Miss `.slide.dark` overrides                      | "Dark" scenes use wrong background color                  |
| Invent card/panel structures                      | Rounded corners where templates use sharp (or vice versa) |
| Skip template CSS, write own                      | Element spacing, font sizes, layout grids all wrong       |
| Use 3 cards when template has 4                   | Breaks the grid, gaps look wrong                          |

## Integration with HyperFrames Skill

This guide runs during Step 1 (Design system) of the hyperframes workflow. When a DESIGN.html with templates is detected:

1. Replace the "read design.md" path with template extraction (this guide)
2. Continue to Step 2 (prompt expansion) — but scene beats must map to specific template types
3. Continue to Step 3 (build) — each scene uses template HTML structures and the template CSS
