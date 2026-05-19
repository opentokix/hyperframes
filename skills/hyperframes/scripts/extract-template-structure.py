#!/usr/bin/env python3
"""Extract template structure as a compact component inventory + slide archetype index.

For each template, produces:
{
  "template": "slug",
  "slides": [{ "type": "cover", "components": ["hero-headline", "overline"] }, ...],
  "components": { "hero-headline": "<div ...>{{text}}</div>", ... },
  "decoratives": ["<svg>...</svg>"],
  "chrome": { "page_number": "...", "nav_hint": "..." }
}
"""
import re, sys, os, json
from html.parser import HTMLParser


def get_slides(html):
    """Extract top-level slide elements using a proper parser approach."""
    # Find the slides container
    # Templates use: <div class="slides">, <div class="slide-deck">, <deck-stage>, or direct sections
    slides = []

    # Match top-level slide elements
    # Patterns: section.slide, div.slide, deck-stage > section (with any class)
    # First try deck-stage sections
    deck_match = re.search(r'<deck-stage[^>]*>', html)
    if deck_match:
        # deck-stage templates: sections are direct children
        pattern = r'<(section)\b[^>]*>'
        region_start = deck_match.end()
        region_end = html.find('</deck-stage>', region_start)
        if region_end == -1:
            region_end = len(html)
        search_html = html[region_start:region_end]
        slide_starts = [(m, region_start) for m in re.finditer(pattern, search_html)]
    else:
        slide_starts = [(m, 0) for m in re.finditer(
            r'<(section|div)\b[^>]*\bclass="[^"]*\bslide\b[^"]*"[^>]*>',
            html
        )]

    for i, (m, offset) in enumerate(slide_starts):
        tag = m.group(1)
        start = offset + m.start()
        # Find the matching close tag by counting depth
        depth = 1
        pos = offset + m.end()
        while depth > 0 and pos < len(html):
            open_m = re.search(rf'<{tag}\b', html[pos:])
            close_m = re.search(rf'</{tag}>', html[pos:])
            if close_m is None:
                break
            if open_m and open_m.start() < close_m.start():
                depth += 1
                pos += open_m.end()
            else:
                depth -= 1
                if depth == 0:
                    end = pos + close_m.end()
                    slides.append(html[start:end])
                pos += close_m.end()

    return slides


def classify_slide(slide_html, index, css_text=""):
    """Classify a slide by archetype using content heuristics."""
    text = re.sub(r'<[^>]+>', ' ', slide_html)
    cls_match = re.search(r'class="([^"]+)"', slide_html[:300])
    cls = cls_match.group(1) if cls_match else ""

    # Class-name hints
    cls_lower = cls.lower()
    if any(k in cls_lower for k in ['cover', 'hero', 'title', 'poster']):
        return "cover"
    if any(k in cls_lower for k in ['quote', 'manifesto', 'statement']):
        return "quote"
    if any(k in cls_lower for k in ['data', 'stat', 'metric', 'financial', 'chart']):
        return "data"
    if any(k in cls_lower for k in ['road', 'timeline', 'phase', 'process']):
        return "process"
    if any(k in cls_lower for k in ['close', 'cta', 'end', 'contact']):
        return "cta"
    if any(k in cls_lower for k in ['service', 'feature', 'pillar', 'grid', 'gallery']):
        return "grid"
    if any(k in cls_lower for k in ['agenda', 'toc', 'overview', 'summary']):
        return "overview"
    if any(k in cls_lower for k in ['team', 'people', 'about']):
        return "team"

    # Content heuristics
    stats = re.findall(r'\d{2,}[%+MKBk$€£]|\$[\d,.]+', text)
    if len(stats) >= 2:
        return "data"
    if '<li' in slide_html and slide_html.count('<li') >= 3:
        return "detail"
    if index == 0:
        return "cover"

    return "content"


