"""Checks for references/spec/07-sequences.md."""
from _lib import rule, expect, P
from _tracklib import (GROUP_OF, DATA_GUID, key, closure, groups, tracks, prop, length, seq_mc, seq_sources, new_seqs)

PREVIEW_1080_23976 = 'fc3cd4d9-d839-8259-9276-05c5000000ea'
EDITING_MODE = '795454d9-d3c2-429d-9474-923ab13b7018'
WORK_OUT_NEW = 15235011792000


@rule('seq.object')
def _(ev):
    for s in ev.steps:
        seqs = s.objs('Sequence')
        expect(seqs, f'{s}: no sequences')
        for e in seqs:
            kids = [c.tag for c in e if c.tag != 'MarkerOwner']
            expect(kids == ['Node', 'PersistentGroupContainer', 'TrackGroups', 'Name', 'PreviewFormatIdentifier'], f'{s}: Sequence children {kids}')
            expect(e.get('ObjectUID') and e.find('PersistentGroupContainer/LinkContainer') is not None, f'{s}: identity/LinkContainer')
            for tg in e.findall('TrackGroups/TrackGroup'):
                expect(tg.get('Index') is not None and P.txt(tg, 'First') in GROUP_OF and s.ref(tg, 'Second') is not None, f'{s}: TrackGroup entry')
            refs = sorted(r.tag for r in s.referrers(e))
            expect(refs == ['AudioSequenceSource', 'VideoSequenceSource'], f'{s}: Sequence referred to by {refs}')


@rule('seq.media-types')
def _(ev):
    for s in ev.steps:
        for e in s.objs('Sequence'):
            g = {}
            for tg in e.findall('TrackGroups/TrackGroup'):
                grp = s.ref(tg, 'Second')
                expect(GROUP_OF[P.txt(tg, 'First')] == grp.tag, f'{s}: {P.txt(tg, "First")} -> {grp.tag}')
                g[P.txt(tg, 'First')] = grp
            expect(set(g) == set(GROUP_OF), f'{s}: groups {set(g)}')
            expect(g[DATA_GUID].find('TrackGroup/Tracks') is None, f'{s}: DataTrackGroup has tracks')
            for guid, grp in g.items():
                for t in tracks(s, grp):
                    for path in ('ClipTrack/Track/MediaType', 'ClipTrack/ClipItems/MediaType', 'ClipTrack/TransitionItems/MediaType'):
                        expect(P.txt(t, path) == guid, f'{s}: {t.tag} {path} = {P.txt(t, path)}')


@rule('seq.frame-size-rate')
def _(ev):
    for s in ev.steps:
        for e in s.objs('Sequence'):
            g = groups(s, e)
            rect = P.txt(g['VideoTrackGroup'], 'FrameRect')
            expect(rect == '0,0,1920,1080', f'{s}: FrameRect {rect}')
            expect((prop(e, 'MZ.Sequence.PreviewFrameSizeWidth'), prop(e, 'MZ.Sequence.PreviewFrameSizeHeight')) == ('1920', '1080'), f'{s}: preview size')
            for t in tracks(s, g['VideoTrackGroup']):
                for ti in t.findall('ClipTrack/ClipItems/TrackItems/TrackItem'):
                    it = s.ref(ti)
                    expect(P.txt(it, 'FrameRect') == rect and it.find('PixelAspectRatio') is not None, f'{s}: item FrameRect/PixelAspectRatio')
            expect(P.txt(g['VideoTrackGroup'], 'TrackGroup/FrameRate') == P.txt(g['DataTrackGroup'], 'TrackGroup/FrameRate'), f'{s}: video and data rates differ')
            expect(P.txt(g['AudioTrackGroup'], 'TrackGroup/FrameRate'), f'{s}: no audio rate')
        if s.n == '19':   # the 1280x720 interview clip on a 1080p sequence, saved by Premiere
            med = next(m for m in s.objs('Media') if (P.txt(m, 'FilePath') or '').endswith('/interview.mp4'))
            expect(P.txt(s.ref(med, 'VideoStream'), 'FrameRect') == '0,0,1280,720', f'{s}: interview.mp4 is not 1280x720')


