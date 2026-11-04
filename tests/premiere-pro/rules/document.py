"""Checks for references/spec/02-document-structure.md."""
import collections, re
from _lib import rule, expect, P, step

from _doc import (UID_CLASSES, LOCAL, V4, PER_TYPE_CLASSIDS, objects, project, local, key, refmap,  # noqa: F401
                  node_ids, is_sequence_masterclip)


@rule('doc.top-level-objects')
def _(ev):
    for s in ev.steps:
        first = s.root[0]
        expect(first.tag == 'Project' and first.get('ObjectRef') == '1' and not first.get('ObjectID') and not len(first),
               f'{s}: first child is {first.tag} {first.attrib}')
        expect(all(key(e) for e in objects(s)), f'{s}: a direct child has no ObjectID/ObjectUID')


@rule('doc.identity-attribute')
def _(ev):
    seen = set()
    for s in ev.steps:
        for e in objects(s):
            a, u = e.get('ObjectID'), e.get('ObjectUID')
            expect(bool(a) != bool(u), f'{s}: {e.tag} has {"both" if a else "neither"}')
            expect((e.tag in UID_CLASSES) == bool(u), f'{s}: {e.tag} uses {"ObjectUID" if u else "ObjectID"}')
            expect(u or re.fullmatch(r'[1-9]\d*', a), f'{s}: {e.tag} ObjectID {a!r}')
            seen.add(e.tag)
    expect(UID_CLASSES <= seen, f'not shown: {sorted(UID_CLASSES - seen)}')


@rule('doc.classid-version-constant')
def _(ev):
    cv = collections.defaultdict(set)
    for s in ev.steps:
        for e in objects(s):
            cv[e.tag].add((e.get('ClassID'), e.get('Version')))
    for tag, v in cv.items():
        expect(len({ver for _, ver in v}) == 1, f'{tag} has Versions {sorted({ver for _, ver in v})}')
        if tag not in PER_TYPE_CLASSIDS:
            expect(len(v) == 1, f'{tag} has ClassIDs {sorted(c for c, _ in v)}')
    expect(any(len(cv[t]) > 1 for t in PER_TYPE_CLASSIDS), 'no tag with one ClassID per value type')


@rule('doc.no-nesting')
def _(ev):
    for s in ev.steps:
        loc = local(s)
        expect(any(x.get('ObjectID') for x in loc), f'{s}: no local objects inside Project')
        for e in objects(s):
            for x in e.iter():
                if x is not e and key(x) and x not in loc:
                    expect(False, f'{s}: {x.tag} nested in {e.tag}')


@rule('doc.refs-resolve')
def _(ev):
    for s in ev.steps:
        loc, n = local(s), 0
        for e in objects(s):
            for x in e.iter():
                k = x.get('ObjectRef') or x.get('ObjectURef')
                if not k or x in loc:
                    continue
                expect(not len(x) and not (x.text or '').strip(), f'{s}: reference {x.tag} has content')
                expect(k in s.ids, f'{s}: {e.tag}/{x.tag} -> {k} does not resolve'); n += 1
        expect(n, f'{s}: no references')


@rule('doc.every-object-referenced')
def _(ev):
    for s in ev.steps:
        m = refmap(s)
        orphans = [e.tag for e in objects(s) if e.tag != 'Project' and not m[key(e)]]
        expect(not orphans, f'{s}: unreferenced {orphans[:5]}')


@rule('doc.list-index')
def _(ev):
    for s in ev.steps:
        lists = 0
        for e in s.root.iter():
            groups = collections.defaultdict(list)
            for c in e:
                if c.get('Index') is not None:
                    groups[c.tag].append(int(c.get('Index')))
            for t, ix in groups.items():
                expect(ix == list(range(len(ix))), f'{s}: {e.tag}/{t} Index {ix[:8]}'); lists += 1
        for trk in s.objs('VideoClipTrack') + s.objs('AudioClipTrack'):
            st = [int(P.txt(s.ref(x), './/TrackItem/Start') or 0) for x in trk.findall('ClipTrack/ClipItems/TrackItems/TrackItem')]
            expect(st == sorted(st), f'{s}: track items not in time order {st}')
        expect(lists, f'{s}: no lists')


def _count(s, m, e):
    return len(m[key(e)])


