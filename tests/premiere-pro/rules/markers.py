"""Checks for references/spec/13-markers.md."""
import re
from _lib import rule, expect, dva, media_of, P

MARKERS_CID, MARKER_CID = 'bee50706-b524-416c-9f03-b596ce5f6866', 'a45508e0-3ff7-4d04-90a7-2e0dfff4c910'
ZERO = '00000000-0000-0000-0000-000000000000'


def seq_markers(s, seq_el):
    ms = s.ref(seq_el, 'MarkerOwner/Markers')
    return [s.ref(m, 'Second') for m in ms.findall('Markers/Marker')] if ms is not None else []


@rule('markers.sequence-markers')
def _(ev):
    for a, b in ev.pairs:
        na = sum(len(seq_markers(a, e)) for e in a.objs('Sequence'))
        nb = sum(len(seq_markers(b, e)) for e in b.objs('Sequence'))
        expect(na == 0 and nb == 2, f'{a}: {na} sequence markers, {b}: {nb} (want 0 then 2)')
        types = sorted(dva(m)['mType'] for e in b.objs('Sequence') for m in seq_markers(b, e))
        expect(types == ['Chapter', 'Comment'], f'marker types {types}')
        expect(all('mDuration' not in dva(m) for e in b.objs('Sequence') for m in seq_markers(b, e)), 'a marker has a duration')


@rule('markers.backup-own-guids')
def _(ev):
    for s in ev.steps:
        by_seq = {P.txt(e, 'Name'): {dva(m)['mMarkerID'] for m in seq_markers(s, e)} for e in s.objs('Sequence')}
        with_markers = {k: v for k, v in by_seq.items() if v}
        expect(len(with_markers) >= 2, f'{s}: markers on {list(with_markers)} only; need a sequence and its backup')
        allg = [g for v in with_markers.values() for g in v]
        expect(len(allg) == len(set(allg)), f'{s}: marker GUIDs shared between sequences')


@rule('markers.script-written')
def _(ev):
    import json
    for s in ev.steps:
        expect(s.generated, f'{s} is not script-written')
        ms = [m for e in s.objs('Sequence') for m in seq_markers(s, e)]
        expect(ms, f'{s}: no sequence markers')
        for m in ms:
            d = dva(m)
            expect(re.fullmatch(r'[0-9a-f-]{36}', d['mMarkerID']) and d['mCuePointList'][0]['mKey'].startswith('keywordExtDVAv1_'), f'{s}: marker form')
        keys = [dva(m)['mCuePointList'][0]['mKey'] for m in ms]
        expect(len(keys) == len(set(keys)), f'{s}: cue-point keys repeat')


@rule('markers.media-owner')
def _(ev):
    for a, b in ev.pairs:
        expect(not a.objs('Markers'), f'{a} already has Markers objects')
        by_media = {}
        for tag in ('VideoClip', 'AudioClip'):
            for c in b.objs(tag):
                m = media_of(b, c)
                if m is None:
                    continue
                mk = b.ref(c, 'Clip/MarkerOwner/Markers')
                expect(mk is not None, f'{b}: a {tag} of a media file has no MarkerOwner')
                by_media.setdefault(m.get('ObjectUID') or m.get('ObjectID'), set()).add(mk.get('ObjectID'))
                expect(mk.find('Markers') is None, f'{b}: a media Markers object is not empty at import')
        expect(by_media and all(len(v) == 1 for v in by_media.values()), f'{b}: clips of one media point at different Markers')


@rule('markers.sequence-clips-have-none')
def _(ev):
    for s in ev.steps:
        for tag in ('VideoClip', 'AudioClip'):
            for c in s.objs(tag):
                src = s.ref(c, 'Clip/Source')
                if src is not None and src.tag.endswith('SequenceSource'):
                    expect(c.find('Clip/MarkerOwner') is None, f'{s}: a sequence MasterClip clip has a MarkerOwner')


