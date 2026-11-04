#!/usr/bin/env python3
"""Every prproj.py command is either proven against Premiere or refused as unproven.

Write commands are proven by tests/premiere-pro/replay_steps.py (their output matches
Premiere's own save, or a script-written step that was opened in Premiere). Read commands
are proven here: each runs on a step and must report what Premiere did in that step. A
command that is in neither list fails this test, so nothing new ships without proof.
"""
import json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, 'skills', 'premiere-pro-projects', 'scripts')
STEPS = os.path.join(ROOT, 'fixtures', 'premiere-pro', 'steps')
sys.path.insert(0, SCRIPTS)
import prproj as P  # noqa: E402


def step(n):
    return next(os.path.join(STEPS, f) for f in sorted(os.listdir(STEPS)) if f.startswith(n))


def run(*args, ok=True):
    r = subprocess.run([sys.executable, '-I', os.path.join(SCRIPTS, 'prproj.py'), *args], capture_output=True, text=True)
    if ok and r.returncode:
        raise AssertionError(f"prproj.py {' '.join(args)} failed: {r.stderr.strip()[-300:]}")
    return r


def js(*args):
    return json.loads(run(*args, '--json').stdout)


def near(a, b, tol=0.002):
    return abs(a - b) <= tol


# write commands: where their proof lives
REPLAYED = {
    'place': 'steps 04→05 (A/V), 11→12-gen (--video-only)', 'split': 'steps 05→06', 'trim': 'steps 06→07',
    'delete': 'steps 07→08 (--ripple)', 'set-track': 'steps 08→09, 09→10', 'add-marker': 'steps 10→11',
    'backup-seq': 'step 17-gen', 'add-transform': 'step 12-gen', 'fade-in': 'step 13-gen', 'fade-out': 'steps 14-gen, 15',
    'crossfade': 'steps 15, 16-gen', 'rename-speaker': 'steps 21→22, 23-gen', 'set-speaker': 'steps 21→22, 23-gen',
}


def t_summary():
    out = run('summary', step('11')).stdout
    assert 'clip-a' in out and 'Custom' in out, out[:300]


def t_cuts():
    s = js('cuts', step('08'), '--seq', 'clip-a')
    v = [t for t in s['tracks'] if t['type'] == 'VideoClipTrack' and t['items']][0]['items']
    got = [(x['name'], round(x['start'], 3), round(x['end'], 3), round(x['src_in'], 3)) for x in v]
    assert got == [('clip-a.mp4', 0.0, 4.963, 0.0), ('clip-b.mp4', 4.963, 23.023, 0.0)], got


def t_markers():
    ms = js('markers', step('11'), '--seq', 'clip-a')
    got = [(m['name'], m['type'], m['colour']) for m in ms]
    assert got == [('Marker_Test', 'Comment', '#E96F24'), ('Chapter 01', 'Chapter', '#AF8BB1')], got
    assert near(ms[0]['time'], 2.002) and near(ms[1]['time'], 8.634, 0.001), [m['time'] for m in ms]
    ch = run('markers', step('11'), '--seq', 'clip-a', '--chapters', ok=False)
    assert 'Chapter 01' in ch.stdout, ch.stdout


def t_effects():
    rows = js('effects', step('12'), '--seq', 'clip-a')
    pip = next(r for r in rows if r['track'] == 1 and r['item'] == 1)
    tf = [c for c in pip['components'] if c['match_name'] == 'AE.ADBE Geometry2']
    assert len(tf) == 1, pip['components']
    pos = next(p for p in tf[0]['params'] if p['name'] == 'Position')
    assert near(pos['keys'][0]['timeline_sec'], 12.012), pos['keys'][0]


def t_transcript():
    tr = js('transcript', step('19'))
    words = [w['w'] for sg in tr['segments'] for w in sg['words'] if w['w']]
    fillers = sum(w.get('kind') == 'filler' for sg in tr['segments'] for w in sg['words'])
    assert words[:2] == ['Hi,', 'Sean.'] and len(words) == 205 and fillers == 12, (words[:3], len(words), fillers)


