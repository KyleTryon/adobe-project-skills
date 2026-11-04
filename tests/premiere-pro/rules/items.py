"""Checks for references/spec/09-track-items-and-links.md (§9 track items, §10 links)."""
from collections import Counter
from _lib import rule, expect, media_of, P

from _timeline import (ITEM_TAGS, CLIP_TAGS, PAIR, ITEM_CLASSES, timeline, item, all_items, tl_count, link_members, need_items)


# ---------- §9.1 anatomy ----------

@rule('items.child-order')
def _(ev):
    """The timeline classes (the 11 objects) keep one child order: no two objects of a class order any two children differently."""
    need_items(ev)
    before = {}
    for s in ev.steps:
        for e in s.root:
            if e.tag not in ITEM_CLASSES:
                continue
            stack = [(e.tag, e)]
            while stack:
                path, el = stack.pop()
                if path.endswith('Node/Properties'):
                    continue
                kids = [c.tag for c in el]
                pos = {}
                for i, k in enumerate(kids):
                    pos.setdefault(k, i)
                for a in pos:
                    for b in pos:
                        if pos[a] < pos[b]:
                            prev = before.setdefault((path, a, b), s.name)
                            expect((path, b, a) not in before, f'{s}: {path} has {a} before {b}, {before.get((path, b, a))} the other way')
                if len(path.split('/')) < 4:
                    # Node/Properties is a keyed bag of settings, not schema children
                    stack += [(f'{path}/{c.tag}', c) for c in el if len(c) and not (c.tag == 'Properties' and el.tag == 'Node')]


@rule('items.track-item-parts')
def _(ev):
    need_items(ev)
    for s in ev.steps:
        for _, t, it in all_items(s):
            e = it['el']
            expect(s.ref(e, 'ClipTrackItem/ComponentOwner/Components') is not None, f'{s}: item without a component chain')
            expect(e.find('ClipTrackItem/TrackItem/End') is not None, f'{s}: item without TrackItem/End')
            expect(it['sub'] is not None and it['sub'].tag == 'SubClip', f'{s}: item without SubClip')
            expect(it['clip'] is not None and it['clip'].tag in CLIP_TAGS, f'{s}: SubClip/Clip is {it["clip"]}')
            mc = it['sub'].find('MasterClip')
            expect(mc is not None and mc.get('ObjectURef') and s.ref(mc).tag == 'MasterClip', f'{s}: SubClip/MasterClip is not an ObjectURef to a MasterClip')
            expect(it['name'], f'{s}: SubClip has no Name')
            if e.tag == 'VideoClipTrackItem':
                expect(e.find('ClipTrackItem/HeadTransition') is None and e.find('ClipTrackItem/TailTransition') is None, f'{s}: video item with a transition ref')


@rule('items.clip-parts')
def _(ev):
    need_items(ev)
    for s in ev.steps:
        for _, t, it in all_items(s):
            c = it['clip']
            expect(c.find('Clip/Source') is not None and it['clipid'] and it['in_present'] and it['out'] is not None,
                   f'{s}: timeline clip missing Source/ClipID/InPoint/OutPoint')
            expect(it['label'], f'{s}: timeline clip without a label in Node/Properties')
            if media_of(s, c) is not None:
                expect(s.ref(c, 'Clip/MarkerOwner/Markers') is not None, f'{s}: media timeline clip without MarkerOwner/Markers')


@rule('items.audio-clip-channels')
def _(ev):
    n = 0
    for s in ev.steps:
        for _, t, it in all_items(s):
            c = it['clip']
            if c.tag != 'AudioClip':
                continue
            n += 1
            sec = [s.ref(x) for x in c.findall('SecondaryContents/SecondaryContentItem')]
            expect(len(sec) == 2 and all(x is not None and x.tag == 'SecondaryContent' for x in sec), f'{s}: {len(sec)} SecondaryContents')
            src = {P.txt(x, './/Content') or (x.find('.//Content').get('ObjectRef') if x.find('.//Content') is not None else None) for x in sec}
            idx = sorted(P.txt(x, './/ChannelIndex') for x in sec)
            expect(idx == ['0', '1'], f'{s}: ChannelIndex {idx}')
            expect(len(src) == 1, f'{s}: SecondaryContents point at different sources {src}')
            expect(c.find('AudioChannelLayout') is not None, f'{s}: no AudioChannelLayout')
    expect(n, 'no audio clips')


