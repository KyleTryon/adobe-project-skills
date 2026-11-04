"""Checks for references/spec/12-effects-and-keyframes.md (effects.*, keys.*)."""
import math, re
from _lib import rule, expect, P, TPS

VCHAIN, ACHAIN = 'VideoComponentChain', 'AudioComponentChain'
CHAIN_OWNERS = {VCHAIN: {'VideoClipTrackItem', 'VideoTrackGroup'},
                ACHAIN: {'AudioClipTrackItem', 'AudioClipTrack', 'AudioMixTrack', 'MasterClip'}}
PARAM_TAGS = ('PointComponentParam', 'VideoComponentParam', 'AudioComponentParam', 'ArbVideoComponentParam')
CID = {('point', 'v'): 'ca81d347-309b-44d2-acc7-1c572efb973c', ('float', 'v'): 'fe47129e-6c94-4fc0-95d5-c056a517aaf3',
       ('bool', 'v'): 'cc12343e-f113-4d3b-ae05-b287db77d461', ('enum', 'v'): '6e02e8bb-2569-46b2-8ab1-4ab11c43e9c8',
       ('float', 'a'): 'a714635e-a628-4b27-9d59-77eba47dbc1a', ('bool', 'a'): '32657501-3aa4-445f-a49b-d09ecb9fa1ae'}
TRANSFORM_IDS = ['1', '2', '11', '3', '4', '5', '6', '7', '8', '9', '10', '12']
TRANSFORM_NAMES = {'1': 'Anchor Point', '2': 'Position', '3': 'Scale Height', '4': 'Scale Width', '5': 'Skew',
                   '6': 'Skew Axis', '7': 'Rotation', '8': 'Opacity', '10': 'Shutter Angle', '12': 'Sampling'}
STATIC_T = '-91445760000000000'


def owners(s, el):
    return [r for r in s.referrers(el) if r.tag != 'Project']


def refs_to(s, el, tags):
    out = []
    for x in el.iter():
        k = x.get('ObjectRef') or x.get('ObjectURef')
        t = s.ids.get(k) if k else None
        if t is not None and t.tag in tags:
            out.append(t)
    return out


def components(s, chain):
    return [s.ref(c) for c in chain.findall('ComponentChain/Components/Component')]


def params(s, comp):
    return [s.ref(p) for p in comp.findall('Component/Params/Param') + comp.findall('AudioComponent/Component/Params/Param')]


def transforms(s):
    return [c for c in s.objs('VideoFilterComponent') if P.txt(c, 'MatchName') == 'AE.ADBE Geometry2']


def item_of_component(s, comp):
    """(track item, its clip) for a component on a track item's chain."""
    for ch in s.objs(VCHAIN):
        if comp in components(s, ch):
            it = next(o for o in owners(s, ch) if o.tag.endswith('ClipTrackItem'))
            sc = s.ref(it, 'ClipTrackItem/SubClip')
            return it, s.ref(sc, 'Clip')
    raise AssertionError('component not on a track item')


def value_kind(v):
    if ':' in v:
        return 'point'
    if v in ('true', 'false'):
        return 'bool'
    if re.fullmatch(r'-?\d+', v):
        return 'enum'
    if re.fullmatch(r'-?(\d+\.\d*|\.\d+)(e[-+]?\d+)?', v, re.I):
        return 'float'
    return '?'


def keys_of(pe):
    raw = P.txt(pe, 'Keyframes') or ''
    return [k.split(',') for k in raw.split(';') if k]


def pt(v):
    x, y = v.split(':'); return float(x), float(y)


# ---------- 12.1 chains ----------

@rule('effects.chain-owners')
def _(ev):
    for s in ev.steps:
        for tag in (VCHAIN, ACHAIN):
            for ch in s.objs(tag):
                own = owners(s, ch)
                expect(len(own) == 1 and own[0].tag in CHAIN_OWNERS[tag], f'{s}: a {tag} owned by {[o.tag for o in own]}')
        for tag, chain in (('VideoClipTrackItem', VCHAIN), ('AudioClipTrackItem', ACHAIN), ('VideoTrackGroup', VCHAIN),
                           ('AudioClipTrack', ACHAIN), ('AudioMixTrack', ACHAIN)):
            for o in s.objs(tag):
                expect(len(refs_to(s, o, {chain})) == 1, f'{s}: a {tag} owns {len(refs_to(s, o, {chain}))} chains')
        mcs = [m for m in s.objs('MasterClip') if any(c.tag == 'AudioClip' for c in refs_to(s, m, {'AudioClip'}))]
        expect(mcs, f'{s}: no MasterClip with audio')
        for m in mcs:
            expect(refs_to(s, m, {ACHAIN}), f'{s}: MasterClip {P.txt(m, "Name")} has audio but no AudioComponentChain')
        expect(s.objs('VideoClipTrackItem') and s.objs('AudioClipTrackItem'), f'{s}: no track items')


