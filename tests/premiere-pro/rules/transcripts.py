"""Checks for references/spec/14-transcripts-and-captions.md (transcripts.*, captions.*)."""
import base64, os, re, struct
from _lib import rule, expect, P, TPS, ROOT

PROVIDER = '9a139944-f00d-4f74-ac45-751e998bb5dc'
SYNTH_IMPL = '42008e7a-de6f-4270-96de-7e287abb9b4b'
DATA_TYPE = 'd8143ffe-eec4-4d2a-a909-d5f7bf094dc5'
PUNCT = '.,?!'


def doc(s):
    ds = s.objs('ExternallyProvidedTranscriptDocument')
    expect(len(ds) == 1, f'{s}: {len(ds)} transcript documents')
    return ds[0]


def blob(s):
    return base64.b64decode(doc(s).find('TranscriptData').text.strip())


def model(s):
    return P.transcript_model(blob(s))


def words(m):
    return [w for sg in m['segments'] for w in sg['words']]


def hash_len_ok(s):
    h = doc(s).find('TranscriptData').get('BinaryHash')
    return int(h.replace('-', '')[-8:], 16) == len(blob(s)) + 12


def abbrev(t):
    return '.' in t[:-1]


@rule('transcripts.object-chain')
def _(ev):
    for s in ev.steps:
        tcs = s.objs('TranscriptClip')
        expect(len(tcs) == 1, f'{s}: {len(tcs)} TranscriptClips')
        tc = tcs[0]
        owner = [r for r in s.referrers(tc) if r.tag != 'Project']
        expect([o.tag for o in owner] == ['MasterClip'], f'{s}: TranscriptClip referred to by {[o.tag for o in owner]}')
        expect(any(s.ref(c) is tc for c in owner[0].findall('.//Clips/Clip')), f'{s}: TranscriptClip not in MasterClip/Clips')
        src = s.ref(tc, 'DataClip/Clip/Source')
        expect(src is not None and src.tag == 'DataMediaSource', f'{s}: source {src.tag if src is not None else None}')
        med = s.ref(src, 'MediaSource/Media')
        expect(P.txt(med, 'Title') == 'SyntheticTranscript' and P.txt(med, 'ImplementationID') == SYNTH_IMPL, f'{s}: synthetic Media')
        expect(P.txt(med, 'FilePath') == '1398035014' == str(int.from_bytes(b'STRF', 'big')), f"{s}: FilePath {P.txt(med, 'FilePath')}")
        ds = s.ref(med, 'DataStream')
        expect(ds is not None and ds.tag == 'DataStream', f'{s}: no DataStream')
        d = s.ref(tc, 'TranscriptTextSegments')
        expect(d is doc(s), f'{s}: TranscriptTextSegments does not point at the document')
        expect(P.txt(d, 'TranscriptProvider') == PROVIDER and d.find('TranscriptData').get('Encoding') == 'base64', f'{s}: document fields')


@rule('transcripts.media-time')
def _(ev):
    ref = P.read_srt_words(os.path.join(ROOT, 'fixtures', 'premiere-pro', 'media', 'interview.srt'))
    for s in ev.steps:
        tr = s.transcripts()[0]
        hyp = [w for sg in tr['segments'] for w in sg['words'] if w['w']]
        _d, st = P.compare_words(hyp, ref)
        expect(abs(st['median_offset_s']) < 0.25, f"{s}: median offset {st['median_offset_s']} s from the media's own captions")


