"""Helpers shared by sequences.py and tracks.py (not a check module)."""
from _lib import P

VIDEO_GUID = '228cda18-3625-4d2d-951e-348879e4ed93'
AUDIO_GUID = '80b8e3d5-6dca-4195-aefb-cb5f407ab009'
DATA_GUID = 'd8143ffe-eec4-4d2a-a909-d5f7bf094dc5'
GROUP_OF = {VIDEO_GUID: 'VideoTrackGroup', AUDIO_GUID: 'AudioTrackGroup', DATA_GUID: 'DataTrackGroup'}


def key(e):
    return e.get('ObjectID') or e.get('ObjectUID')


def closure(s, el, stop=()):
    """Every object reachable from el by references (el included), not entering `stop` keys."""
    seen, todo = {}, [el]
    while todo:
        e = todo.pop()
        k = key(e)
        if k in seen or k in stop:
            continue
        seen[k] = e
        for x in e.iter():
            r = x.get('ObjectRef') or x.get('ObjectURef')
            if r and r in s.ids:
                todo.append(s.ids[r])
    return seen


def groups(s, seq_el):
    """{group tag: group element} for a Sequence."""
    out = {}
    for tg in seq_el.findall('TrackGroups/TrackGroup'):
        g = s.ref(tg, 'Second')
        out[g.tag] = g
    return out


def tracks(s, group):
    return [s.ref(t) for t in group.findall('TrackGroup/Tracks/Track')]


def prop(e, k):
    return P.txt(e, f'Node/Properties/{k}')


def length(s, seq_el):
    sq = s.seq(P.txt(seq_el, 'Name'))
    return max((i['end_ticks'] for t in sq['tracks'] for i in t['items']), default=0)


def seq_mc(s, seq_el):
    """The MasterClip whose clips use this sequence's sources."""
    for mc in s.objs('MasterClip'):
        for c in mc.findall('Clips/Clip'):
            cl = s.ref(c)
            src = s.ref(cl, 'Clip/Source') if cl is not None else None
            if src is not None and src.tag.endswith('SequenceSource') and s.ref(src, 'SequenceSource/Sequence') is seq_el:
                return mc
    return None


def seq_sources(s, seq_el):
    return [o for o in s.objs('VideoSequenceSource') + s.objs('AudioSequenceSource') if s.ref(o, 'SequenceSource/Sequence') is seq_el]


def new_seqs(a, b):
    names = {P.txt(e, 'Name') for e in a.objs('Sequence')}
    return [e for e in b.objs('Sequence') if P.txt(e, 'Name') not in names]