@rule('effects.implicit-defaults')
def _(ev):
    n = 0
    for s in ev.steps:
        for ch in s.objs(VCHAIN) + s.objs(ACHAIN):
            own = owners(s, ch)[0].tag
            flags = {c.tag: (c.text or '').strip() for c in ch if c.tag.startswith('Default')}
            if own == 'VideoClipTrackItem':
                want = {'DefaultMotion': 'true', 'DefaultOpacity': 'true', 'DefaultMotionComponentID': '1', 'DefaultOpacityComponentID': '2'}
            elif own in ('AudioClipTrackItem', 'MasterClip'):
                want = {'DefaultVol': 'true', 'DefaultVolumeComponentID': '1', 'DefaultChannelVolumeComponentID': '2'}
            else:
                want = {}
            expect(flags == want, f'{s}: {own} chain flags {flags}')
            n += bool(want)
    expect(n, 'no item chains in the evidence')


@rule('effects.components-absent-when-empty')
def _(ev):
    empty = full = 0
    for s in ev.steps:
        for ch in s.objs(VCHAIN) + s.objs(ACHAIN):
            lst = ch.find('ComponentChain/Components')
            items = ch.findall('ComponentChain/Components/Component')
            expect((lst is None) == (not items), f'{s}: Components present={lst is not None} with {len(items)} components')
            empty += lst is None; full += lst is not None
    expect(empty and full, f'evidence lacks empty ({empty}) or non-empty ({full}) chains')


@rule('effects.component-ids')
def _(ev):
    seen = 0
    for s in ev.steps:
        for ch in s.objs(VCHAIN) + s.objs(ACHAIN):
            ids = [P.txt(c, 'Component/ID') or P.txt(c, 'AudioComponent/Component/ID') for c in components(s, ch)]
            expect(len(ids) == len(set(ids)), f'{s}: repeated component IDs {ids}')
            if ch.tag == VCHAIN and P.txt(ch, 'DefaultMotion') == 'true' and ids:
                nums = [int(i) for i in ids]
                expect(1 not in nums and 2 not in nums, f'{s}: IDs 1/2 used while Motion/Opacity are implicit: {ids}')
                expect(min(nums) == 3, f'{s}: first added effect has ID {min(nums)}, not max({{1,2}})+1 = 3')
                seen += 1
    expect(seen, 'no video chain with an added effect in the evidence')


@rule('effects.active-component-view-state')
def _(ev):
    KEY = 'ComponentChain/Node/Properties/MZ.ComponentChain.ActiveComponentID'
    def flags(s):
        out = {}
        for tag, chain in (('VideoClipTrackItem', VCHAIN), ('AudioClipTrackItem', ACHAIN)):
            for it in s.objs(tag):
                sc = s.ref(it, 'ClipTrackItem/SubClip'); clip = s.ref(sc, 'Clip')
                ch = refs_to(s, it, {chain})[0]
                out[P.txt(clip, 'Clip/ClipID')] = ch.find(KEY) is not None
        return out
    for a, b in ev.pairs:
        fa, fb = flags(a), flags(b)
        gained = [k for k in fb if fb[k] and k in fa and not fa[k]]
        expect(gained, f'no clip chain gained MZ.ComponentChain.ActiveComponentID from {a} to {b}')


# ---------- 12.2 components and params ----------

@rule('effects.filter-component')
def _(ev):
    for s in ev.steps:
        ts = transforms(s)
        expect(ts, f'{s}: no Transform')
        for c in ts:
            idx = [p.get('Index') for p in c.findall('Component/Params/Param')]
            expect(idx == [str(i) for i in range(len(idx))] and idx, f'{s}: Param indexes {idx}')
            expect(P.txt(c, 'Component/ID') and P.txt(c, 'Component/DisplayName') == 'Transform', f'{s}: Component/ID or DisplayName')
            expect(P.txt(c, 'VideoFilterType') == '2', f"{s}: VideoFilterType {P.txt(c, 'VideoFilterType')}")


