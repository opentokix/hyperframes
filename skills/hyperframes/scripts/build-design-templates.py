#!/usr/bin/env python3
"""Generate design.html for each template by reading its CSS tokens.

The template's own design system (fonts, colors, borders, shadows, spacing)
becomes the page's visual language. Same HTML structure, CSS derived from tokens.

Usage:
    python3 build-design-templates.py [templates-dir]
"""
import re, os, sys, json


def parse_root_vars(css):
    """Extract :root CSS custom properties into a dict."""
    m = re.search(r':root\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', css, re.DOTALL)
    if not m:
        return {}
    block = m.group(1)
    props = {}
    for pm in re.finditer(r'--([\w-]+)\s*:\s*([^;]+);', block):
        props[pm.group(1)] = pm.group(2).strip()
    return props


def classify_scheme(props):
    """Determine if template is dark or light based on bg color."""
    bg = props.get('tp-secondary', props.get('c-bg', '#000000'))
    bg = re.search(r'#([0-9a-fA-F]{6})', bg)
    if bg:
        r = int(bg.group(1)[:2], 16)
        return 'dark' if r < 128 else 'light'
    return 'dark'


def extract_fonts(props):
    """Extract font families from template tokens."""
    fonts = {}
    for key in ['f-display', 'f-heading', 'f-head', 'f-body', 'f-mono']:
        if key in props:
            val = props[key]
            fm = re.search(r'"([^"]+)"', val)
            if fm:
                fonts[key] = fm.group(1)
    return fonts


def extract_border_style(props):
    """Classify border treatment."""
    border = props.get('border', '')
    shadow = props.get('shadow', props.get('shadow-sm', ''))
    if '4px' in border or '3px' in border:
        return 'heavy'
    if '1px' in border:
        return 'hairline'
    if shadow and 'px' in shadow and 'blur' not in shadow.lower():
        return 'offset'
    return 'subtle'


def extract_radius(props):
    """Get corner radius."""
    r = props.get('radius', props.get('radius-sm', '0'))
    m = re.search(r'(\d+)', r)
    return int(m.group(1)) if m else 0