@rule('markers.sequence-owner')
def _(ev):
    for a, b in ev.pairs:
        for e in b.objs('Sequence'):
            mo = e.find('MarkerOwner')
            if mo is None:
                continue
            kids = [c.tag for c in e]
            i = kids.index('MarkerOwner')
            expect(kids[i - 1] == 'Node' and kids[i + 1] == 'PersistentGroupContainer', f'{b}: MarkerOwner sits between {kids[i-1]} and {kids[i+1]}')
            expect(mo.get('Version') == '1', f"MarkerOwner Version {mo.get('Version')}")
            mk = b.ref(mo, 'Markers')
            expect([r.tag for r in b.referrers(mk)] == ['Sequence'], f'{b}: sequence Markers referred to by {[r.tag for r in b.referrers(mk)]}')
            before = a.seq_el(P.txt(e, 'Name'))
            expect(before is not None and before.find('MarkerOwner') is None, f'{a} already had a MarkerOwner on {P.txt(e, "Name")}')
        expect(any(e.find('MarkerOwner') is not None for e in b.objs('Sequence')), f'{b}: no sequence has a MarkerOwner')


@rule('markers.markers-class')
def _(ev):
    for s in ev.steps:
        for m in s.objs('Markers'):
            expect((m.get('ClassID'), m.get('Version')) == (MARKERS_CID, '4'), f"{s}: Markers {m.get('ClassID')} v{m.get('Version')}")
            if m.find('Markers') is not None:
                expect(m.find('Markers').get('Version') == '1', f'{s}: inner Markers list Version')


@rule('markers.list-entries')
def _(ev):
    for s in ev.steps:
        for m in s.objs('Markers'):
            lst = m.find('Markers')
            if lst is None:
                continue
            for e in lst.findall('Marker'):
                mk = s.ref(e, 'Second')
                expect(mk is not None and mk.tag == 'Marker', f'{s}: list entry does not point at a Marker')
                expect(P.txt(e, 'First') == dva(mk)['mMarkerID'], f'{s}: First is not the marker GUID')
        for tag in ('VideoClip', 'AudioClip'):
            for c in s.objs(tag):
                mk = s.ref(c, 'Clip/MarkerOwner/Markers')
                if mk is not None and media_of(s, c) is not None:
                    expect(mk.find('Markers') is None, f'{s}: a media clip Markers object has a list')


@rule('markers.byguid')
def _(ev):
    for s in ev.steps:
        for m in s.objs('Markers'):
            expect(P.txt(m, 'ByGUID') == 'byGUID', f"{s}: ByGUID = {P.txt(m, 'ByGUID')!r}")


@rule('markers.sequence-states-zero')
def _(ev):
    for s in ev.steps:
        expect(any(e.find('MarkerOwner') is not None for e in s.objs('Sequence')), f'{s}: no sequence markers')
        for e in s.objs('Sequence'):
            mk = s.ref(e, 'MarkerOwner/Markers')
            if mk is not None:
                expect(P.txt(mk, 'LastMetadataState') == ZERO and P.txt(mk, 'LastContentState') == ZERO, f'{s}: sequence Markers states not zero')


@rule('markers.media-content-state')
def _(ev):
    n = 0
    for s in ev.steps:
        for tag in ('VideoClip', 'AudioClip'):
            for c in s.objs(tag):
                med = media_of(s, c)
                mk = s.ref(c, 'Clip/MarkerOwner/Markers')
                if med is None or mk is None:
                    continue
                expect(P.txt(mk, 'LastContentState') == P.txt(med, 'ContentAndMetadataState'),
                       f'{s}: LastContentState differs from the Media ContentAndMetadataState'); n += 1
    expect(n, 'no media clip with Markers in the evidence')


@rule('markers.not-time-ordered')
def _(ev):
    for s in ev.steps:
        e = s.seq_el('clip-a')
        names = [dva(m)['mName'] for m in seq_markers(s, e)]
        expect(names == ['Chapter 01', 'Marker_Test'], f'{s}: list order {names}')
        t = [dva(m)['mStartTime']['ticks'] for m in seq_markers(s, e)]
        expect(t[0] > t[1], f'{s}: the list happens to be in time order')


