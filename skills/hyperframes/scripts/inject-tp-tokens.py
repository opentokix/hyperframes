#!/usr/bin/env python3
"""Inject --tp-* palette tokens into template :root blocks.

For each template:
1. Read :root CSS variables
2. Classify into 4 roles: primary (text), secondary (bg), tertiary (muted), accent (vibrant)
3. Add --tp-* declarations with template defaults
4. Rewire only the role vars to reference --tp-* with fallbacks

Does NOT touch: variant colors, fonts, hardcoded hex in rules, or any non-:root CSS.
"""
import re, os, sys, colorsys

def hex_to_hsl(hex_str):
    hex_str = hex_str.strip().lstrip('#')
    if len(hex_str) == 3:
        hex_str = hex_str[0]*2 + hex_str[1]*2 + hex_str[2]*2
    r, g, b = int(hex_str[0:2], 16)/255, int(hex_str[2:4], 16)/255, int(hex_str[4:6], 16)/255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h*360, s*100, l*100

def parse_root_vars(css):
    root_match = re.search(r':root\s*\{([^}]+)\}', css, re.DOTALL)
    if not root_match:
        return [], ""
    block = root_match.group(1)
    vars_list = []
    for m in re.finditer(r'(--[\w-]+)\s*:\s*([^;]+);', block):
        name, val = m.group(1), m.group(2).strip()
        hex_match = re.search(r'#[0-9a-fA-F]{3,8}', val)
        if hex_match:
            vars_list.append((name, hex_match.group(), val, m.start(), m.end()))
    return vars_list, root_match

def classify_vars(vars_list, scheme):
    if not vars_list:
        return {}

    analyzed = []
    for name, hex_val, full_val, start, end in vars_list:
        h, s, l = hex_to_hsl(hex_val)
        analyzed.append({
            'name': name, 'hex': hex_val, 'full_val': full_val,
            'h': h, 's': s, 'l': l, 'start': start, 'end': end
        })

    # Name-based hints (strongest signal)
    name_hints = {
        'secondary': ['bg', 'paper', 'canvas', 'ground', 'cream', 'white', 'void', 'deep-navy', 'dark-void'],
        'primary': ['fg', 'ink', 'text', 'dark', 'black'],
        'accent': ['accent', 'sun', 'neon', 'pink', 'red', 'green', 'coral', 'blue', 'cyan', 'yellow', 'ember'],
        'tertiary': ['muted', 'gray', 'grey', 'line', 'border', 'light', 'soft', 'haze'],
    }

    roles = {}
    used = set()

    # First pass: strong name matches
    for role, hints in name_hints.items():
        if role in roles:
            continue
        for v in analyzed:
            if v['name'] in used:
                continue
            vname = v['name'].lower().replace('--', '').replace('c-', '')
            # Exact or prefix match
            for hint in hints:
                if vname == hint or vname.startswith(hint + '-') or vname.startswith(hint):
                    # For bg/secondary: prefer the main background (not variants like bg-alt, bg-2)
                    if role == 'secondary' and any(x in vname for x in ['alt', 'deep', 'dark', '2', '3']):
                        continue
                    # For primary/fg: prefer the main text color
                    if role == 'primary' and any(x in vname for x in ['2', '3', 'alt']):
                        continue
                    # For accent: prefer first saturated match
                    if role == 'accent' and v['s'] < 20:
                        continue
                    roles[role] = v
                    used.add(v['name'])
                    break
            if role in roles:
                break

    # Second pass: luminance-based for missing roles
    if 'secondary' not in roles:
        # BG is usually darkest (dark scheme) or lightest (light scheme)
        candidates = [v for v in analyzed if v['name'] not in used]
        if candidates:
            if scheme == 'dark':
                bg = min(candidates, key=lambda v: v['l'])
            else:
                bg = max(candidates, key=lambda v: v['l'])
            roles['secondary'] = bg
            used.add(bg['name'])

    if 'primary' not in roles:
        candidates = [v for v in analyzed if v['name'] not in used]
        if candidates:
            if scheme == 'dark':
                fg = max(candidates, key=lambda v: v['l'])
            else:
                fg = min(candidates, key=lambda v: v['l'])
            roles['primary'] = fg
            used.add(fg['name'])

    if 'accent' not in roles:
        candidates = [v for v in analyzed if v['name'] not in used]
        if candidates:
            accent = max(candidates, key=lambda v: v['s'])
            if accent['s'] > 15:
                roles['accent'] = accent
                used.add(accent['name'])

    if 'tertiary' not in roles:
        candidates = [v for v in analyzed if v['name'] not in used]
        if candidates:
            if 'accent' in roles:
                ac_h = roles['accent']['h']
                def hue_dist(h1, h2):
                    d = abs(h1 - h2)
                    return min(d, 360 - d)
                # Prefer a muted color near the accent hue
                tertiary = min(candidates, key=lambda v: hue_dist(v['h'], ac_h) + v['s'] * 0.5)
            else:
                tertiary = min(candidates, key=lambda v: v['s'])
            roles['tertiary'] = tertiary
            used.add(tertiary['name'])

    return roles

