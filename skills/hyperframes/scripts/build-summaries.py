#!/usr/bin/env python3
"""Build summary.html for each template — compact design system + layout skeletons.

Output per template:
1. Minified CSS: :root tokens + base class definitions (no comments, no theme variants,
   no animation keyframes, no nav/chrome engine CSS)
2. One HTML skeleton per unique slide type with {{placeholder}} content

Usage:
    python3 build-summaries.py [templates-dir]
"""
import re, os, sys, json


def extract_css(html, template_dir=None):
    styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    if template_dir:
        for m in re.finditer(r'<link[^>]*href="([^"]+\.css)"', html):
            href = m.group(1)
            if 'fonts.googleapis' in href:
                continue
            css_path = os.path.join(template_dir, href)
            if os.path.exists(css_path):
                with open(css_path) as f:
                    styles.append(f.read())
    return '\n'.join(styles)


def minify_css(css):
    # Strip comments
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    # Strip lines that are only whitespace
    lines = [l for l in css.split('\n') if l.strip()]
    css = '\n'.join(lines)
    return css


def strip_theme_variants(css):
    """Remove nested variant overrides but keep base .slide.dark/.slide.orange rules."""
    # Remove nested blocks like .orange .stat-value { ... } or .dark .muted { ... }
    css = re.sub(r'\.(orange|dark|light)\s+\.[^\{]+\{[^}]*\}', '', css)
    return css


def strip_animation_css(css):
    """Remove @keyframes and animation-related rules."""
    css = re.sub(r'@keyframes\s+\w+\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}', '', css, flags=re.DOTALL)
    css = re.sub(r'\[data-anim[^\]]*\]\s*\{[^}]*\}', '', css)
    css = re.sub(r'\[data-delay[^\]]*\]\s*\{[^}]*\}', '', css)
    css = re.sub(r'\.slide\.is-active\s+\[data-anim[^\]]*\]\s*\{[^}]*\}', '', css)
    return css


def strip_nav_css(css):
    """Remove navigation/chrome engine CSS."""
    nav_selectors = ['#nav-dots', '.nav-dot', '#slide-counter', '#deck']
    for sel in nav_selectors:
        css = re.sub(re.escape(sel) + r'[^{]*\{[^}]*\}', '', css)
    return css


def strip_engine_css(css):
    """Remove slide engine mechanics (transitions, will-change)."""
    # Remove generic .slide base positioning (agent writes its own)
    # Keep .slide layout rules (grid-template-rows etc)
    return css