def generate_page_css(scheme, fonts, border_style, radius, props):
    """Generate the page design CSS from template tokens."""
    is_dark = scheme == 'dark'
    heavy = border_style == 'heavy'

    disp = fonts.get('f-display', fonts.get('f-heading', fonts.get('f-head', 'system-ui')))
    body = fonts.get('f-body', 'system-ui')
    mono = fonts.get('f-mono', 'monospace')

    if border_style == 'heavy':
        border_rule = '4px solid var(--black,var(--secondary))'
        shadow_rule = '8px 8px 0 var(--black,var(--secondary))'
        shadow_sm = '4px 4px 0 var(--black,var(--secondary))'
        swatch_hover = 'transform:translate(-3px,-3px);box-shadow:11px 11px 0 var(--black,var(--secondary))'
        card_shadow = shadow_rule
    elif border_style == 'hairline':
        border_rule = '1px solid var(--hairline)'
        shadow_rule = 'none'
        shadow_sm = 'none'
        swatch_hover = 'transform:translateY(-4px)'
        card_shadow = '0 12px 36px rgba(0,0,0,.35)'
    else:
        border_rule = '1px solid rgba(128,128,128,.15)'
        shadow_rule = '0 4px 16px rgba(0,0,0,.12)'
        shadow_sm = '0 2px 8px rgba(0,0,0,.08)'
        swatch_hover = 'transform:translateY(-3px);box-shadow:0 8px 24px rgba(0,0,0,.15)'
        card_shadow = shadow_rule

    r = f'{radius}px' if radius > 0 else '0'

    MINUS = '\\2212'
    CHECK = '\\2713'
    CROSS = '\\2717'
    MDASH = '\\2014'

    css = f"""*,*::before,*::after{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:var(--secondary)}}
body{{color:var(--primary);font:400 14px/1.6 "{mono}",monospace;-webkit-font-smoothing:antialiased;overflow-x:hidden}}
::selection{{background:var(--accent);color:var(--secondary)}}

#design-bg{{position:fixed;inset:0;width:100%;height:100%;z-index:-2;opacity:{'.55' if is_dark else '.85'};pointer-events:none}}
#bg-veil{{position:fixed;inset:0;z-index:-1;pointer-events:none;background:{'radial-gradient(ellipse at 30% 20%,transparent 0%,var(--secondary) 75%)' if is_dark else 'none'}}}

.rail{{position:fixed;top:0;left:0;right:0;height:{'44px' if is_dark else '56px'};display:flex;align-items:center;justify-content:space-between;padding:0 var(--pad-x);background:{'color-mix(in srgb,var(--secondary) 78%,transparent)' if is_dark else 'var(--primary)'};{'backdrop-filter:blur(14px);' if is_dark else ''}border-bottom:{border_rule};{'box-shadow:' + shadow_sm + ';' if border_style == 'heavy' else ''}z-index:100;font:500 {'11' if is_dark else '12'}px/1 "{mono}",monospace;letter-spacing:.{'14' if is_dark else '06'}em;text-transform:uppercase}}
.rail .brand{{color:var(--accent);display:inline-flex;align-items:center;gap:10px;font:{'900 14px/1' if is_dark else '400 22px/1'} "{disp}",sans-serif}}
.rail .brand .dot{{width:{'9' if is_dark else '22'}px;height:{'9' if is_dark else '22'}px;background:var(--accent);{'border:3px solid var(--secondary);transform:rotate(-6deg)' if border_style == 'heavy' else ''}}}
.rail nav{{display:flex;gap:{'28' if is_dark else '6'}px}}
.rail nav a{{color:{'var(--primary)' if is_dark else 'var(--secondary)'};text-decoration:none;{'padding:6px 10px;border:2px solid transparent;' if border_style == 'heavy' else ''}transition:all .15s}}
.rail nav a:hover{{color:var(--accent){';background:var(--accent);border-color:var(--secondary)' if border_style == 'heavy' else ''}}}
@media(max-width:880px){{.rail nav{{display:none}}}}

section{{position:relative;padding:var(--pad-y) var(--pad-x)}}
.section-head{{display:grid;grid-template-columns:{'11em' if border_style == 'heavy' else '9em'} 1fr;gap:clamp(24px,4vw,56px);align-items:{'end' if border_style == 'heavy' else 'baseline'};{'border-top:' + border_rule + ';padding-top:28px;' if border_style != 'heavy' else ''}margin-bottom:clamp(36px,5vh,64px)}}
.section-head .num{{font:{'600' if border_style == 'heavy' else '500'} 12px/1 "{mono}",monospace;letter-spacing:.{'1' if border_style == 'heavy' else '18'}em;text-transform:uppercase;color:var(--accent){';display:inline-block;border:3px solid var(--secondary);background:var(--primary);padding:6px 14px;box-shadow:' + shadow_sm + ';justify-self:start;transform:rotate(-3deg)' if border_style == 'heavy' else ''}}}
.section-head h2{{font:{'400' if border_style == 'heavy' else '900'} clamp({'48px,8vw,128px' if border_style == 'heavy' else '36px,6vw,84px'})/.{'88' if border_style == 'heavy' else '92'} "{disp}",sans-serif;letter-spacing:-.0{'1' if border_style == 'heavy' else '35'}em;margin:0;text-transform:{'uppercase' if border_style == 'heavy' else 'lowercase'}}}
.section-head .lede{{grid-column:2;max-width:60ch;margin-top:18px;font-size:15px;line-height:1.6{'color:var(--primary);opacity:.65' if is_dark else ''}}}

.cover{{{'background:var(--accent);color:var(--secondary)' if is_dark else 'background:var(--primary);color:var(--secondary)'}}};min-height:100vh;padding:{'80px' if is_dark else '110px'} var(--pad-x) {'48px' if is_dark else '60px'};display:{'grid;grid-template-rows:auto 1fr auto' if is_dark else 'flex;flex-direction:column;justify-content:center'}}}
.cover-headline{{{'align-self:end;' if is_dark else ''}margin:0;font:900 clamp({'80px,17vw,280px' if is_dark else '64px,13vw,200px'})/.{'82' if is_dark else '88'} "{disp}",sans-serif;letter-spacing:-.04em;text-transform:{'lowercase' if is_dark else 'uppercase'}}}
.cover-foot{{margin-top:{'48' if is_dark else '56'}px;padding-top:{'20' if is_dark else '28'}px;border-top:{border_rule};display:grid;grid-template-columns:repeat(4,1fr);gap:24px}}
.cover-foot .cell{{display:flex;flex-direction:column;gap:6px}}
.cover-foot .k{{font:500 {'10' if is_dark else '11'}px/1 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase;opacity:.55}}
.cover-foot .v{{font:500 13px/1.4 "{mono}",monospace}}
.cover-foot .v.big{{font:800 {'28' if is_dark else '32'}px/1 "{disp}",sans-serif;letter-spacing:-.02em}}
@media(max-width:760px){{.cover-foot{{grid-template-columns:1fr 1fr}}}}

.manifesto{{padding:clamp(60px,9vh,120px) var(--pad-x);{'border-top:' + border_rule + ';border-bottom:' + border_rule if border_style == 'heavy' else 'border-bottom:' + border_rule}}}
.manifesto-grid{{display:grid;grid-template-columns:{'11em' if border_style == 'heavy' else '9em'} 1fr;gap:clamp(24px,4vw,56px);align-items:start;max-width:1400px;margin:0 auto}}
.manifesto-grid .num{{font:500 12px/1 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--accent)}}
.manifesto p{{font:{'800' if border_style == 'heavy' else '700'} clamp(28px,{'4' if border_style == 'heavy' else '3.8'}vw,{'60' if border_style == 'heavy' else '56'}px)/1.05 "{disp}",sans-serif;letter-spacing:-.025em;max-width:22ch;margin:0;text-transform:{'uppercase' if border_style == 'heavy' else 'lowercase'}}}
.manifesto p em{{font-style:normal;{'background:var(--secondary);color:var(--accent);padding:0 .15em' if border_style == 'heavy' else 'color:var(--accent)'}}}

.palette{{display:grid;grid-template-columns:repeat(4,1fr);gap:{'24px' if border_style == 'heavy' else '2px'};{'background:rgba(128,128,128,.1);border:' + border_rule if border_style != 'heavy' else ''}}}
.swatch{{{'border:' + border_rule + ';box-shadow:' + shadow_rule + ';' if border_style == 'heavy' else ''}padding:28px 24px;aspect-ratio:3/4;display:flex;flex-direction:column;justify-content:space-between;border-radius:{r};transition:all .2s}}
.swatch:hover{{{swatch_hover}}}
.swatch .role{{font:500 11px/1 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase{';padding:4px 8px;background:var(--primary);border:2px solid var(--secondary);align-self:flex-start' if border_style == 'heavy' else ''}}}
.swatch .name{{font:900 clamp(28px,3.4vw,48px)/.92 "{disp}",sans-serif;letter-spacing:-.025em;text-transform:{'uppercase' if border_style == 'heavy' else 'lowercase'};margin-top:auto}}
.swatch .hex{{font:500 12px/1 "{mono}",monospace;margin-top:8px}}
.swatch .usage{{font:400 11px/1.5 "{mono}",monospace;margin-top:6px;opacity:.65}}
.swatch--primary{{background:var(--primary);color:var(--secondary)}}
.swatch--secondary{{background:var(--secondary);color:var(--primary)}}
.swatch--tertiary{{background:var(--tertiary);color:var(--primary)}}
.swatch--accent{{background:var(--accent);color:var(--secondary)}}
@media(max-width:880px){{.palette{{grid-template-columns:repeat(2,1fr)}}}}

.specimen{{{'border:' + border_rule + ';background:var(--primary);color:var(--secondary);box-shadow:' + shadow_rule + ';' if border_style == 'heavy' else ''}max-width:1400px;margin:0 auto;display:flex;flex-direction:column}}
.spec-row{{display:grid;grid-template-columns:{'12em' if border_style == 'heavy' else '11em'} 1fr;gap:{'28' if border_style == 'heavy' else '32'}px;padding:28px {'32px' if border_style == 'heavy' else '0'};border-{'bottom:3px solid var(--secondary)' if border_style == 'heavy' else 'top:' + border_rule};align-items:baseline}}
.spec-row:{'last-child' if border_style == 'heavy' else 'first-child'}{{border:0;padding-top:0}}
.spec-row .meta{{font:500 11px/1.4 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase;display:flex;flex-direction:column;gap:4px;{'color:var(--secondary);opacity:.6' if border_style == 'heavy' else 'color:var(--primary);opacity:.4'}}}
.spec-row .meta b{{color:var(--accent);font:400 22px/1 "{disp}",sans-serif}}
.spec-display{{font:900 clamp(56px,10vw,152px)/.88 "{disp}",sans-serif;letter-spacing:-.04em;text-transform:{'uppercase' if border_style == 'heavy' else 'lowercase'}}}
.spec-h1{{font:800 clamp(40px,7vw,104px)/.9 "{disp}",sans-serif;letter-spacing:-.03em;text-transform:{'uppercase' if border_style == 'heavy' else 'lowercase'}}}
.spec-h2{{font:700 clamp(28px,4.2vw,64px)/1 "{disp}",sans-serif;letter-spacing:-.02em}}
.spec-lead{{font:500 clamp(18px,2vw,26px)/1.45 "{disp}",sans-serif}}
.spec-body{{font:{'500' if border_style == 'heavy' else '400'} 17px/1.65 "{disp}",sans-serif;max-width:60ch}}
.spec-label{{font:{'600' if border_style == 'heavy' else '500'} 13px/1 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase{';color:var(--accent)' if is_dark else ''}}}

.surface-grid{{display:grid;grid-template-columns:1.1fr 1fr;gap:{'32' if border_style == 'heavy' else '48'}px;max-width:1400px;margin:0 auto}}
@media(max-width:880px){{.surface-grid{{grid-template-columns:1fr}}}}
.demo-card{{background:var(--primary);color:var(--secondary);border-radius:{r};padding:{'32' if border_style == 'heavy' else '28'}px;{'border:' + border_rule + ';' if border_style == 'heavy' else ''}box-shadow:{card_shadow};display:flex;flex-direction:column;gap:18px}}
.demo-card .tag{{align-self:flex-start;font:{'600' if border_style == 'heavy' else '500'} {'11' if border_style == 'heavy' else '10'}px/1 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase;{'border:3px solid var(--secondary);background:var(--accent);padding:6px 14px;box-shadow:' + shadow_sm if border_style == 'heavy' else 'color:var(--accent);border:1px solid var(--accent);padding:4px 8px'}}}
.demo-card h3{{margin:0;font:900 36px/1 "{disp}",sans-serif;letter-spacing:-.02em;text-transform:{'uppercase' if border_style == 'heavy' else 'lowercase'}}}
.demo-card p{{margin:0;font:400 15px/1.6 "{disp}",sans-serif;opacity:.7}}
.tokens{{list-style:none;padding:0;margin:0;{'border:' + border_rule + ';background:var(--primary);color:var(--secondary);box-shadow:' + shadow_rule if border_style == 'heavy' else 'border-top:' + border_rule}}}
.tokens li{{display:grid;grid-template-columns:1fr auto auto;gap:18px;align-items:center;padding:18px {'24px' if border_style == 'heavy' else '0'};border-bottom:{'3px solid var(--secondary)' if border_style == 'heavy' else border_rule}}}
.tokens li:last-child{{border:0}}
.tokens .name{{font:{'600' if border_style == 'heavy' else '500'} 12px/1 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase{'' if border_style == 'heavy' else ';opacity:.6'}}}
.tokens .val{{font:800 20px/1 "{disp}",sans-serif}}
.tokens .bar{{height:{'8' if border_style == 'heavy' else '6'}px;background:var(--accent){';border:2px solid var(--secondary)' if border_style == 'heavy' else ''}}}

.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:{'32' if border_style == 'heavy' else '48'}px;max-width:1400px;margin:0 auto}}
@media(max-width:880px){{.two-col{{grid-template-columns:1fr}}}}
.panel{{{'background:var(--primary);border:' + border_rule + ';box-shadow:' + shadow_rule if border_style == 'heavy' else 'border:' + border_rule + ';background:color-mix(in srgb,var(--secondary) 70%,transparent)'}}};padding:{'32' if border_style == 'heavy' else '36'}px;border-radius:{r};display:flex;flex-direction:column;gap:22px}}
.panel .label-row{{font:500 11px/1 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--accent){';display:inline-block;align-self:flex-start;background:var(--accent);color:var(--secondary);border:3px solid var(--secondary);padding:6px 14px;box-shadow:' + shadow_sm if border_style == 'heavy' else ''}}}
.panel h4{{margin:0;font:{'400 40px/1' if border_style == 'heavy' else '800 32px/1'} "{disp}",sans-serif;text-transform:{'uppercase' if border_style == 'heavy' else 'lowercase'}}}
.panel p{{margin:0;font:{'500 14px/1.65' if border_style == 'heavy' else '400 13px/1.7'} "{disp}",sans-serif;{'max-width:42ch' if border_style == 'heavy' else 'opacity:.65;max-width:38ch'}}}

.bg-preview{{border:{border_rule};{'box-shadow:' + shadow_rule + ';' if border_style == 'heavy' else ''}aspect-ratio:4/3;position:relative;overflow:hidden;background:var(--secondary);border-radius:{r}}}
.bg-preview canvas{{width:100%;height:100%;display:block}}
.bg-preview .badge{{position:absolute;bottom:{'14' if border_style == 'heavy' else '12'}px;left:{'14' if border_style == 'heavy' else '12'}px;font:{'600' if border_style == 'heavy' else '500'} {'11' if border_style == 'heavy' else '10'}px/1 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase;{'color:var(--secondary);background:var(--accent);border:3px solid var(--secondary);padding:6px 12px' if border_style == 'heavy' else 'background:color-mix(in srgb,var(--secondary) 75%,transparent);padding:6px 10px;backdrop-filter:blur(8px)'}}}

details.code-block{{{'background:var(--primary);border:3px solid var(--secondary)' if border_style == 'heavy' else 'border:' + border_rule + ';background:color-mix(in srgb,var(--secondary) 60%,transparent)'}}};margin-top:12px;border-radius:{r}}}
details.code-block summary{{cursor:pointer;padding:{'12px 16px' if border_style == 'heavy' else '14px 18px'};list-style:none;font:{'600' if border_style == 'heavy' else '500'} {'12' if border_style == 'heavy' else '11'}px/1 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase;{'display:flex;justify-content:space-between;background:var(--accent)' if border_style == 'heavy' else 'color:var(--accent);display:flex;justify-content:space-between'}}}
details.code-block summary::-webkit-details-marker{{display:none}}
details.code-block summary::after{{content:"+";font:900 18px/1 "{disp}",sans-serif{';color:var(--accent)' if border_style != 'heavy' else ''}}}
details.code-block[open] summary::after{{content:"{MINUS}"}}
details.code-block pre{{margin:0;padding:16px;border-top:{'3px solid var(--secondary)' if border_style == 'heavy' else border_rule};font:11px/1.6 "{mono}",monospace;{'background:var(--primary);color:var(--secondary);opacity:.7' if border_style == 'heavy' else 'color:var(--primary);opacity:.65;background:transparent'};overflow-x:auto;white-space:pre-wrap;word-break:break-word;max-height:320px;overflow-y:auto}}

.rules-grid{{display:grid;grid-template-columns:1fr 1fr;gap:{'32' if border_style == 'heavy' else '48'}px;max-width:1400px;margin:0 auto}}
@media(max-width:880px){{.rules-grid{{grid-template-columns:1fr}}}}
.rules-col{{{'border:' + border_rule + ';padding:32px;box-shadow:' + shadow_rule if border_style == 'heavy' else ''}}}
.rules-col.do{{{'background:var(--accent);transform:rotate(-.6deg)' if border_style == 'heavy' else ''}}}
.rules-col.dont{{{'background:var(--primary);color:var(--secondary);transform:rotate(.6deg)' if border_style == 'heavy' else ''}}}
.rules-col h3{{font:{'400 64px/1' if border_style == 'heavy' else '900 56px/1'} "{disp}",sans-serif;letter-spacing:-.03em;margin:0 0 {'24' if border_style == 'heavy' else '28'}px;text-transform:{'uppercase' if border_style == 'heavy' else 'lowercase'}}}
.rules-col.do h3{{color:var(--accent)}}
.rules-col.dont h3{{opacity:.4}}
.rules-col ul{{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:{'12' if border_style == 'heavy' else '0'}px}}
.rules-col li{{display:grid;grid-template-columns:2em 1fr;gap:{'12' if border_style == 'heavy' else '8'}px;padding:{'14px 16px' if border_style == 'heavy' else '16px 0'};{'background:var(--primary);border:3px solid var(--secondary);box-shadow:' + shadow_sm + ';' if border_style == 'heavy' else 'border-top:' + border_rule + ';'}font:500 {'15px/1.45' if border_style == 'heavy' else '18px/1.45'} "{disp}",sans-serif}}
.rules-col li::before{{font:{'900 22px/1' if border_style == 'heavy' else '800 22px/1.2'} "{disp}",sans-serif;align-self:{'center' if border_style == 'heavy' else 'start'};{'text-align:center;width:1.6em;height:1.6em;display:flex;align-items:center;justify-content:center;border:2px solid var(--secondary)' if border_style == 'heavy' else ''}}}
.rules-col.do li::before{{content:"{CHECK if border_style == 'heavy' else '+'}";{'background:var(--accent)' if border_style == 'heavy' else 'color:var(--accent)'}}}
.rules-col.dont li::before{{content:"{CROSS if border_style == 'heavy' else MDASH}";opacity:.4}}

.templates-wrap{{{'background:var(--accent);border-top:' + border_rule + ';border-bottom:' + border_rule if border_style == 'heavy' else 'background:color-mix(in srgb,var(--secondary) 96%,var(--accent))'}}}
.templates-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:{'28' if border_style == 'heavy' else '24'}px;max-width:1400px;margin:0 auto}}
@media(max-width:1100px){{.templates-grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:720px){{.templates-grid{{grid-template-columns:1fr}}}}
.tmpl{{background:{'var(--primary)' if border_style == 'heavy' else 'var(--secondary)'};{'border:' + border_rule + ';box-shadow:' + shadow_rule if border_style == 'heavy' else 'border:' + border_rule};overflow:hidden;border-radius:{r};transition:all .2s}}
.tmpl:hover{{{swatch_hover.replace('translate(-3px,-3px)', 'translate(-3px,-3px)') if border_style == 'heavy' else 'border-color:var(--accent);transform:translateY(-2px)'}}}
.tmpl-thumb{{width:100%;aspect-ratio:16/9;overflow:hidden;position:relative;background:{'var(--secondary)' if border_style == 'heavy' else '#050505'};border-bottom:{'3px solid var(--secondary)' if border_style == 'heavy' else border_rule}}}
.tmpl-thumb .scale-wrap{{width:1920px;height:1080px;transform-origin:top left}}
.tmpl-foot{{display:flex;justify-content:space-between;padding:{'12px 16px' if border_style == 'heavy' else '14px 18px'};font:{'600' if border_style == 'heavy' else '500'} {'12' if border_style == 'heavy' else '11'}px/1 "{mono}",monospace;letter-spacing:.{'08' if border_style == 'heavy' else '14'}em;text-transform:uppercase}}
.tmpl-foot .idx{{{'background:var(--accent);border:2px solid var(--secondary);padding:2px 8px' if border_style == 'heavy' else 'color:var(--accent)'}}}

footer.endcap{{background:{'var(--secondary);color:var(--primary)' if border_style == 'heavy' else 'var(--accent);color:var(--secondary)'};padding:80px var(--pad-x) 60px;display:grid;grid-template-columns:1fr auto;gap:48px;align-items:end}}
footer.endcap .endmark{{font:900 clamp({'72px,14vw,220px' if border_style == 'heavy' else '60px,13vw,220px'})/.85 "{disp}",sans-serif;letter-spacing:-.04em;text-transform:{'uppercase' if border_style == 'heavy' else 'lowercase'};margin:0}}
footer.endcap .meta{{font:500 12px/2 "{mono}",monospace;letter-spacing:.1em;text-transform:uppercase;opacity:.6;text-align:right}}
footer.endcap .meta b{{opacity:1;color:var(--accent)}}"""
    return css


