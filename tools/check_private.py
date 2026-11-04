#!/usr/bin/env python3
"""Look for personal data in files about to be committed.

Premiere writes the editor's machine into every project: absolute paths with the user
name, volume names, recent files, sometimes inside base64 or UTF-16 blobs. This checks
.prproj files (decompressed, and every base64 blob decoded as UTF-8 and UTF-16LE), media
metadata and text files for identifiers taken from *your* machine, so it works for any
contributor without listing anyone's details in the repo:

  * your user name and home folder (`$USER`, `$HOME`), mounted volume names (/Volumes)
  * your git user.name and user.email
  * any extra words in `.private-words` (one per line, git-ignored), e.g. client or project names

  python3 -I tools/check_private.py FILE ...     # exit 1 and list hits
  python3 -I tools/check_private.py --all        # every tracked or staged file

The git name may appear in LICENSE and .claude-plugin/marketplace.json (attribution), and the
repo's own GitHub address (owner/repo, from `git remote get-url origin`) may appear anywhere.
"""
import base64, getpass, gzip, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME_OK = {'LICENSE', '.claude-plugin/marketplace.json'}
MEDIA = ('.mp4', '.mov', '.wav', '.png', '.jpg', '.jpeg')


def git(*a):
    try:
        return subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True).stdout.strip()
    except OSError:
        return ''


def identifiers():
    ids = {}   # pattern -> label
    user = os.environ.get('USER') or getpass.getuser()
    if user and user not in ('root', 'runner', 'editor') and len(user) > 2:
        ids[re.escape(user)] = 'your user name'
    home = os.path.expanduser('~')
    if home not in ('/', '/root') and len(home) > 6:
        ids[re.escape(home)] = 'your home folder'
    if os.path.isdir('/Volumes'):
        for v in os.listdir('/Volumes'):
            if v not in ('Macintosh HD', 'Recovery', 'Preboot', 'VM', 'Data', 'Update') and len(v) > 2:
                ids[r'/Volumes/' + re.escape(v)] = 'a mounted volume'
    name, email = git('config', 'user.name'), git('config', 'user.email')
    if name and len(name) > 2:
        ids[re.escape(name)] = 'NAME'
    if email and 'noreply' not in email:
        ids[re.escape(email)] = 'your git email'
    pw = os.path.join(ROOT, '.private-words')
    if os.path.exists(pw):
        for w in open(pw, encoding='utf-8'):
            w = w.strip()
            if w and not w.startswith('#'):
                ids[re.escape(w)] = f'private word ({w})'
    return ids


def repo_slug():
    """'Owner/repo' from the origin remote, so the repo's own address isn't flagged."""
    m = re.search(r'github\.com[:/]+([^/\s]+/[^/\s]+?)(?:\.git)?/?$', git('remote', 'get-url', 'origin'))
    return m.group(1) if m else None


def texts(path):
    raw = open(path, 'rb').read()
    if path.endswith('.prproj'):
        x = (gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw).decode('utf-8', 'replace')
        out = [x]
        for b in re.findall(r'Encoding="base64"[^>]*>([A-Za-z0-9+/=\s]{16,})<', x):
            try:
                d = base64.b64decode(re.sub(r'\s', '', b))
                out += [d.decode('utf-8', 'ignore'), d.decode('utf-16-le', 'ignore')]
            except ValueError:
                pass
        return out
    if path.lower().endswith(MEDIA):
        return [' '.join(x.decode() for x in re.findall(rb'[ -~]{5,}', raw))]
    if b'\0' in raw[:4096]:
        return []
    return [raw.decode('utf-8', 'replace')]


def main(argv):
    files = argv
    if '--all' in argv or not argv:
        files = sorted(set(git('ls-files').splitlines()) | set(git('diff', '--cached', '--name-only').splitlines()))
    ids = identifiers()
    if not ids:
        print('check_private: nothing to look for on this machine'); return 0
    rx = {p: re.compile(p, re.I) for p in ids}
    slug = repo_slug()
    hits = []
    for f in files:
        p = os.path.join(ROOT, f) if not os.path.isabs(f) else f
        rel = os.path.relpath(p, ROOT)
        if not os.path.isfile(p) or rel == '.private-words':
            continue
        for t in texts(p):
            if slug:
                t = re.sub(re.escape(slug), '<this repo>', t, flags=re.I)
            for pat, label in ids.items():
                if label == 'NAME' and rel in NAME_OK:
                    continue
                m = rx[pat].search(t)
                if m:
                    hits.append(f"{rel}: {'your git name' if label == 'NAME' else label}: …{t[max(0, m.start() - 30):m.end() + 30]!r}…")
                    break
    for h in hits:
        print('PRIVATE ', h)
    if hits:
        print(f"\n{len(hits)} file(s) contain personal data. Scrub them (tools/premiere-pro/scrub_steps.py for home paths) "
              "or remove them before committing.")
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
