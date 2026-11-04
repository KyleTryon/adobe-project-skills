#!/usr/bin/env python3
"""schema_dump.py - infer the .prproj object schema from real projects.

Usage: python3 -I schema_dump.py [--json] [--class NAME] PROJECT.prproj [MORE.prproj ...]
       python3 -I schema_dump.py --write|--check STEPS.prproj ...

Read-only. For every top-level object class (the direct children of <PremiereData>)
it reports ClassID(s), Version(s), how many objects were seen, every element path
under the object with how often it is present, the kind of value it holds, and which
classes each reference points to. Values are reduced to their kind ('int', 'int64',
'guid', 'path', 'base64', ...) plus, for small closed sets of numbers or flags, the
values seen, so the output carries no file names, paths, transcript text or other
personal content and can be published.

This is how references/prproj-schema.json (the catalogue scripts and validate read) and
references/prproj-classes.md (the same, for reading) are produced from the public steps.
Run it on projects from another Premiere version and diff the JSON to see what changed.

  --json          machine-readable output instead of markdown
  --class NAME    only that class (e.g. VideoComponentChain)
  --write         regenerate references/prproj-schema.json and prproj-classes.md from the files given
  --check         exit 1 if those two files differ from what --write would produce
Exit status: 0 ok, 1 unreadable project, 2 bad arguments.
"""
import sys, re, gzip, json, argparse, os, glob
from collections import defaultdict, Counter
import xml.etree.ElementTree as ET

GUID = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
INT = re.compile(r'^-?\d+$')
FLOAT = re.compile(r'^-?(\d+\.\d*|\.\d+|\d+)(e[-+]?\d+)?$', re.I)
POINT = re.compile(r'^-?[\d.e+-]+:-?[\d.e+-]+$', re.I)
TICKS_PER_SEC = 254016000000
PURPOSE = {
    'AudioClip': 'audio clip instance: Source, ClipID, In/OutPoint, SecondaryContents, channel layout',
    'AudioClipTrack': 'audio track (A1, A2, …)',
    'AudioClipTrackItem': 'audio item on a track: Start/End, component chain, `<ID>` GUID',
    'AudioCompileSettings': 'audio side of a compile setting',
    'AudioComponentChain': 'audio stack (item, MasterClip, track)',
    'AudioComponentParam': 'audio effect parameter: float (Level, Balance, Volume) or bool (Mute, Bypass)',
    'AudioFader': 'track fader',
    'AudioMediaSource': 'Clip source → Media (audio)',
    'AudioMeter': 'track meter',
    'AudioMixTrack': 'sequence master bus',
    'AudioSequenceSource': 'Clip source → Sequence (a sequence used as a clip), audio',
    'AudioSettings': 'audio settings shell owned by project/compile settings',
    'AudioStream': 'duration, layout, peak/conform cache paths',
    'AudioTrackGroup': 'audio tracks + MasterTrack',
    'AudioTrackInlet': 'master inlet listing the source tracks',
    'AudioTransitionTrackItem': 'audio fade or crossfade on a track (`TransitionItems`, `HeadTransition`/`TailTransition`)',
    'BinProjectItem': 'bin',
    'ClipChannelGroupVectorSerializer': 'MasterClip audio channel groups (empty if no audio)',
    'ClipChannelSerializer': 'one channel: `mSourceChannelIndex`, `SourceClipIndex`',
    'ClipChannelVectorSerializer': 'one group; `ChannelType` 1 stereo / 0 mono',
    'ClipLoggingInfo': 'ClipName, media in/out, frame rate, timecode format',
    'ClipProjectItem': 'project-panel entry → MasterClip',
    'CompileSettings': 'export/compile presets (movie, still, audio, custom, video preview)',
    'DataMediaSource': 'TranscriptClip source',
    'DataStream': 'stream of the synthetic transcript Media',
    'DataTrackGroup': 'caption/data tracks group',
    'DefaultPanProcessor': 'master panner',
    'DefaultSequenceSettings': 'defaults for new sequences',
    'DummyCaptureSettings': 'capture settings placeholder',
    'ExternallyProvidedTranscriptDocument': 'FlatBuffer `TranscriptData`',
    'IngestSettings': 'ingest options',
    'Link': 'ties the linked A/V track items',
    'Markers': 'marker list of a master clip (empty until a marker is added) or a sequence',
    'Marker': 'one marker: a DVAMarker JSON string (name, comment, type, start time, colour)',
    'FileProjectItem': 'project item for a non-media file (e.g. a .txt)',
    'MasterClip': 'clip identity: Clips list, logging, channel map',
    'Media': 'one file on disk: paths, importer, streams',
    'PointComponentParam': '2-D point parameter (Position, Anchor Point)',
    'Project': 'root: properties, settings refs, `NextID`',
    'ProjectSettings': 'project-wide settings',
    'RootProjectItem': '"Root Bin"',
    'ScratchDiskSettings': 'scratch disk locations',
    'SecondaryContent': 'per-channel ref from an AudioClip to its source',
    'Sequence': 'timeline: TrackGroups, Links, view state',
    'StereoToStereoPanProcessor': 'track panner',
    'SubClip': 'track item → (MasterClip, Clip); `Name` shown on the timeline',
    'TranscriptClip': 'Speech-to-Text clip in a MasterClip',
    'VideoClip': 'video clip instance: Source, ClipID, In/OutPoint, label',
    'VideoClipTrack': 'video track (V1, V2, …)',
    'VideoClipTrackItem': 'video item on a track: Start/End, component chain',
    'VideoCompileSettings': 'video side of a compile setting',
    'VideoComponentChain': 'video effect stack (track item or track group)',
    'VideoComponentParam': 'video effect parameter: float, bool, enum or colour (Scale, Rotation, Opacity, Skew, …)',
    'VideoFilterComponent': 'one effect; `MatchName` e.g. `AE.ADBE Geometry2` (Transform)',
    'VideoMediaSource': 'Clip source → Media (video)',
    'VideoSequenceSource': 'Clip source → Sequence (a sequence used as a clip), video',
    'VideoSettings': 'video settings shell owned by project/compile settings',
    'VideoStream': 'duration, fps, size, codec FourCC, alpha',
    'VideoTrackGroup': 'video tracks, sequence FrameRate/FrameRect',
    'WorkspaceSettings': 'workspace state'}