def inject_tokens_into_css(css_content, scheme):
    vars_list, root_match = parse_root_vars(css_content)
    if not vars_list or not root_match:
        return None, None
    roles = classify_vars(vars_list, scheme)
    if len(roles) < 2:
        return None, None

    tp_lines = ["\n    /* Palette tokens — override to re-theme */"]
    for role in ['primary', 'secondary', 'tertiary', 'accent']:
        if role in roles:
            tp_lines.append(f"    --tp-{role}: {roles[role]['hex']};")
    tp_lines.append("    /* Surface tokens */")
    tp_lines.append("    --tp-radius: 4px;")
    tp_lines.append("    --tp-padding: 20px;")
    tp_lines.append("    --tp-gap: 16px;")
    tp_lines.append("    --tp-shadow: none;")
    tp_block = "\n".join(tp_lines) + "\n"

    root_block = root_match.group(1)
    new_block = root_block
    for role, v in roles.items():
        old_decl_pattern = re.compile(
            re.escape(v['name']) + r'\s*:\s*' + re.escape(v['full_val']) + r'\s*;'
        )
        replacement = f"{v['name']}: var(--tp-{role}, {v['full_val']});"
        new_block = old_decl_pattern.sub(replacement, new_block, count=1)

    new_block = tp_block + new_block
    new_css = css_content[:root_match.start(1)] + new_block + css_content[root_match.end(1):]

    mapped = ", ".join(f"{r}={roles[r]['name']}" for r in ['primary','secondary','tertiary','accent'] if r in roles)
    return new_css, mapped

def inject_tokens(html_path, scheme='dark'):
    with open(html_path) as f:
        html = f.read()

    # Try inline CSS first
    new_css, mapped = inject_tokens_into_css(html, scheme)
    if new_css:
        with open(html_path, 'w') as f:
            f.write(new_css)
        return mapped

    # Try external styles.css in same directory
    css_path = os.path.join(os.path.dirname(html_path), 'styles.css')
    if os.path.exists(css_path):
        with open(css_path) as f:
            css = f.read()
        new_css, mapped = inject_tokens_into_css(css, scheme)
        if new_css:
            with open(css_path, 'w') as f:
                f.write(new_css)
            return mapped

    return False

def main():
    templates_dir = sys.argv[1] if len(sys.argv) > 1 else "skills/hyperframes/templates/presentations"
    index_path = os.path.join(os.path.dirname(templates_dir), "index.json")

    with open(index_path) as f:
        import json
        index = json.load(f)

    for t in index['templates']:
        html_path = os.path.join(templates_dir, t['slug'], 'template.html')
        if not os.path.exists(html_path):
            continue
        result = inject_tokens(html_path, t.get('scheme', 'dark'))
        if result:
            print(f"  ✓ {t['slug']}: {result}")
        else:
            print(f"  ✗ {t['slug']}: no :root vars found")

if __name__ == '__main__':
    main()