@rule('markers.marker-class')
def _(ev):
    for s in ev.steps:
        ms = s.objs('Marker')
        expect(ms, f'{s}: no Marker objects')
        for m in ms:
            expect((m.get('ClassID'), m.get('Version')) == (MARKER_CID, '3'), f"{s}: Marker {m.get('ClassID')} v{m.get('Version')}")
            expect([c.tag for c in m] == ['DVAMarker'], f'{s}: Marker children {[c.tag for c in m]}')


@rule('markers.dvamarker-keys')
def _(ev):
    for s in ev.steps:
        e = s.seq_el('clip-a')
        got = {dva(m)['mName']: dva(m) for m in seq_markers(s, e)}
        expect(set(got) == {'Marker_Test', 'Chapter 01'}, f'{s}: names {set(got)}')
        a, b = got['Marker_Test'], got['Chapter 01']
        expect(a['mStartTime']['ticks'] == 508540032000 and b['mStartTime']['ticks'] == 2193078888000, 'start ticks')
        expect(508540032000 == 48 * 10594584000 and 2193078888000 == 207 * 10594584000, 'tick arithmetic')
        expect((a['mType'], b['mType']) == ('Comment', 'Chapter'), 'types')
        expect(a['mComment'] == 'this is a comment', 'comment text')
        for d in (a, b):
            cl = d['mCuePointList']
            expect(len(cl) == 1 and cl[0]['mKey'].startswith('keywordExtDVAv1_') and re.fullmatch(r'\{"color":\d+\}', cl[0]['mValue']), f'cue point {cl}')
        expect(a['mCuePointList'][0]['mKey'] != b['mCuePointList'][0]['mKey'], 'cue-point keys are the same on both markers')
        for x in s.ref(e, 'MarkerOwner/Markers').findall('Markers/Marker'):
            expect(P.txt(x, 'First') == dva(s.ref(x, 'Second'))['mMarkerID'], 'mMarkerID differs from First')


@rule('markers.json-form')
def _(ev):
    import json
    for s in ev.steps:
        expect(s.objs('Marker'), f'{s}: no Marker objects')
        for m in s.objs('Marker'):
            raw = P.txt(m, 'DVAMarker')
            d = json.loads(raw)['DVAMarker']
            expect(list(d) == sorted(d), f'{s}: keys not alphabetical: {list(d)}')
            expect(raw == json.dumps({'DVAMarker': d}, separators=(',', ':'), sort_keys=True, ensure_ascii=False), f'{s}: JSON has whitespace or other formatting')
            expect('\\"color\\"' in raw, f'{s}: mValue is not an escaped JSON string')


@rule('markers.colour-bgr')
def _(ev):
    for s in ev.steps:
        col = {dva(m)['mName']: int(re.search(r'\d+', dva(m)['mCuePointList'][0]['mValue']).group(0)) for m in s.objs('Marker')}
        expect(col.get('Marker_Test') == 4280578025 == 0xFF246FE9, f'orange: {col}')
        expect(col.get('Chapter 01') == 4289825711 == 0xFFB18BAF, f'pink: {col}')
        bgr = lambda h: 0xFF000000 | int(h[4:6], 16) << 16 | int(h[2:4], 16) << 8 | int(h[0:2], 16)
        expect(bgr('E96F24') == 4280578025 and bgr('AF8BB1') == 4289825711, 'N = 0xFF000000 | B<<16 | G<<8 | R does not give the stored values for #E96F24 / #AF8BB1')


@rule('markers.zero-length-no-duration')
def _(ev):
    for s in ev.steps:
        expect(s.objs('Marker'), f'{s}: no Marker objects')
        for m in s.objs('Marker'):
            keys = set(dva(m))
            expect(keys == {'mComment', 'mCuePointList', 'mMarkerID', 'mName', 'mStartTime', 'mType'}, f'{s}: keys {sorted(keys)}')