def build_design_template(slug, props, scheme, fonts, border_style, radius, meta):
    """Build the full design.html template with __TOKEN__ sentinels."""
    disp = fonts.get('f-display', fonts.get('f-heading', fonts.get('f-head', 'system-ui')))
    mono = fonts.get('f-mono', 'monospace')
    is_dark = scheme == 'dark'

    page_css = generate_page_css(scheme, fonts, border_style, radius, props)

    font_families = set()
    for f in fonts.values():
        font_families.add(f)
    font_link_parts = []
    for f in sorted(font_families):
        if f in ('system-ui', 'monospace', 'sans-serif', 'serif'):
            continue
        font_link_parts.append(f'family={f.replace(" ", "+")}:wght@300;400;500;600;700;800;900')
    font_link = '&'.join(font_link_parts)

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>__NAME__ — Design System</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?{font_link}__FONT_LINK_EXTRA__&display=swap" rel="stylesheet" />
<script type="importmap">
{{"imports":{{"three":"https://cdn.jsdelivr.net/npm/three@0.167.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.167.0/examples/jsm/"}}}}
</script>
<style id="ds-tokens">
:root{{
  --primary:__PRIMARY__; --secondary:__SECONDARY__; --tertiary:__TERTIARY__; --accent:__ACCENT__;
  --hairline:color-mix(in srgb,var(--primary) 12%,transparent);
  --f-disp:"{disp}",sans-serif; --f-mono:"{mono}",monospace;
  --pad-x:clamp(24px,5vw,88px); --pad-y:clamp(40px,6vh,100px);
}}
</style>
<style>
{page_css}
</style>
<style id="template-css">
__TEMPLATE_CSS__
</style>
</head>
<body>
<canvas id="design-bg"></canvas>
<div id="bg-veil"></div>

