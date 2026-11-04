"""Checks for references/spec/11-transitions.md."""
from _lib import rule, expect, P
from _timeline import timeline, item, media_len

CID = '23f687b6-9c5a-42f4-bea1-e7b3e28e7082'
ORDER = ['TransitionTrackItem/TrackItem/Start', 'TransitionTrackItem/TrackItem/End', 'TransitionTrackItem/HasOutgoingClip',
         'TransitionTrackItem/HasIncomingClip', 'TransitionTrackItem/DisplayName', 'TransitionTrackItem/MatchName',
         'TransitionTrackItem/Alignment', 'AudioChannelLayout']


def transitions(s):
    """[(sequence, track dict, transition el, Index, items referencing it as Head, as Tail)]"""
    out = []
    for name, d in timeline(s).items():
        for t in d['tracks']:
            for idx, tr in t['trans']:
                k = tr.get('ObjectID')
                heads = [it for it in t['items'] if it['el'].find('ClipTrackItem/HeadTransition') is not None
                         and it['el'].find('ClipTrackItem/HeadTransition').get('ObjectRef') == k]
                tails = [it for it in t['items'] if it['el'].find('ClipTrackItem/TailTransition') is not None
                         and it['el'].find('ClipTrackItem/TailTransition').get('ObjectRef') == k]
                out.append((name, t, tr, idx, heads, tails))
    return out


def ticks(tr, tag):
    return int(P.txt(tr, f'TransitionTrackItem/TrackItem/{tag}') or 0)


def flag(tr, tag):
    return P.txt(tr, f'TransitionTrackItem/{tag}')


def kind(tr):
    return (flag(tr, 'HasOutgoingClip'), flag(tr, 'HasIncomingClip'))


def need(ev, want=None):
    for s in ev.steps:
        ts = transitions(s)
        expect(ts, f'{s}: no transitions')
        if want:
            expect(any(kind(x[2]) == want for x in ts), f'{s}: no transition with outgoing/incoming {want}')


@rule('transitions.placement')
def _(ev):
    need(ev)
    for s in ev.steps:
        for name, t, tr, idx, heads, tails in transitions(s):
            expect(t['tag'] == 'AudioClipTrack', f'{s}: transition on a {t["tag"]}')
            st = [ticks(x, 'Start') for _, x in t['trans']]
            expect(st == sorted(st) and [i for i, _ in t['trans']] == list(range(len(st))), f'{s}: TransitionItems not in time order')
            out, inc = kind(tr)
            expect(len(tails) == (out == 'true') and len(heads) == (inc == 'true'), f'{s}: {kind(tr)} referenced as {len(heads)} head, {len(tails)} tail')
            cut = ticks(tr, 'Start') + int(flag(tr, 'Alignment'))
            for it in heads:
                expect(it['start'] == cut, f'{s}: HeadTransition on a clip that does not start at the cut')
            for it in tails:
                expect(it['end'] == cut, f'{s}: TailTransition on a clip that does not end at the cut')
            for it in heads + tails:
                kids = [c.tag for c in it['el'].find('ClipTrackItem')]
                i = kids.index('SubClip')
                after = [k for k in kids[i + 1:] if k.endswith('Transition')]
                expect([k for k in kids if k.endswith('Transition')] == after, f'{s}: transition refs before SubClip: {kids}')
                expect(after == sorted(after, key=lambda k: k != 'HeadTransition'), f'{s}: Tail before Head: {after}')


@rule('transitions.class')
def _(ev):
    need(ev)
    for s in ev.steps:
        for name, t, tr, idx, heads, tails in transitions(s):
            expect((tr.get('ClassID'), tr.get('Version')) == (CID, '4'), f'{s}: {tr.get("ClassID")} v{tr.get("Version")}')
            paths = []
            for c in tr:
                if c.tag == 'TransitionTrackItem':
                    for g in c:
                        if g.tag == 'TrackItem':
                            paths += [f'TransitionTrackItem/TrackItem/{x.tag}' for x in g]
                        else:
                            paths.append(f'TransitionTrackItem/{g.tag}')
                else:
                    paths.append(c.tag)
            expect(paths[:len(ORDER)] == ORDER, f'{s}: children {paths}')


def rows(ev, want):
    out = []
    for s in ev.steps:
        for x in transitions(s):
            if kind(x[2]) == want:
                out.append((s, x))
    expect(out, f'no transition with outgoing/incoming {want} in the evidence')
    return out


def fade_shape(tr):
    return P.txt(tr, 'FadeShapeValue')