@rule('doc.referrers-one')
def _(ev):
    for s in ev.steps:
        m = refmap(s)
        tl_items = {x.get('ObjectRef') for tr in s.objs('VideoClipTrack') + s.objs('AudioClipTrack')
                    for x in tr.findall('ClipTrack/ClipItems/TrackItems/TrackItem')}
        linked = {x.get('ObjectRef') for l in s.objs('Link') for x in l.findall('.//TrackItems/TrackItem')}
        seq_markers = [s.ref(e, 'MarkerOwner/Markers') for e in s.objs('Sequence') if e.find('MarkerOwner') is not None]
        groups = {
            'chains': s.objs('VideoComponentChain') + s.objs('AudioComponentChain'),
            'components': s.objs('VideoFilterComponent'),
            'params': s.objs('VideoComponentParam') + s.objs('AudioComponentParam') + s.objs('PointComponentParam'),
            'SubClips': s.objs('SubClip'), 'clips': s.objs('VideoClip') + s.objs('AudioClip'),
            'SecondaryContent': s.objs('SecondaryContent'),
            'unlinked track items': [s.ids[k] for k in tl_items - linked],
            'video tracks': s.objs('VideoClipTrack'), "a sequence's Markers": seq_markers, 'Marker': s.objs('Marker'),
        }
        for name, objs in groups.items():
            expect(objs, f'{s}: no {name}')
            bad = [o.tag for o in objs if _count(s, m, o) != 1]
            expect(not bad, f'{s}: {name} with other than one referrer: {bad[:3]}')


@rule('doc.referrers-two')
def _(ev):
    for s in ev.steps:
        m = refmap(s)
        linked = [s.ids[x.get('ObjectRef')] for l in s.objs('Link') for x in l.findall('.//TrackItems/TrackItem')]
        expect(linked, f'{s}: no linked items')
        for it in linked:
            expect(sorted(r.tag for r in m[key(it)]) in (['AudioClipTrack', 'Link'], ['Link', 'VideoClipTrack']), f'{s}: linked item referrers {[r.tag for r in m[key(it)]]}')
        fades = [t for t in s.objs('AudioTransitionTrackItem') if _count(s, m, t) == 2]
        expect(fades, f'{s}: no single-clip fade')
        for t in fades:
            tags = sorted(r.tag for r in m[key(t)])
            expect(tags == ['AudioClipTrack', 'AudioClipTrackItem'], f'{s}: fade referrers {tags}')
        for t in s.objs('AudioClipTrack'):
            expect(sorted(r.tag for r in m[key(t)]) == ['AudioTrackGroup', 'AudioTrackInlet'], f'{s}: audio track referrers {[r.tag for r in m[key(t)]]}')
        for q in s.objs('Sequence'):
            expect(sorted(r.tag for r in m[key(q)]) == ['AudioSequenceSource', 'VideoSequenceSource'], f'{s}: Sequence referrers {[r.tag for r in m[key(q)]]}')


@rule('doc.referrers-three')
def _(ev):
    for s in ev.steps:
        m = refmap(s)
        xf = [t for t in s.objs('AudioTransitionTrackItem') if P.txt(t, './/MatchName') == 'Constant Power']
        expect(xf, f'{s}: no crossfade')
        for t in xf:
            tags = sorted(r.tag for r in m[key(t)])
            expect(tags == ['AudioClipTrack', 'AudioClipTrackItem', 'AudioClipTrackItem'], f'{s}: crossfade referrers {tags}')


@rule('doc.referrers-shared')
def _(ev):
    for s in ev.steps:
        m = refmap(s)
        for mc in s.objs('MasterClip'):
            want = {key(c) for c in s.objs('ClipProjectItem') if s.ref(c, 'MasterClip') is mc}
            want |= {key(c) for c in s.objs('SubClip') if s.ref(c, 'MasterClip') is mc}
            expect({key(r) for r in m[key(mc)]} == want and len(m[key(mc)]) == len(want), f'{s}: MasterClip {P.txt(mc, "Name")} referrers')
        for t in ('VideoMediaSource', 'AudioMediaSource', 'VideoSequenceSource', 'AudioSequenceSource'):
            for src in s.objs(t):
                want = {key(c) for c in s.objs('VideoClip') + s.objs('AudioClip') if s.ref(c, 'Clip/Source') is src}
                want |= {key(x) for x in s.objs('SecondaryContent') if any(s.ids.get(r.get('ObjectRef')) is src for r in x.iter() if r.get('ObjectRef'))}
                expect({key(r) for r in m[key(src)]} == want, f'{s}: {t} referrers {[r.tag for r in m[key(src)]]}')
        for med in s.objs('Media'):
            tags = {r.tag for r in m[key(med)]}
            expect(tags and tags <= {'VideoMediaSource', 'AudioMediaSource', 'DataMediaSource'}, f'{s}: Media referrers {tags}')
        from _lib import media_of
        for mk in s.objs('Markers'):
            rs = m[key(mk)]
            if rs and all(r.tag in ('VideoClip', 'AudioClip') for r in rs):
                media = {key(media_of(s, r)) for r in rs if media_of(s, r) is not None}
                expect(len(media) == 1 and len([r for r in rs if media_of(s, r) is not None]) == len(rs), f'{s}: media Markers shared across media {media}')
                expect(all(media_of(s, c) is not None and key(media_of(s, c)) in media and key(s.ref(c, 'Clip/MarkerOwner/Markers')) == key(mk)
                           for c in s.objs('VideoClip') + s.objs('AudioClip') if media_of(s, c) is not None and key(media_of(s, c)) in media),
                       f'{s}: a clip of that media points elsewhere')