@rule('effects.param-classes')
def _(ev):
    for s in ev.steps:
        kinds = set()
        for tag in PARAM_TAGS:
            for pe in s.objs(tag):
                side = 'a' if tag == 'AudioComponentParam' else 'v'
                sk = P.txt(pe, 'StartKeyframe')
                if sk:
                    k = value_kind(sk.split(',')[1])
                elif side == 'a':
                    k = {'Volume': 'float', 'Balance': 'float', 'Mute': 'bool'}.get(P.txt(pe, 'Name'), '?')
                else:
                    k = '?'
                expect((k, side) in CID, f"{s}: {tag} {P.txt(pe, 'Name')} holds {k}")
                expect(pe.get('ClassID') == CID[(k, side)], f"{s}: {tag} {P.txt(pe, 'Name')} ({k}) has ClassID {pe.get('ClassID')}")
                expect(tag != 'PointComponentParam' or k == 'point', f'{s}: a PointComponentParam holds {k}')
                kinds.add((k, side))
        expect(kinds == set(CID), f'{s}: evidence shows only {sorted(kinds)}')


@rule('effects.parameter-ids-stable')
def _(ev):
    for a, b in ev.pairs:
        ta, tb = transforms(a), transforms(b)
        expect(len(ta) == 1 and len(tb) == 1, f'want one Transform in each of {a}, {b}')
        ia = [P.txt(p, 'ParameterID') for p in params(a, ta[0])]
        ib = [P.txt(p, 'ParameterID') for p in params(b, tb[0])]
        expect(ia == ib, f'ParameterIDs {ia} became {ib}')


# ---------- 12.3 / 12.4 keyframes ----------

@rule('keys.static-form')
def _(ev):
    pts = scal = 0
    for s in ev.steps:
        for v in re.findall(r'<StartKeyframe>([^<]*)<', s.xml):
            f = v.split(',')
            expect(f[0] == STATIC_T and len(f) >= 8, f'{s}: StartKeyframe {v}')
            if ':' in f[1]:
                expect(f[2:] == '0,0,0,0,0,0,5,4,0,0,0,0'.split(','), f'{s}: point StartKeyframe {v}'); pts += 1
            else:
                expect(f[2:] == ['0'] * 6 and value_kind(f[1]) in ('float', 'bool', 'enum'), f'{s}: scalar StartKeyframe {v}'); scal += 1
    expect(pts and scal, f'evidence lacks point ({pts}) or scalar ({scal}) StartKeyframes')


@rule('keys.start-keyframe-kept')
def _(ev):
    n = 0
    for s in ev.steps:
        for tag in PARAM_TAGS:
            for pe in s.objs(tag):
                ks = keys_of(pe)
                if not ks:
                    continue
                sk = P.txt(pe, 'StartKeyframe')
                expect(sk, f'{s}: an animated param lost its StartKeyframe')
                expect(sk.split(',')[1] != ks[0][1], f'{s}: StartKeyframe equals the first key ({ks[0][1]}), so the evidence shows nothing')
                n += 1
    expect(n, 'no animated param in the evidence')


@rule('keys.animated-video-param')
def _(ev):
    n = 0
    for s in ev.steps:
        for tag in ('PointComponentParam', 'VideoComponentParam'):
            for pe in s.objs(tag):
                kids = [c.tag for c in pe]
                if 'Keyframes' not in kids:
                    expect('IsTimeVarying' not in kids, f'{s}: IsTimeVarying on a static param'); continue
                expect(P.txt(pe, 'IsTimeVarying') == 'true', f'{s}: animated param without IsTimeVarying true')
                i = kids.index('IsTimeVarying')
                expect((kids[i - 1] == 'Name') if 'Name' in kids else i == 0, f'{s}: IsTimeVarying position {kids}')
                expect(kids[kids.index('StartKeyframe') + 1] == 'Keyframes', f'{s}: Keyframes not right after StartKeyframe {kids}')
                n += 1
    expect(n, 'no animated video param in the evidence')


def point_keys(s):
    out = []
    for c in transforms(s):
        for pe in params(s, c):
            if pe.tag == 'PointComponentParam' and keys_of(pe):
                out.append((c, pe, keys_of(pe)))
    return out


@rule('keys.point-key-format')
def _(ev):
    for s in ev.steps:
        pk = point_keys(s)
        expect(pk, f'{s}: no animated point param')
        for c, pe, ks in pk:
            it, clip = item_of_component(s, c)
            start = int(P.txt(it, './/TrackItem/Start') or 0); end = int(P.txt(it, './/TrackItem/End'))
            inp = int(P.txt(clip, './/InPoint') or 0); spd = float(P.txt(clip, './/PlaybackSpeed') or 1)
            expect(int(ks[0][0]) == inp, f'{s}: first key at {ks[0][0]}, clip InPoint {inp}')
            for k in ks:
                expect(len(k) == 14 and ':' in k[1], f'{s}: point key {k}')
                expect(k[2] in ('0', '5') and k[3] == '0' and k[8:10] == ['5', '4'], f'{s}: constants in {k}')
                tl = start + (int(k[0]) - inp) / spd
                expect(start <= tl <= end, f'{s}: key at source {k[0]} maps outside its clip')
            expect({k[2] for k in ks} == {'0', '5'}, f'{s}: evidence lacks linear or Bezier keys')