@rule('transitions.fade-in')
def _(ev):
    for s, (name, t, tr, idx, heads, tails) in rows(ev, ('false', 'true')):
        expect(flag(tr, 'MatchName') == 'Custom Fade' == flag(tr, 'DisplayName'), f'{s}: name {flag(tr, "MatchName")}')
        expect(flag(tr, 'Alignment') == '0' and fade_shape(tr) == '0', f'{s}: Alignment {flag(tr, "Alignment")}, FadeShapeValue {fade_shape(tr)}')
        expect(len(heads) == 1 and not tails and heads[0]['start'] == ticks(tr, 'Start'), f'{s}: not the clip\'s HeadTransition at its head')


def fade_out(ev):
    for s, (name, t, tr, idx, heads, tails) in rows(ev, ('true', 'false')):
        expect(flag(tr, 'MatchName') == 'Custom Fade' == flag(tr, 'DisplayName'), f'{s}: name {flag(tr, "MatchName")}')
        d = ticks(tr, 'End') - ticks(tr, 'Start')
        expect(int(flag(tr, 'Alignment')) == d and fade_shape(tr) == '0', f'{s}: Alignment {flag(tr, "Alignment")} vs duration {d}')
        expect(len(tails) == 1 and not heads and tails[0]['end'] == ticks(tr, 'End'), f'{s}: not the clip\'s TailTransition at its tail')


@rule('transitions.fade-out-script')
def _(ev):
    for s in ev.steps:
        expect(s.generated, f'{s} is not script-written')
    fade_out(ev)


@rule('transitions.fade-out')
def _(ev):
    fade_out(ev)


@rule('transitions.crossfade')
def _(ev):
    for s, (name, t, tr, idx, heads, tails) in rows(ev, ('true', 'true')):
        expect(flag(tr, 'MatchName') == 'Constant Power' == flag(tr, 'DisplayName'), f'{s}: name {flag(tr, "MatchName")}')
        d = ticks(tr, 'End') - ticks(tr, 'Start')
        expect(2 * int(flag(tr, 'Alignment')) == d, f'{s}: Alignment {flag(tr, "Alignment")} is not d/2 of {d}')
        expect(fade_shape(tr) is None, f'{s}: crossfade has FadeShapeValue')
        expect(len(tails) == 1 and len(heads) == 1 and tails[0]['end'] == heads[0]['start'], f'{s}: not the left clip\'s Tail and the right clip\'s Head at one cut')


@rule('transitions.alignment')
def _(ev):
    need(ev)
    for s in ev.steps:
        for name, t, tr, idx, heads, tails in transitions(s):
            cut = (heads[0]['start'] if heads else tails[0]['end'])
            expect(int(flag(tr, 'Alignment')) == cut - ticks(tr, 'Start'), f'{s}: Alignment {flag(tr, "Alignment")} ≠ cut − Start {cut - ticks(tr, "Start")}')


@rule('transitions.crossfade-handles')
def _(ev):
    for s, (name, t, tr, idx, heads, tails) in rows(ev, ('true', 'true')):
        L, R = tails[0], heads[0]
        cut = L['end']
        a, b = ticks(tr, 'Start'), ticks(tr, 'End')
        expect(a < cut < b, f'{s}: crossfade does not span the cut')
        expect(L['end'] == cut == R['start'], f'{s}: the items do not keep their edges at the cut')
        tail = b - cut; head = cut - a
        expect(L['out'] + tail <= media_len(s, L['clip']), f'{s}: left clip has less than {tail} ticks of handle')
        expect(R['in'] - head >= 0, f'{s}: right clip has less than {head} ticks of handle')
        expect(L['out'] < media_len(s, L['clip']) and R['in'] > 0, f'{s}: a clip sits at the end of its media')


@rule('transitions.no-volume-keys')
def _(ev):
    n = 0
    for s in ev.steps:
        for name, t, tr, idx, heads, tails in transitions(s):
            for it in heads + tails:
                chain = s.ref(it['el'], 'ClipTrackItem/ComponentOwner/Components')
                expect(chain is not None and chain.tag == 'AudioComponentChain', f'{s}: faded item without an audio chain')
                expect(P.txt(chain, 'DefaultVol') == 'true', f'{s}: faded clip has DefaultVol {P.txt(chain, "DefaultVol")}')
                expect(chain.find('ComponentChain/Components') is None, f'{s}: faded clip has components in its chain')
                n += 1
    expect(n, 'no faded clips')
