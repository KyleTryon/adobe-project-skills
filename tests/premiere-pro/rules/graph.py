"""Checks for references/spec/04-object-graph-and-project.md (§4 graph, §5 project)."""
import os
from _lib import rule, expect, P
from _doc import project, refmap, key


@rule('graph.timeline-clip-owns-clip')
def _(ev):
    for s in ev.steps:
        master = {k.get('ObjectRef') for mc in s.objs('MasterClip') for k in mc.findall('Clips/Clip')}
        subs = s.objs('SubClip')
        expect(subs, f'{s}: no timeline clips')
        owned = [s.ref(sc, 'Clip') for sc in subs]
        expect(len({key(c) for c in owned}) == len(owned), f'{s}: two SubClips share a clip')
        for sc, c in zip(subs, owned):
            expect(key(c) not in master, f'{s}: a timeline clip is a MasterClip clip')
            mc = s.ref(sc, 'MasterClip')
            srcs = {key(s.ref(s.ref(k), 'Clip/Source')) for k in mc.findall('Clips/Clip') if s.ref(k).tag == c.tag}
            expect(key(s.ref(c, 'Clip/Source')) in srcs, f'{s}: timeline clip source is not its MasterClip\'s')


@rule('project.structure')
def _(ev):
    for s in ev.steps:
        p = project(s)
        kids = [c.tag for c in p]
        expect(p.get('ObjectID') == '1' and kids[0] == 'Node' and p.find('Node/Properties') is not None, f'{s}: Project {p.attrib} {kids[:2]}')
        expect(kids[-1] == 'NextID', f'{s}: last child {kids[-1]}')
        settings = [s.ids.get(c.get('ObjectRef')) for c in p if c.get('ObjectRef')]
        expect(settings and all(x is not None and x.tag.endswith('Settings') for x in settings), f'{s}: Project refs {[x.tag if x is not None else None for x in settings]}')


def prop(s, k):
    return P.txt(project(s), f'Node/Properties/{k}')


@rule('project.properties')
def _(ev):
    guids = set()
    for s in ev.steps:
        for k in ('MZ.BuildVersion.Created', 'MZ.BuildVersion.Modified'):
            v = prop(s, k)
            expect(v and v.startswith('26.5.2x5 - '), f'{s}: {k} = {v!r}')
        guids.add(prop(s, 'MZ.Project.GUID'))
    expect(len(guids) == 1 and None not in guids, f'MZ.Project.GUID changes: {guids}')


def open_list(s):
    return {c.tag: c.text for c in project(s).find('Node/Properties') if c.tag.startswith('MZ.PrefixKey.OpenSequenceGuidList.')}


@rule('project.open-sequence-list')
def _(ev):
    for a, b in ev.pairs:
        sa, sb = {e.get('ObjectUID') for e in a.objs('Sequence')}, {e.get('ObjectUID') for e in b.objs('Sequence')}
        new = sb - sa
        la, lb = set(open_list(a).values()), set(open_list(b).values())
        expect(len(new) == 1 and lb == la | new and set(lb) <= sb, f'{a}→{b}: open list {sorted(lb)}, new sequence {new}')


@rule('project.next-sequence-index')
def _(ev):
    for a, b in ev.pairs:
        expect(prop(a, 'MZ.NextSequenceIndex') is None and prop(b, 'MZ.NextSequenceIndex') == '2'
               and len(a.objs('Sequence')) == 1 and len(b.objs('Sequence')) == 2, f'{a}→{b}: NextSequenceIndex {prop(a, "MZ.NextSequenceIndex")}→{prop(b, "MZ.NextSequenceIndex")}')


@rule('project.rewritten-on-save')
def _(ev):
    for a, b in zip(ev.steps, ev.steps[1:]):
        expect(prop(a, 'MZ.BuildVersion.Modified') != prop(b, 'MZ.BuildVersion.Modified'), f'{a}→{b}: Modified kept')
        expect(prop(a, 'project.settings.lastknowngoodprojectpath') != prop(b, 'project.settings.lastknowngoodprojectpath'), f'{a}→{b}: path kept')
    for s in ev.steps:
        path = prop(s, 'project.settings.lastknowngoodprojectpath')
        expect(path.startswith('/') and path.endswith('.prproj'), f'{s}: path {path!r}')
        expect(prop(s, 'project.settings.lastknownparentdirectorypathaboveprojectpath') == os.path.dirname(os.path.dirname(path)), f'{s}: parent path')
    expect(len(ev.steps) > 1, 'needs consecutive saves')


@rule('project.settings-owners')
def _(ev):
    for s in ev.steps:
        m = refmap(s)
        for t in ('VideoSettings', 'AudioSettings', 'DefaultSequenceSettings'):
            objs = s.objs(t)
            expect(objs, f'{s}: no {t}')
            for e in objs:
                tags = {r.tag for r in m[key(e)]}
                expect(tags and tags <= {'ProjectSettings', 'VideoCompileSettings', 'AudioCompileSettings'}, f'{s}: {t} referred to by {tags}')
