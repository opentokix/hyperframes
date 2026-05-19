# Figma to DESIGN.html

Extract a design system from a Figma file and generate a bespoke DESIGN.html. This is the lossless path — exact hex values, font weights, border radii, padding, and shadow definitions come directly from the Figma API, not approximated from screenshots.

## Prerequisites

- Figma MCP tools available (`get_design_context`, `search_design_system`), OR
- Figma REST API access via personal access token + `curl`

## When to use

- User provides a Figma URL (`figma.com/design/:fileKey/...`)
- User says "use this Figma file" or "extract from Figma"
- User has a Figma design system file and wants a DESIGN.html for video composition

## Extraction process

### Step 1: Get the file structure

**Via MCP:**

```
get_design_context(fileKey, nodeId="0:1", excludeScreenshot=true)
```

**Via REST API (if MCP rate-limited):**

```bash
curl -s -H "X-Figma-Token: $TOKEN" \
  "https://api.figma.com/v1/files/$FILE_KEY?depth=1"
```

This returns the page list. Identify the relevant pages by name:

| Look for                             | Contains                                   |
| ------------------------------------ | ------------------------------------------ |
| "Colours", "Colors", "Palette"       | Color swatches with hex values             |
| "Typography", "Type", "Fonts"        | Font specimens with family/weight/size     |
| "Buttons", "Components"              | Button components with radius/padding/fill |
| "Brand Guidelines", "Brand Overview" | Complete brand summary                     |
| "Grids", "Shadows", "Elevation"      | Spacing system and shadow definitions      |
| "Logo", "Brand Mark"                 | Logo treatment                             |
| "Icons", "Iconography"               | Icon style                                 |

### Step 2: Extract colors

Fetch the Colors page at depth 6-8:

```bash
curl -s -H "X-Figma-Token: $TOKEN" \
  "https://api.figma.com/v1/files/$FILE_KEY/nodes?ids=$COLORS_PAGE_ID&depth=8"
```

Walk the node tree. For each node with `type: "RECTANGLE"` or `"ELLIPSE"` that has solid fills, extract:

- The `color` RGBA values → convert to hex: `#${Math.round(r*255).toString(16)}...`
- The parent/ancestor `name` for the color role (e.g., "Primary", "Green Grass", "Info Blue")

Group colors by their section headings (found in adjacent TEXT nodes). Map to the 4-role model:

| Figma section                  | → Picker role |
| ------------------------------ | ------------- |
| Primary brand color / main CTA | `--accent`    |
| Background / canvas            | `--secondary` |
| Body text / ink / dark neutral | `--primary`   |
| Muted / secondary text / gray  | `--tertiary`  |

### Step 3: Extract typography

Fetch the Typography page at depth 6:

```bash
curl -s -H "X-Figma-Token: $TOKEN" \
  "https://api.figma.com/v1/files/$FILE_KEY/nodes?ids=$TYPE_PAGE_ID&depth=6"
```

For each TEXT node, extract from the `style` object:

- `fontFamily` — the exact font name
- `fontWeight` — numeric weight (400, 500, 600, 700, 800, 900)
- `fontSize` — in px
- `lineHeightPx` — line height in px (compute ratio: `lineHeightPx / fontSize`)
- `letterSpacing` — in px (convert to em: `letterSpacing / fontSize`)

Build the hierarchy table from the token names (found in adjacent TEXT nodes like "Title/XXL", "Text/M", "Tag/S").

**Font resolution:** Check if the extracted fonts are on Google Fonts. If yes, use directly. If proprietary, check `fonts/` directory for `.woff2` files, then fall back to the design.md's substitute recommendations.

### Step 4: Extract surface properties

Fetch the Buttons/Components page at depth 6:

```bash
curl -s -H "X-Figma-Token: $TOKEN" \
  "https://api.figma.com/v1/files/$FILE_KEY/nodes?ids=$BUTTONS_PAGE_ID&depth=6"
```

For each COMPONENT or INSTANCE node, extract:

- `cornerRadius` — border-radius in px
- `paddingTop/Right/Bottom/Left` — padding values
- `itemSpacing` — gap between children
- `strokeWeight` — border width
- `strokes[].color` — border color
- `fills[].color` — background color
- `effects[]` — shadow definitions (type, color, offset, radius, spread)

Build the radius scale from unique `cornerRadius` values across all components.
Build the spacing scale from unique padding/gap values.
Identify the shadow tier(s) — often 0 (flat), 1 (subtle), or 2 (elevated).

### Step 5: Craft the DESIGN.html

With the extracted tokens, follow [design-showcase.md](design-showcase.md):

