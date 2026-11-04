"""Checks for references/spec/03-value-encodings.md."""
import base64, hashlib, re
from _lib import rule, expect, P, dva

TPS = 254016000000


@rule('values.rates')
def _(ev):
    for s in ev.steps:
        v = {int(P.txt(e, 'FrameRate')) for e in s.objs('VideoStream')}
        a = {int(P.txt(e, 'FrameRate')) for e in s.objs('AudioStream')}
        expect({10594584000, 10160640000, 8475667200} <= v, f'{s}: video rates {sorted(v)}')
        expect(a == {5292000}, f'{s}: audio rates {sorted(a)}')
        expect(abs(TPS / 10594584000 - 24000 / 1001) < 1e-9 and TPS / 10160640000 == 25 and abs(TPS / 8475667200 - 30000 / 1001) < 1e-9
               and TPS / 5292000 == 48000, 'rates are not 23.976, 25, 29.97 fps and 48 kHz')
        expect(10594584000 / 5292000 == 2002, 'a 23.976 frame is not 2002 samples')


def track_items(s):
    return [e for t in ('VideoClipTrackItem', 'AudioClipTrackItem') for e in s.objs(t)]


@rule('values.defaults-omitted')
def _(ev):
    seen = set()
    for s in ev.steps:
        items = track_items(s)
        expect(not any(P.txt(e, './/TrackItem/Start') == '0' for e in items), f'{s}: TrackItem/Start 0 written')
        if any(e.find('.//TrackItem/Start') is None for e in items) and any(e.find('.//TrackItem/Start') is not None for e in items):
            seen.add('start')
        expect(not any('Motion' in (P.txt(c, './/MatchName') or '') for c in s.objs('VideoFilterComponent')), f'{s}: a Motion component is written')
        if s.objs('VideoClipTrackItem'):
            seen.add('motion')
        expect(not any(len(x) == 0 for x in s.root.iter('Properties')), f'{s}: an empty Node/Properties is written')
        if any(n.find('Properties') is None for n in s.root.iter('Node')):
            seen.add('props')
        expect('false' not in {x.text for x in s.root.iter('IsLocked')}, f'{s}: IsLocked false written')
        tracks = s.objs('VideoClipTrack') + s.objs('AudioClipTrack')
        named = [t for t in tracks if t.find('.//MZ.TrackName') is not None]
        expect(len(named) < len(tracks), f'{s}: every track has a name written')
        seen.add('track')
        fader = [p for f in s.objs('AudioFader') for p in (s.ref(x) for x in f.iter() if x.get('ObjectRef')) if p is not None and p.tag == 'AudioComponentParam']
        dflt = [p for p in fader if P.txt(p, 'Name') in ('Volume', 'Mute') and p.find('StartKeyframe') is None]
        expect(not any(P.txt(p, 'Name') == 'Volume' and p.find('StartKeyframe') is not None for p in fader), f'{s}: fader Volume StartKeyframe written at default')
        if dflt:
            seen.add('fader')
        for m in s.objs('Marker'):
            expect(set(dva(m)) == {'mComment', 'mCuePointList', 'mMarkerID', 'mName', 'mStartTime', 'mType'}, f'{s}: marker keys {sorted(dva(m))}')
            seen.add('marker')
    expect(seen == {'start', 'motion', 'props', 'track', 'fader', 'marker'}, f'evidence shows only {sorted(seen)}')


def effect_params(s):
    out = []
    for c in s.objs('VideoFilterComponent') + s.objs('AudioFilterComponent'):
        out += [s.ref(x) for x in c.findall('.//Params/Param')]
    return [p for p in out if p is not None]


@rule('values.always-written')
def _(ev):
    zero = 0
    for s in ev.steps:
        for p in effect_params(s):
            expect(p.find('StartKeyframe') is not None, f'{s}: effect param {P.txt(p, "Name")} has no StartKeyframe')
        for sc in s.objs('SubClip'):
            c = s.ref(sc, 'Clip')
            expect(c.find('Clip/InPoint') is not None, f'{s}: timeline clip without Clip/InPoint')
            zero += P.txt(c, 'Clip/InPoint') == '0'
    expect(zero and any(effect_params(s) for s in ev.steps), 'evidence has no 0 InPoint or no effect params')


BLOB = re.compile(r'\n(\t*)<(\w+) Encoding="base64" BinaryHash="([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})">([A-Za-z0-9+/=]+)\n\1</\2>')


def blobs(s):
    return BLOB.findall(s.xml)


@rule('values.blob-form')
def _(ev):
    for s in ev.steps:
        b = blobs(s)
        n_attr = len(re.findall(r'Encoding="base64"', s.xml))
        expect(b and len(b) == n_attr, f'{s}: {n_attr} base64 elements, {len(b)} in the documented form')
        expect({t for _, t, _, _ in b} == {'ModificationState', 'TranscriptData'}, f'{s}: blob tags {sorted({t for _, t, _, _ in b})}')


@rule('values.binaryhash-length')
def _(ev):
    n = 0
    for s in ev.steps:
        for _, tag, h, data in blobs(s):
            d = base64.b64decode(data)
            expect(int(h.replace('-', '')[24:], 16) == len(d) + 12, f'{s}: {tag} hash length part {h[-8:]} vs {len(d)}+12')
            hx = h.replace('-', '')[:24]
            for alg in ('md5', 'sha1', 'sha256'):
                for src in (d, data.encode()):
                    expect(hashlib.new(alg, src).hexdigest()[:24] != hx, f'{s}: {tag} content part is {alg}')
            n += 1
    expect(n, 'no blobs in the evidence')


@rule('values.binaryhash-content-unchecked')
def _(ev):
    for s in ev.steps:
        expect(s.generated, f'{s} is not script-written')
        t = [x for x in blobs(s) if x[1] == 'TranscriptData']
        expect(t, f'{s}: no transcript blob')
        for _, _, h, data in t:
            d = base64.b64decode(data)
            hx = h.replace('-', '')
            expect(hx[:24] == hashlib.md5(d).hexdigest()[:24] and int(hx[24:], 16) == len(d) + 12, f'{s}: transcript hash is not the script-written MD5 form')
