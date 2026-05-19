#!/usr/bin/env python3
"""Build design-picker.html with template data, moodboard data, and optional design.md integration.

Usage:
    python3 build-design-picker.py \
        --template skills/hyperframes/templates/design-picker.html \
        --templates-dir /tmp/beautiful-html-templates/templates \
        --presentations-dir skills/hyperframes/templates/presentations \
        --output .hyperframes/pick-design.html \
        < picker-data.json

If design.md or DESIGN.md exists in cwd, parses it and generates a
'user-design' template card that appears first in the picker grid with
auto-advance to Phase 2.

picker-data.json must contain:
    {
      "architectures": [...], "palettes": [...], "typepairs": [...],
      "moodboards": [...], "prompt": {...}, "prompt_text": {...},
      "prompt_desc": "..."
    }
"""
import json, sys, os, re, shutil, argparse


def parse_design_md(path):
    """Extract brand name, colors, and font substitute from a design.md file."""
    with open(path) as f:
        md = f.read()

    def find_color(pattern):
        m = re.search(pattern, md, re.IGNORECASE)
        return m.group(1) if m else None

    primary = find_color(r'colors\.primary\}.*?(#[0-9a-fA-F]{6})') or \
              find_color(r'primary[^#]{0,40}(#[0-9a-fA-F]{6})')
    canvas = find_color(r'canvas[^#]{0,40}(#[0-9a-fA-F]{6})')
    ink = find_color(r'ink\}`[^#]*[—–-]\s*`?(#[0-9a-fA-F]{6})') or \
          find_color(r'\bink\b[^#]{0,40}(#[0-9a-fA-F]{6})')
    muted = find_color(r'charcoal[^#]{0,40}(#[0-9a-fA-F]{6})') or \
            find_color(r'graphite[^#]{0,40}(#[0-9a-fA-F]{6})') or \
            find_color(r'muted[^#]{0,40}(#[0-9a-fA-F]{6})')

    p_text = ink or '#1a1a1a'
    p_bg = canvas or '#ffffff'
    p_muted = muted or '#636363'
    p_accent = primary or '#024ad8'

    font_match = re.search(r'single-family.*?:\s*\*?\*?([^*(]+?)(?:\*\*|\s*\()', md, re.IGNORECASE)
    font_name = font_match.group(1).strip() if font_match else None

    subs = re.findall(r'^\s*[-*]\s*\*\*([^*]+)\*\*\s+at weights', md, re.MULTILINE)
    font_sub = subs[0].strip() if subs else 'Inter'

    brand_match = re.search(r'(\w+)\s+reads like', md)
    if not brand_match:
        brand_match = re.search(r"(\w+)'s\s+\w+\s+surfaces?\b", md)
    if not brand_match:
        brand_match = re.search(r'^##?\s+(.+)', md, re.MULTILINE)
    brand_name = brand_match.group(1).strip() if brand_match else 'Your Design'
    if brand_name.lower() in ('overview', 'colors', 'typography', 'layout'):
        brand_name = 'Your Design'

    return {
        'brand': brand_name,
        'primary': p_text,
        'secondary': p_bg,
        'tertiary': p_muted,
        'accent': p_accent,
        'font': font_sub,
        'font_original': font_name,
    }


