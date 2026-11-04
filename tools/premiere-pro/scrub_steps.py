#!/usr/bin/env python3
"""Remove machine details from saved Premiere projects, in place.

Premiere writes absolute paths (media, peak files, the last-saved path) that show your
user name and where you keep the repo. This rewrites them to neutral forms:

  * <wherever the repo is>/...                 -> /Users/editor/adobe-project-skills/...
  * /Users/<your name>/... (anything else)     -> /Users/editor/...

Run it on new steps before committing; --check only reports (the pre-commit hook and CI
run it). fixtures/premiere-pro/generated/build.sh --local maps the neutral paths back to
your machine so Premiere finds the media without asking.

    python3 -I tools/premiere-pro/scrub_steps.py [--check] [FILES...]   (default: steps/*.prproj)
"""
import glob, gzip, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CANON = '/Users/editor/adobe-project-skills'
# the repo under any folder, under its current or earlier name
REPO_RE = re.compile(r'/Users/[^/<"&\s]+/(?:[^<"&\s]*?/)?(?:adobe-creative-cloud-skills|adobe-project-skills)(?=/|<|"|$)')
HOME_RE = re.compile(r'/Users/(?!editor/)([^/<"&\s]+)/')


def scrub(x):
    x = x.replace(os.path.realpath(ROOT), CANON)
    x = REPO_RE.sub(lambda m: m.group(0) if m.group(0) == CANON else CANON, x)
    return HOME_RE.sub('/Users/editor/', x)


def main():
    args = [a for a in sys.argv[1:] if a != '--check']
    check = '--check' in sys.argv
    files = args or sorted(glob.glob(os.path.join(ROOT, 'fixtures', 'premiere-pro', 'steps', '*.prproj')))
    dirty = 0
    for f in files:
        raw = open(f, 'rb').read()
        x = (gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw).decode('utf-8')
        y = scrub(x)
        if y == x:
            continue
        dirty += 1
        what = sorted(set(HOME_RE.findall(x))) or ['repo location']
        if check:
            print(f"needs scrubbing: {os.path.basename(f)} ({', '.join(what)})")
            continue
        open(f, 'wb').write(gzip.compress(y.encode('utf-8')))
        print(f"scrubbed {os.path.basename(f)} ({', '.join(what)})")
    if check and dirty:
        sys.exit(1)
    if not dirty:
        print('all clean')


if __name__ == '__main__':
    main()
