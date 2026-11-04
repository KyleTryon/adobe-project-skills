#!/usr/bin/env python3
"""selftest.py - check prproj.py's assumptions against real Premiere projects.

Usage: python3 -I selftest.py PROJECT.prproj [MORE.prproj ...]

Read-only. Run it on projects saved by the Premiere version you're working with
(ideally ones with Transform moves, speed changes and audio keyframes). Each check
compares what prproj.py would write or compute with what Premiere itself wrote, so a
failure means the format has drifted and the matching reference file needs updating
before you trust the write commands on that version.

Checks:
  parse        file unpacks, objects index, transcripts decode
  timeline     every track item: timeline duration == (Out - In) / PlaybackSpeed
  transform    every Transform has the 12 params prproj.py's template writes, same
               tags/ClassIDs/ParameterIDs/child order (values ignored)
  keyframes    every Position/Level animation is reproduced by keyframe_string()
               from its own key times, values and interpolation flags
  keytimes     keyframes of Transform-ed clips map onto their clip's timeline span
Exit status 1 if any check fails.
"""
import sys, os, re, importlib.util
import xml.etree.ElementTree as ET

TRUNCATED = []
sys.dont_write_bytecode = True  # don't leave __pycache__ in the skill folder
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('prproj', os.path.join(HERE, 'prproj.py'))
pp = importlib.util.module_from_spec(spec); spec.loader.exec_module(pp)


def close(a, b, rel=1e-6, abs_=1e-8):
    # Premiere derives speeds from full-precision values but prints values to ~12
    # digits, so tiny speeds differ in the 5th digit; 1e-8 absolute covers that.
    return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))


def same_key(orig, mine, kind):
    for ka, kb in zip(orig.strip(';').split(';'), mine.strip(';').split(';')):
        fa, fb = ka.split(','), kb.split(',')
        if len(fa) != len(fb):
            return False
        for j, (x, y) in enumerate(zip(fa, fb)):
            if ':' in x:
                if not all(close(float(p), float(q)) for p, q in zip(x.split(':'), y.split(':'))):
                    return False
            elif not close(float(x), float(y)):
                # Premiere sometimes truncates a tiny float's exponent ('6.766e-10' is
                # written '6.766e-1'), and a later save then keeps the wrong value
                # (0.6766). Accept it when the significant digits agree.
                sig = lambda z: re.sub(r'[^0-9]', '', ('%.17e' % abs(float(z))).split('e')[0])[:3]
                if abs(float(y)) < 1e-8 and sig(x) == sig(y):
                    TRUNCATED.append(x)
                    continue
                return False
    return len(orig.strip(';').split(';')) == len(mine.strip(';').split(';'))


