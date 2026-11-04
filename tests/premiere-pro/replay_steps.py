#!/usr/bin/env python3
"""Replay tests: Premiere is the referee.

Each case takes a recorded Premiere save (fixtures/premiere-pro/steps/NN-*.prproj),
makes the same edit with scripts/prproj.py, and diffs the result against Premiere's
own save of that edit. GUIDs our script has to invent (ClipIDs, item IDs, marker IDs)
are aligned by position first; the only differences allowed are listed in ALLOWED (optionally for one step only).

    python3 -I tests/premiere-pro/replay_steps.py            # all cases
    python3 -I tests/premiere-pro/replay_steps.py split      # cases whose name contains 'split'

Exit status 1 if any case fails.
"""
import os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCRIPTS = os.path.join(ROOT, 'skills', 'premiere-pro-projects', 'scripts')
STEPS = os.path.join(ROOT, 'fixtures', 'premiere-pro', 'steps')
sys.path.insert(0, SCRIPTS)
import prproj as P  # noqa: E402

# (name, before, after, [commands]); each command is the argv after `prproj.py CMD IN OUT`
CASES = [
    ('place clip-b after clip-a', '04-custom_seq', '05-add_clip_b',
     [['place', '--seq', 'clip-a', '--clip', 'clip-b.mp4', '--at', '19.978']]),
    ('split (razor) at frame 119', '05-add_clip_b', '06-cut',
     [['split', '--seq', 'clip-a', '--at', '119f', '--track', '0']]),
    ('trim end of clip-b', '06-cut', '07-trim_about_2_seconds',
     [['trim', '--seq', 'clip-a', '--track', '0', '--item', '3', '--end', '38.038']]),
    ('ripple delete', '07-trim_about_2_seconds', '08-ripple_delete',
     [['delete', '--seq', 'clip-a', '--track', '0', '--item', '2', '--ripple']]),
    ('lock V1, mute A1', '08-ripple_delete', '09-lock_and_mute',
     [['set-track', '--seq', 'clip-a', '--track', '0', '--lock', 'on'],
      ['set-track', '--seq', 'clip-a', '--track', '3', '--mute', 'on']]),
    ('rename V2', '09-lock_and_mute', '10-rename_track',
     [['set-track', '--seq', 'clip-a', '--track', '1', '--name', 'Graphics']]),
    # regression: steps written by prproj.py and checked in Premiere (names with -gen-)
    ('verified: place video-only + Transform slide-in', '11-markers', '12-gen-pip',
     [['place', '--seq', 'clip-a', '--clip', 'clip-a.mp4', '--at', '12', '--track', '1', '--in', '5', '--duration', '4', '--video-only'],
      ['add-transform', '--seq', 'clip-a', '--track', '1', '--item', '1', '--set', 'scale=40', '--motion-blur', 'on',
       '--keys', 'position', '0f=1.3:0.75@linear, 12f=0.78:0.75, -12f=0.78:0.75, -1f=1.3:0.75@linear']]),
    ('verified: unmute + audio fade-in', '12-gen-pip', '13-gen-audio-fade',
     [['set-track', '--seq', 'clip-a', '--track', '3', '--mute', 'off'],
      ['fade-in', '--seq', 'clip-a', '--track', '3', '--item', '2', '--duration', '24f']]),
    ('verified: audio fade-out', '13-gen-audio-fade', '14-gen-audio-fade-out',
     [['fade-out', '--seq', 'clip-a', '--track', '3', '--item', '2', '--duration', '24f']]),
    ('verified: roll the cut with two trims, crossfade, fade-out', '12-gen-pip', '16-gen-crossfade',
     [['set-track', '--seq', 'clip-a', '--track', '3', '--mute', 'off'],
      ['set-track', '--seq', 'clip-a', '--track', '0', '--lock', 'off'],
      ['trim', '--seq', 'clip-a', '--track', '0', '--item', '2', '--start', '6.298'],
      ['trim', '--seq', 'clip-a', '--track', '0', '--item', '1', '--end', '6.298'],
      ['crossfade', '--seq', 'clip-a', '--track', '3', '--item', '1', '--duration', '1'],
      ['fade-out', '--seq', 'clip-a', '--track', '3', '--item', '2', '--duration', '24f']]),
    ('verified: backup, unlock, rename + unmute, split, trims, markers', '11-markers', '17-gen-backup_split_trims_markers',
     [['backup-seq', '--seq', 'clip-a', '--name', 'clip-a (backup before verify)'],
      ['set-track', '--seq', 'clip-a', '--track', '0', '--lock', 'off'],
      ['set-track', '--seq', 'clip-a', '--track', '3', '--mute', 'off', '--name', 'Dialogue'],
      ['split', '--seq', 'clip-a', '--at', '10'],
      ['trim', '--seq', 'clip-a', '--track', '0', '--item', '3', '--end', '22'],
      ['trim', '--seq', 'clip-a', '--track', '0', '--item', '2', '--start', '6'],
      ['add-marker', '--seq', 'clip-a', '--at', '0', '--name', 'Intro', '--type', 'Chapter', '--colour', 'pink'],
      ['add-marker', '--seq', 'clip-a', '--at', '15', '--name', 'Check this cut', '--comment', 'added by add-marker',
       '--colour', 'orange']]),
    ('verified: a new sequence for the interview (backup-seq of an empty one + place)', '04-custom_seq', '18-gen-interview_sequence',
     [['backup-seq', '--seq', 'Custom', '--name', 'Interview'],
      ['place', '--seq', 'Interview', '--clip', 'interview.mp4', '--at', '0']]),
    ('two markers', '10-rename_track', '11-markers',
     [['add-marker', '--seq', 'clip-a', '--at', '00:00:08:15', '--name', 'Chapter 01',
       '--comment', 'Chapter 01 Comment', '--type', 'Chapter', '--colour', 'pink'],
      ['add-marker', '--seq', 'clip-a', '--at', '00:00:02:00', '--name', 'Marker_Test',
       '--comment', 'this is a comment', '--colour', 'orange']]),
]