def generate_user_design(design_md_data, output_dir, base_design_html):
    """Generate template.html and design.html for the user-design virtual template."""
    d = design_md_data
    os.makedirs(output_dir, exist_ok=True)

    bg = d["secondary"]
    fg = d["primary"]
    mt = d["tertiary"]
    ac = d["accent"]
    fn = d["font"]
    br = d["brand"]
    fnlink = fn.replace(" ", "+")

    template_html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<link href="https://fonts.googleapis.com/css2?family={fnlink}:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root {{
  --bg:{bg}; --fg:{fg}; --mt:{mt}; --ac:{ac};
  --tp-primary:{bg}; --tp-secondary:{fg}; --tp-tertiary:{mt}; --tp-accent:{ac};
  --hair:color-mix(in srgb,{fg} 12%,transparent);
  --surf:color-mix(in srgb,{bg} 94%,{fg});
  --dim:color-mix(in srgb,{fg} 55%,{bg});
  --cr:12px; --pad:20px; --gap:16px; --shadow:0 2px 8px rgba(0,0,0,.06);
}}
*,*::before,*::after {{ box-sizing:border-box }}
html,body {{ margin:0;padding:0;background:var(--bg);color:var(--fg);font-family:'{fn}',sans-serif }}
.slide {{ width:100%;height:100vh;display:flex;flex-direction:column;justify-content:center;padding:100px 120px;position:relative;overflow:hidden }}
.card {{ background:var(--surf);border:1px solid var(--hair);border-radius:var(--cr);padding:var(--pad);display:flex;flex-direction:column;gap:calc(var(--gap) * 0.75);box-shadow:var(--shadow) }}
.btn {{ padding:14px 28px;border-radius:calc(var(--cr) * 0.33);font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;border:none }}
.btn-fill {{ background:var(--ac);color:var(--bg) }}
.btn-ghost {{ background:transparent;color:var(--fg);border:1px solid var(--hair) }}

/* ── Slide 1: Hero ── */
.s1 {{ padding:0 }}
.s1-inner {{ display:grid;grid-template-columns:1.1fr 1fr;height:100%;position:relative }}
.s1-left {{ display:flex;flex-direction:column;justify-content:center;padding:100px 100px 100px 120px;gap:20px;z-index:1 }}
.s1-overline {{ font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;color:var(--ac) }}
.s1-headline {{ font-size:clamp(72px,9vw,130px);font-weight:700;line-height:.88;margin:0;letter-spacing:-.04em }}
.s1-headline .ac {{ color:var(--ac) }}
.s1-sub {{ font-size:20px;line-height:1.45;color:var(--dim);max-width:32ch;margin:0 }}
.s1-ctas {{ display:flex;gap:var(--gap);margin-top:12px }}
.s1-cta {{ padding:14px 32px;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;border-radius:calc(var(--cr) * 0.33);border:none }}
.s1-cta-fill {{ background:var(--ac);color:var(--bg) }}
.s1-cta-ghost {{ background:transparent;color:var(--fg);border:1px solid var(--hair) }}
.s1-right {{ position:relative;display:flex;align-items:center;justify-content:center }}
.s1-deco {{ position:absolute;width:80px;background:var(--ac);transform:skewX(-18deg) }}
.s1-deco-l {{ left:-20px;top:12%;height:55%;opacity:.15 }}
.s1-deco-r {{ right:-20px;bottom:12%;height:40%;opacity:.1 }}
.s1-swatches {{ display:grid;grid-template-columns:1fr 1fr;gap:var(--gap);width:80%;max-width:400px;z-index:1 }}
.s1-sw {{ border-radius:var(--cr);padding:var(--pad);display:flex;flex-direction:column;justify-content:flex-end;gap:3px;min-height:110px;box-shadow:var(--shadow) }}
.s1-sw span:first-child {{ font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;opacity:.6 }}
.s1-sw span:last-child {{ font-size:14px;font-weight:500;font-family:monospace }}

/* ── Slide 2: Palette ── */

/* ── Slide 3: Type specimen ── */
.s3-display {{ font-size:clamp(80px,12vw,140px);font-weight:700;line-height:.85;letter-spacing:-.03em }}
.s3-h1 {{ font-size:48px;font-weight:600;line-height:1;margin-top:20px }}
.s3-body {{ font-size:20px;line-height:1.5;color:var(--dim);max-width:52ch;margin-top:14px }}
.s3-label {{ font-size:12px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--ac);margin-top:20px }}
.s3-meta {{ display:flex;gap:32px;margin-top:24px;padding-top:20px;border-top:1px solid var(--hair) }}
.s3-meta-item {{ display:flex;flex-direction:column;gap:4px }}
.s3-meta-item span:first-child {{ font-size:10px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:var(--dim) }}
.s3-meta-item span:last-child {{ font-size:15px;font-weight:500 }}