# ---------- §9.2 timing ----------

@rule('items.timing')
def _(ev):
    need_items(ev)
    for s in ev.steps:
        for n, t, it in all_items(s):
            expect(it['speed'] == 1.0, f'{s}: speed {it["speed"]}')
            expect(it['end'] - it['start'] == it['out'] - it['in'], f'{s} {n}: End−Start {it["end"] - it["start"]} ≠ Out−In {it["out"] - it["in"]}')


@rule('items.frame-grid')
def _(ev):
    need_items(ev)
    for s in ev.steps:
        for n, d in timeline(s).items():
            f = d['frame']
            for t in d['tracks']:
                for it in t['items']:
                    expect(it['start'] % f == 0 and it['end'] % f == 0, f'{s} {n}: {it["tag"]} {it["start"]}-{it["end"]} off the {f}-tick grid')


# ---------- §9.3 per-track invariants ----------

@rule('items.track-invariants')
def _(ev):
    need_items(ev)
    for s in ev.steps:
        ids, aids = [], []
        for n, d in timeline(s).items():
            for t in d['tracks']:
                idx = [i for i, _ in t['entries']]
                expect(idx == list(range(len(idx))), f'{s} {n}: Index {idx}')
                its = t['items']
                expect([x['start'] for x in its] == sorted(x['start'] for x in its), f'{s} {n}: items not in Start order')
                for a, b in zip(its, its[1:]):
                    expect(a['end'] <= b['start'], f'{s} {n}: items overlap')
                for it in its:
                    expect(it['start_present'] == (it['start'] != 0), f'{s} {n}: Start written as {P.txt(it["el"], "ClipTrackItem/TrackItem/Start")!r}')
                    expect(it['in_present'], f'{s} {n}: InPoint missing')
                    ids.append(it['clipid'])
                    if it['aid']:
                        aids.append(it['aid'])
        expect(len(ids) == len(set(ids)), f'{s}: duplicate ClipIDs')
        expect(len(aids) == len(set(aids)), f'{s}: duplicate audio item IDs')


@rule('items.clipid-stable')
def _(ev):
    """ClipID survives a save while the ObjectIDs are renumbered."""
    renum = 0
    for a, b in ev.pairs:
        A = {it['clipid']: it for _, _, it in all_items(a)}
        B = {it['clipid']: it for _, _, it in all_items(b)}
        kept = set(A) & set(B)
        expect(kept, f'{a}→{b}: no ClipID survives')
        for k in kept:
            expect(A[k]['name'] == B[k]['name'] and A[k]['in'] == B[k]['in'], f'{a}→{b}: ClipID {k} now names a different clip')
            renum += A[k]['clip'].get('ObjectID') != B[k]['clip'].get('ObjectID')
    expect(renum, 'no clip was renumbered in the cited saves, so ClipID never had to identify one')


# ---------- §9.4 edits ----------

def new_items(a, b):
    old = {it['clipid'] for _, _, it in all_items(a)}
    return [(n, t, it) for n, t, it in all_items(b) if it['clipid'] not in old]


def same_seq_tracks(a, b, seq):
    return timeline(a)[seq], timeline(b)[seq]


@rule('edits.place')
def _(ev):
    for a, b in ev.pairs:
        d = tl_count(b) - tl_count(a)
        expect(d == PAIR and not (tl_count(a) - tl_count(b)), f'{a}→{b}: object change {dict(d)}')
        new = new_items(a, b)
        expect(len(new) == 2 and {it['tag'] for _, _, it in new} == set(ITEM_TAGS), f'{a}→{b}: new items {[(it["tag"]) for _, _, it in new]}')
        seq = new[0][0]
        tl = timeline(b)[seq]
        for _, t, it in new:
            expect(t['tag'] in ('VideoClipTrack', 'AudioClipTrack') and tl['tracks'].index(t) in (0, 3), f'{a}→{b}: placed on track {tl["tracks"].index(t)}')
            expect([x['start'] for x in t['items']] == sorted(x['start'] for x in t['items']), 'track list not in time order')
        mem = [{m.get('ObjectID') for m in link_members(b, l)} for l in tl['links']]
        expect({it['key'] for _, _, it in new} in mem, f'{a}→{b}: the new pair is not linked')
        A, B = by_clipid(a, seq), by_clipid(b, seq)
        for k, x in A.items():
            y = B.get(k)
            expect(y and (x['start'], x['end'], x['in'], x['out']) == (y['start'], y['end'], y['in'], y['out']), f'{a}→{b}: an existing item changed, so this is not a plain place')


