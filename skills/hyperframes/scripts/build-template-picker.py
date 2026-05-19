#!/usr/bin/env python3
"""Build a template picker HTML from the template and injected data.

Usage:
    python3 build-template-picker.py \
        --template skills/hyperframes/templates/template-picker.html \
        --templates-dir /path/to/beautiful-html-templates/templates \
        --output .hyperframes/template-picker.html \
        < data.json

data.json must contain:
    { "palettes": [...], "prompt_text": {...}, "prompt_desc": "..." }

The script reads index.json from templates-dir parent, extracts CSS color vars
from each template, and injects all data into the HTML template.
"""
import json, sys, re, os, argparse

def extract_color_vars(html_path):
    with open(html_path) as f:
        html = f.read()
    root_match = re.search(r':root\s*\{([^}]+)\}', html)
    if not root_match:
        return []
    return [m[0] for m in re.findall(r'(--[\w-]+)\s*:\s*([^;]+)', root_match.group(1))
            if '#' in m[1] or 'rgb' in m[1]]

def extract_preview(html_path, slug):
    """Extract the first slide + scoped CSS as an inline preview HTML string."""
    with open(html_path) as f:
        html = f.read()

    # Extract all <style> blocks
    styles = re.findall(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
    css = '\n'.join(styles)

    # Find the first slide
    # Try: deck-stage > section, section.slide, div.slide, .slide
    slide_html = ""
    for pattern in [
        r'(<section[^>]*class="[^"]*s-cover[^"]*"[^>]*>.*?</section>)',
        r'(<section[^>]*class="[^"]*slide[^"]*"[^>]*>.*?</section>)',
        r'(<div[^>]*class="[^"]*slide[^"]*"[^>]*>.*?</div>\s*(?=<div[^>]*class="[^"]*slide|</div>))',
    ]:
        m = re.search(pattern, html, re.DOTALL)
        if m:
            slide_html = m.group(1)
            break

    if not slide_html:
        # Fallback: grab the body content
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
        if body_match:
            slide_html = body_match.group(1)[:3000]

    if not css and not slide_html:
        return ""

    # Scope CSS: prefix all selectors with .tp-{slug}
    scope_class = f"tp-{slug}"
    scoped_css = css
    # Replace :root with .tp-{slug} scope
    scoped_css = scoped_css.replace(':root', f'.{scope_class}')
    # Prefix other selectors (rough but effective)
    # Replace top-level selectors that start with a letter, ., # or [
    lines = []
    for line in scoped_css.split('\n'):
        stripped = line.strip()
        # Skip @import, @font-face, @keyframes
        if stripped.startswith('@') or stripped.startswith('}') or stripped.startswith('/*') or not stripped:
            lines.append(line)
            continue
        # If line contains { and doesn't start with space (top-level selector)
        if '{' in stripped and not line.startswith(' ') and not line.startswith('\t'):
            # Prefix each selector before {
            before_brace = stripped.split('{')[0]
            after_brace = '{'.join(stripped.split('{')[1:])
            selectors = before_brace.split(',')
            prefixed = ', '.join(
                f'.{scope_class} {s.strip()}' if not s.strip().startswith(f'.{scope_class}') else s.strip()
                for s in selectors
            )
            lines.append(f'      {prefixed} {{{after_brace}')
        else:
            lines.append(line)
    scoped_css = '\n'.join(lines)

    # Strip any script tags from the slide HTML
    slide_html = re.sub(r'<script[^>]*>.*?</script>', '', slide_html, flags=re.DOTALL)

    # Build inline preview: scoped style + slide content
    preview = (
        f'<div class="{scope_class}" style="width:1920px;height:1080px;position:relative;overflow:hidden;">'
        f'<style>{scoped_css}</style>'
        f'{slide_html}'
        f'</div>'
    )

    return preview

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--template', required=True)
    parser.add_argument('--templates-dir', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    data = json.load(sys.stdin)

    index_path = os.path.join(os.path.dirname(args.templates_dir), 'index.json')
    with open(index_path) as f:
        index = json.load(f)

    # Import structure extraction
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    try:
        from importlib import import_module
        extract_mod = {}
        exec(open(os.path.join(script_dir, 'extract-template-structure.py')).read().split('def main')[0], extract_mod)
        extract_structure = extract_mod.get('extract_structure')
    except Exception:
        extract_structure = None

    templates = []
    for t in index['templates']:
        html_path = os.path.join(args.templates_dir, t['slug'], 'template.html')
        if not os.path.exists(html_path):
            continue
        preview = extract_preview(html_path, t['slug'])
        entry = {
            'slug': t['slug'],
            'name': t['name'],
            'tagline': t['tagline'],
            'scheme': t['scheme'],
            'density': t['density'],
            'colorVars': extract_color_vars(html_path),
            'preview_html': preview
        }
        if extract_structure:
            try:
                entry['structure'] = extract_structure(html_path, t['slug'])
            except Exception:
                pass
        templates.append(entry)

    with open(args.template) as f:
        html = f.read()

    html = html.replace('__PALETTES_JSON__', json.dumps(data['palettes']))
    html = html.replace('__PROMPT_TEXT_JSON__', json.dumps(data['prompt_text']))
    html = html.replace('__TEMPLATES_JSON__', json.dumps(templates))
    html = html.replace('__MOTION_TEMPLATES_JSON__', json.dumps(data.get('motion_templates', [])))
    html = html.replace('__PROMPT_DESC__', data.get('prompt_desc', ''))

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        f.write(html)

    print(f"Written to {args.output} ({len(templates)} templates)")

if __name__ == '__main__':
    main()
