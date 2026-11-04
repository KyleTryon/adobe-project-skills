"""Checks for references/spec/16-checklist.md (checklist.*)."""
import base64, json, os, re, sys
from collections import Counter
from _lib import rule, expect, P, SKILL

sys.path.insert(0, os.path.join(SKILL, 'scripts'))
import schema_dump as S  # noqa: E402

GUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
PARAM_CID = {('point', 'v'): 'ca81d347-309b-44d2-acc7-1c572efb973c', ('float', 'v'): 'fe47129e-6c94-4fc0-95d5-c056a517aaf3',
             ('bool', 'v'): 'cc12343e-f113-4d3b-ae05-b287db77d461', ('enum', 'v'): '6e02e8bb-2569-46b2-8ab1-4ab11c43e9c8',
             ('float', 'a'): 'a714635e-a628-4b27-9d59-77eba47dbc1a', ('bool', 'a'): '32657501-3aa4-445f-a49b-d09ecb9fa1ae'}
KEY = re.compile(r'-?\d+,-?[\d.e+-]+:-?[\d.e+-]+,[05],0(,-?[\d.e+-]+){4},5,4(,-?[\d.e+-]+){4}', re.I)


def project_el(s):
    return next(e for e in s.root if e.tag == 'Project' and e.get('ObjectID'))


def ref_counts(s):
    """Referrer counts per target key, ignoring the Project-local view-state list."""
    c = Counter()
    local = set(project_el(s).find(S.LOCAL_SCOPE).iter()) if project_el(s).find(S.LOCAL_SCOPE) is not None else set()
    for e in s.root:
        for x in e.iter():
            if x in local:
                continue
            k = x.get('ObjectRef') or x.get('ObjectURef')
            if k:
                c[k] += 1
    return c, local


def kind(v):
    if ':' in v: return 'point'
    if v in ('true', 'false'): return 'bool'
    if re.fullmatch(r'-?\d+', v): return 'enum'
    return 'float'


def tracks(s, seq_el):
    out = []
    for tg in seq_el.findall('.//TrackGroups/TrackGroup'):
        g = s.ref(tg, 'Second')
        for t in g.findall('TrackGroup/Tracks/Track'):
            out.append((g, t, s.ref(t)))
    return out


