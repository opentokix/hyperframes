#!/usr/bin/env python3
"""Convert presentation templates to use a standard CSS variable contract.

For each template:
1. Parse :root CSS variables to identify the palette
2. Classify each variable as bg/fg/accent/muted/surface/border by name+luminance
3. Replace ALL hardcoded hex colors throughout the entire HTML with var() references
4. Add a standard :root block with --tp-* variables
5. Map original variable definitions to use --tp-* tokens

Standard contract:
  --tp-bg, --tp-fg, --tp-ac, --tp-ac2, --tp-mt, --tp-surface, --tp-border
  --tp-hf (headline font), --tp-bf (body font), --tp-mf (mono font)
"""
import re, os, sys, json, colorsys

def hex_to_rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    if len(h) < 6:
        return (128, 128, 128)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

def luminance(r, g, b):
    return (r * 0.299 + g * 0.587 + b * 0.114) / 255 * 100

def saturation(r, g, b):
    _, s, _ = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    return s * 100

def classify_color(hex_val, var_name=""):
    """Classify a color by its role: bg, fg, ac, mt, surface, border."""
    r, g, b = hex_to_rgb(hex_val)
    lum = luminance(r, g, b)
    sat = saturation(r, g, b)
    vl = var_name.lower()

    # Name-based classification (highest priority)
    if re.search(r'accent|sun|ember|coral|pink|highlight|primary|active|brand|neon|red|orange|yellow|green|blue|violet|purple|magenta|cyan|teal', vl):
        return 'ac'
    if re.search(r'bg|paper|canvas|cream|bone|surface|white|offwhite|ivory', vl):
        if lum > 70:
            return 'bg'
        return 'surface'
    if re.search(r'fg|ink|text|dark|black', vl):
        return 'fg'
    if re.search(r'mute|gray|grey|secondary|subtle|soft|light', vl):
        return 'mt'
    if re.search(r'line|rule|border|divider|outline', vl):
        return 'border'

    # Luminance-based fallback
    if lum > 88:
        return 'bg'
    if lum < 15:
        return 'fg'
    if sat > 40:
        return 'ac'
    if lum > 55:
        return 'mt'
    return 'surface'