<div class="rail">
  <div class="brand"><span class="dot"></span>__NAME__</div>
  <nav><a href="#palette">01</a><a href="#type">02</a><a href="#surface">03</a><a href="#motion">04</a><a href="#background">05</a><a href="#guidelines">06</a><a href="#templates">07</a></nav>
</div>

<header class="cover">
  <h1 class="cover-headline">__NAME_LINE1____NAME_LINE2__.</h1>
  <div class="cover-foot">
    <div class="cell"><span class="k">Template</span><span class="v">{slug}</span></div>
    <div class="cell"><span class="k">Type</span><span class="v big">{disp}</span></div>
    <div class="cell"><span class="k">Accent</span><span class="v">__ACCENT_LABEL__</span></div>
    <div class="cell"><span class="k">Doc</span><span class="v">07 sections · __SLIDE_COUNT__ templates</span></div>
  </div>
</header>

<section class="manifesto">
  <div class="manifesto-grid">
    <div class="num">&#8212; Manifesto</div>
    <p>{meta.get('tagline', 'design is <em>intent</em>.')}</p>
  </div>
</section>

<section id="palette">
  <div class="section-head">
    <div class="num">01 &#8212; Palette</div>
    <h2>{'Four Tokens.' if border_style == 'heavy' else 'four colors.'}</h2>
    <p class="lede">__PALETTE_LEDE__</p>
  </div>
  <div class="palette">
    <div class="swatch swatch--primary"><div class="role">Primary</div><div><div class="name">__PRIMARY_NAME__</div><div class="hex">__PRIMARY__</div><div class="usage">{'Ink on dark.' if is_dark else 'Canvas.'}</div></div></div>
    <div class="swatch swatch--secondary"><div class="role">Secondary</div><div><div class="name">__SECONDARY_NAME__</div><div class="hex">__SECONDARY__</div><div class="usage">{'Canvas.' if is_dark else 'Ink.'}</div></div></div>
    <div class="swatch swatch--tertiary"><div class="role">Tertiary</div><div><div class="name">__TERTIARY_NAME__</div><div class="hex">__TERTIARY__</div><div class="usage">Muted. Borders.</div></div></div>
    <div class="swatch swatch--accent"><div class="role">Accent</div><div><div class="name">__ACCENT_NAME__</div><div class="hex">__ACCENT__</div><div class="usage">Signal. Reserved.</div></div></div>
  </div>