@rule('transcripts.flatbuffer')
def _(ev):
    for s in ev.steps:
        b = blob(s); fb = P.FB(b)
        root = fb.u32(0)
        expect(8 <= root < len(b), f'{s}: root offset {root}')
        expect(not re.fullmatch(rb'[A-Za-z0-9]{4}', b[4:8]), f'{s}: bytes 4-8 look like a file identifier {b[4:8]!r}')
        d = fb.ref(root + fb.fields(root)[0]); df = fb.fields(d)
        segs = fb.vec(d + df[0])
        m = model(s)
        starts = [sg['start'] for sg in m['segments']]
        expect(starts == sorted(starts) and len(starts) > 1, f'{s}: segments not chronological')
        expect(segs == sorted(segs, reverse=True), f'{s}: segment tables are not stored back to front')
        for sg in m['segments']:
            ts = [w[0] for w in sg['words'] if 0 in w]
            expect(ts == sorted(ts), f'{s}: words not chronological')
        lens = {len(fb.fields(w)) for sg in segs for w in fb.vec(sg + fb.fields(sg)[3])}
        expect(len(lens) > 1, f'{s}: every word vtable is the same length, so no defaults are omitted')
        expect(m['speakers'], f'{s}: no speakers vector')


@rule('transcripts.word-flags')
def _(ev):
    for s in ev.steps:
        ws = words(model(s)); pauses = fillers = 0
        for w in ws:
            t = w.get(2, '')
            if not t:
                expect((w.get(6) == 3) != (w.get(7) == 1), f'{s}: empty token flags {w}')
                expect(w.get(4) == 1 and not w.get(5), f'{s}: empty token f4/f5 {w}')
                pauses += w.get(6) == 3; fillers += w.get(7) == 1
                continue
            expect(not w.get(6) and not w.get(7), f'{s}: word {t!r} has pause/filler flags')
            punct = t[-1] in PUNCT and not abbrev(t)
            expect(bool(w.get(4)) == punct, f'{s}: {t!r} f4={w.get(4)}')
            expect(bool(w.get(5)) == (t[-1] in '.?!' and not abbrev(t)), f'{s}: {t!r} f5={w.get(5)}')
        expect(pauses and fillers, f'{s}: evidence lacks pauses ({pauses}) or fillers ({fillers})')
        expect(any(abbrev(w.get(2, '')) for w in ws), f'{s}: no abbreviation in the evidence')


@rule('transcripts.speaker-edits-written')
def _(ev):
    for a, b in ev.pairs:
        expect(b.generated, f'{b} is not script-written')
        ma, mb = model(a), model(b)
        strip = lambda m: [[{k: v for k, v in w.items()} for w in sg['words']] for sg in m['segments']]
        expect(strip(ma) == strip(mb), 'words changed')
        expect([x['id'] for x in ma['speakers']] == [x['id'] for x in mb['speakers']], 'speaker GUIDs changed')
        expect([x['name'] for x in ma['speakers']] != [x['name'] for x in mb['speakers']], 'no speaker renamed')
        expect([sg['speaker'] for sg in ma['segments']] != [sg['speaker'] for sg in mb['segments']], 'no turn reassigned')
        expect(blob(b) == P.transcript_build(mb), f'{b}: blob is not the scripts\' own layout')
        expect(blob(b) != blob(a), 'blob unchanged')
        expect(doc(b).find('TranscriptData').get('BinaryHash') != doc(a).find('TranscriptData').get('BinaryHash'), 'hash unchanged')
        expect(hash_len_ok(b), f'{b}: BinaryHash length part is not len + 12')


@rule('transcripts.adds-clip')
def _(ev):
    for a, b in ev.pairs:
        expect(not a.objs('TranscriptClip'), f'{a} already has a TranscriptClip')
        tc = b.objs('TranscriptClip')
        expect(len(tc) == 1, f'{b}: {len(tc)} TranscriptClips')
        mc = [r for r in b.referrers(tc[0]) if r.tag == 'MasterClip'][0]
        clips = [b.ref(c) for c in mc.findall('.//Clips/Clip')]
        expect(clips[-1] is tc[0], f'{b}: the TranscriptClip is not the MasterClip\'s last clip')
        name = P.txt(mc, 'Name')
        before = next(m for m in a.objs('MasterClip') if P.txt(m, 'Name') == name)
        expect(len(before.findall('.//Clips/Clip')) == len(clips) - 1, f'{name}: clip count did not grow by one')
        expect(name.endswith('.mp4'), f'owner is {name}, not a media MasterClip')
        for t in ('DataMediaSource', 'DataStream', 'ExternallyProvidedTranscriptDocument'):
            expect(len(b.objs(t)) == 1 and not a.objs(t), f'{t} not new in {b}')
        expect(not [r for r in b.referrers(tc[0]) if r.tag == 'Sequence'], 'a Sequence refers to the TranscriptClip')