/* ── Slide 2: Feature reveal ── */
.s2 {{ padding:0 }}
.s2-inner {{ display:grid;grid-template-columns:1fr 1.1fr;height:100% }}
.s2-photo {{ background:var(--surf);position:relative;display:flex;align-items:center;justify-content:center }}
.s2-photo-placeholder {{ width:70%;aspect-ratio:4/3;background:linear-gradient(135deg,color-mix(in srgb,var(--ac) 8%,var(--surf)),var(--surf));border-radius:var(--cr);border:1px solid var(--hair);box-shadow:var(--shadow) }}
.s2-photo-badge {{ position:absolute;top:32px;left:32px;padding:6px 14px;background:var(--ac);color:var(--bg);font-size:12px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;border-radius:calc(var(--cr) * 0.25) }}
.s2-content {{ display:flex;flex-direction:column;justify-content:center;padding:80px;gap:var(--gap) }}
.s2-eyebrow {{ font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;color:var(--ac) }}
.s2-title {{ font-size:44px;font-weight:600;line-height:1.05;margin:0 }}
.s2-body {{ font-size:18px;line-height:1.5;color:var(--dim);max-width:38ch;margin:0 }}
.s2-specs {{ display:flex;gap:var(--gap);margin-top:12px;padding-top:var(--pad);border-top:1px solid var(--hair) }}
.s2-spec {{ display:flex;flex-direction:column;gap:2px }}
.s2-spec-val {{ font-size:20px;font-weight:600 }}
.s2-spec-label {{ font-size:11px;color:var(--dim);letter-spacing:.04em }}

/* ── Slide 3: Data grid ── */
.s3-grid {{ display:grid;grid-template-columns:repeat(3,1fr);gap:var(--gap);margin-top:32px }}
.s3-card {{ background:var(--surf);border:1px solid var(--hair);border-radius:var(--cr);padding:var(--pad);display:flex;flex-direction:column;gap:8px;box-shadow:var(--shadow) }}
.s3-card-num {{ font-size:56px;font-weight:700;line-height:1;color:var(--ac) }}
.s3-card-label {{ font-size:14px;color:var(--dim);letter-spacing:.04em }}
.s3-card-body {{ font-size:14px;line-height:1.4;color:var(--dim);margin-top:auto;padding-top:12px;border-top:1px solid var(--hair) }}
.s3-bar {{ display:flex;gap:2px;margin-top:8px }}
.s3-bar span {{ height:4px;border-radius:2px }}

/* ── Slide 4: Split content + stats ── */
.s4 {{ padding:0 }}
.s4-inner {{ display:grid;grid-template-columns:1fr 1fr;height:100% }}
.s4-left {{ background:var(--surf);display:flex;flex-direction:column;justify-content:center;padding:80px;gap:20px }}
.s4-right {{ display:grid;grid-template-rows:1fr 1fr;gap:0 }}
.s4-stat {{ display:flex;flex-direction:column;justify-content:center;align-items:center;gap:8px;border-bottom:1px solid var(--hair) }}
.s4-stat-num {{ font-size:72px;font-weight:700;line-height:1;color:var(--ac) }}
.s4-stat-label {{ font-size:13px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:var(--dim) }}

/* ── Slide 5: Quote / proof ── */
.s5 {{ align-items:center;text-align:center }}
.s5-mark {{ font-size:120px;line-height:.6;color:var(--ac);opacity:.3;margin-bottom:16px }}
.s5-quote {{ font-size:clamp(28px,4vw,44px);font-weight:500;line-height:1.35;max-width:20ch;margin:0 }}
.s5-attr {{ font-size:14px;color:var(--dim);margin-top:24px;letter-spacing:.04em }}
.s5-rule {{ width:60px;height:3px;background:var(--ac);margin-top:20px;border-radius:2px }}

/* ── Slide 6: Dark closing ── */
.s6 {{ background:var(--fg);color:var(--bg);align-items:center;text-align:center }}
.s6 .s1-overline {{ color:var(--ac) }}
.s6-headline {{ font-size:clamp(56px,8vw,96px);font-weight:700;line-height:.9;margin:16px 0 0;letter-spacing:-.02em }}
.s6-headline .ac {{ color:var(--ac) }}
.s6-sub {{ font-size:20px;line-height:1.45;color:color-mix(in srgb,var(--bg) 60%,var(--fg));max-width:40ch;margin:16px 0 0 }}
.s6-ctas {{ display:flex;gap:var(--gap);margin-top:28px }}
</style>
</head>
<body>