@rule('keys.reproduce-position')
def _(ev):
    for s in ev.steps:
        for c, pe, ks in point_keys(s):
            t = [int(k[0]) / TPS for k in ks]; p = [pt(k[1]) for k in ks]; lin = [k[2] == '0' for k in ks]
            n = len(ks)
            for i, k in enumerate(ks):
                f = [float(x) for x in (k[4:8] + k[10:14])]
                sp_in, inf_in, sp_out, inf_out, tix, tiy, tox, toy = f
                prev = i > 0; nxt = i < n - 1
                d_in = (p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) if prev else (0, 0)
                d_out = (p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]) if nxt else (0, 0)
                want_sp_in = math.hypot(*d_in) / (t[i] - t[i - 1]) if (prev and lin[i]) else 0
                want_sp_out = math.hypot(*d_out) / (t[i + 1] - t[i]) if (nxt and lin[i]) else 0
                if lin[i]:
                    want_inf = (1 / 6, 1 / 6)
                else:
                    want_inf = (1 / 3 if prev and any(d_in) else 1 / 6, 1 / 3 if nxt and any(d_out) else 1 / 6)
                want = [want_sp_in, want_inf[0], want_sp_out, want_inf[1], -d_in[0] / 6, -d_in[1] / 6, d_out[0] / 6, d_out[1] / 6]
                bad = [(j, g, w) for j, (g, w) in enumerate(zip(f, want)) if abs(g - w) > 1e-9 * max(1, abs(w))]
                expect(not bad, f'{s}: key {i} fields (index, stored, rule) {bad}')


# ---------- 12.5 / 12.6 ----------

def transform_layout(s):
    ts = transforms(s)
    expect(len(ts) == 1, f'{s}: {len(ts)} Transforms')
    ps = params(s, ts[0])
    ids = [P.txt(p, 'ParameterID') for p in ps]
    expect(ids == TRANSFORM_IDS, f'{s}: ParameterIDs {ids}')
    for p in ps:
        nm = P.txt(p, 'Name'); pid = P.txt(p, 'ParameterID')
        expect(nm is None or nm == TRANSFORM_NAMES.get(pid), f'{s}: param {pid} named {nm}')
        expect((nm is None) == (pid in ('9', '11')), f'{s}: param {pid} Name present={nm is not None}')
    return {P.txt(p, 'ParameterID'): p for p in ps}


@rule('effects.transform-params')
def _(ev):
    for s in ev.steps:
        ps = transform_layout(s)
        expect(P.txt(ps['10'], 'StartKeyframe').split(',')[1] == '240.', f'{s}: Shutter Angle not 240')
        expect(ps['12'].get('ClassID') == CID[('enum', 'v')], f'{s}: Sampling not an enum')


@rule('effects.transform-written')
def _(ev):
    for s in ev.steps:
        expect(s.generated, f'{s} is not script-written')
        ps = transform_layout(s)
        expect(P.txt(ps['9'], 'StartKeyframe').split(',')[1] == 'false', f"{s}: Use Composition's Shutter Angle is not false (motion blur on)")


@rule('effects.track-fader')
def _(ev):
    def muted(s):
        out = []
        for f in s.objs('AudioFader'):
            for p in params(s, f):
                if P.txt(p, 'Name') == 'Mute' and P.txt(p, 'CurrentValue') == 'true':
                    out.append(f)
        return out
    for a, b in ev.pairs:
        for s in (a, b):
            for tr in s.objs('AudioClipTrack') + s.objs('AudioMixTrack'):
                ch = refs_to(s, tr, {ACHAIN})[0]
                tags = [c.tag for c in components(s, ch)]
                expect(tags == ['AudioFader', 'AudioMeter'], f'{s}: track chain components {tags}')
            for f in s.objs('AudioFader'):
                names = [P.txt(p, 'Name') for p in params(s, f)]
                expect(names == ['Volume', 'Mute'], f'{s}: fader params {names}')
        expect(not muted(a) and len(muted(b)) == 1, f'muted faders: {len(muted(a))} in {a}, {len(muted(b))} in {b}')