@rule('seq.editing-mode-guid')
def _(ev):
    for s in ev.steps:
        vals = {prop(e, 'MZ.Sequence.EditingModeGUID') for e in s.objs('Sequence')}
        expect(vals == {EDITING_MODE}, f'{s}: EditingModeGUID {vals}')


@rule('seq.preview-format')
def _(ev):
    for a, b in ev.pairs:
        made = new_seqs(a, b)
        expect(made, f'{a}→{b}: no new sequence')
        for e in made:
            g = groups(b, e)
            expect(P.txt(g['VideoTrackGroup'], 'FrameRect') == '0,0,1920,1080' and P.txt(g['VideoTrackGroup'], 'TrackGroup/FrameRate') == '10594584000', f'{b}: not 1080p 23.976')
            expect(P.txt(e, 'PreviewFormatIdentifier') == PREVIEW_1080_23976, f'{b}: PreviewFormatIdentifier {P.txt(e, "PreviewFormatIdentifier")}')


@rule('seq.edit-line')
def _(ev):
    for a, b in ev.pairs:
        ea, eb = a.seq_el('clip-a'), b.seq_el('clip-a')
        expect(prop(ea, 'MZ.EditLine') != prop(eb, 'MZ.EditLine'), f'{a}→{b}: EditLine did not move')
        expect(prop(eb, 'MZ.WorkOutPoint') != str(length(b, eb)), f'{b}: WorkOutPoint equals the length here')


@rule('seq.length-zoomout')
def _(ev):
    for s in ev.steps:
        for e in s.objs('Sequence'):
            want = length(s, e)
            z = int(prop(e, 'Monitor.ProgramZoomOut'))
            expect(z == want, f'{s}: {P.txt(e, "Name")} ProgramZoomOut {z}, longest clip End {want}')


def _series(ev, name='clip-a'):
    out = []
    for s in ev.steps:
        e = s.seq_el(name)
        expect(e is not None, f'{s}: no {name}')
        out.append((s, e))
    expect(len(out) >= 3, 'need a run of steps')
    return out


@rule('seq.zoomout-follows')
def _(ev):
    ser = _series(ev)
    lens = [length(s, e) for s, e in ser]
    expect(any(y > x for x, y in zip(lens, lens[1:])) and any(y < x for x, y in zip(lens, lens[1:])), f'length never both rose and fell: {lens}')
    for s, e in ser:
        expect(int(prop(e, 'Monitor.ProgramZoomOut')) == length(s, e), f'{s}: ZoomOut != length')


@rule('seq.workout-fixed')
def _(ev):
    ser = _series(ev)
    w = {prop(e, 'MZ.WorkOutPoint') for _, e in ser}
    first_len = length(*ser[0])
    expect(w == {str(first_len)}, f'WorkOutPoint {w}, length when made {first_len}')
    expect(len({length(s, e) for s, e in ser}) > 1, 'length never changed')


@rule('seq.original-duration-rises')
def _(ev):
    ser = _series(ev)
    prev, top = 0, 0
    for s, e in ser:
        ods = {int(P.txt(o, 'OriginalDuration')) for o in seq_sources(s, e)}
        expect(len(ods) == 1, f'{s}: the two sources disagree {ods}')
        od = ods.pop()
        top = max(top, length(s, e))
        expect(od >= prev and od >= top, f'{s}: OriginalDuration {od} fell or is below the longest length so far {top}')
        prev = od


def _cuts(s, name='clip-a'):
    return [[(i['start_ticks'], i['end_ticks'], i['in_ticks'], i['out_ticks'], i['name']) for i in t['items']] for t in s.seq(name)['tracks']]