def t_cut_transcript():
    w = js('cut-transcript', step('19'), '--seq', 'Interview')
    assert w[0]['w'] == 'Hi,' and near(w[0]['t'], 1.02), w[0]
    srt = run('cut-transcript', step('19'), '--seq', 'Interview', '--srt').stdout
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(w, f)
    again = run('srt-from-words', f.name).stdout
    os.unlink(f.name)
    assert again == srt and '  ' not in srt and srt.startswith('1\n00:00:01,020 --> '), srt[:80]


def t_speakers():
    a = js('speakers', step('21'))
    b = js('speakers', step('22'))
    assert [x['speaker'] for x in a][:2] == ['Speaker 1', 'Speaker 2'], a[:2]
    assert {x['speaker'] for x in b} == {'Interviewer', 'Sean Campbell'}, {x['speaker'] for x in b}


def t_compare_transcript():
    d = js('compare-transcript', step('19'), '--ref', os.path.join(ROOT, 'fixtures', 'premiere-pro', 'media', 'interview.srt'))
    assert abs(d['stats']['wer'] - 0.0404) < 0.0005, d['stats']


def t_diff():
    d = js('diff', step('05'), step('06'))
    added = [(x['class'], x['objects']) for x in d['added']]
    assert added == [('Link', 11)] and not d['removed'], f'razor at frame 119 should add one linked pair of 11 objects: {added}'
    same = js('diff', step('06'), step('06'))['counts']
    assert same['added'] == same['removed'] == same['changed'] == 0, same


def t_validate():
    for f in sorted(os.listdir(STEPS)):
        r = run('validate', os.path.join(STEPS, f), ok=False)
        assert r.returncode == 0 and 'VALID' in r.stdout, f'{f}: {r.stdout.strip()[-200:]}'


def t_pack_unpack():
    with tempfile.TemporaryDirectory() as d:
        x, p = os.path.join(d, 'a.xml'), os.path.join(d, 'a.prproj')
        run('unpack', step('11'), x); run('pack', x, p)
        assert P.load_xml(p) == P.load_xml(step('11')), 'unpack/pack changed the XML'


READS = {'summary': t_summary, 'cuts': t_cuts, 'markers': t_markers, 'effects': t_effects, 'transcript': t_transcript,
         'cut-transcript': t_cut_transcript, 'srt-from-words': t_cut_transcript, 'speakers': t_speakers,
         'compare-transcript': t_compare_transcript, 'diff': t_diff, 'validate': t_validate,
         'unpack': t_pack_unpack, 'pack': t_pack_unpack}


def main():
    src = open(os.path.join(SCRIPTS, 'prproj.py')).read()
    cmds = re.findall(r"'([\w-]+)'", re.search(r"ap.add_argument\('cmd', choices=\[(.*?)\]\)", src, re.S).group(1))
    fails = 0
    for c in cmds:
        if c in P.UNPROVEN:
            r = run(c, step('11'), os.devnull, '--seq', 'clip-a', ok=False)
            ok = r.returncode == 2 and 'unproven' in r.stderr
            print(f"{'PASS' if ok else 'FAIL'}  {c}: unproven, refused without --unproven ({P.UNPROVEN[c]})")
        elif c in REPLAYED:
            ok = True
            print(f"PASS  {c}: proven by replay_steps.py ({REPLAYED[c]})")
        elif c in READS:
            try:
                READS[c](); ok = True
                print(f"PASS  {c}: reports what Premiere did")
            except AssertionError as e:
                ok = False
                print(f"FAIL  {c}: {e}")
        else:
            ok = False
            print(f"FAIL  {c}: no proof. Add a replay case or a read check here, or list it in prproj.UNPROVEN")
        fails += not ok
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
