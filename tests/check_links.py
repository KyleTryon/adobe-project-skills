#!/usr/bin/env python3
"""Check every relative link in the repo's Markdown: the file exists and, for `#anchor`,
the heading exists (GitHub's slug rules). Exit 1 and list the broken ones otherwise.

  python3 tests/check_links.py
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {'.git', 'node_modules', '__pycache__'}
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)\)')


def slug(h):
    h = re.sub(r'`', '', h.strip().lower())
    h = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', h)
    h = re.sub(r'[^\w\- ]', '', h)
    return h.replace(' ', '-')


def strip_code(text):
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    return re.sub(r'`[^`\n]*`', '``', text)


_anchors = {}
def anchors(path):
    if path not in _anchors:
        seen, out = {}, set()
        for ln in open(path, encoding='utf-8'):
            m = re.match(r'^#{1,6} (.*)', ln)
            if m:
                s = slug(m.group(1)); n = seen.get(s, 0); seen[s] = n + 1
                out.add(s if n == 0 else f'{s}-{n}')
        _anchors[path] = out
    return _anchors[path]


def main():
    bad = []
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x not in SKIP and not x.endswith('-workspace')]
        for f in files:
            if not f.endswith('.md'):
                continue
            src = os.path.join(d, f)
            for m in LINK.finditer(strip_code(open(src, encoding='utf-8').read())):
                tgt = m.group(1)
                if re.match(r'^[a-z]+:', tgt):
                    continue
                path, _, frag = tgt.partition('#')
                full = os.path.normpath(os.path.join(d, path)) if path else src
                rel = os.path.relpath(src, ROOT)
                if not os.path.exists(full):
                    bad.append(f'{rel}: {tgt} (no such file)')
                elif frag and full.endswith('.md') and frag not in anchors(full):
                    bad.append(f'{rel}: {tgt} (no such heading)')
    for b in bad:
        print(b)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