ENUM_LIMIT = 8     # report the values of a field when it never took more than this many
MAX_PATHS = 120    # per class, to keep huge Properties bags readable


def load(path):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return ET.fromstring(raw.decode('utf-8'))


def kind_of(tag, text):
    t = (text or '').strip()
    if not t:
        return 'empty'
    if t in ('true', 'false'):
        return 'bool'
    if GUID.match(t):
        return 'guid'
    if INT.match(t):
        v = int(t)
        if abs(v) >= 10 ** 9:
            return 'int64'
        return 'int'
    if FLOAT.match(t):
        return 'float'
    if POINT.match(t):
        return 'point'
    if t.startswith('-91445760000000000,') or (t.count(',') >= 7 and ';' in t):
        return 'keyframes'
    if t.count(',') >= 1 and all(FLOAT.match(x) or x in ('true', 'false') for x in t.split(',')):
        return 'csv-numbers'
    if t.startswith('{') or t.startswith('['):
        return 'json'
    if t.startswith('&lt;') or t.startswith('<'):
        return 'escaped-xml'
    if '/' in t or '\\' in t or re.match(r'^[A-Za-z]:', t):
        return 'path'
    if len(t) > 64 and re.fullmatch(r'[A-Za-z0-9+/=\s]+', t):
        return 'base64'
    return 'string'


ANY_GUID = re.compile(r'[0-9a-fA-F]{8}(?:(?:-|_45_)[0-9a-fA-F]{4}){3}(?:-|_45_)[0-9a-fA-F]{12}')
LOCAL_SCOPE = 'Node/Properties/ProjectViewState.List'   # Project-local object IDs (references/spec/02-document-structure.md §2.3)


def norm_tag(tag):
    """Property keys can embed per-project GUIDs or counters; normalise them so the
    catalogue carries no project-specific identifiers."""
    tag = ANY_GUID.sub('<guid>', tag)
    return re.sub(r'(OpenSequenceGuidList)\.\d+$', r'\1.N', tag)


