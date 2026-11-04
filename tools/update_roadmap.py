#!/usr/bin/env python3
"""Recompute the progress figures in skills/README.md.

  * each roadmap group's percentage from its feature rows (✅ 1, 🟡 ½, ⬜ 0) and the overall figure;
  * the Premiere proof line: how many spec claims are proven by checks (tests/premiere-pro/test_rules.py)
    and how many commands are proven or refused (tests/premiere-pro/test_commands.py).

  python3 -I tools/update_roadmap.py           # rewrite skills/README.md
  python3 -I tools/update_roadmap.py --check   # exit 1 if it's out of date (CI)
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'skills', 'README.md')
W = {'✅': 1.0, '🟡': 0.5, '⬜': 0.0}


def proof_line():
    sys.path.insert(0, os.path.join(ROOT, 'tests', 'premiere-pro'))
    sys.path.insert(0, os.path.join(ROOT, 'tests', 'premiere-pro', 'rules'))
    import test_rules as T
    import test_commands as C
    T.load_checks()
    tags = [t for t in T.tags() if t['kind'] in 'OV' and t['id']]
    src = open(os.path.join(ROOT, 'skills', 'premiere-pro-projects', 'scripts', 'prproj.py'), encoding='utf-8').read()
    cmds = re.findall(r"'([\w-]+)'", re.search(r"ap.add_argument\('cmd', choices=\[(.*?)\]\)", src, re.S).group(1))
    proven = [c for c in cmds if c in C.REPLAYED or c in C.READS]
    refused = [c for c in cmds if c in C.P.UNPROVEN]
    return (f"**Proof:** {len(tags)} claims in the spec and guides, each checked against the steps it cites "
            f"({len(T.L.RULES)} checks); {len(proven)} of {len(cmds)} commands proven against Premiere, "
            f"{len(refused)} refused until a step proves them ({', '.join(f'`{c}`' for c in refused)}).")


def main():
    s = old = open(P, encoding='utf-8').read()
    groups = {}
    for m in re.finditer(r'^### (.+?)\n\n\| \| Feature.*?\n\|---.*?\n((?:\|.*\n)+)', s, re.M):
        marks = re.findall(r'^\| (✅|🟡|⬜) \|', m.group(2), re.M)
        if marks:
            groups[m.group(1)] = (sum(W[x] for x in marks), len(marks))
    for g, (w, n) in groups.items():
        pct = round(100 * w / n); bar = '█' * round(pct / 10) + '░' * (10 - round(pct / 10))
        s = re.sub(r'(\| \[%s\]\(#[^)]+\) \| )`[█░]+` \d+%%' % re.escape(g), lambda m: f"{m.group(1)}`{bar}` {pct}%", s)
    tw = sum(w for w, _ in groups.values()); tn = sum(n for _, n in groups.values())
    s = re.sub(r'Overall: \*\*\d+%\*\* of the \d+ features listed', f'Overall: **{round(100 * tw / tn)}%** of the {tn} features listed', s)
    line = proof_line()
    if '**Proof:**' in s:
        s = re.sub(r'^\*\*Proof:\*\*.*$', lambda m: line, s, flags=re.M)
    else:
        s = s.replace('\n| Area | Complete |', '\n' + line + '\n\n| Area | Complete |', 1)
    if '--check' in sys.argv:
        if s != old:
            print('skills/README.md progress figures are out of date: run python3 -I tools/update_roadmap.py')
            return 1
        print('skills/README.md progress figures are current')
        return 0
    open(P, 'w', encoding='utf-8').write(s)
    for g, (w, n) in groups.items():
        print(f"{round(100 * w / n):>3}%  {g}")
    print(f"{round(100 * tw / tn):>3}%  overall ({tn} features)")
    print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main())