</section>

<section id="type">
  <div class="section-head">
    <div class="num">02 &#8212; Typography</div>
    <h2>{'Big. Heavy.' if border_style == 'heavy' else 'type scale.'}</h2>
  </div>
  <div class="specimen">
    <div class="spec-row"><div class="meta"><span>Display</span><b>{disp}</b></div><div class="spec-display">{'HELLO WORLD.' if border_style == 'heavy' else 'hello world.'}</div></div>
    <div class="spec-row"><div class="meta"><span>H1</span><b>{disp}</b></div><div class="spec-h1">{'CHAPTER ONE' if border_style == 'heavy' else 'chapter one'}</div></div>
    <div class="spec-row"><div class="meta"><span>H2</span><b>{disp}</b></div><div class="spec-h2">Slide headlines.</div></div>
    <div class="spec-row"><div class="meta"><span>Body</span><b>{disp}</b></div><p class="spec-body">Body copy below 24px is forbidden in video compositions.</p></div>
    <div class="spec-row"><div class="meta"><span>Label</span><b>{mono}</b></div><div class="spec-label">// chrome · labels · metadata</div></div>
  </div>
</section>

<section id="surface">
  <div class="section-head">
    <div class="num">03 &#8212; Surface</div>
    <h2>{'Borders. Shadows.' if border_style == 'heavy' else 'corners. depth.'}</h2>
  </div>
  <div class="surface-grid">
    <div class="demo-card">
      <span class="tag">// example</span>
      <h3>{'EXAMPLE CARD.' if border_style == 'heavy' else 'example card.'}</h3>
      <p>Configured corners, padding, shadow.</p>
    </div>
    <ul class="tokens">
      <li><span class="name">Corners</span><span class="val">__CORNER_RADIUS__</span><span class="bar" style="width:8px"></span></li>
      <li><span class="name">Padding</span><span class="val">__PADDING__</span><span class="bar" style="width:32px"></span></li>
      <li><span class="name">Gap</span><span class="val">__GAP__</span><span class="bar" style="width:32px"></span></li>
      <li><span class="name">Elevation</span><span class="val">__ELEVATION__</span><span class="bar" style="width:18px"></span></li>
      <li><span class="name">Density</span><span class="val">__DENSITY__</span><span class="bar" style="width:48px"></span></li>
    </ul>
  </div>
