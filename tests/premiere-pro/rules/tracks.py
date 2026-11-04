"""Checks for references/spec/08-tracks.md."""
from collections import Counter
from _lib import rule, expect, P
from _tracklib import key, closure, groups, tracks, new_seqs

AUDIO_TRACK_OBJECTS = Counter({'AudioClipTrack': 1, 'AudioComponentChain': 1, 'AudioFader': 1, 'AudioMeter': 1,
                               'StereoToStereoPanProcessor': 1, 'AudioComponentParam': 3})
MASTER_OBJECTS = Counter({'AudioMixTrack': 1, 'AudioComponentChain': 1, 'AudioFader': 1, 'AudioComponentParam': 2,
                          'AudioMeter': 1, 'DefaultPanProcessor': 1, 'AudioTrackInlet': 1})


def all_groups(s):
    for e in s.objs('Sequence'):
        g = groups(s, e)
        yield e, g['VideoTrackGroup'], g['AudioTrackGroup']


def param_names(s, comp):
    return [P.txt(s.ref(p), 'Name') for p in comp.findall('.//Params/Param')]


@rule('tracks.order')
def _(ev):
    for s in ev.steps:
        for e, vg, ag in all_groups(s):
            for g in (vg, ag):
                idx = [int(t.get('Index')) for t in g.findall('TrackGroup/Tracks/Track')]
                expect(idx == list(range(len(idx))), f'{s}: Track@Index {idx}')
                expect(all(t.get('ObjectURef') for t in g.findall('TrackGroup/Tracks/Track')), f'{s}: a Track entry is not an ObjectURef')
        if s.n == '03':   # New Sequence from Clip puts the clip on V1/A1
            e = s.seq_el('clip-a'); g = groups(s, e)
            for grp in ('VideoTrackGroup', 'AudioTrackGroup'):
                ts = tracks(s, g[grp])
                expect(ts[0].find('ClipTrack/ClipItems/TrackItems') is not None and all(t.find('ClipTrack/ClipItems/TrackItems') is None for t in ts[1:]), f'{s}: the clip is not on Index 0 of {grp}')
        if s.n == '10':   # V2 renamed Graphics
            v = tracks(s, groups(s, s.seq_el('clip-a'))['VideoTrackGroup'])
            expect(P.txt(v[1], 'ClipTrack/Track/Node/Properties/MZ.TrackName') == 'Graphics', f'{s}: Index 1 is not the renamed V2')
    expect({x.n for x in ev.steps} >= {'03', '10'}, 'evidence must include steps 03 and 10')


@rule('tracks.index-four-times')
def _(ev):
    for s in ev.steps:
        n = 0
        for e, vg, ag in all_groups(s):
            for g in (vg, ag):
                for tr in g.findall('TrackGroup/Tracks/Track'):
                    t = s.ref(tr)
                    vals = {tr.get('Index'), P.txt(t, 'ClipTrack/Track/Index'), P.txt(t, 'ClipTrack/ClipItems/Index'), P.txt(t, 'ClipTrack/TransitionItems/Index')}
                    expect(len(vals) == 1, f'{s}: track position written as {vals}'); n += 1
        expect(n, f'{s}: no tracks')


@rule('tracks.ids')
def _(ev):
    for a, b in ev.pairs:
        made = new_seqs(a, b)
        expect(made, f'{a}→{b}: no new sequence')
        for e in made:
            g = groups(b, e)
            for grp, first, extra in (('VideoTrackGroup', 1, 1), ('AudioTrackGroup', 2, 2)):
                ids = [int(P.txt(t, 'ClipTrack/Track/ID')) for t in tracks(b, g[grp])]
                expect(len(ids) == len(set(ids)) and min(ids) == first, f'{b}: {grp} IDs {ids}')
                nxt = int(P.txt(g[grp], 'TrackGroup/NextTrackID'))
                expect(nxt == len(ids) + extra, f'{b}: {grp} NextTrackID {nxt} for {len(ids)} tracks')
            expect(P.txt(b.ref(g['AudioTrackGroup'], 'MasterTrack'), 'Track/ID') == '1', f'{b}: master track ID')