@rule('seq.change-version')
def _(ev):
    ser = _series(ev)
    vals = []
    for (sa, ea), (sb, eb) in zip(ser, ser[1:]):
        va, vb = int(P.txt(seq_mc(sa, ea), 'MasterClipChangeVersion')), int(P.txt(seq_mc(sb, eb), 'MasterClipChangeVersion'))
        edited = _cuts(sa) != _cuts(sb)
        expect(vb > va if edited else vb == va, f'{sa}→{sb}: MasterClipChangeVersion {va}→{vb}, edited={edited}')
    vals = [int(P.txt(seq_mc(s, e), 'MasterClipChangeVersion')) for s, e in ser]
    expect(sorted(set(vals)) == [16, 28, 35, 41, 47], f'values {vals}')


@rule('seq.change-version-script')
def _(ev):
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        ea, eb = a.seq_el('clip-a'), b.seq_el('clip-a')
        expect(_cuts(a) != _cuts(b), f'{a}→{b}: clip-a not edited')
        va, vb = P.txt(seq_mc(a, ea), 'MasterClipChangeVersion'), P.txt(seq_mc(b, eb), 'MasterClipChangeVersion')
        expect(va == vb, f'{a}→{b}: MasterClipChangeVersion {va}→{vb}')


def _clip_objects(s, link):
    """The objects a placed linked clip adds: Link + both items and what they own (not the media's)."""
    stop = {key(e) for e in s.objs('Sequence')}
    for mc in s.objs('MasterClip'):
        srcs = [s.ref(s.ref(c), 'Clip/Source') for c in mc.findall('Clips/Clip')]
        if not any(x is not None and x.tag.endswith('SequenceSource') for x in srcs):
            stop |= set(closure(s, mc))
    return closure(s, link, stop)


@rule('seq.new-from-clip')
def _(ev):
    for a, b in ev.pairs:
        made = new_seqs(a, b)
        expect(len(made) == 1, f'{a}→{b}: {len(made)} new sequences')
        e = made[0]
        name = P.txt(e, 'Name')
        cpi = next(c for c in b.objs('ClipProjectItem') if P.txt(c, 'ProjectItem/Name') == name)
        bin_ = next(x for x in b.objs('BinProjectItem') + b.objs('RootProjectItem') if any(i.get('ObjectURef') == cpi.get('ObjectUID') for i in x.findall('ProjectItemContainer/Items/Item')))
        src_name = name + '.mp4'
        expect(any(b.ref(i).tag == 'ClipProjectItem' and P.txt(b.ref(i), 'ProjectItem/Name') == src_name for i in bin_.findall('ProjectItemContainer/Items/Item')), f'{b}: {name} is not in the bin of {src_name}')
        g = groups(b, e)
        expect((len(tracks(b, g['VideoTrackGroup'])), len(tracks(b, g['AudioTrackGroup']))) == (3, 3), f'{b}: track counts')
        sq = b.seq(name)
        v1, a1 = sq['tracks'][0]['items'], [t for t in sq['tracks'] if t['type'] == 'AudioClipTrack'][0]['items']
        expect(len(v1) == 1 == len(a1) and v1[0]['start'] == 0 == a1[0]['start'] and v1[0]['name'] == src_name, f'{b}: clip not on V1/A1 at 0')
        links = [b.ref(l) for l in e.findall('PersistentGroupContainer/LinkContainer/Links/Link')]
        expect(len(links) == 1, f'{b}: {len(links)} links')
        d = P.diff_projects(a.xml, b.xml)
        total = next(x['objects'] for x in d['added'] if x['name'] == name)
        clip = len(_clip_objects(b, links[0]))
        expect((total, clip) == (65, 11), f'{b}: {total} objects, {clip} for the clip')
        end = str(v1[0]['end_ticks'])
        expect(prop(e, 'Monitor.ProgramZoomOut') == end and prop(e, 'MZ.WorkOutPoint') == end, f'{b}: ZoomOut/WorkOut')
        expect({P.txt(o, 'OriginalDuration') for o in seq_sources(b, e)} == {end}, f'{b}: OriginalDuration')
        mc_src = b.ref(b.ref(cpi, 'MasterClip'), 'Clips/Clip')
        vs = next(m for m in b.objs('Media') if P.txt(m, 'FilePath').endswith('/' + src_name))
        expect(P.txt(b.ref(vs, 'VideoStream'), 'FrameRect') == P.txt(g['VideoTrackGroup'], 'FrameRect')
               and P.txt(b.ref(vs, 'VideoStream'), 'FrameRate') == P.txt(g['VideoTrackGroup'], 'TrackGroup/FrameRate'), f'{b}: settings not the clip\'s')