</section>

<section id="motion">
  <div class="section-head">
    <div class="num">04 &#8212; Motion</div>
    <h2>__EASING_HEADLINE__</h2>
    <p class="lede">__EASING_LEDE__</p>
  </div>
  <div class="two-col">
    <div class="panel">
      <div class="label-row">// easing</div>
      <h4>__EASING_NAME__</h4>
      <p>__EASING_DESC__</p>
      <pre>__EASING_VALUE__</pre>
    </div>
    <div class="panel">
      <div class="label-row">// duration</div>
      <h4>__DURATION_DEFAULT__</h4>
      <p>__DURATION_DESC__</p>
      <pre>__DURATION_VALUES__</pre>
    </div>
  </div>
</section>

<section id="background">
  <div class="section-head">
    <div class="num">05 &#8212; Background</div>
    <h2>__BG_HEADLINE__</h2>
    <p class="lede">__BG_LEDE__</p>
  </div>
  <div class="two-col">
    <div class="bg-preview"><canvas id="bg-preview-canvas"></canvas><span class="badge">// __BG_BADGE__</span></div>
    <div style="display:flex;flex-direction:column;gap:8px">
      <ul class="tokens" style="border-top:none">
        <li><span class="name">Geometry</span><span class="val">__BG_TYPE__</span><span class="bar" style="width:36px"></span></li>
        <li><span class="name">Density</span><span class="val">__BG_DENSITY__</span><span class="bar" style="width:42px"></span></li>
        <li><span class="name">Speed</span><span class="val">__BG_SPEED__</span><span class="bar" style="width:18px"></span></li>
        <li><span class="name">Strength</span><span class="val">__BG_STRENGTH__</span><span class="bar" style="width:52px"></span></li>
        <li><span class="name">Grain</span><span class="val">__BG_GRAIN__</span><span class="bar" style="width:24px"></span></li>
      </ul>
      <details class="code-block"><summary>// shader config</summary>