def conform(s):
    x = s.xml
    keys = Counter(e.get('ObjectID') or e.get('ObjectUID') for e in s.root if e.get('ObjectID') or e.get('ObjectUID'))
    expect(all(n == 1 for n in keys.values()), f'{s}: duplicate identities')                                  # 1
    rc, local = ref_counts(s)
    expect(all(k in s.ids for k in rc), f'{s}: unresolved references {[k for k in rc if k not in s.ids][:3]}')  # 1
    expect(not S.unseen(s.root), f'{s}: structure not in the catalogue: {S.unseen(s.root)}')                     # 2
    for tag, side in (('PointComponentParam', 'v'), ('VideoComponentParam', 'v'), ('AudioComponentParam', 'a')):
        for pe in s.objs(tag):
            sk = P.txt(pe, 'StartKeyframe')
            k = kind(sk.split(',')[1]) if sk else {'Volume': 'float', 'Balance': 'float', 'Mute': 'bool'}.get(P.txt(pe, 'Name'))
            expect(pe.get('ClassID') == PARAM_CID.get((k, side)), f'{s}: {tag} {P.txt(pe, "Name")} ClassID')        # 2
    for parent in s.root.iter():                                                                                  # 3
        idx = [c.get('Index') for c in parent if c.get('Index') is not None]
        if idx:
            expect(idx == [str(i) for i in range(len(idx))], f'{s}: {parent.tag} indexes {idx}')
    for seq in s.objs('Sequence'):
        gid = Counter()
        ends = []
        for g, t, trk in tracks(s, seq):
            ct = trk.find('ClipTrack')
            pos = {t.get('Index'), P.txt(ct, 'Track/Index'), ct.find('ClipItems').get('Index') if ct.find('ClipItems') is not None else None,
                   ct.find('TransitionItems').get('Index') if ct.find('TransitionItems') is not None else None}
            pos.discard(None)
            expect(len(pos) == 1, f'{s}: track position disagrees {pos}')                                         # 4
            tid = int(P.txt(ct, 'Track/ID')); gid[(g.tag, tid)] += 1
            expect(tid < int(P.txt(g, 'TrackGroup/NextTrackID')), f'{s}: Track/ID {tid} not below NextTrackID')    # 4
            items = [s.ref(i) for i in ct.findall('ClipItems/TrackItems/TrackItem')]
            prev_end = None; starts = []
            for it in items:
                st_el = it.find('.//TrackItem/Start')
                st = int(st_el.text) if st_el is not None else 0
                expect(st_el is None or st != 0, f'{s}: Start written as 0')                                       # 5
                en = int(P.txt(it, './/TrackItem/End'))
                sc = s.ref(it, 'ClipTrackItem/SubClip'); clip = s.ref(sc, 'Clip')
                expect(clip.find('Clip/InPoint') is not None, f'{s}: timeline clip without InPoint')                 # 5
                inp = int(P.txt(clip, 'Clip/InPoint')); out = int(P.txt(clip, 'Clip/OutPoint'))
                spd = float(P.txt(clip, 'Clip/PlaybackSpeed') or 1)
                expect(abs((en - st) - (out - inp) / spd) <= 1, f'{s}: End-Start != (Out-In)/speed')              # 5
                fr = int(P.txt(seq, './/FrameRate') or 0) or None
                vfr = next(int(P.txt(gg, 'TrackGroup/FrameRate')) for gg, _, _ in tracks(s, seq) if gg.tag == 'VideoTrackGroup') if any(gg.tag == 'VideoTrackGroup' for gg, _, _ in tracks(s, seq)) else None
                if vfr:
                    expect(st % vfr == 0 and en % vfr == 0, f'{s}: {it.tag} {st}-{en} off the frame grid')          # 5
                expect(prev_end is None or st >= prev_end, f'{s}: overlapping items')                              # 5
                prev_end = en; starts.append(st); ends.append(en)
            expect(starts == sorted(starts), f'{s}: track items not sorted by Start')                              # 3
        expect(all(n == 1 for n in gid.values()), f'{s}: repeated Track/ID')                                        # 4
        ag = next((s.ref(tg, 'Second') for tg in seq.findall('.//TrackGroups/TrackGroup') if s.ref(tg, 'Second').tag == 'AudioTrackGroup'), None)
        if ag is not None:
            mix = s.ref(ag, 'TrackGroup/MasterTrack') if ag.find('TrackGroup/MasterTrack') is not None else None
            inlets = [o for o in s.objs('AudioTrackInlet') if any(r.tag == 'AudioMixTrack' for r in s.referrers(o))]
            want = [t.get('ObjectURef') for t in ag.findall('TrackGroup/Tracks/Track')]
            expect(any([q.get('ObjectURef') for q in i.findall('Sources/Source')] == want for i in inlets), f'{s}: no inlet lists the audio tracks')  # 3
        zo = P.txt(seq, 'Node/Properties/Monitor.ProgramZoomOut')
        expect(zo is not None and int(zo) == max(ends, default=0), f"{s}: {P.txt(seq, 'Name')} ProgramZoomOut {zo} vs length {max(ends, default=0)}")  # 8
        for l in [s.ref(l) for l in seq.findall('PersistentGroupContainer/LinkContainer/Links/Link')]:
            expect(len(l.findall('.//TrackItems/TrackItem')) == 2, f'{s}: link with {len(l.findall(".//TrackItems/TrackItem"))} members')  # 7
        members = [m.get('ObjectRef') for l in [s.ref(l) for l in seq.findall('PersistentGroupContainer/LinkContainer/Links/Link')]
                   for m in l.findall('.//TrackItems/TrackItem')]
        expect(len(members) == len(set(members)), f'{s}: an item is in two links')                                 # 7
    for tag in ('VideoComponentChain', 'AudioComponentChain', 'VideoFilterComponent', 'AudioFader', 'AudioMeter', 'SubClip',
                'SecondaryContent', 'PointComponentParam', 'VideoComponentParam', 'AudioComponentParam'):
        for o in s.objs(tag):                                                                                     # 6
            expect(rc[o.get('ObjectID') or o.get('ObjectUID')] == 1, f'{s}: {tag} referenced {rc[o.get("ObjectID")]} times')
    for sc in s.objs('SubClip'):
        expect(rc[s.ref(sc, 'Clip').get('ObjectID')] == 1, f'{s}: a timeline clip is referenced more than once')   # 6
    cids = re.findall(r'<ClipID>([^<]+)</ClipID>', x)
    expect(len(cids) == len(set(cids)), f'{s}: repeated ClipIDs')                                                   # 6
    gids = [e.text for e in s.root.iter('ID') if e.text and GUID.match(e.text)]
    expect(len(gids) == len(set(gids)), f'{s}: repeated GUID IDs')                                                  # 6
    for ch in s.objs('VideoComponentChain'):                                                                      # 9
        mns = [P.txt(s.ref(c), 'MatchName') for c in ch.findall('ComponentChain/Components/Component')]
        ids = [int(P.txt(s.ref(c), 'Component/ID')) for c in ch.findall('ComponentChain/Components/Component')]
        expect(not (P.txt(ch, 'DefaultMotion') == 'true' and 'AE.ADBE Motion' in mns), f'{s}: DefaultMotion with explicit Motion')
        expect(len(ids) == len(set(ids)) and all(i >= 3 for i in ids), f'{s}: component IDs {ids}')
    for kf in re.findall(r'<Keyframes>([^<]*)</Keyframes>', x):                                                   # 10
        expect(kf.endswith(';') and all(KEY.fullmatch(k) for k in kf[:-1].split(';')), f'{s}: keyframe string {kf[:60]}')
    for lst in s.objs('Markers'):                                                                                  # 12
        for e in lst.findall('Markers/Marker'):
            mk = s.ref(e, 'Second')
            d = json.loads(P.txt(mk, 'DVAMarker'))['DVAMarker']
            expect(P.txt(e, 'First') == d['mMarkerID'], f'{s}: First != mMarkerID')
    listed = Counter(e.get('ObjectRef') for lst in s.objs('Markers') for e in lst.findall('Markers/Marker/Second'))
    expect(all(listed[m.get('ObjectID')] == 1 for m in s.objs('Marker')), f'{s}: a Marker is not listed exactly once')
    for seq in s.objs('Sequence'):                                                                                 # 13
        for g, t, trk in tracks(s, seq):
            trans = {i.get('ObjectRef') for i in trk.findall('ClipTrack/TransitionItems/TrackItems/TrackItem')}
            for i in trk.findall('ClipTrack/ClipItems/TrackItems/TrackItem'):
                it = s.ref(i)
                st = int(P.txt(it, './/TrackItem/Start') or 0); en = int(P.txt(it, './/TrackItem/End'))
                for side, cut in (('HeadTransition', st), ('TailTransition', en)):
                    h = it.find('ClipTrackItem/' + side)
                    if h is None:
                        continue
                    expect(h.get('ObjectRef') in trans, f'{s}: {side} not in the track\'s TransitionItems')
                    tr = s.ref(h)
                    expect(int(P.txt(tr, './/TrackItem/Start') or 0) + int(P.txt(tr, './/Alignment') or 0) == cut, f'{s}: transition Start + Alignment is not the cut')
    for d in s.objs('ExternallyProvidedTranscriptDocument'):                                                       # 14
        td = d.find('TranscriptData'); b = base64.b64decode(td.text.strip())
        expect(int(td.get('BinaryHash').replace('-', '')[-8:], 16) == len(b) + 12, f'{s}: BinaryHash length part')
        for sg in P.transcript_model(b)['segments']:
            ws = sg['words']
            expect(ws[0][0] == sg['start'] and ws[-1][0] + ws[-1][1] == sg['start'] + sg['dur'], f'{s}: segment bounds differ from its words')


