#!/usr/bin/env python3
"""Rebuild skills/premiere-pro-projects/evals/files/ from the demo project's steps.

Every eval input is a step, or a step plus prproj.py commands, so the inputs can't drift
from the evidence. --check rebuilds into a temporary folder and compares instead of
writing: copies must be byte-identical, built files equal apart from the fresh GUIDs and
UIDs the commands generate (compared with prproj.py's graph diff).

  python3 -I tools/premiere-pro/build_eval_files.py          # write evals/files/
  python3 -I tools/premiere-pro/build_eval_files.py --check  # exit 1 if any differ
"""
import os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STEPS = os.path.join(ROOT, 'fixtures', 'premiere-pro', 'steps')
SKILL = os.path.join(ROOT, 'skills', 'premiere-pro-projects')
OUT = os.path.join(SKILL, 'evals', 'files')
PRPROJ = os.path.join(SKILL, 'scripts', 'prproj.py')

# name -> (source: a step file name or another eval file, [prproj.py commands run as CMD FILE FILE ARGS])
FILES = {
    'pip.prproj': ('11-markers.prproj', [
        ['place', '--seq', 'clip-a', '--clip', 'clip-a.mp4', '--at', '12', '--track', '1', '--in', '5', '--duration', '4', '--video-only']]),
    'trimmed.prproj': ('16-gen-crossfade.prproj', []),
    'interview.prproj': ('18-gen-interview_sequence.prproj', []),
    'review.prproj': ('17-gen-backup_split_trims_markers.prproj', []),
    'transcribed.prproj': ('21-speaker_labeling.prproj', []),
    'interview-cut.prproj': ('transcribed.prproj', [
        ['split', '--seq', 'Interview', '--at', '383f'],
        ['split', '--seq', 'Interview', '--at', '516f'],
        ['delete', '--seq', 'Interview', '--track', '0', '--item', '2', '--ripple']]),
    'no-handles.prproj': ('08-ripple_delete.prproj', []),
    'named-speakers.prproj': ('23-gen-speakers_fixed.prproj', []),
}


def build(dest):
    os.makedirs(dest, exist_ok=True)
    for name, (src, cmds) in FILES.items():          # in order: later files may start from earlier ones
        s = os.path.join(dest, src) if src in FILES else os.path.join(STEPS, src)
        out = os.path.join(dest, name)
        shutil.copyfile(s, out)
        for c in cmds:
            r = subprocess.run([sys.executable, '-I', PRPROJ, c[0], out, out] + c[1:], capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(f'{name}: {" ".join(c)} failed:\n{r.stderr or r.stdout}')


GUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)


def _norm(xml, base):
    """Replace GUIDs the commands generated (absent from the source) by their order of appearance."""
    known, seen = set(GUID.findall(base)), {}
    return GUID.sub(lambda m: m.group(0) if m.group(0) in known else seen.setdefault(m.group(0), f'<new-{len(seen)}>'), xml)


def same(have, new, src):
    if open(have, 'rb').read() == open(new, 'rb').read():
        return True, 'identical'
    if src is None:
        return False, 'differs from its step'
    sys.path.insert(0, os.path.dirname(PRPROJ))
    import prproj as P
    base = P.load_xml(src)
    ok = _norm(P.load_xml(have), base) == _norm(P.load_xml(new), base)
    return ok, 'equal apart from generated IDs' if ok else 'differs from what its recipe builds (rebuild without --check, then prproj.py diff)'


def main():
    if '--check' not in sys.argv:
        build(OUT)
        print(f'rebuilt {len(FILES)} files in {os.path.relpath(OUT, ROOT)}')
        return 0
    bad = 0
    with tempfile.TemporaryDirectory() as t:
        build(t)
        for name, (_, cmds) in FILES.items():
            have = os.path.join(OUT, name)
            if not os.path.exists(have):
                ok, why = False, 'missing'
            else:
                src = FILES[name][0]
                base = os.path.join(t, src) if src in FILES else os.path.join(STEPS, src)
                ok, why = same(have, os.path.join(t, name), base if cmds else None)
            bad += not ok
            print(f"{'PASS' if ok else 'FAIL'}  eval file {name}: {why}")
    extra = sorted(set(os.listdir(OUT)) - set(FILES))
    for e in extra:
        print(f'FAIL  eval file {e}: not built by this script'); bad += 1
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