def walk(el, prefix, out, ids, by_id, cls_of_ref):
    for c in el:
        p = f"{prefix}/{norm_tag(c.tag)}" if prefix else norm_tag(c.tag)
        attrs = {k: v for k, v in c.attrib.items()}
        if 'ObjectRef' in attrs or 'ObjectURef' in attrs:
            ref = attrs.get('ObjectRef') or attrs.get('ObjectURef')
            key = p + ('@ObjectURef' if 'ObjectURef' in attrs else '@ObjectRef')
            if p.startswith(LOCAL_SCOPE):
                out[key].append(('local ref (Project scope)', None))
            else:
                tgt = by_id.get(ref)
                out[key].append(('ref', tgt.tag if tgt is not None else '?unresolved'))
        for a in ('Index', 'Version', 'Encoding', 'BinaryHash'):
            if a in attrs and a != 'Version':
                out[f"{p}@{a}"].append((kind_of(a, attrs[a]) if a != 'Index' else 'index', attrs[a] if a == 'Encoding' else None))
        if c.get('ObjectID') and p.startswith(LOCAL_SCOPE):
            out[p + '@ObjectID'].append(('local id (Project scope)', None))
        if len(c):
            out[p].append(('element', None))
            walk(c, p, out, ids, by_id, cls_of_ref)
        else:
            k = kind_of(c.tag, c.text)
            if attrs.get('Encoding') == 'base64':
                k = 'base64' if (c.text or '').strip() else 'base64 (deduplicated, self-closing)'
            elif ('ObjectRef' in attrs or 'ObjectURef' in attrs) and k == 'empty':
                continue  # the @ObjectRef row describes it
            out[p].append((k, (c.text or '').strip()))


BUILDS = set()


def _build(root):
    t = root.findtext('.//MZ.BuildVersion.Modified') or root.findtext('.//MZ.BuildVersion.Created') or ''
    return t.split(' - ')[0].strip() or '?'


def step_name(path):
    """'…/steps/05-add_clip_b.prproj' -> '05'; other files keep their stem."""
    stem = os.path.splitext(os.path.basename(path))[0]
    m = re.match(r'^(\d\d)(?:-|$)', stem)
    return m.group(1) if m else stem


def analyse(paths):
    classes = {}
    for path in paths:
        root = load(path)
        top = [e for e in root if e.get('ObjectID') or e.get('ObjectUID')]
        by_id = {}
        for e in top:
            by_id[e.get('ObjectID') or e.get('ObjectUID')] = e
        incoming = defaultdict(Counter)
        for e in top:
            local = set()
            if e.tag == 'Project':  # skip the Project-local view-state list (references/spec/02-document-structure.md §2.3)
                lst = e.find(LOCAL_SCOPE)
                if lst is not None:
                    local = set(lst.iter())
            for x in e.iter():
                if x in local:
                    continue
                r = x.get('ObjectRef') or x.get('ObjectURef')
                if r and r in by_id:
                    incoming[by_id[r].tag][e.tag] += 1
        BUILDS.add(_build(root))
        for e in top:
            c = classes.setdefault(e.tag, {'classids': Counter(), 'versions': Counter(), 'count': 0,
                                           'id_kind': Counter(), 'fields': defaultdict(list),
                                           'incoming': Counter(), 'files': set(), 'order': []})
            c['classids'][e.get('ClassID')] += 1
            c['versions'][e.get('Version')] += 1
            c['count'] += 1
            c['files'].add(path)
            c['id_kind']['ObjectUID' if e.get('ObjectUID') else 'ObjectID'] += 1
            fields = defaultdict(list)   # insertion order = document order within this object
            walk(e, '', fields, None, by_id, None)
            prev = -1
            for k, vals in fields.items():
                c['fields'][k].append(vals)
                # merge into the class-wide order: a new path goes right after the
                # path that preceded it in this object
                if k in c['order']:
                    prev = c['order'].index(k)
                else:
                    c['order'].insert(prev + 1, k); prev += 1
        for tag, cnt in incoming.items():
            if tag in classes:
                classes[tag]['incoming'].update(cnt)
    return classes


def summarise(classes):
    out = {}
    for tag, c in sorted(classes.items()):
        fields = []
        for p in c['order']:
            per_obj = c['fields'][p]
            present = len(per_obj)
            flat = [v for vals in per_obj for v in vals]
            kinds = Counter(k for k, _ in flat)
            entry = {'path': p, 'present': present, 'of': c['count'],
                     'kinds': dict(kinds.most_common())}
            if 'ref' in kinds:
                entry['targets'] = dict(Counter(v for k, v in flat if k == 'ref').most_common())
            vals = Counter(v for k, v in flat if k in ('bool', 'int') and v is not None)
            if vals and len(vals) <= ENUM_LIMIT and 'int64' not in kinds:
                entry['values'] = sorted(vals, key=lambda s: (len(s), s))
            enc = Counter(v for k, v in flat if v and p.endswith('@Encoding'))
            if enc:
                entry['values'] = sorted(enc)
            fields.append(entry)
        # keep first-seen document order: it follows the order Premiere writes children in
        out[tag] = {'classids': dict(c['classids']), 'versions': dict(c['versions']), 'count': c['count'],
                    'identity': dict(c['id_kind']), 'referenced_by': dict(c['incoming'].most_common()),
                    'seen_in': sorted({step_name(f) for f in c['files']}), 'fields': fields}
    return out