1. Write the one-sentence character description
2. Place on the 6 character axes
3. Map colors to the 4-token model (`--primary`, `--secondary`, `--tertiary`, `--accent`)
4. Set the extracted fonts (display + body from the Figma type page)
5. Set surface properties (radius scale, padding, gap, shadow from components)
6. Build each section styled to the brand's character — using the EXACT values from Figma

**Critical:** Use the extracted values verbatim. Don't round `cornerRadius: 12.0` to `12px` and then decide "that's close to 16px." The Figma API gives exact values — use them.

### Step 6: Export components as SVG

The Figma REST API exports any node as a lossless SVG:

```bash
curl -s -H "X-Figma-Token: $TOKEN" \
  "https://api.figma.com/v1/images/$FILE_KEY?ids=$NODE_ID1,$NODE_ID2&format=svg"
```

Returns `{ "images": { "node:id": "https://...s3.amazonaws.com/..." } }`. Download each URL — the SVG contains exact shapes, colors, text-as-paths, strokes. Truly lossless vector exports.

**What to export:**

- Default-state buttons (primary, secondary, outline, dark)
- Tags/badges/pills
- Section tags and dividers
- Logo/brand mark
- Icons (if vector)
- Illustrations (if vector)

### Step 7: Build slides as component references

The slides in `summary.html` are **component references for the composition agent**. Each slide shows actual Figma components at 1920×1080 scale. The agent copies the slide's HTML/SVG structure and swaps content — no guessing.

**Inline the exported SVGs** directly in the slide HTML. The agent reads the SVG source to extract exact CSS values or uses the SVG as-is.

| Slide | Shows                                              | Source                          |
| ----- | -------------------------------------------------- | ------------------------------- |
| 1     | All button variants at video scale                 | Inline SVGs from Step 6         |
| 2     | Card components with exact padding, radius, border | CSS from Step 4 node properties |
| 3     | Tags, badges, pills                                | Inline SVGs from Step 6         |
| 4     | A real layout composition from the Figma           | CSS grid from Step 4            |
| 5     | Typography in a composed layout (not a specimen)   | Fonts from Step 3               |
| 6     | Illustrations, icons, logo as inline SVG           | SVG exports from Step 6         |

**The slides ARE the component spec.** The agent doesn't guess what a card looks like — it copies the slide's structure.

**Via MCP (if available):** Call `get_design_context` on individual component nodes for full HTML/CSS. Adapt to vanilla HTML.

**Via REST API:** Export as SVG for lossless vector components. Use node properties for CSS values.

## REST API reference

### File structure

```
GET /v1/files/:key?depth=1
→ { document: { children: [{ id, name, type:"CANVAS" }] } }
```

### Node details

```
GET /v1/files/:key/nodes?ids=:id1,:id2&depth=N
→ { nodes: { ":id1": { document: { ...node tree... } } } }
```

### Key node properties for extraction

| Property                       | What it gives you                                       |
| ------------------------------ | ------------------------------------------------------- |
| `fills[].color.{r,g,b,a}`      | Background color (0-1 floats → multiply by 255 for hex) |
| `strokes[].color`              | Border color                                            |
| `strokeWeight`                 | Border width                                            |
| `cornerRadius`                 | Border-radius                                           |
| `paddingTop/Right/Bottom/Left` | CSS padding                                             |
| `itemSpacing`                  | CSS gap                                                 |
| `effects[].type`               | `DROP_SHADOW`, `INNER_SHADOW`, `BACKGROUND_BLUR`        |
| `effects[].color`              | Shadow color                                            |
| `effects[].offset.{x,y}`       | Shadow offset                                           |
| `effects[].radius`             | Shadow blur                                             |
| `effects[].spread`             | Shadow spread                                           |
| `style.fontFamily`             | Font family name                                        |
| `style.fontWeight`             | Font weight (numeric)                                   |
| `style.fontSize`               | Font size in px                                         |
| `style.lineHeightPx`           | Line height in px                                       |
| `style.letterSpacing`          | Letter spacing in px                                    |
| `characters`                   | Text content                                            |

### Authentication

```bash
curl -H "X-Figma-Token: $PERSONAL_ACCESS_TOKEN" "https://api.figma.com/v1/..."
```

Generate a personal access token at: figma.com → Settings → Personal access tokens

## Integration with HyperFrames skill

This guide runs during Step 1 (Design system) when the user provides a Figma URL:

1. Extract file structure → identify color/type/component pages
2. Pull each page via REST API or MCP
3. Extract tokens (colors, fonts, radii, padding, shadows)
4. Craft DESIGN.html via [design-showcase.md](design-showcase.md) using exact Figma values
5. Craft `summary.html` slides using Figma component CSS
6. Offer the picker for fine-tuning
7. Continue to Step 2 (prompt expansion)