def process_template(html_path):
    with open(html_path) as f:
        html = f.read()

    # Extract :root block
    root_match = re.search(r':root\s*\{([^}]+)\}', html)
    if not root_match:
        return html, 0

    root_block = root_match.group(1)
    orig_vars = {}
    for m in re.findall(r'(--[\w-]+)\s*:\s*([^;]+)', root_block):
        orig_vars[m[0]] = m[1].strip()

    # Classify each variable
    var_roles = {}
    role_values = {'bg': [], 'fg': [], 'ac': [], 'mt': [], 'surface': [], 'border': []}

    for var_name, val in orig_vars.items():
        hex_match = re.search(r'#[0-9a-fA-F]{3,8}', val)
        if hex_match:
            role = classify_color(hex_match.group(), var_name)
            var_roles[var_name] = role
            role_values[role].append((var_name, hex_match.group()))

    # Pick the primary value for each role (first occurrence)
    primary = {}
    for role, vals in role_values.items():
        if vals:
            primary[role] = vals[0][1]

    if not primary.get('bg'):
        primary['bg'] = '#ffffff'
    if not primary.get('fg'):
        primary['fg'] = '#000000'
    if not primary.get('ac'):
        primary['ac'] = primary.get('fg', '#333333')
    if not primary.get('mt'):
        primary['mt'] = '#888888'

    # Find font variables and font-family declarations
    font_vars = {}
    headline_font = "system-ui"
    body_font = "system-ui"
    mono_font = "monospace"
    for var_name, val in orig_vars.items():
        vl = var_name.lower()
        if re.search(r'font|display|heading|body|mono|serif', vl) and '#' not in val:
            font_vars[var_name] = val
            clean_val = val.split(',')[0].strip().strip('"').strip("'")
            if re.search(r'display|heading|headline', vl):
                headline_font = clean_val
            elif re.search(r'body|text', vl):
                body_font = clean_val
            elif re.search(r'mono', vl):
                mono_font = clean_val

    # If no font vars found, try to extract from CSS font-family rules
    if not font_vars:
        font_matches = re.findall(r'font-family:\s*["\']?([^"\';\n,]+)', html)
        seen = set()
        for fm in font_matches:
            fm = fm.strip()
            if fm.lower() not in ('sans-serif', 'serif', 'monospace', 'system-ui', 'inherit', 'cursive') and fm not in seen:
                seen.add(fm)
                if not headline_font or headline_font == "system-ui":
                    headline_font = fm
                elif body_font == "system-ui":
                    body_font = fm

    # Build the --tp-* variable block
    tp_block = "\n  /* Template Picker configurable tokens */\n"
    tp_block += f"  --tp-bg: {primary.get('bg', '#fff')};\n"
    tp_block += f"  --tp-fg: {primary.get('fg', '#000')};\n"
    tp_block += f"  --tp-ac: {primary.get('ac', '#888')};\n"
    tp_block += f"  --tp-mt: {primary.get('mt', '#888')};\n"
    tp_block += f"  --tp-surface: {primary.get('surface', primary.get('bg', '#fff'))};\n"
    tp_block += f"  --tp-border: {primary.get('border', primary.get('mt', '#ccc'))};\n"
    tp_block += f'  --tp-hf: "{headline_font}";\n'
    tp_block += f'  --tp-bf: "{body_font}";\n'
    tp_block += f'  --tp-mf: "{mono_font}";\n'

    # Rewrite original variable definitions to reference --tp-* tokens
    new_root_block = root_block
    for var_name, role in var_roles.items():
        orig_val = orig_vars[var_name]
        tp_var = f"--tp-{role}"
        # Replace the value in the :root block
        pattern = re.escape(var_name) + r'\s*:\s*' + re.escape(orig_val)
        replacement = f"{var_name}: var({tp_var}, {orig_val})"
        new_root_block = re.sub(pattern, replacement, new_root_block, count=1)

    # Insert --tp-* block at start of :root
    new_root_block = tp_block + new_root_block

    # Replace the :root block
    html = html[:root_match.start(1)] + new_root_block + html[root_match.end(1):]

    # Build color map: known palette hex → var() reference
    color_map = {}
    for var_name, val in orig_vars.items():
        hex_match = re.search(r'#[0-9a-fA-F]{3,8}', val)
        if hex_match:
            hex_val = hex_match.group().lower()
            if len(hex_val) == 4:
                hex_val = '#' + hex_val[1]*2 + hex_val[2]*2 + hex_val[3]*2
            role = var_roles.get(var_name, 'ac')
            if hex_val not in color_map:
                color_map[hex_val] = f"var(--tp-{role})"

    replacements = 0
    # Split HTML at :root block boundary — only replace OUTSIDE :root
    root_end = html.find('}', html.find(':root'))
    if root_end > 0:
        before_root = html[:root_match.start()]
        root_section = html[root_match.start():root_end+1]
        after_root = html[root_end+1:]

        # Replace known palette colors
        for hex_val, var_ref in color_map.items():
            count = len(re.findall(re.escape(hex_val), after_root, re.IGNORECASE))
            if count > 0:
                after_root = re.sub(re.escape(hex_val), var_ref, after_root, flags=re.IGNORECASE)
                replacements += count

        # Find and replace remaining hardcoded hex colors not in palette
        remaining_hexes = re.findall(r'(?<!var\(--tp-)#[0-9a-fA-F]{3,6}(?![0-9a-fA-F])', after_root)
        for raw_hex in set(remaining_hexes):
            normalized = raw_hex.lower()
            if normalized in ('#fff', '#000', '#ffffff', '#000000'):
                continue
            if normalized in color_map:
                continue
            role = classify_color(raw_hex)
            var_ref = f"var(--tp-{role})"
            count = after_root.count(raw_hex)
            after_root = after_root.replace(raw_hex, var_ref)
            replacements += count

        # Replace hardcoded font-family declarations with var references
        # Match font-family: "SomeFont", fallback patterns
        if headline_font and headline_font != "system-ui":
            font_pattern = re.escape(f'"{headline_font}"') + r'|' + re.escape(f"'{headline_font}'") + r'|' + re.escape(headline_font)
            count = len(re.findall(font_pattern, after_root))
            if count > 0:
                after_root = re.sub(font_pattern, 'var(--tp-hf)', after_root)
                replacements += count

        if body_font and body_font != "system-ui" and body_font != headline_font:
            font_pattern = re.escape(f'"{body_font}"') + r'|' + re.escape(f"'{body_font}'") + r'|' + re.escape(body_font)
            count = len(re.findall(font_pattern, after_root))
            if count > 0:
                after_root = re.sub(font_pattern, 'var(--tp-bf)', after_root)
                replacements += count

        html = before_root + root_section + after_root

    # Add background layer variable for shader swap
    html = html.replace(
        '/* Template Picker configurable tokens */',
        '/* Template Picker configurable tokens */\n  --tp-bg-layer: none; /* set to shader canvas or gradient */'
    )

    return html, replacements

def main():
    templates_dir = sys.argv[1] if len(sys.argv) > 1 else "skills/hyperframes/templates/presentations"

    total = 0
    total_replacements = 0

    for slug in sorted(os.listdir(templates_dir)):
        html_path = os.path.join(templates_dir, slug, "template.html")
        if not os.path.isfile(html_path):
            continue

        html, replacements = process_template(html_path)

        with open(html_path, 'w') as f:
            f.write(html)

        total += 1
        total_replacements += replacements
        status = f"  {slug}: {replacements} color replacements"
        if replacements > 0:
            status += " ✓"
        print(status)

    print(f"\nProcessed {total} templates, {total_replacements} total color replacements")

if __name__ == '__main__':
    main()