<pre>__SHADER_CONFIG__</pre>
      </details>
      <details class="code-block"><summary>// vertex shader</summary>
<pre id="vtx-src">__SHADER_VERTEX__</pre>
      </details>
      <details class="code-block"><summary>// fragment shader</summary>
<pre id="frg-src">__SHADER_FRAGMENT__</pre>
      </details>
    </div>
  </div>
</section>

<section id="guidelines">
  <div class="section-head">
    <div class="num">06 &#8212; Guidelines</div>
    <h2>{"Do. Don’t." if border_style == 'heavy' else "do and don’t."}</h2>
  </div>
  <div class="rules-grid">
    <div class="rules-col do"><h3>{'DO.' if border_style == 'heavy' else 'do.'}</h3><ul>__DOS__</ul></div>
    <div class="rules-col dont"><h3>{"DON'T." if border_style == 'heavy' else "don't."}</h3><ul>__DONTS__</ul></div>
  </div>
</section>

<section id="templates" class="templates-wrap">
  <div class="section-head">
    <div class="num">07 &#8212; Templates</div>
    <h2>__SLIDE_COUNT_WORD__<br/>{'Frames.' if border_style == 'heavy' else 'frames.'}</h2>
  </div>
  <div class="templates-grid" id="templates-grid"></div>