@rule('doc.local-scope')
def _(ev):
    for s in ev.steps:
        lst = project(s).find(LOCAL)
        expect(lst is not None and lst.get('ObjectID') == '2', f'{s}: ProjectViewState.List missing or not ObjectID 2')
        lids = [int(x.get('ObjectID')) for x in lst.iter() if x is not lst and x.get('ObjectID')]
        expect(lids and min(lids) >= 1 and max(lids) <= 60, f'{s}: local IDs {min(lids)}–{max(lids)}')
        expect(set(map(str, lids)) & set(s.ids), f'{s}: local IDs never collide with global ones')


@rule('doc.objectid-dense')
def _(ev):
    for s in ev.steps:
        expect(not s.generated, f'{s} is script-written')
        ids = [int(e.get('ObjectID')) for e in objects(s) if e.get('ObjectID')]
        expect(ids == sorted(ids), f'{s}: ObjectIDs not increasing in document order')
        expect(sorted(ids + [2]) == list(range(1, max(ids) + 1)), f'{s}: ObjectIDs not dense with the local list as 2')


@rule('doc.new-objectid')
def _(ev):
    for a, b in ev.pairs:
        old = {int(e.get('ObjectID')) for e in objects(a) if e.get('ObjectID')}
        new = [int(e.get('ObjectID')) for e in objects(b) if e.get('ObjectID') and int(e.get('ObjectID')) not in old]
        expect(b.generated and new and min(new) == max(old) + 1, f'{b}: new IDs start at {min(new) if new else None}, max before {max(old)}')
        ids = [int(e.get('ObjectID')) for e in objects(b) if e.get('ObjectID')]
        expect(len(ids) == len(set(ids)), f'{b}: duplicate ObjectIDs')


@rule('doc.uids-v4')
def _(ev):
    for s in ev.steps:
        u = [e.get('ObjectUID') for e in objects(s) if e.get('ObjectUID')]
        expect(u and all(V4.match(x) for x in u), f'{s}: non-v4 ObjectUIDs')
        c = [x.text for x in s.root.iter('ClipID')]
        expect(all(V4.match(x or '') for x in c), f'{s}: non-v4 ClipIDs')


@rule('doc.root-uid-changes')
def _(ev):
    for a, b in zip(ev.steps, ev.steps[1:]):
        ra, rb = a.objs('RootProjectItem')[0].get('ObjectUID'), b.objs('RootProjectItem')[0].get('ObjectUID')
        expect(ra != rb, f'{a}→{b}: RootProjectItem UID kept')
        ua = {e.get('ObjectUID') for e in objects(a) if e.get('ObjectUID') and e.tag != 'RootProjectItem'}
        ub = {e.get('ObjectUID') for e in objects(b) if e.get('ObjectUID')}
        expect(ua <= ub, f'{a}→{b}: {len(ua - ub)} ObjectUIDs lost')
    expect(len(ev.steps) > 1, 'needs consecutive saves')


@rule('doc.media-uids-regenerated')
def _(ev):
    for a, b in ev.pairs:
        ua = {e.get('ObjectUID') for e in a.objs('Media')}
        ub = {e.get('ObjectUID') for e in b.objs('Media')}
        expect(len(ua) == len(ub) and not (ua & ub), f'{a}→{b}: {len(ua & ub)} Media UIDs kept')


@rule('doc.nextid')
def _(ev):
    for s in ev.steps:
        n = node_ids(s)
        nxt = int(P.txt(project(s), 'NextID'))
        expect(nxt == 1 + max(n.values()), f'{s}: NextID {nxt}, max Node/ID {max(n.values())}')
        root = s.objs('RootProjectItem')[0]
        expect(n.get(root) == 1000000, f'{s}: root Node/ID {n.get(root)}')


@rule('doc.node-id-on-placement')
def _(ev):
    for a, b in ev.pairs:
        na, nb = node_ids(a), node_ids(b)
        old = {key(e) for e in na}
        new = sorted(v for e, v in nb.items() if key(e) not in old and e.tag != 'RootProjectItem')
        nxt_a, nxt_b = int(P.txt(project(a), 'NextID')), int(P.txt(project(b), 'NextID'))
        if b.n == '01':
            expect(not new and nxt_a == nxt_b and a.objs('MasterClip') == [] and b.objs('MasterClip'), f'{a}→{b}: import gave Node IDs {new}')
            continue
        expect(new == list(range(nxt_a, nxt_a + len(new))) and new and nxt_b == nxt_a + len(new), f'{a}→{b}: new Node IDs {new}, NextID {nxt_a}→{nxt_b}')
        for e in nb:
            if key(e) not in old and e.tag != 'RootProjectItem':
                expect(e.tag == 'MasterClip' and not is_sequence_masterclip(b, e)
                       and any(b.ref(x, 'MasterClip') is e for x in b.objs('SubClip')), f'{b}: {e.tag} got a Node ID without being placed')


