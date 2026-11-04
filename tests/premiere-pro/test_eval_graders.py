#!/usr/bin/env python3
"""Check the eval graders against known answers, without running any agent.

For each case it builds a correct output with the skill's own commands (what a good run
would leave behind) and checks every script-graded assertion passes; checks the untouched
input fails where an edit was required; and, for the multi-step cases, builds plausible
wrong edits and checks the graders catch them.

  python3 -I tests/premiere-pro/test_eval_graders.py
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKILL = os.path.join(ROOT, 'skills', 'premiere-pro-projects')
sys.path.insert(0, os.path.join(SKILL, 'evals'))
sys.path.insert(0, os.path.join(SKILL, 'scripts'))
import graders as G  # noqa: E402
import prproj as P  # noqa: E402

PR = [sys.executable, '-I', os.path.join(SKILL, 'scripts', 'prproj.py')]
BK = lambda s: [['backup-seq', '--seq', s, '--name', f'{s} (backup)']]
F = G.TPF / G.TPS_


def run(proj, *c):
    r = subprocess.run(PR + [c[0], proj, proj] + list(c[1:]), capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{' '.join(c)}: {r.stderr.strip()[-300:]}")


def cuts(proj, seq):
    return json.loads(subprocess.run(PR + ['cuts', proj, '--seq', seq, '--json'], capture_output=True, text=True, check=True).stdout)


def a1_index(proj, seq):
    return next(i for i, t in enumerate(cuts(proj, seq)['tracks']) if t['type'] == 'AudioClipTrack')


def rough_cut(proj, extra=None):
    """Remove every filler and the interviewer's turn, cutting in the gaps between words."""
    tr = P.transcripts(P.load_xml(proj))[0]
    words = [w for sg in tr['segments'] for w in sg['words'] if w['w']]
    turn = next(sg for sg in tr['segments'] if any(w['w'] == "Let's" for w in sg['words']))
    ranges = [(w['t'], w['t'] + w['d']) for sg in tr['segments'] for w in sg['words'] if w.get('kind') == 'filler']
    ranges.append((turn['start'], max(w['t'] + w['d'] for w in turn['words'])))
    ranges.sort(); merged = []
    for a, b in ranges:
        if merged and a <= merged[-1][1] + 1e-6:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    frames = []
    for a, b in merged:
        pe = max([w['t'] + w['d'] for w in words if w['t'] + w['d'] <= a + 1e-6] or [0])
        ne = min([w['t'] for w in words if w['t'] >= b - 1e-6] or [1e9])
        fa = -(-pe // F)                      # first frame at or after the last kept word's end
        fa = fa if fa * F <= a + F / 2 else round(a / F)
        fb = ne // F                          # last frame at or before the next kept word
        fb = fb if fb * F >= b - F / 2 else round(b / F)
        if fb > fa:
            frames.append((int(fa), int(fb)))
    for fa, fb in frames:
        run(proj, 'split', '--seq', 'Interview', '--at', f'{fa}f')
        run(proj, 'split', '--seq', 'Interview', '--at', f'{fb}f')
    for fa, fb in reversed(frames):           # from the end, so earlier pieces keep their numbers
        items = cuts(proj, 'Interview')['tracks'][0]['items']
        n = next(k for k, i in enumerate(items, 1) if round(i['start_ticks'] / G.TPF) == fa)
        run(proj, 'delete', '--seq', 'Interview', '--track', '0', '--item', str(n), '--ripple')


def assemble(proj, fade='1'):
    run(proj, 'backup-seq', '--seq', 'Custom', '--name', 'Assembly')
    at = 0
    for clip, a, b in G.ASSEMBLY:
        run(proj, 'place', '--seq', 'Assembly', '--clip', clip, '--at', f'{at}f', '--in', str(a), '--out', str(b))
        at = round(cuts(proj, 'Assembly')['tracks'][0]['items'][-1]['end_ticks'] / G.TPF)
    t = a1_index(proj, 'Assembly')
    for item in ('1', '2'):
        run(proj, 'crossfade', '--seq', 'Assembly', '--track', str(t), '--item', item, '--duration', fade)


def chapters(proj):
    run(proj, 'backup-seq', '--seq', 'Interview', '--name', 'Interview (backup)')
    prev = None
    for n, sg in enumerate(P.transcripts(P.load_xml(proj))[0]['segments']):
        if sg['speaker'] != prev:
            run(proj, 'add-marker', '--seq', 'Interview', '--at', '0' if prev is None else str(sg['start']),
                '--name', sg['speaker'], '--type', 'Chapter')
            prev = sg['speaker']


def cut_and_crossfade(proj, end='10', fade=True):
    for c in BK('clip-a') + [['split', '--seq', 'clip-a', '--at', '8'], ['split', '--seq', 'clip-a', '--at', end],
                             ['delete', '--seq', 'clip-a', '--track', '0', '--item', '3', '--ripple']]:
        run(proj, *c)
    if fade:
        run(proj, 'crossfade', '--seq', 'clip-a', '--track', str(a1_index(proj, 'clip-a')), '--item', '2', '--duration', '1')


GOOD = {   # case -> prproj.py commands (FILE FILE implied), 'srt', or a builder function
    'pip-slide-in': BK('clip-a') + [['add-transform', '--seq', 'clip-a', '--track', '1', '--item', '1', '--motion-blur', 'on',
                                      '--keys', 'position', '0f=1.6:0.5, 10f=0.5:0.5']],
    'trimmed-head-slide': BK('clip-a') + [['add-transform', '--seq', 'clip-a', '--track', '0', '--item', '2',
                                            '--keys', 'position', '0f=0.3:0.5, 24f=0.5:0.5']],
    'split-interview': BK('Interview') + [['split', '--seq', 'Interview', '--at', '45']],
    'label-while-open': [],
    'filler-markers': BK('Interview') + [['add-marker', '--seq', 'Interview', '--at', str(t), '--name', 'uh'] for t in G.FILLERS],
    'transcript-cut': BK('Interview') + [['split', '--seq', 'Interview', '--at', '1771f'], ['split', '--seq', 'Interview', '--at', '1836f'],
                                          ['delete', '--seq', 'Interview', '--track', '0', '--item', '2', '--ripple']],
    'captions-after-cut': 'srt',
    'rename-speakers': [['rename-speaker', '--from', 'Speaker 1', '--to', 'Interviewer'],
                        ['rename-speaker', '--from', 'Speaker 2', '--to', 'Sean Campbell']],
    'crossfade-no-handles': [],
    'rough-cut': lambda p: (run(p, *BK('Interview')[0]), rough_cut(p)),
    'assemble': assemble,
    'speaker-chapters': chapters,
    'cut-and-crossfade': cut_and_crossfade,
    'trim-blocked-by-fade': [],
    'speed-not-covered': [],
}
REPLY = {'speaker-chapters': '0:00 HR Screener\n0:10 Sean Campbell\n0:15 HR Screener\n0:21 Sean Campbell\n0:50 HR Screener\n0:58 Sean Campbell\n'}
# assertions the untouched input must fail (proves the check can fail)
MUST_FAIL_UNTOUCHED = {'pip-slide-in': [1, 2], 'trimmed-head-slide': [1, 2], 'split-interview': [1, 3],
                       'filler-markers': [1], 'transcript-cut': [1, 3, 4], 'captions-after-cut': [0],
                       'rename-speakers': [1, 2], 'rough-cut': [1, 2], 'assemble': [1, 2, 4],
                       'speaker-chapters': [1, 4], 'cut-and-crossfade': [1, 3, 4]}
# plausible wrong edits, and the assertions that must catch them
BROKEN = {
    'rough-cut': [('a cut that removes words too', lambda p: [run(p, *c) for c in GOOD['transcript-cut']], [1, 3])],
    'assemble': [('2 s crossfades instead of 1 s', lambda p: assemble(p, fade='2'), [4])],
    'cut-and-crossfade': [('3 s removed instead of 2', lambda p: cut_and_crossfade(p, end='11'), [1, 4]),
                          ('no crossfade', lambda p: cut_and_crossfade(p, fade=False), [3])],
    'speaker-chapters': [('Comment markers instead of chapters', lambda p: [run(p, 'add-marker', '--seq', 'Interview', '--at', str(t), '--name', 'x')
                                                                             for t in (0, 10.14, 15.98, 21.54, 50.7, 58.22)], [1])],
}


def build(case, d, how=None):
    proj = os.path.join(d, 'demo.prproj')
    shutil.copyfile(os.path.join(SKILL, case['files'][0]), proj)
    how = GOOD[case['name']] if how is None else how
    if how == 'srt':
        out = subprocess.run(PR + ['cut-transcript', proj, '--seq', 'Interview', '--srt'], capture_output=True, text=True, check=True).stdout
        open(os.path.join(d, 'interview.srt'), 'w').write(out)
    elif callable(how):
        how(proj)
    else:
        for c in how:
            run(proj, *c)


def grade(case, d, reply=''):
    return G.grade_scripted(case, G.Run(case, os.path.join(SKILL, case['files'][0]), d, reply))


def main():
    evals = json.load(open(os.path.join(SKILL, 'evals', 'evals.json')))
    fails = 0
    for case in evals['evals']:
        name = case['name']
        with tempfile.TemporaryDirectory() as good, tempfile.TemporaryDirectory() as bare:
            build(case, good)
            shutil.copyfile(os.path.join(SKILL, case['files'][0]), os.path.join(bare, 'demo.prproj'))
            g, u = grade(case, good, REPLY.get(name, '')), grade(case, bare)
        bad = {k: v[1] for k, v in g.items() if v is not G.JUDGE and not v[0]}
        missed = [k for k in MUST_FAIL_UNTOUCHED.get(name, []) if u[k] is G.JUDGE or u[k][0]]
        caught = []
        for label, how, keys in BROKEN.get(name, []):
            with tempfile.TemporaryDirectory() as b:
                build(case, b, how)
                r = grade(case, b, REPLY.get(name, ''))
            caught += [(label, k) for k in keys if r[k] is G.JUDGE or r[k][0]]
        ok = not bad and not missed and not caught
        fails += not ok
        n = sum(v is not G.JUDGE for v in g.values())
        extra = f", {len(BROKEN.get(name, []))} broken edit(s) caught" if name in BROKEN else ''
        print(f"{'PASS' if ok else 'FAIL'}  graders {name}: {n} script checks pass on a correct output"
              + (f", untouched input fails {MUST_FAIL_UNTOUCHED[name]}" if name in MUST_FAIL_UNTOUCHED else '') + extra)
        for k, ev in bad.items():
            print(f'        correct output failed {k}: {ev}')
        for k in missed:
            print(f'        untouched input passed {k}: {u[k]}')
        for label, k in caught:
            print(f'        broken edit "{label}" passed {k}')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
