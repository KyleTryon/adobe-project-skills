"""Timeline helpers shared by items.py and transitions.py (not a rules module)."""
from collections import Counter
from _lib import expect, media_of, P

ITEM_TAGS = ('VideoClipTrackItem', 'AudioClipTrackItem')
CLIP_TAGS = ('VideoClip', 'AudioClip')
# the 11 objects of a placed linked A/V pair (two audio channels)
PAIR = Counter({'Link': 1, 'VideoClipTrackItem': 1, 'AudioClipTrackItem': 1, 'SubClip': 2, 'VideoClip': 1,
                'AudioClip': 1, 'VideoComponentChain': 1, 'AudioComponentChain': 1, 'SecondaryContent': 2})
ITEM_CLASSES = set(PAIR)


def _int(el, path):
    t = P.txt(el, path)
    return int(t) if t not in (None, '') else None


def timeline(s):
    """{seq name: {'frame': ticks, 'tracks': [{'tag', 'el', 'entries': [(Index, item el)], 'items': [dict]}],
    'links': [Link el], 'el': Sequence}}"""
    out = {}
    for seq in s.objs('Sequence'):
        name = P.txt(seq, 'Name')
        d = {'el': seq, 'tracks': [], 'frame': None, 'links': []}
        for tg in seq.findall('TrackGroups/TrackGroup/Second'):
            grp = s.ref(tg)
            if grp is None:
                continue
            if grp.tag == 'VideoTrackGroup':
                d['frame'] = _int(grp, './/FrameRate')
            for tr in grp.findall('.//Tracks/Track'):
                trk = s.ref(tr)
                entries = [(int(t.get('Index')), s.ref(t)) for t in trk.findall('ClipTrack/ClipItems/TrackItems/TrackItem')]
                trans = [(int(t.get('Index')), s.ref(t)) for t in trk.findall('ClipTrack/TransitionItems/TrackItems/TrackItem')]
                d['tracks'].append({'tag': trk.tag, 'el': trk, 'entries': entries, 'trans': trans,
                                    'items': [item(s, e) for _, e in entries]})
        lc = seq.find('PersistentGroupContainer/LinkContainer')
        d['link_container'] = lc
        d['links'] = [s.ref(l) for l in seq.findall('PersistentGroupContainer/LinkContainer/Links/Link')]
        d['link_entries'] = seq.findall('PersistentGroupContainer/LinkContainer/Links/Link')
        out[name] = d
    return out


def item(s, el):
    sc = s.ref(el, 'ClipTrackItem/SubClip')
    clip = s.ref(sc, 'Clip') if sc is not None else None
    ti = el.find('ClipTrackItem/TrackItem')
    lab = clip.find('Clip/Node/Properties') if clip is not None else None
    return {'el': el, 'key': el.get('ObjectID'), 'tag': el.tag, 'sub': sc, 'clip': clip,
            'start_present': ti.find('Start') is not None, 'start': _int(ti, 'Start') or 0, 'end': _int(ti, 'End'),
            'in_present': clip is not None and clip.find('Clip/InPoint') is not None,
            'in': _int(clip, 'Clip/InPoint') if clip is not None else None,
            'out': _int(clip, 'Clip/OutPoint') if clip is not None else None,
            'speed': float(P.txt(clip, 'Clip/PlaybackSpeed') or 1) if clip is not None else 1.0,
            'clipid': P.txt(clip, 'Clip/ClipID') if clip is not None else None,
            'aid': P.txt(el, 'ID') if el.tag == 'AudioClipTrackItem' else None,
            'label': P.txt(lab, 'asl.clip.label.name') if lab is not None else None,
            'name': P.txt(sc, 'Name') if sc is not None else None}


def all_items(s):
    return [(n, t, it) for n, d in timeline(s).items() for t in d['tracks'] for it in t['items']]


def media_len(s, clip):
    """Duration of the clip's media stream in ticks (VideoStream/AudioStream Duration)."""
    med = media_of(s, clip)
    expect(med is not None, f'{s}: clip has no media')
    want = 'VideoStream' if clip.tag == 'VideoClip' else 'AudioStream'
    for x in med.iter():
        r = s.ref(x) if (x.get('ObjectRef') or x.get('ObjectURef')) else None
        if r is not None and r.tag == want:
            return _int(r, 'Duration')
    raise AssertionError(f'{s}: no {want} for {P.txt(med, "Title") or "media"}')


def tl_count(s):
    return Counter(e.tag for e in s.root if e.tag in ITEM_CLASSES)


def link_members(s, link):
    return [s.ref(t) for t in link.findall('TrackItemGroup/TrackItems/TrackItem')]


def need_items(ev):
    for s in ev.steps:
        expect(all_items(s), f'{s}: no track items')