def compress_whitespace(css):
    """Collapse multiple blank lines, trim indentation."""
    # Reduce indentation to 2 spaces
    lines = []
    for line in css.split('\n'):
        stripped = line.strip()
        if not stripped:
            continue
        # Detect indent level
        indent = len(line) - len(line.lstrip())
        new_indent = min(indent // 4, 2) * 2
        lines.append(' ' * new_indent + stripped)
    return '\n'.join(lines)


def extract_root_tokens(css):
    """Extract :root { ... } block."""
    m = re.search(r':root\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', css, re.DOTALL)
    if m:
        return ':root {\n' + m.group(1).strip() + '\n}'
    return ''


def extract_class_definitions(css):
    """Extract class definitions, excluding theme variants and animations."""
    css = re.sub(r':root\s*\{[^}]*\}', '', css, flags=re.DOTALL)
    rules = []
    for m in re.finditer(r'([.#][\w-][^{]*)\{([^}]*)\}', css):
        selector = m.group(1).strip()
        body = m.group(2).strip()
        # Skip theme variants
        if re.match(r'\.(orange|dark|light)\s', selector):
            continue
        # Skip animation/nav
        if any(k in selector for k in ['data-anim', 'data-delay', 'nav-dot', '#deck', '#nav', '#slide-counter', 'is-active']):
            continue
        # Skip keyframes (handled separately)
        if '@keyframes' in selector:
            continue
        # Skip empty
        if not body:
            continue
        rules.append(f'{selector} {{ {body} }}')
    return '\n'.join(rules)


INNER_CONTAINERS = {'slide-body', 'slide-content', 'slide-chrome', 'slide-foot',
                     'slide-counter', 'slides-container'}


def get_slide_type(cls):
    """Extract slide type from class string."""
    for c in cls.split():
        if c.startswith('slide--'):
            return c
        if c.startswith('s-'):
            return c
        if c.startswith('slide-') and c not in INNER_CONTAINERS:
            return c
    for c in cls.split():
        if c.startswith('bg-'):
            return c
        if c not in ('slide', 'active', 'dark', 'light', 'hairlines'):
            return c
    return 'slide'


def has_slide_class(cls):
    """Check if class string has 'slide' as a standalone class (not slide-body etc)."""
    return 'slide' in cls.split()


def get_slides(html):
    """Extract slide sections from any template structure."""
    html_flat = re.sub(r'\s+', ' ', html)
    slides = []
    # Match <section class="..."> and <div class="slide ..."> (standalone slide class only)
    pattern = r'(<(?:section)\s+[^>]*class="([^"]+)"[^>]*>|<div\s+[^>]*class="([^"]+)"[^>]*>)'
    for m in re.finditer(pattern, html_flat):
        cls = m.group(2) or m.group(3)
        if m.group(3) and not has_slide_class(cls):
            continue
        stype = get_slide_type(cls)
        start = m.start()
        tag = 'section' if '<section' in m.group(0) else 'div'
        depth = 1
        pos = m.end()
        while depth > 0 and pos < len(html_flat):
            open_m = re.search(r'<' + tag + r'\b', html_flat[pos:])
            close_m = re.search(r'</' + tag + r'>', html_flat[pos:])
            if close_m is None:
                break
            if open_m and open_m.start() < close_m.start():
                depth += 1
                pos += open_m.end()
            else:
                depth -= 1
                if depth == 0:
                    slides.append((stype, html_flat[start:pos + close_m.end()]))
                pos += close_m.end()
    return slides



def strip_content(slide_html):
    """Replace text content with {{placeholders}}, remove data-anim/style attrs."""
    result = re.sub(r'\s+data-anim="[^"]*"', '', slide_html)
    result = re.sub(r'\s+data-delay="\d+"', '', result)
    result = re.sub(r'\s+style="[^"]*"', '', result)

    def replace_text(m):
        tag_open = m.group(1)
        text = m.group(2).strip()
        tag_close = m.group(3)
        if not text or text.startswith('<') or text.startswith('{'):
            return m.group(0)
        cls = tag_open.lower()
        if any(c in cls for c in ['display', '"h1', '"h2', '"h3', 'heading', 'title']):
            return f'{tag_open}{{{{headline}}}}{tag_close}'
        elif any(c in cls for c in ['lead', 'body', 'desc', 'lede', 'meta']):
            return f'{tag_open}{{{{body}}}}{tag_close}'
        elif any(c in cls for c in ['label', 'kicker', 'caption', 'muted', 'note', 'source']):
            return f'{tag_open}{{{{label}}}}{tag_close}'
        elif any(c in cls for c in ['stat-value', 'num', 'value', 'v "']):
            return f'{tag_open}{{{{number}}}}{tag_close}'
        elif len(text) < 30:
            return f'{tag_open}{{{{text}}}}{tag_close}'
        else:
            return f'{tag_open}{{{{body}}}}{tag_close}'
    result = re.sub(r'(<[^>]+>)([^<]+)(</[^>]+>)', replace_text, result)
    # Remove HTML comments
    result = re.sub(r'<!--.*?-->', '', result, flags=re.DOTALL)
    # Collapse blank lines
    result = re.sub(r'\n\s*\n+', '\n', result)
    return result.strip()


def build_summary(html_path, slug):
    with open(html_path) as f:
        html = f.read()

    template_dir = os.path.dirname(html_path)
    css = extract_css(html, template_dir)

    # Extract and compress CSS
    root_tokens = extract_root_tokens(css)
    clean_css = minify_css(css)
    clean_css = strip_theme_variants(clean_css)
    clean_css = strip_animation_css(clean_css)
    clean_css = strip_nav_css(clean_css)
    class_defs = extract_class_definitions(clean_css)
    compressed_css = compress_whitespace(root_tokens + '\n' + class_defs)

    # Extract font links
    font_links = re.findall(r'<link[^>]*fonts\.googleapis[^>]*>', html)

    # Extract unique slide skeletons
    slides = get_slides(html)

    seen_types = set()
    skeletons = []
    for stype, slide_html in slides:
        if stype in seen_types:
            continue
        seen_types.add(stype)
        skeleton = strip_content(slide_html)
        skeletons.append((stype, skeleton))

    # Build summary HTML
    out = f'<!-- {slug} — design summary -->\n'
    out += '<style>\n' + compressed_css + '\n</style>\n\n'
    for link in font_links:
        out += link + '\n'
    out += '\n'
    for stype, skeleton in skeletons:
        out += f'<!-- {stype} -->\n{skeleton}\n\n'

    return out


def main():
    templates_dir = sys.argv[1] if len(sys.argv) > 1 else "skills/hyperframes/templates/presentations"
    index_path = os.path.join(os.path.dirname(templates_dir), "index.json")

    with open(index_path) as f:
        index = json.load(f)

    total_saved = 0
    for t in index['templates']:
        html_path = os.path.join(templates_dir, t['slug'], 'template.html')
        if not os.path.exists(html_path):
            continue

        summary = build_summary(html_path, t['slug'])
        out_path = os.path.join(templates_dir, t['slug'], 'summary.html')
        with open(out_path, 'w') as f:
            f.write(summary)

        orig_size = os.path.getsize(html_path)
        summ_size = len(summary)
        pct = int((1 - summ_size / orig_size) * 100)
        total_saved += orig_size - summ_size
        print(f"  {t['slug']}: {orig_size//1024}K → {summ_size//1024}K ({pct}% smaller)")

    print(f"\nTotal saved: {total_saved//1024}K across {len(index['templates'])} templates")


if __name__ == '__main__':
    main()