<!-- Hook: brand hero with accent decorations -->
<section class="slide s1" data-slide="1">
  <div class="s1-inner">
    <div class="s1-left">
      <div class="s1-overline">{br} · Design System</div>
      <h1 class="s1-headline">{br}<span class="ac">.</span></h1>
      <p class="s1-sub">Visual identity for video compositions. Palette, type, motion, and surface tokens — configured and ready to render.</p>
      <div class="s1-ctas">
        <div class="s1-cta s1-cta-fill">Explore System</div>
        <div class="s1-cta s1-cta-ghost">Export</div>
      </div>
    </div>
    <div class="s1-right">
      <div class="s1-deco s1-deco-l"></div>
      <div class="s1-deco s1-deco-r"></div>
      <div class="s1-swatches">
        <div class="s1-sw" style="background:var(--fg);color:var(--bg)"><span>Primary</span><span class="sw-hex-val" data-role="fg">{fg}</span></div>
        <div class="s1-sw" style="background:var(--bg);color:var(--fg);border:1px solid var(--hair)"><span>Secondary</span><span class="sw-hex-val" data-role="bg">{bg}</span></div>
        <div class="s1-sw" style="background:var(--mt);color:var(--bg)"><span>Tertiary</span><span class="sw-hex-val" data-role="mt">{mt}</span></div>
        <div class="s1-sw" style="background:var(--ac);color:var(--bg);grid-column:1/-1"><span>Accent</span><span class="sw-hex-val" data-role="ac">{ac}</span></div>
      </div>
    </div>
  </div>
</section>

<!-- Feature reveal: product/announcement frame -->
<section class="slide s2" data-slide="2">
  <div class="s2-inner">
    <div class="s2-photo">
      <div class="s2-photo-placeholder"></div>
      <div class="s2-photo-badge">New</div>
    </div>
    <div class="s2-content">
      <div class="s2-eyebrow">{br} · Featured</div>
      <h2 class="s2-title">The product headline goes here at scale</h2>
      <p class="s2-body">Supporting copy describes the feature, announcement, or product at comfortable reading size for video.</p>
      <div class="s2-specs">
        <div class="s2-spec"><span class="s2-spec-val" style="color:var(--ac)">4K</span><span class="s2-spec-label">Resolution</span></div>
        <div class="s2-spec"><span class="s2-spec-val">12hr</span><span class="s2-spec-label">Battery</span></div>
        <div class="s2-spec"><span class="s2-spec-val">1.2kg</span><span class="s2-spec-label">Weight</span></div>
      </div>
      <div style="display:flex;gap:var(--gap);margin-top:var(--gap)">
        <div class="s1-cta s1-cta-fill">Learn More</div>
        <div class="s1-cta s1-cta-ghost">Compare</div>
      </div>
    </div>
  </div>
</section>

<!-- Data grid: metrics/stats frame -->
<section class="slide" data-slide="3">
  <div style="font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;color:var(--ac)">{br} · By the Numbers</div>
  <h2 style="font-size:48px;font-weight:600;line-height:1;margin:12px 0 0">Key metrics<span style="color:var(--ac)">.</span></h2>
  <div class="s3-grid">
    <div class="s3-card"><div class="s3-card-num">10B+</div><div class="s3-card-label">Devices shipped</div><div class="s3-bar"><span style="background:var(--ac);flex:3"></span><span style="background:var(--hair);flex:1"></span></div><div class="s3-card-body">Across consumer, enterprise, and education markets worldwide.</div></div>
    <div class="s3-card"><div class="s3-card-num">175</div><div class="s3-card-label">Countries served</div><div class="s3-bar"><span style="background:var(--ac);flex:2.5"></span><span style="background:var(--hair);flex:1"></span></div><div class="s3-card-body">Global operations with localized supply chains.</div></div>
    <div class="s3-card"><div class="s3-card-num">99.9%</div><div class="s3-card-label">Uptime SLA</div><div class="s3-bar"><span style="background:var(--ac);flex:4"></span><span style="background:var(--hair);flex:0.1"></span></div><div class="s3-card-body">Enterprise-grade reliability for managed fleets.</div></div>
  </div>