# Cases where the "before" file is Premiere's save with one thing taken out again
# (strip_*(xml) -> xml), then put back by the script and compared with Premiere's save.
def strip_transition(name):
    def f(xml):
        m = re.search(r'\n\t<AudioTransitionTrackItem ObjectID="(\d+)"[^>]*>(?:(?!</AudioTransitionTrackItem>).)*?'
                      r'<DisplayName>%s</DisplayName>.*?</AudioTransitionTrackItem>' % re.escape(name), xml, re.S)
        k = m.group(1); xml = xml[:m.start()] + xml[m.end():]
        xml = re.sub(r'\n\t+<(Head|Tail)Transition ObjectRef="%s"/>' % k, '', xml)
        xml = re.sub(r'\n\t+<TrackItem Index="\d+" ObjectRef="%s"/>' % k, '', xml)
        def reindex(mm):
            n = [-1]
            return re.sub(r'Index="\d+"', lambda q: (n.__setitem__(0, n[0] + 1) or f'Index="{n[0]}"'), mm.group(0))
        return re.sub(r'<TransitionItems Version="3">.*?</TransitionItems>', reindex, xml, flags=re.S)
    return f


STRIPPED = [
    ('constant-power crossfade (94 frames)', '15-handles_and_crossfade', strip_transition('Constant Power'),
     [['crossfade', '--seq', 'clip-a', '--track', '3', '--item', '1', '--duration', '94f']]),
    ('audio fade-out (24 frames)', '15-handles_and_crossfade', strip_transition('Custom Fade'),
     [['fade-out', '--seq', 'clip-a', '--track', '3', '--item', '2', '--duration', '24f']]),
]

# Differences that are expected and why.
ALLOWED = [
    (r'/MasterClipChangeVersion$', 'Premiere bumps this counter on every edit; the scripts leave it'),
    (r'^/ComponentChain(/Node.*)?$', 'Effect Controls view state Premiere writes when a clip is selected'),
    (r'AudioCategorization|/ESP\.|EssentialSound|^/ClipTrackItem/TrackItem/Node', "Premiere's automatic audio type tagging (Essential Sound)"),
    (r'^/RelativePath$', 'step 04 was saved one folder up, so its relative paths differ'),
    (r'^/FrameRect$', 'interview_sequence', "18-gen predates the place fix: it gave the item the clip's 1280x720, which Premiere "
                      "rewrote to the sequence's 1920x1080 on its next save (step 19); place now writes the sequence size"),
]