@rule('checklist.premiere-saves-conform')
def _(ev):
    for s in ev.steps:
        expect(not s.generated, f'{s} is script-written')
        conform(s)
    have = lambda f: any(f(s) for s in ev.steps)
    expect(have(lambda s: s.objs('Marker')) and have(lambda s: s.objs('AudioTransitionTrackItem'))
           and have(lambda s: s.objs('ExternallyProvidedTranscriptDocument')) and have(lambda s: '<Keyframes>' in s.xml),
           'evidence lacks markers, transitions, transcripts or keyframes')


@rule('checklist.transform-keys-in-range')
def _(ev):
    n = 0
    for s in ev.steps:
        for c in s.objs('VideoFilterComponent'):
            if P.txt(c, 'MatchName') != 'AE.ADBE Geometry2':
                continue
            ch = next(ch for ch in s.objs('VideoComponentChain') if any(s.ref(x) is c for x in ch.findall('ComponentChain/Components/Component')))
            it = next(r for r in s.referrers(ch) if r.tag == 'VideoClipTrackItem')
            clip = s.ref(s.ref(it, 'ClipTrackItem/SubClip'), 'Clip')
            inp, out = int(P.txt(clip, 'Clip/InPoint')), int(P.txt(clip, 'Clip/OutPoint'))
            fr = 10594584000
            for p in c.findall('Component/Params/Param'):
                for k in (P.txt(s.ref(p), 'Keyframes') or '').split(';'):
                    if k:
                        t = int(k.split(',')[0])
                        expect(inp - 3 * fr <= t <= out + 3 * fr, f'{s}: key at {t} outside {inp}-{out}'); n += 1
    expect(n, 'no Transform keys in the evidence')