</section>

<!-- Composition: split frame with stats -->
<section class="slide s4" data-slide="4">
  <div class="s4-inner">
    <div class="s4-left">
      <div style="font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:1.2px;color:var(--ac)">03 · Composition</div>
      <h2 style="font-size:48px;font-weight:600;line-height:1;margin:12px 0 0">Split frame<span style="color:var(--ac)">.</span></h2>
      <p style="font-size:18px;line-height:1.45;color:var(--dim);margin:12px 0 0;max-width:36ch">Content on left, data on right. The accent color marks exactly one focal element per frame — the stat number.</p>
      <div style="display:flex;gap:var(--gap);margin-top:var(--gap)">
        <div class="s1-cta s1-cta-fill">Primary</div>
        <div class="s1-cta s1-cta-ghost">Secondary</div>
      </div>
    </div>
    <div class="s4-right">
      <div class="s4-stat"><div class="s4-stat-num">10B+</div><div class="s4-stat-label">Devices shipped</div></div>
      <div class="s4-stat" style="border:0"><div class="s4-stat-num">175</div><div class="s4-stat-label">Countries served</div></div>
    </div>
  </div>
</section>

<!-- Quote / testimonial frame -->
<section class="slide s5" data-slide="5">
  <div class="s5-mark">"</div>
  <p class="s5-quote">Design at the speed of decision.</p>
  <div class="s5-attr">— {br} Design System</div>
  <div class="s5-rule"></div>
</section>

<!-- Dark closing frame -->
<section class="slide s6" data-slide="6">
  <div class="s1-overline">{br}</div>
  <h2 class="s6-headline">Ready to<br>build<span class="ac">.</span></h2>
  <p class="s6-sub">Tokens configured. Export the design system and start composing video frames.</p>
  <div class="s6-ctas">
    <div class="s1-cta s1-cta-fill">Create DESIGN.html</div>
    <div class="s1-cta s1-cta-ghost" style="border-color:color-mix(in srgb,var(--bg) 20%,var(--fg));color:var(--bg)">Browse Templates</div>
  </div>
</section>