@rule('transcripts.unlabelled')
def _(ev):
    for s in ev.steps:
        m = model(s)
        expect([x['name'] for x in m['speakers']] == ['Unknown'], f"{s}: speakers {[x['name'] for x in m['speakers']]}")
        expect(all(sg['speaker'] == m['speakers'][0]['id'] for sg in m['segments']), f'{s}: a segment has another speaker')
        durs = [sg['dur'] / TPS for sg in m['segments']]
        expect(len(durs) > 2 and all(20 <= d <= 40 for d in durs[:-1]), f'{s}: segment lengths {durs}')


@rule('transcripts.labelled')
def _(ev):
    for s in ev.steps:
        m = model(s)
        names = {x['id']: x['name'] for x in m['speakers']}
        expect(sorted(names.values()) == ['Speaker 1', 'Speaker 2'], f'{s}: speakers {sorted(names.values())}')
        seq = [names.get(sg['speaker']) for sg in m['segments']]
        expect(None not in seq, f'{s}: a segment points at no speaker')
        expect(seq == ['Speaker 1', 'Speaker 2', 'Speaker 1', 'Speaker 2', 'Speaker 1', 'Speaker 2', 'Speaker 2'], f'{s}: turns {seq}')
        expect(m['f5_same'], f'{s}: Document f2 and f5 are different vectors')


@rule('transcripts.rename-reassign')
def _(ev):
    for a, b in ev.pairs:
        ma, mb = model(a), model(b)
        expect([x['id'] for x in ma['speakers']] == [x['id'] for x in mb['speakers']], 'speaker GUIDs changed')
        expect(sorted(x['name'] for x in mb['speakers']) == ['Interviewer', 'Sean Campbell'], f"names {[x['name'] for x in mb['speakers']]}")
        changed = [i for i, (x, y) in enumerate(zip(ma['segments'], mb['segments'])) if x['speaker'] != y['speaker']]
        expect(len(changed) == 1, f'{len(changed)} segments changed speaker')
        expect(blob(a) != blob(b) and doc(a).find('TranscriptData').get('BinaryHash') != doc(b).find('TranscriptData').get('BinaryHash'), 'blob or hash not rebuilt')
        expect(hash_len_ok(b), f'{b}: BinaryHash length part is not len + 12')


@rule('captions.data-track-group')
def _(ev):
    rates = set()
    for s in ev.steps:
        expect(s.objs('Sequence'), f'{s}: no sequences')
        for e in s.objs('Sequence'):
            groups = {P.txt(tg, 'First'): s.ref(tg, 'Second') for tg in e.findall('.//TrackGroups/TrackGroup')}
            dg = groups.get(DATA_TYPE)
            expect(dg is not None and dg.tag == 'DataTrackGroup', f'{s}: {P.txt(e, "Name")} has no DataTrackGroup')
            vg = next(g for g in groups.values() if g.tag == 'VideoTrackGroup')
            fr = P.txt(dg, 'TrackGroup/FrameRate')
            expect(fr == P.txt(vg, 'TrackGroup/FrameRate'), f'{s}: data frame rate {fr} differs from the sequence')
            expect(dg.find('TrackGroup/Tracks') is None, f'{s}: DataTrackGroup has tracks')
            rates.add(fr)
    expect(rates, 'no sequences in the evidence')