</section>

<template id="tmpl-source">
__SLIDE_CARDS__
</template>

<footer class="endcap">
  <h2 class="endmark">{'THE END.' if border_style == 'heavy' else 'end.'}</h2>
  <div class="meta">
    <div><b>__NAME__</b> · v1</div>
    <div>{disp} / {mono}</div>
    <div>__DATE__</div>
  </div>
</footer>

<script>
(function(){{
  document.getElementById('templates-grid').appendChild(document.getElementById('tmpl-source').content.cloneNode(true));
  function rescale(){{document.querySelectorAll('.tmpl-thumb').forEach(t=>{{const w=t.querySelector('.scale-wrap');if(w)w.style.transform='scale('+(t.clientWidth/1920)+')'}})}}
  addEventListener('load',rescale);addEventListener('resize',rescale);requestAnimationFrame(rescale);
  if(document.fonts&&document.fonts.ready)document.fonts.ready.then(rescale);
}})();
</script>

__SHADER_SCRIPT__

</body>
</html>'''


def main():
    templates_dir = sys.argv[1] if len(sys.argv) > 1 else "skills/hyperframes/templates/presentations"
    index_path = os.path.join(os.path.dirname(templates_dir), "index.json")

    with open(index_path) as f:
        index = json.load(f)

    for t in index['templates']:
        slug = t['slug']
        summary_path = os.path.join(templates_dir, slug, 'summary.html')
        design_path = os.path.join(templates_dir, slug, 'design.html')

        if not os.path.exists(summary_path):
            continue

        # Skip hand-crafted designs
        if os.path.exists(design_path):
            size = os.path.getsize(design_path)
            if size > 5000:
                print(f"  {slug}: SKIP (hand-crafted, {size//1024}K)")
                continue

        with open(summary_path) as f:
            summary = f.read()

        styles = re.findall(r'<style[^>]*>(.*?)</style>', summary, re.DOTALL)
        css = '\n'.join(styles)
        props = parse_root_vars(css)
        scheme = classify_scheme(props)
        fonts = extract_fonts(props)
        border_style = extract_border_style(props)
        radius = extract_radius(props)

        meta = {'tagline': t.get('tagline', 'design is <em>intent</em>.')}

        design = build_design_template(slug, props, scheme, fonts, border_style, radius, meta)

        with open(design_path, 'w') as f:
            f.write(design)

        print(f"  {slug}: {scheme} / {border_style} / r{radius} / {list(fonts.values())[:2]}")

    print(f"\nGenerated design.html for {len(index['templates'])} templates")


if __name__ == '__main__':
    main()