</body>
</html>'''

    with open(os.path.join(output_dir, 'template.html'), 'w') as f:
        f.write(template_html)

    # Copy design.html and summary.html only if they don't already exist.
    # If the agent crafted them, don't overwrite with the generic template.
    presentations_parent = os.path.dirname(os.path.dirname(base_design_html))
    dst_design = os.path.join(output_dir, 'design.html')
    if not os.path.exists(dst_design):
        user_design_src = os.path.join(presentations_parent, 'user-design', 'design.html')
        if os.path.exists(user_design_src):
            shutil.copy2(user_design_src, dst_design)
        else:
            shutil.copy2(base_design_html, dst_design)
    dst_summary = os.path.join(output_dir, 'summary.html')
    if not os.path.exists(dst_summary):
        user_summary_src = os.path.join(presentations_parent, 'user-design', 'summary.html')
        if os.path.exists(user_summary_src):
            shutil.copy2(user_summary_src, dst_summary)


def main():
    parser = argparse.ArgumentParser(description='Build design-picker.html')
    parser.add_argument('--template', required=True, help='Path to design-picker.html template')
    parser.add_argument('--templates-dir', required=True, help='Path to beautiful-html-templates/templates')
    parser.add_argument('--presentations-dir', default=None, help='Path to presentations dir with design.html files')
    parser.add_argument('--output', required=True, help='Output path for built picker')
    args = parser.parse_args()

    data = json.load(sys.stdin)

    index_path = os.path.join(os.path.dirname(args.templates_dir), 'index.json')
    with open(index_path) as f:
        index = json.load(f)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    from importlib import util as imp_util
    build_tp_path = os.path.join(script_dir, 'build-template-picker.py')
    spec = imp_util.spec_from_file_location('build_tp', build_tp_path)
    build_tp = imp_util.module_from_spec(spec)
    spec.loader.exec_module(build_tp)

    # Parse design.md
    design_md_data = None
    for name in ('design.md', 'DESIGN.md'):
        if os.path.exists(name):
            design_md_data = parse_design_md(name)
            print(f"Parsed {name}: {design_md_data['brand']} — "
                  f"{design_md_data['secondary']}/{design_md_data['primary']}/"
                  f"{design_md_data['accent']}/{design_md_data['tertiary']} — "
                  f"font: {design_md_data['font']}")
            break

    # Generate user-design template
    if design_md_data:
        output_parent = os.path.dirname(os.path.abspath(args.output))
        ud_dir = os.path.join(output_parent, '..', 'templates', 'user-design')
        ud_dir = os.path.normpath(ud_dir)
        base_design = None
        if args.presentations_dir:
            base_design = os.path.join(args.presentations_dir, 'block-frame', 'design.html')
        if not base_design or not os.path.exists(base_design):
            base_design = os.path.join(os.path.dirname(args.template), 'presentations', 'block-frame', 'design.html')
        if os.path.exists(base_design):
            generate_user_design(design_md_data, ud_dir, base_design)
            print(f"Generated {ud_dir}/ (template.html + design.html)")
        else:
            print(f"Warning: base design.html not found at {base_design}")
            design_md_data = None

    # Extract template data
    templates = []
    for t in index['templates']:
        html_path = os.path.join(args.templates_dir, t['slug'], 'template.html')
        if not os.path.exists(html_path):
            continue
        preview = build_tp.extract_preview(html_path, t['slug'])
        templates.append({
            'slug': t['slug'],
            'name': t['name'],
            'tagline': t['tagline'],
            'scheme': t['scheme'],
            'density': t['density'],
            'colorVars': build_tp.extract_color_vars(html_path),
            'preview_html': preview
        })

    # Prepend user-design
    if design_md_data:
        d = design_md_data
        ud_html = os.path.join(output_parent, '..', 'templates', 'user-design', 'template.html')
        ud_html = os.path.normpath(ud_html)
        preview = build_tp.extract_preview(ud_html, 'user-design') if os.path.exists(ud_html) else ''
        templates.insert(0, {
            'slug': 'user-design',
            'name': d['brand'] + ' Design',
            'tagline': 'Your provided design system from design.md',
            'scheme': 'light' if d['secondary'].lower() in ('#ffffff', '#fff') else 'dark',
            'density': 'normal',
            'colorVars': [],
            '_provided': True,
            'preview_html': preview,
        })

    # Read template
    with open(args.template) as f:
        html = f.read()

    # Inject placeholders
    html = html.replace('__ARCHITECTURES_JSON__', json.dumps(data['architectures']))
    html = html.replace('__PALETTES_JSON__', json.dumps(data['palettes']))
    html = html.replace('__TYPEPAIRS_JSON__', json.dumps(data['typepairs']))
    html = html.replace('__MOODBOARDS_JSON__', json.dumps(data['moodboards']))
    html = html.replace('__PROMPT_JSON__', json.dumps(data['prompt']))
    html = html.replace('__TEMPLATES_JSON__', json.dumps(templates))
    html = html.replace('__PROMPT_TEXT_JSON__', json.dumps(data['prompt_text']))
    html = html.replace('__PROMPT_DESC__', data.get('prompt_desc', ''))

    # Set base href relative to output location so template paths resolve correctly
    output_dir = os.path.dirname(os.path.abspath(args.output))
    project_root = os.getcwd()
    rel = os.path.relpath(project_root, output_dir)
    base_href = rel.rstrip('/') + '/' if rel != '.' else './'
    html = html.replace('__BASE_HREF__', base_href)

    # Inject DESIGN_MD
    dm_json = json.dumps(design_md_data) if design_md_data else 'null'
    html = html.replace(
        'var PROMPT_TEXT = ',
        f'var DESIGN_MD = {dm_json};\n      var PROMPT_TEXT = '
    )

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        f.write(html)

    print(f"Written {args.output} ({len(templates)} templates, design_md={'yes' if design_md_data else 'no'})")


if __name__ == '__main__':
    main()
