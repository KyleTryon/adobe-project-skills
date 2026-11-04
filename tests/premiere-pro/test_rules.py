#!/usr/bin/env python3
"""Every claim in the spec is proven by a test.

Scans references/spec/*.md and the task guides for status tags:

  [O: <steps> #<rule-id>]   observed: Premiere wrote it; the check runs on the cited steps
  [V: <steps> #<rule-id>]   verified: the scripts wrote it and Premiere opened it (cite -gen- steps)

and fails when a tag has no rule ID, cites a step that doesn't exist, names a rule with no
check, or its check fails on the cited steps; when a check has no tag; and when an unproven
tag ([D], [N]) is left in. Prints the coverage at the end.

  python3 -I tests/premiere-pro/test_rules.py            # all rules
  python3 -I tests/premiere-pro/test_rules.py markers    # rule IDs containing "markers"
  python3 -I tests/premiere-pro/test_rules.py --list     # every tag and where it is
"""
import glob, importlib.util, os, re, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'rules'))
import _lib as L  # noqa: E402

FILES = sorted(glob.glob(os.path.join(L.SPEC, '*.md'))) + sorted(glob.glob(os.path.join(L.SKILL, 'references', '*.md')))
TAG = re.compile(r'\[(V|O|D|N)(?::\s*([^\]#]*?))?\s*(?:#([a-z0-9][\w.-]*))?\]')
STRICT = True     # [D]/[N] tags are not allowed: unproven material lives in the backlog
# words that mark an unproven claim in prose; the claim belongs in the backlog instead
HEDGES = re.compile(r'\b(derived|not observed|unverified|unconfirmed|assumed|is a guess|(?:is|are) expected to)\b', re.I)


def load_checks():
    for f in sorted(glob.glob(os.path.join(HERE, 'rules', '*.py'))):
        if os.path.basename(f).startswith('_'):
            continue
        spec = importlib.util.spec_from_file_location(os.path.basename(f)[:-3], f)
        spec.loader.exec_module(importlib.util.module_from_spec(spec))


def tags():
    out = []
    for f in FILES:
        code = False
        for i, ln in enumerate(open(f, encoding='utf-8'), 1):
            if ln.lstrip().startswith('```'):
                code = not code
            if code:
                continue
            for m in TAG.finditer(re.sub(r'`[^`]*`', '', ln)):
                out.append({'file': os.path.relpath(f, L.SKILL), 'line': i, 'kind': m.group(1),
                            'cite': (m.group(2) or '').strip(), 'id': m.group(3), 'text': m.group(0)})
    return out


def hedges():
    out = []
    for f in FILES + [os.path.join(L.SKILL, 'SKILL.md')]:
        code = False
        for i, ln in enumerate(open(f, encoding='utf-8'), 1):
            if ln.lstrip().startswith('```'):
                code = not code
            m = None if code else HEDGES.search(re.sub(r'`[^`]*`', '', ln))
            if m:
                out.append(f"{os.path.relpath(f, L.SKILL)}:{i}: unproven wording '{m.group(0)}' (prove it, or move it to the backlog)")
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    pick = args[0] if args else ''
    load_checks()
    ts = tags()
    if '--list' in sys.argv:
        for t in ts:
            print(f"{t['file']}:{t['line']}  {t['text']}")
        return 0
    fails, ran = [], 0
    proven = [t for t in ts if t['kind'] in 'OV']
    for t in ts:
        where = f"{t['file']}:{t['line']}"
        if t['kind'] in 'DN':
            if STRICT:
                fails.append(f"{where}: unproven tag {t['text']} (prove it or move it to the backlog)")
            continue
        if not t['id']:
            fails.append(f"{where}: {t['text']} has no rule ID (#area.name)"); continue
        if pick and pick not in t['id']:
            continue
        if t['id'] not in L.RULES:
            fails.append(f"{where}: no check for #{t['id']}"); continue
        if not t['cite']:
            fails.append(f"{where}: #{t['id']} cites no steps"); continue
        try:
            ev = L.evidence(t['cite'])
        except ValueError as e:
            fails.append(f"{where}: #{t['id']}: {e}"); continue
        if t['kind'] == 'V' and not any(s.generated for s in ev.all()):
            fails.append(f"{where}: [V] #{t['id']} must cite a script-written (-gen-) step"); continue
        try:
            L.RULES[t['id']](ev); ran += 1
            print(f"PASS  #{t['id']}  [{t['kind']}: {t['cite']}]")
        except L.Fail as e:
            fails.append(f"{where}: #{t['id']} fails on its evidence: {e}")
        except Exception:
            fails.append(f"{where}: #{t['id']} check crashed:\n{traceback.format_exc(limit=3)}")
    used = {t['id'] for t in proven if t['id']}
    if not pick:
        for rid in sorted(set(L.RULES) - used):
            fails.append(f"check #{rid} has no tag in the spec (remove it or cite it)")
    if not pick:
        fails += hedges()
    for f in fails:
        print('FAIL ', f)
    unproven = sum(t['kind'] in 'DN' for t in ts)
    print(f"\ncoverage: {ran} rule tags proven by a check; {len(proven) - ran} [O]/[V] tags not proven; "
          f"{unproven} unproven [D]/[N] tags; {len(L.RULES)} checks")
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
