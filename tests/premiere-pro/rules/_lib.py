"""Shared helpers for the spec's rule checks.

Every [O] and [V] tag in skills/premiere-pro-projects/references/spec/ carries a rule ID
(`[O: steps 05→06 #split.left-keeps-objects]`). A check is a function registered under
that ID with @rule. test_rules.py parses each tag's citation into the steps it names and
calls the check with them, so a rule is only ever tested on the evidence it cites:

    @rule('markers.colour-bgr')
    def _(ev):                      # ev.steps: the cited steps; ev.pairs: cited before→after pairs
        for s in ev.steps: ...
        expect(cond, 'what went wrong')

A check passes by returning; it fails by raising (use expect()).
"""
import glob, json, os, re, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILL = os.path.join(ROOT, 'skills', 'premiere-pro-projects')
SPEC = os.path.join(SKILL, 'references', 'spec')
STEPS_DIR = os.path.join(ROOT, 'fixtures', 'premiere-pro', 'steps')
sys.path.insert(0, os.path.join(SKILL, 'scripts'))
import prproj as P  # noqa: E402

TPS = 254016000000
FRAME_23976 = 10594584000
RULES = {}


def rule(rid):
    def deco(fn):
        if rid in RULES:
            raise SystemExit(f'rule {rid} registered twice')
        RULES[rid] = fn
        return fn
    return deco


class Fail(AssertionError):
    pass


def expect(cond, msg):
    if not cond:
        raise Fail(msg)


# ---------- steps ----------

STEP_FILES = {re.match(r'(\d\d)', os.path.basename(p)).group(1): p
              for p in sorted(glob.glob(os.path.join(STEPS_DIR, '*.prproj')))}
_cache = {}


class Step:
    def __init__(self, n):
        self.n, self.path = n, STEP_FILES[n]
        self.name = os.path.splitext(os.path.basename(self.path))[0]
        self.generated = '-gen-' in self.name
        self.xml = P.load_xml(self.path)
        self.root = ET.fromstring(self.xml)
        self.ids = P.index(self.root)
        self._seqs = None

    def __repr__(self):
        return f'step {self.name}'

    def objs(self, tag):
        """Top-level objects of a class."""
        return [e for e in self.root if e.tag == tag]

    def ref(self, el, path=None):
        """Follow an ObjectRef/ObjectURef (at `path` under el, or el itself)."""
        x = el.find(path) if path else el
        return P.deref(self.ids, x) if x is not None else None

    def referrers(self, target):
        k = target.get('ObjectID') or target.get('ObjectUID')
        return [e for e in self.root if any(x.get('ObjectRef') == k or x.get('ObjectURef') == k for x in e.iter())]

    @property
    def seqs(self):
        if self._seqs is None:
            self._seqs = P.sequences(self.root, self.ids)
        return self._seqs

    def seq(self, name):
        return next((s for s in self.seqs if s['name'] == name), None)

    def seq_el(self, name):
        return next((e for e in self.objs('Sequence') if P.txt(e, 'Name') == name), None)

    def transcripts(self):
        return P.transcripts(self.xml, self.root, self.ids)


def step(n):
    n = f'{int(n):02d}'
    if n not in _cache:
        _cache[n] = Step(n)
    return _cache[n]


def premiere_steps():
    return [step(n) for n in STEP_FILES if '-gen-' not in STEP_FILES[n]]


# ---------- citations ----------

class Evidence:
    def __init__(self, steps, pairs, text):
        self.steps, self.pairs, self.text = steps, pairs, text

    def all(self):
        """Every step cited, including both ends of each pair."""
        seen, out = set(), []
        for s in self.steps + [x for p in self.pairs for x in p]:
            if s.n not in seen:
                seen.add(s.n); out.append(s)
        return out


NUM = r'(\d\d)(?:-gen)?'


def parse_citation(text):
    """'steps 05→06, 08' / 'step 11' / 'steps 01–22' / 'steps/17-gen, 20-gen' / 'steps 18-gen→19'
    -> (step numbers, (before, after) pairs). Raises ValueError for anything else."""
    t = text.strip()
    t = re.sub(r'^(steps?/|steps?\s+)', '', t)
    singles, pairs = [], []
    for tok in [x.strip() for x in t.split(',') if x.strip()]:
        tok = re.sub(r'^(steps?/|steps?\s+)', '', tok)
        m = re.fullmatch(NUM + r'\s*→\s*' + NUM, tok)
        if m:
            pairs.append((m.group(1), m.group(2))); continue
        m = re.fullmatch(NUM + r'\s*–\s*' + NUM, tok)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if b < a:
                raise ValueError(f'backwards range {tok!r}')
            singles += [f'{i:02d}' for i in range(a, b + 1)]; continue
        m = re.fullmatch(NUM, tok)
        if m:
            singles.append(m.group(1)); continue
        raise ValueError(f'unreadable citation {tok!r}')
    missing = [n for n in singles + [x for p in pairs for x in p] if n not in STEP_FILES]
    if missing:
        raise ValueError(f'cites missing step(s) {", ".join(sorted(set(missing)))}')
    return singles, pairs


def evidence(text):
    singles, pairs = parse_citation(text)
    return Evidence([step(n) for n in singles], [(step(a), step(b)) for a, b in pairs], text)


# ---------- small helpers ----------

def dva(marker_el):
    return json.loads(P.txt(marker_el, 'DVAMarker'))['DVAMarker']


def media_of(s, clip_el):
    """The Media a VideoClip/AudioClip plays, or None for a sequence source."""
    src = s.ref(clip_el, 'Clip/Source')
    if src is None or src.tag not in ('VideoMediaSource', 'AudioMediaSource'):
        return None
    return s.ref(src, 'MediaSource/Media')