def extract_components(slide_html, css_text=""):
    """Extract component patterns from a slide."""
    components = []

    # Large display text (hero headlines)
    for m in re.finditer(r'<(?:div|h[1-3]|span)[^>]*style="[^"]*font-size:\s*(?:clamp\()?(\d+)', slide_html):
        size = int(m.group(1))
        if size >= 60:
            components.append("hero-headline")
        elif size >= 32:
            components.append("section-heading")

    # Stat blocks (large number + label pattern)
    stat_blocks = re.findall(r'<div[^>]*>[\s]*<div[^>]*style="[^"]*font-size:\s*(?:clamp\()?(\d+)[^"]*"[^>]*>\s*[\d$%+,.MKB]+', slide_html)
    for _ in stat_blocks:
        components.append("stat-card")

    # Lists
    if '<ul' in slide_html or '<ol' in slide_html:
        components.append("bullet-list")

    # Buttons/CTAs
    if re.search(r'class="[^"]*btn|button|cta', slide_html, re.I):
        components.append("button")

    # Quote/italic
    if re.search(r'<blockquote|font-style:\s*italic|class="[^"]*quote', slide_html, re.I):
        components.append("pull-quote")

    # Grid layouts
    if re.search(r'grid-template-columns|display:\s*grid', slide_html):
        components.append("grid-layout")

    # Footer/bar
    if re.search(r'class="[^"]*footer|class="[^"]*bar|bottom:\s*0', slide_html):
        components.append("footer-bar")

    # Overline/label
    if re.search(r'text-transform:\s*uppercase.*letter-spacing:\s*0\.\d+em|class="[^"]*label|class="[^"]*overline|class="[^"]*micro', slide_html):
        components.append("overline")

    # Image placeholder
    if re.search(r'<img|IMAGE.PLACEHOLDER|class="[^"]*img|class="[^"]*photo', slide_html, re.I):
        components.append("image")

    # Deduplicate preserving order
    seen = set()
    unique = []
    for c in components:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    return unique if unique else ["content-block"]


def extract_decoratives(html):
    """Extract decorative SVGs and ornamental elements."""
    decoratives = []

    # Inline SVGs (non-icon, decorative)
    for m in re.finditer(r'<svg[^>]*>(.*?)</svg>', html, re.DOTALL):
        svg = m.group(0)
        if len(svg) < 2000:  # Skip huge SVGs
            # Clean: remove IDs, simplify
            svg = re.sub(r'\s+id="[^"]*"', '', svg)
            decoratives.append(svg[:500])  # Cap length

    # Decorative dividers (thin lines, borders)
    for m in re.finditer(r'<div[^>]*style="[^"]*border-(?:top|bottom):[^"]*"[^>]*/?\s*>', html):
        decoratives.append(m.group(0))

    return decoratives[:5]  # Cap at 5


def extract_chrome(html):
    """Extract page chrome patterns (page numbers, nav hints)."""
    chrome = {}

    # Page number patterns
    pn = re.search(r'class="[^"]*(?:pagenum|slide-counter|page-num)[^"]*"[^>]*>(.*?)</(?:div|span)>', html, re.DOTALL)
    if pn:
        chrome["page_number"] = re.sub(r'<[^>]+>', '', pn.group(1)).strip()[:50]

    # Nav hints
    nh = re.search(r'class="[^"]*nav-hint[^"]*"[^>]*>(.*?)</(?:div|span)>', html, re.DOTALL)
    if nh:
        chrome["nav_hint"] = re.sub(r'<[^>]+>', '', nh.group(1)).strip()[:50]

    return chrome


def extract_structure(html_path, slug):
    """Extract full structure from a template."""
    with open(html_path) as f:
        html = f.read()

    # Extract CSS
    css_blocks = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    css_text = '\n'.join(css_blocks)

    slides_html = get_slides(html)

    slides = []
    all_components = set()
    for i, slide in enumerate(slides_html):
        slide_type = classify_slide(slide, i, css_text)
        components = extract_components(slide, css_text)
        slides.append({
            "type": slide_type,
            "components": components
        })
        all_components.update(components)

    decoratives = extract_decoratives(html)
    chrome = extract_chrome(html)

    return {
        "template": slug,
        "slide_count": len(slides_html),
        "slides": slides,
        "component_types": sorted(all_components),
        "decoratives": decoratives,
        "chrome": chrome
    }


def main():
    templates_dir = sys.argv[1] if len(sys.argv) > 1 else "skills/hyperframes/templates/presentations"
    index_path = os.path.join(os.path.dirname(templates_dir), "index.json")

    with open(index_path) as f:
        index = json.load(f)

    for t in index["templates"]:
        html_path = os.path.join(templates_dir, t["slug"], "template.html")
        if not os.path.exists(html_path):
            continue
        structure = extract_structure(html_path, t["slug"])
        print(f"  {t['slug']}: {structure['slide_count']} slides, "
              f"{len(structure['component_types'])} component types, "
              f"{len(structure['decoratives'])} decoratives")

    # Output one example in full
    if index["templates"]:
        slug = "bold-poster"
        path = os.path.join(templates_dir, slug, "template.html")
        if os.path.exists(path):
            s = extract_structure(path, slug)
            print(f"\n=== Example: {slug} ===")
            print(json.dumps(s, indent=2)[:2000])


if __name__ == "__main__":
    main()