@rule('tracks.object-counts')
def _(ev):
    for a, b in ev.pairs:
        made = new_seqs(a, b)
        expect(made, f'{a}→{b}: no new sequence')
        for e in made:
            g = groups(b, e)
            for t in tracks(b, g['VideoTrackGroup']):
                c = closure(b, t)
                expect(len(c) == 1, f'{b}: a video track reaches {len(c)} objects')
            ats = tracks(b, g['AudioTrackGroup'])
            expect(len(ats) == 4, f'{b}: {len(ats)} audio tracks')
            for t in ats:
                c = Counter(x.tag for x in closure(b, t).values())
                expect(c == AUDIO_TRACK_OBJECTS, f'{b}: an audio track is {dict(c)}')
                fader = next(b.ref(x) for x in b.ref(t, 'AudioTrack/ComponentOwner/Components').findall('ComponentChain/Components/Component') if b.ref(x).tag == 'AudioFader')
                expect(param_names(b, fader) == ['Volume', 'Mute'], f'{b}: fader params {param_names(b, fader)}')
                expect(param_names(b, b.ref(t, 'AudioTrack/Panner')) == ['Balance'], f'{b}: panner params')


@rule('tracks.master')
def _(ev):
    for s in ev.steps:
        for e, vg, ag in all_groups(s):
            m = s.ref(ag, 'MasterTrack')
            ts = tracks(s, ag)
            stop = set()
            for t in ts:
                stop |= set(closure(s, t))
            c = Counter(x.tag for x in closure(s, m, stop).values())
            expect(c == MASTER_OBJECTS, f'{s}: master is {dict(c)}')
            inlet = s.ref(m, 'Inlet')
            src = [x.get('ObjectURef') for x in inlet.findall('Sources/Source')]
            expect(src == [x.get('ObjectURef') for x in ag.findall('TrackGroup/Tracks/Track')], f'{s}: inlet Sources differ from Tracks')


@rule('tracks.empty-no-trackitems')
def _(ev):
    empty = full = 0
    for s in ev.steps:
        for e, vg, ag in all_groups(s):
            for t in tracks(s, vg) + tracks(s, ag):
                for cont in ('ClipTrack/ClipItems', 'ClipTrack/TransitionItems'):
                    c = t.find(cont)
                    kids = [x.tag for x in c]
                    if 'TrackItems' in kids:
                        full += 1
                        expect(kids.index('TrackItems') < kids.index('MediaType') and len(t.findall(cont + '/TrackItems/TrackItem')), f'{s}: TrackItems after MediaType or empty')
                    else:
                        empty += 1
    expect(empty and full, 'evidence lacks empty or populated containers')


@rule('tracks.expanded-height')
def _(ev):
    for s in ev.steps:
        ts = [t for e, vg, ag in all_groups(s) for t in tracks(s, vg) + tracks(s, ag)]
        expect(ts and all(t.find('ClipTrack/Track/Node/Properties/TL.SQTrackExpandedHeight') is not None for t in ts), f'{s}: a track without TL.SQTrackExpandedHeight')


def _named_tracks(s, seq):
    g = groups(s, s.seq_el(seq))
    return tracks(s, g['VideoTrackGroup']) + tracks(s, g['AudioTrackGroup'])


@rule('tracks.track-targeted')
def _(ev):
    for a, b in ev.pairs:
        va = [P.txt(t, 'ClipTrack/Track/Node/Properties/MZ.TrackTargeted') for t in _named_tracks(a, 'clip-a')]
        vb = [P.txt(t, 'ClipTrack/Track/Node/Properties/MZ.TrackTargeted') for t in _named_tracks(b, 'clip-a')]
        expect(None not in va + vb and va != vb and set(va + vb) <= {'0', '1'}, f'{a}→{b}: TrackTargeted {va} → {vb}')