@rule('doc.no-node-id')
def _(ev):
    hit = set()
    for a, b in ev.pairs:
        old = {key(e) for e in a.objs('BinProjectItem') + a.objs('MasterClip')}
        nb = node_ids(b)
        for e in b.objs('BinProjectItem'):
            if key(e) not in old:
                expect(e not in nb, f'{b}: new bin has a Node ID'); hit.add('bin')
        for e in b.objs('MasterClip'):
            if key(e) not in old and is_sequence_masterclip(b, e):
                expect(e not in nb, f'{b}: new sequence MasterClip has a Node ID'); hit.add('seq')
    expect(hit == {'bin', 'seq'}, f'evidence shows only {hit}')


@rule('doc.script-node-id')
def _(ev):
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        na = {key(e) for e in node_ids(a)}
        new = [(e, v) for e, v in node_ids(b).items() if key(e) not in na]
        nxt_a, nxt_b = int(P.txt(project(a), 'NextID')), int(P.txt(project(b), 'NextID'))
        expect(len(new) == 1 and new[0][1] == nxt_a and nxt_b == nxt_a + 1, f'{a}→{b}: new {[(e.tag, v) for e, v in new]}, NextID {nxt_a}→{nxt_b}')


FIVE = ('ClipID', 'AudioClipTrackItem/ID', 'AudioClipTrack/AudioTrack/ID', 'AudioMixTrack/AudioTrack/ID', 'AudioTrackGroup/ID')


def five_values(s):
    out = collections.defaultdict(list)
    out['ClipID'] = [x.text for x in s.root.iter('ClipID')]
    for path in FIVE[1:]:
        tag, rest = path.split('/', 1)
        out[path] = [P.txt(e, rest) for e in s.objs(tag) if P.txt(e, rest)]
    return out


@rule('doc.ids-unique')
def _(ev):
    for s in ev.steps:
        for path, vals in five_values(s).items():
            expect(vals and len(vals) == len(set(vals)), f'{s}: {path} repeats ({len(vals)} values, {len(set(vals))} distinct)')


@rule('doc.clone-regenerate')
def _(ev):
    for s in ev.steps:
        expect(s.generated and len(s.objs('Sequence')) >= 3, f'{s}: no cloned sequence')
        for path, vals in five_values(s).items():
            expect(vals and len(vals) == len(set(vals)), f'{s}: {path} repeats after cloning')


@rule('doc.defmappingid-shared')
def _(ev):
    for s in ev.steps:
        c = collections.Counter(P.txt(m, 'DefMappingID') for m in s.objs('MasterClip') if P.txt(m, 'DefMappingID'))
        expect(list(c.values()) == [6], f'{s}: DefMappingID counts {dict(c)}')


CONSTANTS = {'MediaType': 2, 'MZ.Sequence.EditingModeGUID': 1, 'PreviewFormatIdentifier': 1, 'ESP.PresetGuid': 2, 'ImplementationID': 2}


@rule('doc.constants')
def _(ev):
    vals, count = collections.defaultdict(set), collections.Counter()
    for s in ev.steps:
        for t in CONSTANTS:
            for x in s.root.iter(t):
                vals[t].add((x.text or '').strip()); count[t] += 1
    for t, n in CONSTANTS.items():
        expect(count[t] > 2 * n and len(vals[t]) == n, f'{t}: {len(vals[t])} values over {count[t]} occurrences')


def bfs(s):
    loc, order, seen, q = local(s), [], set(), [project(s)]
    seen.add(key(project(s)))
    while q:
        e = q.pop(0); order.append(e)
        for x in e.iter():
            k = x.get('ObjectRef') or x.get('ObjectURef')
            if k and x not in loc and k in s.ids and k not in seen:
                seen.add(k); q.append(s.ids[k])
    return order


@rule('doc.bfs-order')
def _(ev):
    for s in ev.steps:
        expect(not s.generated, f'{s} is script-written')
        o = bfs(s)
        expect([key(e) for e in o] == [key(e) for e in objects(s)], f'{s}: document order is not breadth-first from Project')


@rule('doc.order-free')
def _(ev):
    for s in ev.steps:
        expect(s.generated, f'{s} is not script-written')
        expect([key(e) for e in bfs(s)] != [key(e) for e in objects(s)], f'{s}: happens to be in Premiere order, so it proves nothing')
