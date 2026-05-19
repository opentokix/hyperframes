#!/usr/bin/env python3
"""Replace {{placeholder}} tokens in summary.html with original text from template.html.

For each template:
1. Parse template.html to extract slides and their text content
2. Parse summary.html to find skeleton slides with {{placeholder}} tokens
3. Match by slide type class (slide--cover, slide--chapter, slide-1, etc.)
4. Replace {{headline}}, {{body}}, {{text}}, {{number}}, {{label}} with original text

Usage:
    python3 detokenize-summaries.py [templates-dir]
"""
import re, os, sys, json


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
    return 'slide' in cls.split()


def get_slides(html):
    """Extract slide sections from any template structure."""
    html_flat = re.sub(r'\s+', ' ', html)
    slides = []
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


def extract_texts(slide_html):
    """Extract text content from a slide's HTML, categorized by element class.

    Returns a list of (category, text) tuples in document order.
    Categories: 'headline', 'body', 'label', 'number', 'text'
    """
    texts = []
    # Match elements with text content: <tag ...class="...">text</tag>
    for m in re.finditer(r'(<[^>]+>)([^<]+)(</[^>]+>)', slide_html):
        tag_open = m.group(1)
        text = m.group(2).strip()
        if not text or text.startswith('{'):
            continue
        cls = tag_open.lower()
        if any(c in cls for c in ['display', '"h1', '"h2', '"h3', 'heading', 'title']):
            cat = 'headline'
        elif any(c in cls for c in ['lead', 'body', 'desc', 'lede', 'meta']):
            cat = 'body'
        elif any(c in cls for c in ['label', 'kicker', 'caption', 'muted', 'note', 'source']):
            cat = 'label'
        elif any(c in cls for c in ['stat-value', 'num', 'value', 'v "']):
            cat = 'number'
        elif len(text) < 30:
            cat = 'text'
        else:
            cat = 'body'
        texts.append((cat, text))
    return texts


def replace_tokens_in_skeleton(skeleton_html, original_texts):
    """Replace {{placeholder}} tokens in skeleton HTML with original text.

    Walks through the skeleton finding {{placeholder}} tokens and replaces them
    with the corresponding text from the original, matched by category and order.
    """
    # Build queues per category
    queues = {}
    for cat, text in original_texts:
        queues.setdefault(cat, []).append(text)

    # Track position in each queue
    pos = {cat: 0 for cat in queues}

    def replacer(m):
        tag_open = m.group(1)
        token = m.group(2)
        tag_close = m.group(3)

        # Map token to category
        token_name = token.strip('{}')
        if token_name not in pos:
            # No original text for this category
            return m.group(0)

        idx = pos[token_name]
        if idx < len(queues[token_name]):
            replacement = queues[token_name][idx]
            pos[token_name] = idx + 1
            return f'{tag_open}{replacement}{tag_close}'
        else:
            # Ran out of original texts, keep the token
            return m.group(0)

    result = re.sub(
        r'(<[^>]+>)(\{\{(?:headline|body|text|number|label|value|accent|meta)\}\})(</[^>]+>)',
        replacer,
        skeleton_html
    )
    return result


def process_template(template_dir, slug):
    """Process a single template: detokenize summary.html using template.html."""
    template_path = os.path.join(template_dir, 'template.html')
    summary_path = os.path.join(template_dir, 'summary.html')

    if not os.path.exists(template_path) or not os.path.exists(summary_path):
        return False, "missing files"

    with open(template_path) as f:
        template_html = f.read()
    with open(summary_path) as f:
        summary_html = f.read()

    # Check if summary has any tokens to replace
    if '{{' not in summary_html:
        return False, "no tokens"

    # Extract slides from template.html (originals with real text)
    template_slides = get_slides(template_html)

    # Build a map: slide_type -> list of (category, text) tuples
    # Use first occurrence of each type (same as build-summaries.py)
    original_texts_by_type = {}
    for stype, slide_html in template_slides:
        if stype not in original_texts_by_type:
            original_texts_by_type[stype] = extract_texts(slide_html)

    # Find skeleton slides in summary.html and replace tokens
    # Summary has slides as HTML comments followed by sections
    # Pattern: <!-- slide-type -->\n<section ...>...</section>

    lines = summary_html.split('\n')
    result_lines = []
    replacements = 0

    for i, line in enumerate(lines):
        # Check if this line contains a skeleton slide with tokens
        if '{{' in line:
            # Find the slide type comment above this line
            stype = None
            for j in range(i-1, max(i-3, -1), -1):
                cm = re.search(r'<!--\s*([\w-]+)\s*-->', lines[j])
                if cm:
                    stype = cm.group(1)
                    break

            if stype and stype in original_texts_by_type:
                original = original_texts_by_type[stype]
                new_line = replace_tokens_in_skeleton(line, original)
                token_count_before = line.count('{{')
                token_count_after = new_line.count('{{')
                replacements += token_count_before - token_count_after
                result_lines.append(new_line)
            else:
                result_lines.append(line)
        else:
            result_lines.append(line)

    new_summary = '\n'.join(result_lines)

    with open(summary_path, 'w') as f:
        f.write(new_summary)

    remaining = new_summary.count('{{')
    return True, f"{replacements} replaced, {remaining} remaining"


def main():
    templates_dir = sys.argv[1] if len(sys.argv) > 1 else "skills/hyperframes/templates/presentations"
    index_path = os.path.join(os.path.dirname(templates_dir), "index.json")

    with open(index_path) as f:
        index = json.load(f)

    total_replaced = 0
    total_remaining = 0

    for t in index['templates']:
        slug = t['slug']
        template_dir = os.path.join(templates_dir, slug)

        ok, msg = process_template(template_dir, slug)
        if ok:
            nums = re.findall(r'(\d+)', msg)
            if len(nums) >= 2:
                total_replaced += int(nums[0])
                total_remaining += int(nums[1])
        print(f"  {slug}: {msg}")

    print(f"\nTotal: {total_replaced} tokens replaced, {total_remaining} remaining")


if __name__ == '__main__':
    main()