@rule('tracks.patching-state')
def _(ev):
    for a, b in ev.pairs:
        ea, eb = a.seq_el('clip-a'), b.seq_el('clip-a')
        hsl = lambda e: [x.tag for x in e.find('Node/Properties') if x.tag.startswith('HSL.TimelinePatchingAndTargeting.') and 'Patches' in x.tag]
        expect(not hsl(ea) and hsl(eb), f'{a}→{b}: patch keys {hsl(ea)} → {hsl(eb)}')
        src = lambda s: [t.find('ClipTrack/Track/Node/Properties/MZ.SourceTrackNumber') is not None and t.find('ClipTrack/Track/Node/Properties/MZ.SourceTrackState') is not None
                         for t in _named_tracks(s, 'clip-a') if t.tag == 'AudioClipTrack']
        expect(not any(src(a)) and all(src(b)), f'{a}→{b}: audio MZ.SourceTrackNumber/State {src(a)} → {src(b)}')
        expect(any('AudioPatches' in k for k in hsl(eb)), f'{b}: no AudioPatches key')
        expect(len(b.objs('Sequence')) > len(a.objs('Sequence')), f'{b}: no other sequence was made/opened')


@rule('tracks.name')
def _(ev):
    for a, b in ev.pairs:
        na = [P.txt(t, 'ClipTrack/Track/Node/Properties/MZ.TrackName') for t in _named_tracks(a, 'clip-a')]
        nb = [P.txt(t, 'ClipTrack/Track/Node/Properties/MZ.TrackName') for t in _named_tracks(b, 'clip-a')]
        expect(not any(na) and nb.count('Graphics') == 1 and sum(map(bool, nb)) == 1, f'{a}→{b}: names {na} → {nb}')


@rule('tracks.name-script')
def _(ev):
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        names = lambda s: {(t.tag, P.txt(t, 'ClipTrack/Track/Node/Properties/MZ.TrackName')) for e in s.objs('Sequence') for t in _named_tracks(s, P.txt(e, 'Name'))}
        new = {n for n in names(b) - names(a) if n[1]}
        expect(any(tag == 'AudioClipTrack' for tag, _ in new), f'{a}→{b}: no script-named audio track ({new})')


@rule('tracks.lock')
def _(ev):
    for a, b in ev.pairs:
        la = [t.find('ClipTrack/Track/IsLocked') for t in _named_tracks(a, 'clip-a')]
        lb = [t for t in _named_tracks(b, 'clip-a') if t.find('ClipTrack/Track/IsLocked') is not None]
        expect(all(x is None for x in la) and len(lb) == 1, f'{a}→{b}: locked tracks {len(lb)}')
        tr = lb[0].find('ClipTrack/Track')
        expect(P.txt(tr, 'IsLocked') == 'true' and list(tr)[-1].tag == 'IsLocked', f'{b}: IsLocked value/position')


@rule('tracks.unlock-script')
def _(ev):
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        locked = lambda s: [t.find('ClipTrack/Track/IsLocked') is not None for t in _named_tracks(s, 'clip-a')]
        expect(any(locked(a)) and not any(locked(b)), f'{a}→{b}: clip-a locks {locked(a)} → {locked(b)}')


@rule('tracks.mute')
def _(ev):
    for a, b in ev.pairs:
        def mute(s):
            t = [t for t in _named_tracks(s, 'clip-a') if t.tag == 'AudioClipTrack'][0]
            ch = s.ref(t, 'AudioTrack/ComponentOwner/Components')
            fader = next(s.ref(x) for x in ch.findall('ComponentChain/Components/Component') if s.ref(x).tag == 'AudioFader')
            return next(s.ref(p) for p in fader.findall('.//Params/Param') if P.txt(s.ref(p), 'Name') == 'Mute')
        ma, mb = mute(a), mute(b)
        expect(ma.find('StartKeyframe') is None and ma.find('CurrentValue') is None, f'{a}: Mute already has values')
        kids = [c.tag for c in mb]
        expect(kids[:3] == ['StartKeyframe', 'CurrentValue', 'Name'], f'{b}: Mute children {kids}')
        expect(P.txt(mb, 'StartKeyframe') == '-91445760000000000,true,0,0,0,0,0,0' and P.txt(mb, 'CurrentValue') == 'true', f'{b}: Mute values')