def kinds_str(k):
    return ', '.join(f"{n}" if len(k) == 1 else f"{n}×{c}" for n, c in k.items())


HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(HERE, '..', 'references')
JSON_OUT = os.path.join(REFS, 'prproj-schema.json')
MD_OUT = os.path.join(REFS, 'prproj-classes.md')


def explained_in(tag):
    """Spec files that mention the class by name (in backticks)."""
    out = []
    for f in sorted(glob.glob(os.path.join(REFS, 'spec', '*.md'))):
        if re.search(r'`' + re.escape(tag) + r'(`|/|\[)', open(f, encoding='utf-8').read()):
            out.append(os.path.basename(f))
    return out


def catalogue(paths, classes):
    s = summarise(classes)
    for tag, c in s.items():
        c['purpose'] = PURPOSE.get(tag, '')
        c['explained_in'] = explained_in(tag)
    return {'format': 1, 'generated_by': 'scripts/schema_dump.py --write',
            'premiere_builds': sorted(BUILDS), 'evidence': sorted({step_name(p) for p in paths}),
            'note': 'What was seen in the evidence files, not what Premiere allows. present/of = objects that had the path / objects of the class.',
            'classes': {t: {k: c[k] for k in ('purpose', 'explained_in', 'classids', 'versions', 'count', 'identity',
                                                'referenced_by', 'seen_in', 'fields')} for t, c in s.items()}}


HEADER = """# .prproj class catalogue

Generated from [`prproj-schema.json`](prproj-schema.json) by `scripts/schema_dump.py --write`; don't edit by hand. Read [the spec](spec/README.md) for the rules; this is the structure: for each top-level object class, its ClassID, Version, identity attribute, how many were seen and in which steps, which classes reference it, and every element path under it in the order Premiere writes them, with how often it was present and what kind of value it holds (`int`, `int64`, `guid`, `path`, `base64`, …, plus the values seen when there were few). Nothing from the projects' content is included. `→ X` is a reference to class X.

Evidence: {evidence}. Premiere {builds}. A class or path that isn't here hasn't been seen in the steps, which doesn't mean Premiere never writes it; `prproj.py validate` warns when a project has one.

"""


def anchor(tag):
    return tag.lower()