def align_guids(premiere_xml, ours_xml):
    """Rewrite GUIDs our script invented to the ones Premiere chose, matched by position."""
    ra, rb = P.ET.fromstring(premiere_xml), P.ET.fromstring(ours_xml)
    ia, ib = P.index(ra), P.index(rb)
    sub = {}
    sa = {s['name']: s for s in P.sequences(ra, ia)}
    for s in P.sequences(rb, ib):
        if s['name'] not in sa:
            continue
        for ta, tb in zip(sa[s['name']]['tracks'], s['tracks']):
            ka = sorted(ta['items'], key=lambda i: i['start_ticks'])
            kb = sorted(tb['items'], key=lambda i: i['start_ticks'])
            for x, y in zip(ka, kb):
                for f in ('.//ClipID',):
                    cx, cy = P.txt(ia.get(x['clip_id']), f), P.txt(ib.get(y['clip_id']), f)
                    if cx and cy: sub[cy] = cx
                ex, ey = ia.get(x['item_id']), ib.get(y['item_id'])
                if ex is not None and ey is not None and P.txt(ex, 'ID') and P.txt(ey, 'ID'):
                    sub[P.txt(ey, 'ID')] = P.txt(ex, 'ID')
    for name in sa:
        qa = [e for e in ra.findall('Sequence') if P.txt(e, 'Name') == name]
        qb = [e for e in rb.findall('Sequence') if P.txt(e, 'Name') == name]
        if not qa or not qb:
            continue
        ma, mb = P.read_markers(ra, ia, qa[0]), P.read_markers(rb, ib, qb[0])
        for x, y in zip(ma, mb):
            sub[y['id']] = x['id']
        keys = lambda root: {m.group(2): m.group(1) for m in re.finditer(
            r'keywordExtDVAv1_(%s).*?mMarkerID&?q?u?o?t?;?\\?"?:?\\?"?(%s)' % (P.GUID_RE, P.GUID_RE), root)}
        ka_, kb_ = keys(premiere_xml), keys(ours_xml)
        for mid_b, key_b in kb_.items():
            mid_a = sub.get(mid_b)
            if mid_a in ka_: sub[key_b] = ka_[mid_a]
    for b, a in sub.items():
        if a != b:
            ours_xml = ours_xml.replace(b, a)
    return ours_xml


def align_new_guids(before_xml, ref_xml, ours_xml):
    """For files the scripts wrote themselves (-gen- steps): every GUID that neither
    file inherited from `before` was invented by the script, in the same order each run,
    so map ours onto the reference's by order of first appearance."""
    old = set(re.findall(P.GUID_RE, before_xml))
    def fresh(x):
        seen = []
        for g in re.findall(P.GUID_RE, x):
            if g not in old and g not in seen:
                seen.append(g)
        return seen
    a, b = fresh(ref_xml), fresh(ours_xml)
    if len(a) != len(b):
        return ours_xml
    for x, y in zip(a, b):
        if x != y:
            ours_xml = ours_xml.replace(y, x)
    return ours_xml


def run_case(name, before, after, cmds, strip=None):
    src = os.path.join(STEPS, before + '.prproj'); ref = os.path.join(STEPS, after + '.prproj')
    if not (os.path.exists(src) and os.path.exists(ref)):
        return None, ['fixture steps missing']
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, 'out.prproj'); cur = src
        if strip:
            cur = os.path.join(tmp, 'stripped.prproj')
            open(cur, 'wb').write(P.gzip.compress(strip(P.load_xml(src)).encode('utf-8')))
        for c in cmds:
            r = subprocess.run([sys.executable, '-I', os.path.join(SCRIPTS, 'prproj.py'), c[0], cur, out] + c[1:],
                               capture_output=True, text=True)
            if r.returncode:
                return False, [f"`{' '.join(c)}` failed: {r.stderr.strip()}"]
            cur = out
        prem = P.load_xml(ref); ours = align_guids(prem, P.load_xml(out))
        if '-gen-' in after:
            ours = align_new_guids(P.load_xml(src), prem, ours)
        d = P.diff_projects(prem, ours)
    problems, allowed = [], set()
    for kind in ('added', 'removed', 'moved'):
        for x in d[kind]:
            problems.append(f"{kind}: {x.get('class')} {x.get('where') or x}")
    for ch in d['changed']:
        for p, va, vb in ch['fields']:
            why = next((a[-1] for a in ALLOWED if re.search(a[0], p) and (len(a) == 2 or a[1] in after)), None)
            if why:
                allowed.add(why)
            else:
                problems.append(f"{ch['class']} {ch['where']} {p}: Premiere {P._short(va)} / ours {P._short(vb)}")
    return not problems, problems or sorted(allowed)


# Transcript decoding: Premiere's Speech to Text in step 19 against the official captions.
# Guards the FlatBuffer reader and the comparison (transcripts-and-captions.md, "Speech-to-Text accuracy").
TRANSCRIPT_CHECKS = [
    ('19-speech_to_text', 'interview.srt', False, {'hyp_words': 217, 'ref_words': 223, 'wer': 0.0404}),
    ('19-speech_to_text', 'interview.srt', True, {'hyp_words': 205, 'ref_words': 204, 'wer': 0.0049}),
    ('21-speaker_labeling', 'interview.srt', False, {'hyp_words': 219, 'ref_words': 223, 'wer': 0.0314}),
]
EXPECT_KINDS = {'19-speech_to_text': (22, 12), '21-speaker_labeling': (22, 14)}
EXPECT_SPEAKERS = {'19-speech_to_text': ['Unknown'] * 4,
                   '21-speaker_labeling': ['Speaker 1', 'Speaker 2', 'Speaker 1', 'Speaker 2', 'Speaker 1',
                                           'Speaker 2', 'Speaker 2']}


