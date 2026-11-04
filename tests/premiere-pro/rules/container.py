"""Checks for references/spec/01-container.md."""
import gzip, re
import xml.etree.ElementTree as ET
from _lib import rule, expect

DECL = '<?xml version="1.0" encoding="UTF-8" ?>'


def raw(s):
    return open(s.path, 'rb').read()


@rule('container.gzip-xml')
def _(ev):
    for s in ev.steps:
        b = raw(s)
        expect(b[:2] == b'\x1f\x8b', f'{s}: not gzip')
        text = gzip.decompress(b).decode('utf-8')          # raises on non-UTF-8
        ET.fromstring(text)
        expect(text.count('<PremiereData ') == 1, f'{s}: not one document')


@rule('container.any-gzip-header')
def _(ev):
    for s in ev.steps:
        b = raw(s)
        expect(s.generated, f'{s} is not script-written')
        expect(b[9] == 0xff and int.from_bytes(b[4:8], 'little') != 0, f'{s}: header is not a Python gzip header (OS byte {b[9]}, mtime set)')


@rule('container.declaration')
def _(ev):
    for s in ev.steps:
        lines = s.xml.split('\n')
        expect(lines[0] == DECL, f'{s}: first line {lines[0]!r}')
        expect(lines[1] == '<PremiereData Version="3">', f'{s}: root line {lines[1]!r}')
        expect(s.xml.endswith('</PremiereData>\n\n') and not s.xml.endswith('\n\n\n'), f'{s}: ending {s.xml[-20:]!r}')


@rule('container.tab-indent')
def _(ev):
    for s in ev.steps:
        depth, n = 0, 0
        for i, ln in enumerate(s.xml.split('\n')[1:], 2):
            lead = re.match(r'[ \t]*', ln).group(0)
            expect(' ' not in lead, f'{s}: line {i} indented with spaces')
            t = ln[len(lead):]
            if not t.startswith('<'):
                continue                      # text continuing from the line above (base64)
            if t.startswith('</'):
                depth -= 1
            expect(len(lead) == depth, f'{s}: line {i} has {len(lead)} tabs at depth {depth}')
            n += 1
            if t.startswith('</'):
                continue
            tag = re.match(r'<([\w.:-]+)', t).group(1)
            if not (t.endswith('/>') or f'</{tag}>' in t):
                depth += 1
        expect(n > 30 and depth == 0, f'{s}: unbalanced ({depth}) or too few tags ({n})')


@rule('container.self-closing')
def _(ev):
    for s in ev.steps:
        sc = re.findall(r'<([\w.:-]+)((?:\s[^<>]*?)?)/>', s.xml)
        expect(sc, f'{s}: no self-closing tags')
        bad = [t for t, a in sc if 'ObjectRef=' not in a and 'ObjectURef=' not in a]
        expect(not bad, f'{s}: self-closing non-reference tags {bad[:3]}')
        expect(' />' not in s.xml, f'{s}: a space before />')
        expect(not re.search(r'<([\w.:-]+)[^<>/]*></\1>', s.xml), f'{s}: an empty <X></X> on one line')
        empty = re.findall(r'\n(\t*)<([\w.:-]+)[^<>]*[^/]>\n\1</\2>', s.xml)
        expect(empty, f'{s}: no empty container to show the two-line form')