def to_markdown(cat, index=True):
    cls = cat['classes']
    ev = cat.get('evidence') or []
    lines = [HEADER.replace('{evidence}', f"steps {ev[0]}–{ev[-1]} in `fixtures/premiere-pro/steps/` ({len(ev)} files)" if ev else 'none')
             .replace('{builds}', ', '.join(cat.get('premiere_builds') or ['?']))]
    if index:
        lines.append('## Index\n')
        lines.append('| Class | What it is | Explained in |')
        lines.append('|---|---|---|')
        for tag, c in cls.items():
            spec = ', '.join(f"[{f[:2]}](spec/{f})" for f in c['explained_in']) or '—'
            lines.append(f"| [`{tag}`](#{anchor(tag)}) | {c['purpose'] or ''} | {spec} |")
        lines.append('\n## Classes\n')
    for tag, c in cls.items():
        cids = ', '.join(f"`{k}`" for k in c['classids'])
        vers = ', '.join(sorted(c['versions'], key=lambda v: (v is None, str(v))))
        ident = ' / '.join(c['identity'])
        seen = c['seen_in']
        lines.append(f"### {tag}\n")
        if c['purpose']:
            lines.append(c['purpose'][0].upper() + c['purpose'][1:] + '.\n')
        lines.append(f"ClassID {cids} · Version {vers} · {ident} · {c['count']} seen, in steps {_ranges(seen)}")
        if c['referenced_by']:
            lines.append('Referenced by: ' + ', '.join(f"{k} ({n})" for k, n in c['referenced_by'].items()))
        lines.append('')
        if not c['fields']:
            lines.append('(no children)\n'); continue
        lines.append('| Path | Present | Holds |')
        lines.append('|---|---|---|')
        shown = c['fields']
        if len(shown) > MAX_PATHS:
            shown = [f for f in shown if f['present'] == c['count'] or 'ref' in f['kinds']][:MAX_PATHS]
            lines.append(f"| … | | {len(c['fields']) - len(shown)} optional paths omitted; see prproj-schema.json |")
        for f in shown:
            if set(f['kinds']) == {'element'}:
                continue  # pure containers are implied by their children's paths
            holds = kinds_str({k: v for k, v in f['kinds'].items() if k != 'element'}) or 'container'
            if 'targets' in f:
                holds = '→ ' + ', '.join(f['targets'])
            if 'values' in f:
                holds += ' (' + ', '.join(f['values']) + ')'
            pres = 'always' if f['present'] == f['of'] else f"{f['present']}/{f['of']}"
            lines.append(f"| `{f['path']}` | {pres} | {holds} |")
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def unseen(root, cat=None, limit=6):
    """Compare a project with the catalogue: classes, ClassIDs, Versions and element paths
    the evidence never showed. Returns short warning strings (empty when everything was seen)."""
    if cat is None:
        if not os.path.exists(JSON_OUT):
            return []
        cat = json.load(open(JSON_OUT, encoding='utf-8'))
    known = cat['classes']
    top = [e for e in root if e.get('ObjectID') or e.get('ObjectUID')]
    by_id = {(e.get('ObjectID') or e.get('ObjectUID')): e for e in top}
    new_cls, new_ver, new_paths = set(), set(), {}
    for e in top:
        c = known.get(e.tag)
        if c is None:
            new_cls.add(e.tag); continue
        if e.get('ClassID') not in c['classids'] or e.get('Version') not in c['versions']:
            new_ver.add(f"{e.tag} (ClassID {e.get('ClassID')}, Version {e.get('Version')})")
        have = {f['path'] for f in c['fields']}
        fields = defaultdict(list)
        walk(e, '', fields, None, by_id, None)
        for p in fields:
            if p not in have and not p.startswith('Node/Properties/'):
                new_paths.setdefault(e.tag, set()).add(p)
    out = []
    if new_cls:
        out.append(f"{len(new_cls)} object class(es) not in the catalogue: " + ', '.join(sorted(new_cls)[:limit]))
    if new_ver:
        out.append("ClassID/Version not seen in the evidence: " + ', '.join(sorted(new_ver)[:limit]))
    if new_paths:
        n = sum(len(v) for v in new_paths.values())
        ex = [f"{t}/{sorted(v)[0]}" for t, v in sorted(new_paths.items())][:limit]
        out.append(f"{n} element path(s) not seen in the evidence, e.g. " + ', '.join(ex))
    if out:
        out.append("(unseen structure is normal for features the demo project doesn't use; edit those parts by hand only with care)")
    return out


def _ranges(names):
    nums = sorted(int(n) for n in names if n.isdigit())
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(f"{nums[i]:02d}" if i == j else f"{nums[i]:02d}–{nums[j]:02d}"); i = j + 1
    return ', '.join(out + [n for n in names if not n.isdigit()]) or '—'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('projects', nargs='+')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--class', dest='cls')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    try:
        classes = analyse(a.projects)
    except (OSError, ET.ParseError, UnicodeDecodeError) as e:
        print(f"error: can't read project: {e}", file=sys.stderr); sys.exit(1)
    if a.write or a.check:
        cat = catalogue(a.projects, classes)
        want = {JSON_OUT: json.dumps(cat, indent=1, ensure_ascii=False) + '\n', MD_OUT: to_markdown(cat)}
        if a.write:
            for p, t in want.items():
                open(p, 'w', encoding='utf-8').write(t)
            print(f"wrote {len(cat['classes'])} classes to references/prproj-schema.json and prproj-classes.md")
            return
        stale = [os.path.basename(p) for p, t in want.items()
                 if not os.path.exists(p) or open(p, encoding='utf-8').read() != t]
        for p in stale:
            print(f"{p} is out of date: run schema_dump.py --write on the steps")
        sys.exit(1 if stale else 0)
    if a.cls:
        if a.cls not in classes:
            print(f"error: no class '{a.cls}'. Classes: {', '.join(sorted(classes))}", file=sys.stderr); sys.exit(2)
        classes = {a.cls: classes[a.cls]}
    s = summarise(classes)
    try:
        _emit(a, s)
    except BrokenPipeError:  # e.g. piped into head
        sys.stderr.close()


def _emit(a, s):
    cat = {'evidence': [], 'premiere_builds': sorted(BUILDS),
           'classes': {t: {**c, 'purpose': PURPOSE.get(t, ''), 'explained_in': []} for t, c in s.items()}}
    if a.json:
        print(json.dumps(cat if not a.cls else cat['classes'][a.cls], indent=1))
    else:
        md = to_markdown(cat, index=not a.cls)
        print(md if not a.cls else md.split('### ', 1)[1].join(['### ', '']))


if __name__ == '__main__':
    main()
