#!/usr/bin/env python3
"""prproj-schema.json and prproj-classes.md are what schema_dump.py builds from the steps,
every step is fully covered by the catalogue, and validate's unseen-structure warning fires
on structure the steps never showed."""
import glob, os, subprocess, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, 'skills', 'premiere-pro-projects', 'scripts')
STEPS = sorted(glob.glob(os.path.join(ROOT, 'fixtures', 'premiere-pro', 'steps', '*.prproj')))
sys.path.insert(0, SCRIPTS)
import schema_dump as S  # noqa: E402

fails = 0


def check(ok, what):
    global fails
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {what}")


r = subprocess.run([sys.executable, '-I', os.path.join(SCRIPTS, 'schema_dump.py'), '--check', *STEPS], capture_output=True, text=True)
check(r.returncode == 0, 'prproj-schema.json and prproj-classes.md are up to date with the steps' + ('' if not r.returncode else '\n' + r.stdout))

bad = [os.path.basename(p) for p in STEPS if S.unseen(S.load(p))]
check(not bad, f'every step is fully described by the catalogue{": " + ", ".join(bad) if bad else ""}')

root = S.load(os.path.join(ROOT, 'fixtures', 'premiere-pro', 'steps', '11-markers.prproj'))
m = next(e for e in root if e.tag == 'Marker')
m.set('Version', '99')
ET.SubElement(m, 'NewField').text = '1'
ET.SubElement(root, 'BrandNewClass', ObjectID='999999', ClassID='00000000-0000-0000-0000-000000000000', Version='1')
w = ' '.join(S.unseen(root))
check('BrandNewClass' in w and 'Version 99' in w and 'Marker/NewField' in w, 'unseen() reports a new class, a new Version and a new path')
sys.exit(1 if fails else 0)