@rule('edits.place-script')
def _(ev):
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        new = new_items(a, b)
        expect(len(new) == 2 and {it['tag'] for _, _, it in new} == set(ITEM_TAGS), f'{a}→{b}: new items {len(new)}')
        seq = new[0][0]
        tl = timeline(b)[seq]
        mem = [{m.get('ObjectID') for m in link_members(b, l)} for l in tl['links']]
        expect({it['key'] for _, _, it in new} in mem, f'{b}: the placed pair is not linked')
        for _, _, it in new:
            for tag in ('SubClip',):
                expect(it['sub'] is not None, 'no SubClip')
            expect(s_chain(b, it), f'{b}: placed item without a chain')
        sec = [x for _, _, it in new if it['clip'].tag == 'AudioClip' for x in it['clip'].findall('SecondaryContents/SecondaryContentItem')]
        expect(len(sec) == 2, f'{b}: placed audio clip has {len(sec)} SecondaryContents')


def s_chain(s, it):
    return s.ref(it['el'], 'ClipTrackItem/ComponentOwner/Components') is not None


@rule('edits.default-label')
def _(ev):
    for a, b in ev.pairs:
        new = new_items(a, b)
        expect(new, f'{a}→{b}: no new timeline clips')
        for _, _, it in new:
            if it['name'].endswith('.mp4'):
                expect(it['label'] == 'BE.Prefs.LabelColors.1' and P.txt(it['clip'], 'Clip/Node/Properties/asl.clip.label.color') == '6769408',
                       f'{b}: new {it["name"]} clip labelled {it["label"]}')


def by_clipid(s, seq):
    return {it['clipid']: it for t in timeline(s)[seq]['tracks'] for it in t['items']}


@rule('edits.split')
def _(ev):
    for a, b in ev.pairs:
        seq = 'clip-a'
        A, B = by_clipid(a, seq), by_clipid(b, seq)
        new = [k for k in B if k not in A]
        expect(len(new) == 2, f'{a}→{b}: {len(new)} new clips')
        d = tl_count(b) - tl_count(a)
        expect(d == PAIR, f'{a}→{b}: object change {dict(d)}')
        for k in new:
            r = B[k]
            left = next(x for x in B.values() if x['tag'] == r['tag'] and x['end'] == r['start'] and x['clipid'] in A)
            o = A[left['clipid']]
            expect(left['start'] == o['start'] and left['in'] == o['in'] and left['aid'] == o['aid'], f'{b}: left piece changed more than End/OutPoint')
            expect(left['out'] == left['in'] + (left['end'] - left['start']), 'left OutPoint does not match T')
            expect(r['in'] == left['out'] and r['end'] == o['end'] and r['out'] == o['out'], f'{b}: right piece In/End/Out')
            expect(r['label'] == o['label'], 'label not copied')
            expect(s_ref_markers(b, r) == s_ref_markers(b, left), 'MarkerOwner not shared')
            if r['aid']:
                expect(r['aid'] != left['aid'] and left['aid'] == o['aid'], 'audio ID')
            ra, rl = r['el'].find('ClipTrackItem/TrackItem/Node/Properties'), o['el'].find('ClipTrackItem/TrackItem/Node/Properties')
            if rl is not None and len(rl):
                expect(ra is not None and [x.tag for x in ra] == [x.tag for x in rl], 'Essential Sound properties not copied')
        la = max(x['end'] for x in A.values()); lb = max(x['end'] for x in B.values())
        expect(la == lb, 'length changed')


def s_ref_markers(s, it):
    m = s.ref(it['clip'], 'Clip/MarkerOwner/Markers')
    return m.get('ObjectID') if m is not None else None