SPEAKER_EDITS = [
    ('speakers renamed and a turn reassigned', '21-speaker_labeling', '22-speakers_renamed',
     lambda m: (P.rename_speaker(m, 'Speaker 1', 'Interviewer'), P.rename_speaker(m, 'Speaker 2', 'Sean Campbell'),
                P.assign_speaker(m, int(60 * P.TICKS), 'Interviewer'))),
    ('verified: turn given back to Sean, Interviewer renamed', '22-speakers_renamed', '23-gen-speakers_fixed',
     lambda m: (P.assign_speaker(m, int(60 * P.TICKS), 'Sean Campbell'), P.rename_speaker(m, 'Interviewer', 'HR Screener'))),
]


def _model(path):
    d = P.ET.fromstring(P.load_xml(path)).find('ExternallyProvidedTranscriptDocument')
    return P.transcript_model(P.base64.b64decode(d.find('TranscriptData').text.strip()))


def transcript_checks(pick):
    fails = 0
    for name, before, after, edit in SPEAKER_EDITS:
        if pick not in name:
            continue
        a, b = os.path.join(STEPS, before + '.prproj'), os.path.join(STEPS, after + '.prproj')
        if not (os.path.exists(a) and os.path.exists(b)):
            print(f"SKIP  {name}"); continue
        new, _w = P.rewrite_transcript(P.load_xml(a), 0, lambda m: edit(m) and 'ok')
        mine = P.transcript_model(P.base64.b64decode(P.ET.fromstring(new).find('ExternallyProvidedTranscriptDocument')
                                                     .find('TranscriptData').text.strip()))
        ok = mine == _model(b)
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {before} -> {after}  {name} (transcript decodes identically)")
    # every transcript in the steps survives a rebuild unchanged
    for f in sorted(os.listdir(STEPS)):
        if not f.endswith('.prproj') or 'rebuild' not in pick and pick:
            continue
        x = P.load_xml(os.path.join(STEPS, f))
        if '<ExternallyProvidedTranscriptDocument' not in x:
            continue
        m = _model(os.path.join(STEPS, f))
        ok = P.transcript_model(P.transcript_build(m)) == m
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {f[:-7]}  transcript rebuild round-trip")
    media = os.path.join(ROOT, 'fixtures', 'premiere-pro', 'media')
    for step, ref, nofill, want in TRANSCRIPT_CHECKS:
        name = f"transcript {step} vs {ref}" + (' (no fillers)' if nofill else '')
        if pick not in name:
            continue
        f = os.path.join(STEPS, step + '.prproj')
        if not os.path.exists(f):
            print(f"SKIP  {name}"); continue
        tr = P.transcripts(P.load_xml(f))[0]
        kinds = {}
        for sg in tr['segments']:
            for w in sg['words']:
                kinds[w['kind']] = kinds.get(w['kind'], 0) + 1
        hyp = [dict(w, w='uh') if w['kind'] == 'filler' else w for sg in tr['segments'] for w in sg['words']
               if w['w'] or w['kind'] == 'filler']
        _d, st = P.compare_words(hyp, P.read_srt_words(os.path.join(media, ref)), nofill)
        got = {k: st[k] for k in want}
        ok = (got == want and (kinds.get('pause'), kinds.get('filler')) == EXPECT_KINDS[step]
              and [sg['speaker'] for sg in tr['segments']] == EXPECT_SPEAKERS[step])
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: WER {st['wer']:.1%}" + ('' if ok else f"  expected {want}, got {got}, kinds {kinds}"))
    return fails


def main():
    pick = sys.argv[1] if len(sys.argv) > 1 else ''
    fails = 0
    home = re.compile(r'/Users/(?!editor/)[^/<"&\s]+/')
    for f in sorted(os.listdir(STEPS)) if os.path.isdir(STEPS) else []:
        if f.endswith('.prproj') and home.search(P.load_xml(os.path.join(STEPS, f))):
            print(f"FAIL  {f} contains a home folder path: run tools/premiere-pro/scrub_steps.py")
            fails += 1
    todo = [(n, b, a, c, None) for n, b, a, c in CASES] + [(n, s, s, c, f) for n, s, f, c in STRIPPED]
    for name, before, after, cmds, strip in todo:
        if pick not in name:
            continue
        ok, notes = run_case(name, before, after, cmds, strip)
        status = 'SKIP' if ok is None else ('PASS' if ok else 'FAIL')
        fails += ok is False
        print(f"{status}  {before} -> {after}  {name}" if not strip else f"{status}  {before} minus it, put back  {name}")
        for n in notes:
            print(f"        {'allowed: ' if ok else ''}{n}")
    fails += transcript_checks(pick)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