def check(path):
    fails, notes = [], []
    xml = pp.load_xml(path)
    root = ET.fromstring(xml); ids = pp.index(root)
    try:
        notes.append(f"{len(pp.transcripts(xml, root, ids))} transcripts decode")
    except Exception as e:  # noqa
        fails.append(f"parse: transcripts don't decode ({e})")
    seqs = pp.sequences(root, ids)

    # timeline arithmetic
    n = bad = 0
    for s in seqs:
        for t in s['tracks']:
            for it in t['items']:
                if it['src_in'] is None:
                    continue
                n += 1
                want = (it['out_ticks'] - it['in_ticks']) / (it['speed'] or 1)
                if abs((it['end_ticks'] - it['start_ticks']) - want) > 2:
                    bad += 1
                    if bad <= 3:
                        fails.append(f"timeline: {s['name']} {t['type']} '{it['name']}' at {pp.ts(it['start'])}: "
                                     f"duration {(it['end_ticks'] - it['start_ticks']) / pp.TICKS:.4f}s != "
                                     f"(Out-In)/speed {want / pp.TICKS:.4f}s")
    notes.append(f"timeline: {n - bad}/{n} items consistent")

    # Transform layout vs template
    tmpl = [(tag, cid, str(ver), dict(pre)['ParameterID'], [k for k, _ in pre] + ['StartKeyframe'] + [k for k, _ in post])
            for _k, tag, cid, ver, _kind, _d, pre, post in pp.TRANSFORM_PARAMS]
    nt = badt = 0
    for e in root:
        if e.tag == 'VideoFilterComponent' and pp.txt(e, 'MatchName') == pp.TRANSFORM_MATCH:
            nt += 1
            ps = pp.param_objects(ids, e)
            # IsTimeVarying/Keyframes come and go with animation; CurrentValue is optional
            got = [(p.tag, p.get('ClassID'), p.get('Version'), pp.txt(p, 'ParameterID'),
                    [c.tag for c in p if c.tag not in ('IsTimeVarying', 'Keyframes', 'CurrentValue')]) for p in ps]
            tmpl_cmp = [(a, b, c, d, [x for x in e if x != 'CurrentValue']) for a, b, c, d, e in tmpl]
            if len(got) != 12 or any(g != w for g, w in zip(got, tmpl_cmp)):
                badt += 1
                if badt <= 2:
                    diff = [(i, g, w) for i, (g, w) in enumerate(zip(got, tmpl_cmp)) if g != w]
                    fails.append(f"transform: object {e.get('ObjectID')} differs from template: {diff[:2]}")
    notes.append(f"transform: {nt - badt}/{nt} match the template")

    # keyframe writer reproduces Premiere's strings
    nk = badk = 0
    for e in root:
        kf = pp.txt(e, 'Keyframes')
        if not kf or not kf.strip():
            continue
        if e.tag == 'PointComponentParam':
            kind = 'point'
            conv = lambda v: tuple(float(x) for x in v.split(':'))
        elif e.tag == 'AudioComponentParam' and (pp.txt(e, 'Name') or '') == 'Level':
            kind = 'float'; conv = float
        else:
            continue
        keys = []
        for k in kf.strip(';').split(';'):
            f = k.split(',')
            keys.append((int(f[0]), conv(f[1]), 'ease' if f[2] == '5' else 'linear'))
        if len(keys) < 2:
            continue
        nk += 1
        mine = pp.keyframe_string(kind, keys)
        if not same_key(kf, mine, kind):
            # hand-tuned influences are legal; retry with the influence Premiere used
            # hand-tuned influences are legal: give each eased key the larger of the
            # influences Premiere stored on it and compare again
            per = [max(float(k.split(',')[5]), float(k.split(',')[7])) * 100 for k in kf.strip(';').split(';')]
            if same_key(kf, pp.keyframe_string(kind, [(t, v, f'ease:{x}' if i == 'ease' else i)
                                                      for (t, v, i), x in zip(keys, per)]), kind):
                continue
            badk += 1
            if badk <= 2:
                fails.append(f"keyframes: object {e.get('ObjectID')} not reproduced\n    premiere {kf[:160]}\n    "
                             f"prproj   {mine[:160]}")
    notes.append(f"keyframes: {nk - badk}/{nk} animations reproduced")
    if TRUNCATED:
        notes.append(f"keyframes: {len(TRUNCATED)} tiny speeds Premiere wrote with a truncated exponent "
                     "(harmless here; see effects.md)")
        TRUNCATED.clear()

    # key times fall inside their clip (source-time mapping incl. speed)
    nkt = badkt = 0
    for s in seqs:
        for t in s['tracks']:
            for it in t['items']:
                if t['type'] != 'VideoClipTrack' or not it.get('chain_id'):
                    continue
                for comp in pp.transforms_of(root, ids, it['chain_id']):
                    for p in pp.param_objects(ids, comp):
                        kf = pp.txt(p, 'Keyframes') if p is not None else None
                        if not kf:
                            continue
                        for k in kf.strip(';').split(';'):
                            nkt += 1
                            tl = it['start_ticks'] + (int(k.split(',')[0]) - it['in_ticks']) / (it['speed'] or 1)
                            # a key may sit up to a few frames outside the trimmed clip; far outside = wrong mapping
                            slack = 10 * (s.get('frame_ticks') or 10594584000)
                            if not (it['start_ticks'] - slack <= tl <= it['end_ticks'] + slack):
                                badkt += 1
    if nkt and badkt > nkt * 0.05:
        fails.append(f"keytimes: {badkt}/{nkt} Transform keys fall well outside their clip; the "
                     "source-time mapping in effects.md may not hold for this version")
    notes.append(f"keytimes: {nkt - badkt}/{nkt} keys inside their clip (±10 frames)")
    return fails, notes


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    any_fail = False
    for path in sys.argv[1:]:
        fails, notes = check(path)
        print(f"== {path}")
        for n in notes:
            print('  ok  ', n)
        for f in fails:
            print('  FAIL', f)
        any_fail |= bool(fails)
    sys.exit(1 if any_fail else 0)


if __name__ == '__main__':
    main()