@rule('edits.split-script')
def _(ev):
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        seq = 'clip-a'
        A, B = by_clipid(a, seq), by_clipid(b, seq)
        new = [B[k] for k in B if k not in A]
        expect(len(new) == 2 and {x['tag'] for x in new} == set(ITEM_TAGS), f'{b}: {len(new)} new pieces')
        for r in new:
            left = next((x for x in B.values() if x['tag'] == r['tag'] and x['end'] == r['start'] and x['clipid'] in A), None)
            src = A.get(left['clipid']) if left else None
            expect(src is not None and r['name'] == src['name'], f'{b}: right piece has no left half')
            expect(r['label'] == src['label'] and s_ref_markers(b, r) == s_ref_markers(b, left), 'label/MarkerOwner not copied')
            if r['aid']:
                expect(r['aid'] not in {x['aid'] for x in A.values()}, 'right piece reuses an audio ID')


@rule('edits.trim-end')
def _(ev):
    for a, b in ev.pairs:
        A, B = by_clipid(a, 'clip-a'), by_clipid(b, 'clip-a')
        expect(set(A) == set(B), 'clips added or removed')
        ch = [k for k in A if (A[k]['end'], A[k]['out']) != (B[k]['end'], B[k]['out'])]
        expect(len(ch) == 2 and {A[k]['tag'] for k in ch} == set(ITEM_TAGS), f'{a}→{b}: {len(ch)} items changed')
        for k in A:
            x, y = A[k], B[k]
            expect((x['start'], x['in']) == (y['start'], y['in']), 'start or InPoint moved')
            expect(y['end'] - x['end'] == y['out'] - x['out'], 'End and OutPoint moved by different amounts')
        z = lambda s: P.txt(timeline(s)['clip-a']['el'], 'Node/Properties/Monitor.ProgramZoomOut')
        lb = max(x['end'] for x in B.values())
        expect(int(z(b)) == lb and z(a) != z(b), f'Monitor.ProgramZoomOut {z(a)} → {z(b)}, length {lb}')


def edge_moves(a, b, seq):
    A, B = by_clipid(a, seq), by_clipid(b, seq)
    out = []
    for k in set(A) & set(B):
        x, y = A[k], B[k]
        out.append((x, y))
    return out


@rule('edits.trim-end-script')
def _(ev):
    n = 0
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        for x, y in edge_moves(a, b, 'clip-a'):
            if y['end'] != x['end']:
                n += 1
                expect(y['end'] - x['end'] == y['out'] - x['out'], f'{b}: End and OutPoint moved differently')
    expect(n, 'no tail trim in the evidence')


@rule('edits.trim-start-script')
def _(ev):
    n = 0
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        moved = []
        for x, y in edge_moves(a, b, 'clip-a'):
            if y['start'] != x['start']:
                n += 1; moved.append(y['tag'])
                expect(y['start'] - x['start'] == (y['in'] - x['in']) / y['speed'], f'{b}: Start and InPoint moved differently')
        expect(not moved or sorted(moved) == sorted(ITEM_TAGS), f'{b}: head trim moved {moved}, not both items')
    expect(n, 'no head trim in the evidence')


@rule('edits.ripple-delete')
def _(ev):
    for a, b in ev.pairs:
        d = tl_count(a) - tl_count(b)
        expect(d == PAIR and not (tl_count(b) - tl_count(a)), f'{a}→{b}: removed {dict(d)}')
        A, B = by_clipid(a, 'clip-a'), by_clipid(b, 'clip-a')
        gone = [A[k] for k in A if k not in B]
        expect(len(gone) == 2, 'two items deleted')
        dur = gone[0]['end'] - gone[0]['start']
        for k in B:
            x, y = A[k], B[k]
            if x['start'] >= gone[0]['end']:
                expect(x['start'] - y['start'] == dur and x['end'] - y['end'] == dur and (x['in'], x['out']) == (y['in'], y['out']), f'{b}: later item not shifted by {dur} on Start/End only')
        for t in timeline(b)['clip-a']['tracks']:
            expect([i for i, _ in t['entries']] == list(range(len(t['entries']))), 'not re-indexed')
        expect([i.get('Index') for i in timeline(b)['clip-a']['link_entries']] == [str(i) for i in range(len(timeline(b)['clip-a']['link_entries']))], 'Links not re-indexed')