def _is_empty(s, e):
    sq = s.seq(P.txt(e, 'Name'))
    mc = seq_mc(s, e)
    clips = [s.ref(c) for c in mc.findall('Clips/Clip')]
    return (prop(e, 'MZ.EditLine') == '0' and prop(e, 'MZ.WorkInPoint') == '0'
            and e.find('PersistentGroupContainer/LinkContainer/Links') is None
            and not any(t.find('ClipTrack/ClipItems/TrackItems') is not None or t.find('ClipTrack/TransitionItems/TrackItems') is not None
                        for g in groups(s, e).values() if g.tag != 'DataTrackGroup' for t in tracks(s, g))
            and mc.find('Node') is None
            and all(c.find('Clip/InPoint') is None and c.find('Clip/OutPoint') is None for c in clips)
            and not any(t['items'] for t in sq['tracks']))


@rule('seq.new-sequence-dialog')
def _(ev):
    for a, b in ev.pairs:
        made = new_seqs(a, b)
        expect(len(made) == 1, f'{a}→{b}: {len(made)} new sequences')
        e = made[0]
        cpi = next(c for c in b.objs('ClipProjectItem') if P.txt(c, 'ProjectItem/Name') == P.txt(e, 'Name'))
        root = b.objs('RootProjectItem')[0]
        expect(any(i.get('ObjectURef') == cpi.get('ObjectUID') for i in root.findall('ProjectItemContainer/Items/Item')), f'{b}: not in the root bin')
        g = groups(b, e)
        expect((len(tracks(b, g['VideoTrackGroup'])), len(tracks(b, g['AudioTrackGroup']))) == (3, 4), f'{b}: track counts')
        expect(_is_empty(b, e), f'{b}: the new sequence is not empty')
        d = P.diff_projects(a.xml, b.xml)
        expect(next(x['objects'] for x in d['added'] if x['name'] == P.txt(e, 'Name')) == 62, f'{b}: object count')
        expect(prop(e, 'Monitor.ProgramZoomOut') == '0' and {P.txt(o, 'OriginalDuration') for o in seq_sources(b, e)} == {'0'}, f'{b}: ZoomOut/OriginalDuration')
        expect(prop(e, 'MZ.WorkOutPoint') == str(WORK_OUT_NEW) and WORK_OUT_NEW == 1438 * 10594584000, f'{b}: WorkOutPoint')


@rule('seq.empty-sequence')
def _(ev):
    sizes = {}
    for a, b in ev.pairs:
        for e in new_seqs(a, b):
            d = P.diff_projects(a.xml, b.xml)
            total = next(x['objects'] for x in d['added'] if x['name'] == P.txt(e, 'Name'))
            links = [b.ref(l) for l in e.findall('PersistentGroupContainer/LinkContainer/Links/Link')]
            clip = sum(len(_clip_objects(b, l)) for l in links)
            na = len(tracks(b, groups(b, e)['AudioTrackGroup']))
            sizes[(b.n, P.txt(e, 'Name'))] = total - clip - 8 * (na - 3)
            if not links:
                expect(_is_empty(b, e), f'{b}: {P.txt(e, "Name")} has no clips but is not empty in every listed way')
    expect(len(sizes) == 2 and set(sizes.values()) == {54}, f'empty 3+3 base sizes {sizes}')


@rule('seq.clone-empty-new')
def _(ev):
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        made = new_seqs(a, b)
        expect(len(made) == 1, f'{a}→{b}: {len(made)} new sequences')
        sq = b.seq(P.txt(made[0], 'Name'))
        expect(any(t['items'] for t in sq['tracks']), f'{b}: the new sequence is empty')
        expect(_is_empty(a, a.seq_el('Custom')), f'{a}: Custom is not empty')
