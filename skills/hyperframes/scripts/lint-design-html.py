#!/usr/bin/env python3
"""Lint a design.html template for hardcoded values that should use CSS custom properties.

Checks that every container/card element uses var(--cr), var(--pad), var(--gap),
var(--shadow) instead of hardcoded border-radius, padding, gap, or box-shadow values.

Usage:
    python3 lint-design-html.py presentations/user-design/design.html
"""
import sys, re, os

def _compile_rules(rules):
    for r in rules:
        if 'pattern' in r:
            r['_re'] = re.compile(r['pattern'])
        if 'exclude' in r:
            r['_re_ex'] = re.compile(r['exclude'])
        if 'check_missing' in r:
            r['_re_miss'] = re.compile(r['check_missing'])
    return rules

RULES = _compile_rules([
    {
        'name': 'hardcoded-radius',
        'pattern': r'border-radius:\s*(\d+px)',
        'message': 'Hardcoded border-radius "{match}" — use var(--cr)',
        'exclude': r'var\(--cr\)|calc\(var\(--cr\)|\.bar|\.badge|\.bar\b|3px;opacity',
    },
    {
        'name': 'hardcoded-shadow',
        'pattern': r'box-shadow:\s*(\d+px\s+\d+px)',
        'message': 'Hardcoded box-shadow — use var(--shadow)',
        'exclude': r'var\(--shadow\)',
    },
    {
        'name': 'hardcoded-color-in-css',
        'pattern': r'(?:color|background|border-color):\s*(#[0-9a-fA-F]{3,8})\b',
        'message': 'Hardcoded color "{match}" in CSS — use var(--primary/secondary/tertiary/accent) or color-mix()',
        'exclude': r'var\(--|color-mix\(',
    },
    {
        'name': 'missing-shadow-token',
        'pattern': r'\.(?:demo-card|panel|card|specimen|tmpl|rules-col|swatch|s1-sw|s3-card)\{[^}]+\}',
        'check_missing': r'var\(--shadow',
        'message': 'Container class missing var(--shadow) — depth picker won\'t affect it',
    },
    {
        'name': 'missing-cr-token',
        'pattern': r'\.(?:demo-card|panel|card|specimen|tmpl|rules-col|swatch|bg-preview|s1-sw|s3-card)\{[^}]+\}',
        'check_missing': r'var\(--cr',
        'message': 'Container class missing var(--cr) — corners picker won\'t affect it',
    },
    {
        'name': 'missing-pad-token',
        'pattern': r'\.(?:demo-card|panel|card|specimen|rules-col|swatch|s1-sw|s3-card)\{[^}]+\}',
        'check_missing': r'var\(--pad',
        'message': 'Container class missing var(--pad) — density picker won\'t affect it',
    },
    {
        'name': 'missing-gap-token',
        'pattern': r'\.(?:surface-grid|two-col|palette|rules-grid|templates-grid|row|s3-grid|s1-swatches|s1-ctas|s6-ctas)\{[^}]+\}',
        'check_missing': r'var\(--gap',
        'message': 'Grid class missing var(--gap) — density picker won\'t affect it',
    },
    {
        'name': 'inline-hardcoded-hex',
        'pattern': r'style="[^"]*(?:background|color|border):[^"]*#[0-9a-fA-F]{3,8}',
        'message': 'Inline style with hardcoded hex color — use var(--tp-primary/--tp-secondary/--tp-accent/--tp-tertiary)',
        'exclude': r'var\(--|color-mix\(',
    },
    {
        'name': 'svg-hardcoded-fill',
        'pattern': r'\bfill="(#[0-9a-fA-F]{3,8})"',
        'message': 'SVG fill="{match}" hardcoded — use fill="currentColor" or fill="var(--tp-accent)" so palette switching works',
        'exclude': r'fill="none"|fill="currentColor"|fill="var\(',
    },
    {
        'name': 'svg-hardcoded-stroke',
        'pattern': r'\bstroke="(#[0-9a-fA-F]{3,8})"',
        'message': 'SVG stroke="{match}" hardcoded — use stroke="currentColor" or stroke="var(--tp-primary)"',
        'exclude': r'stroke="none"|stroke="currentColor"|stroke="var\(',
    },
    {
        'name': 'missing-token-sentinels',
        'check_sentinels': ['__PRIMARY__', '__SECONDARY__', '__TERTIARY__', '__ACCENT__',
                           '__TEMPLATE_CSS__', '__SLIDE_CARDS__', '__SHADER_SCRIPT__',
                           '__SHADER_VERTEX__', '__SHADER_FRAGMENT__', '__NAME__',
                           '__CORNER_RADIUS__', '__PADDING__', '__GAP__', '__SHADOW__',
                           '__EASING_NAME__', '__EASING_VALUE__'],
        'only_files': ['design.html'],
    },
])

def lint(path):
    with open(path) as f:
        content = f.read()

    errors = []
    lines = content.split('\n')

    # Extract CSS blocks (between <style> tags)
    css_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    css = '\n'.join(css_blocks)

    basename = os.path.basename(path)
    for rule in RULES:
        # Sentinel check (only for design.html, not summary.html)
        if 'check_sentinels' in rule:
            if 'only_files' in rule and basename not in rule['only_files']:
                continue
            for sentinel in rule['check_sentinels']:
                if sentinel not in content:
                    errors.append(f"MISSING SENTINEL: {sentinel} not found in template")
            continue

        # Missing-property check on matched selectors (skip @media re-declarations)
        if 'check_missing' in rule:
            seen = set()
            pat = rule.get('_re') or re.compile(rule['pattern'])
            miss = rule.get('_re_miss') or re.compile(rule['check_missing'])
            for m in pat.finditer(css):
                block = m.group(0)
                selector = block.split('{')[0].strip()
                if selector in seen:
                    continue
                seen.add(selector)
                if not miss.search(block):
                    errors.append(f"{rule['name']}: {selector} — {rule['message']}")
            continue

        # Pattern match check
        pat = rule.get('_re') or re.compile(rule['pattern'])
        excl = rule.get('_re_ex')
        for i, line in enumerate(lines, 1):
            if excl and excl.search(line):
                continue
            for m in pat.finditer(line):
                msg = rule['message'].replace('{match}', m.group(1) if m.groups() else m.group(0))
                errors.append(f"L{i} {rule['name']}: {msg}")

    return errors

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 lint-design-html.py <path>")
        sys.exit(1)

    errors = lint(sys.argv[1])
    if errors:
        print(f"\n{len(errors)} issue(s) found:\n")
        for e in errors:
            print(f"  ⚠ {e}")
        sys.exit(1)
    else:
        print("✓ No issues found")
        sys.exit(0)