@rule('edits.place-video-only')
def _(ev):
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        d = tl_count(b) - tl_count(a)
        expect(d == Counter({'VideoClipTrackItem': 1, 'SubClip': 1, 'VideoClip': 1, 'VideoComponentChain': 1}), f'{a}→{b}: {dict(d)}')


def mccv(s):
    return {mc.get('ObjectUID'): P.txt(mc, 'MasterClipChangeVersion') for mc in s.objs('MasterClip') if P.txt(mc, 'MasterClipChangeVersion')}


@rule('edits.change-version-premiere')
def _(ev):
    for a, b in ev.pairs:
        A, B = mccv(a), mccv(b)
        up = [k for k in A if k in B and int(B[k]) > int(A[k])]
        expect(up, f'{a}→{b}: no MasterClipChangeVersion went up')


@rule('edits.change-version-script')
def _(ev):
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        A, B = mccv(a), mccv(b)
        expect(all(B.get(k) == v for k, v in A.items() if k in B), f'{a}→{b}: a script edit changed MasterClipChangeVersion')


# ---------- §10 links ----------

@rule('links.structure')
def _(ev):
    n = 0
    for s in ev.steps:
        for name, d in timeline(s).items():
            for i, (e, l) in enumerate(zip(d['link_entries'], d['links'])):
                expect(e.get('Index') == str(i) and l is not None and l.tag == 'Link', f'{s} {name}: Links entry {i}')
                ms = link_members(s, l)
                expect([m.tag for m in ms] == list(ITEM_TAGS), f'{s} {name}: link members {[m.tag for m in ms]}')
                idx = [t.get('Index') for t in l.findall('TrackItemGroup/TrackItems/TrackItem')]
                expect(idx == ['0', '1'], f'{s}: member Index {idx}')
                n += 1
    expect(n, 'no links in the evidence')


@rule('links.same-edges')
def _(ev):
    """Linked items have identical Start/End/In/Out, except a split edit, where the link stays."""
    same = diff = 0
    for s in ev.steps:
        for name, d in timeline(s).items():
            for l in d['links']:
                v, a = [item(s, m) for m in link_members(s, l)]
                if (v['start'], v['end'], v['in'], v['out']) == (a['start'], a['end'], a['in'], a['out']):
                    same += 1
                else:
                    diff += 1
                    expect(v['name'] == a['name'], f'{s}: link joins different media')
    expect(same and diff, f'evidence shows {same} identical and {diff} split-edit links; need both')


@rule('links.order')
def _(ev):
    for a, b in ev.pairs:
        tl = timeline(b)['clip-a']
        st = [item(b, link_members(b, l)[0])['start'] for l in tl['links']]
        expect(st == sorted(st), f'{b}: Links not in time order: {st}')
        expect(len(tl['links']) == len(timeline(a)['clip-a']['links']) + 1, f'{a}→{b}: not one new link')


@rule('links.empty')
def _(ev):
    n = 0
    for a, b in ev.pairs:
        for name, d in timeline(b).items():
            if not d['links']:
                n += 1
                expect(d['link_container'] is not None and d['link_container'].find('Links') is None, f'{b} {name}: empty sequence has a Links element')
    expect(n, 'no sequence without links')


@rule('links.one-link-per-item')
def _(ev):
    for s in ev.steps:
        for name, d in timeline(s).items():
            mem = [m.get('ObjectID') for l in d['links'] for m in link_members(s, l)]
            expect(len(mem) == len(set(mem)), f'{s} {name}: an item is in two links')
        expect(any(timeline(s)[n]['links'] for n in timeline(s)), f'{s}: no links')


@rule('links.delete-pair')
def _(ev):
    for a, b in ev.pairs:
        la, lb = timeline(a)['clip-a']['links'], timeline(b)['clip-a']['links']
        expect(len(lb) == len(la) - 1, f'{a}→{b}: {len(la)} → {len(lb)} links')
        gone = {l.get('ObjectID') for l in la} - {l.get('ObjectID') for l in lb}
        expect(len(gone) == 1 and not [l for l in b.objs('Link') if l.get('ObjectID') in gone], 'deleted Link object still there')
