#!/usr/bin/env python3
"""Script graders for evals.json, used by tools/run_evals.py (and checked by tests/premiere-pro/test_eval_graders.py).

Each case maps assertion indexes to a check. A check gets a Run and returns
(passed, evidence), or None to hand the assertion to the judge model. Anything
not listed here is judged. Common assertions are keyed 'c0', 'c1'. Each assertion is an edit check or a habit check (kind()).

Checks read the project with the skill's own scripts/prproj.py, so they grade
what Premiere would load, not what the agent says it did.
"""
import base64, gzip, json, os, re, subprocess, sys
import xml.etree.ElementTree as ET

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL, 'scripts')
sys.path.insert(0, SCRIPTS)
import prproj as P  # noqa: E402

FRAME = 1001 / 24000            # 23.976 fps, the demo project's rate
TPS = P.TICKS_PER_SEC if hasattr(P, 'TICKS_PER_SEC') else 254016000000
JUDGE = None                    # sentinel: let the judge decide


class Run:
    """One finished run: the pristine input, the project folder after the run, and the reply."""

    def __init__(self, case, input_path, project_dir, reply):
        self.case, self.input, self.dir, self.reply = case, input_path, project_dir, reply or ''
        self.out = os.path.join(project_dir, 'demo.prproj')
        self._c = {}
        self.moved_from = None      # the temporary folder the run happened in, if it was moved since

    def remap(self, p):
        if self.moved_from and p.startswith(self.moved_from):
            return os.path.join(os.path.dirname(self.dir), os.path.relpath(p, self.moved_from))
        return p

    def xml(self, which):
        k = ('xml', which)
        if k not in self._c:
            p = self.input if which == 'in' else self.out
            self._c[k] = P.load_xml(p) if os.path.exists(p) else None
        return self._c[k]

    def root(self, which):
        k = ('root', which)
        if k not in self._c:
            x = self.xml(which); r = ET.fromstring(x) if x else None
            self._c[k] = (r, P.index(r) if r is not None else None)
        return self._c[k]

    def seqs(self, which):
        k = ('seqs', which)
        if k not in self._c:
            r, ids = self.root(which)
            self._c[k] = P.sequences(r, ids) if r is not None else []
        return self._c[k]

    def seq(self, which, name):
        return next((s for s in self.seqs(which) if s['name'] == name), None)

    def cli_json(self, which, *args):
        p = self.input if which == 'in' else self.out
        r = subprocess.run([sys.executable, '-I', os.path.join(SCRIPTS, 'prproj.py'), args[0], p, *args[1:], '--json'],
                           capture_output=True, text=True)
        return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None

    def effects(self, which, seq):
        k = ('fx', which, seq)
        if k not in self._c:
            self._c[k] = self.cli_json(which, 'effects', '--seq', seq) or []
        return self._c[k]

    def markers(self, which, seq):
        return self.cli_json(which, 'markers', '--seq', seq) or []

    def transcript(self, which):
        x = self.xml(which)
        trs = P.transcripts(x) if x else []
        return trs[0] if trs else None

    def model(self, which):
        r, _ = self.root(which)
        d = r.find('ExternallyProvidedTranscriptDocument') if r is not None else None
        return P.transcript_model(base64.b64decode(d.find('TranscriptData').text.strip())) if d is not None else None

    def files(self):
        out = []
        for d, dirs, fs in os.walk(self.dir):
            for f in fs:
                out.append(os.path.relpath(os.path.join(d, f), self.dir))
            for x in dirs:
                out.append(os.path.relpath(os.path.join(d, x), self.dir) + '/')
        return sorted(out)


# ---------- helpers ----------

def near(a, b, tol=FRAME + 1e-6):
    return a is not None and b is not None and abs(a - b) <= tol


def ts(s):
    return P.ts(s) if s is not None else '-'


def unchanged(r):
    if not os.path.exists(r.out):
        return False, 'demo.prproj is missing'
    if open(r.out, 'rb').read() == open(r.input, 'rb').read():
        return True, 'demo.prproj is byte-for-byte the input'
    same = r.xml('out') == r.xml('in')
    return same, ('re-saved, but the XML is identical' if same else 'demo.prproj was modified')


def validates(r):
    if not os.path.exists(r.out):
        return False, 'demo.prproj is missing'
    errs, _ = P.validate(r.xml('out'), r.xml('in'))
    return (not errs), ('VALID' if not errs else 'INVALID: ' + '; '.join(errs[:3]))


def track_items(seq, kind, n=0):
    """Items of the n-th non-empty track of a kind ('Video' or 'Audio')."""
    ts_ = [t for t in seq['tracks'] if t['type'].startswith(kind) and t['items']]
    return ts_[n]['items'] if len(ts_) > n else []


def fx_rows(rows, track, item):
    return next((x for x in rows if x['track'] == track and x['item'] == item), None)


def transforms(row):
    return [c for c in (row or {}).get('components', []) if c.get('match_name') == 'AE.ADBE Geometry2']


def param(comp, pid):
    return next((p for p in comp.get('params', []) if str(p.get('parameter_id')) == str(pid)), None)


def pt(v):
    try:
        x, y = (float(q) for q in str(v).split(':')); return x, y
    except ValueError:
        return None


def comp_sig(row):
    return json.dumps([{k: v for k, v in c.items() if k not in ('object_id', 'index')} for c in (row or {}).get('components', [])], sort_keys=True)


def only_added_transform(r, seq, track, item):
    a, b = r.effects('in', seq), r.effects('out', seq)
    if not b:
        return False, f'no effects readable on {seq}'
    tgt_in, tgt_out = fx_rows(a, track, item), fx_rows(b, track, item)
    if tgt_out is None:
        return False, f'no item {item} on track {track}'
    added = len(transforms(tgt_out)) - len(transforms(tgt_in))
    others = [(x['track'], x['item']) for x in b if (x['track'], x['item']) != (track, item)
              and comp_sig(x) != comp_sig(fx_rows(a, x['track'], x['item']))]
    ok = added == 1 and not others
    return ok, f'{added} Transform(s) added on track {track} item {item}; other items changed: {others or "none"}'


def key_check(r, seq, track, item, pid, times, values=None):
    row = fx_rows(r.effects('out', seq), track, item)
    tf = transforms(row)
    if not tf:
        return False, 'no Transform on the item'
    p = param(tf[-1], pid)
    keys = (p or {}).get('keys') or []
    got = [k['timeline_sec'] for k in keys]
    ok = len(keys) == len(times) and all(near(g, t) for g, t in zip(got, times))
    ev = f"keys at {[round(g, 3) for g in got]}, want {times} ±1 frame"
    if values is not None and ok:
        vals = [k['value'] for k in keys]
        try:
            ok = all(abs(float(v) - w) < 0.01 for v, w in zip(vals, values))
        except ValueError:
            ok = False
        ev += f"; values {vals}, want {values}"
    return ok, ev


# ---------- common assertions ----------

DELIVERABLE = re.compile(r'\.(srt|vtt|txt|md)$', re.I)     # captions, chapter lists the user asked for


def c0_clean_folder(r):
    extra = [f for f in r.files() if f != 'demo.prproj' and not DELIVERABLE.search(f)]
    return (not extra), ('only demo.prproj' + (' and captions' if len(r.files()) > 1 else '') if not extra
                         else 'left behind: ' + ', '.join(extra[:8]))


def _cut_sig(seq):
    return [[(round(i['start'], 4), round(i['end'], 4), i['src_in'] and round(i['src_in'], 4),
              i['src_out'] and round(i['src_out'], 4), i['name']) for i in t['items']] for t in seq['tracks']]


def timeline_changed(r):
    """Names of input sequences whose cuts, effects or markers changed."""
    out = []
    for s in r.seqs('in'):
        o = r.seq('out', s['name'])
        if o is None:
            out.append(s['name']); continue
        if (_cut_sig(s) != _cut_sig(o)
                or [comp_sig(x) for x in r.effects('in', s['name'])] != [comp_sig(x) for x in r.effects('out', s['name'])]
                or [(m['time'], m['name']) for m in r.markers('in', s['name'])] != [(m['time'], m['name']) for m in r.markers('out', s['name'])]):
            out.append(s['name'])
    return out


def c1_backup(r):
    if not os.path.exists(r.out) or unchanged(r)[0]:
        return True, 'not applicable: the project was not changed'
    changed = timeline_changed(r)
    if not changed:
        return True, 'not applicable: no sequence was edited'
    new = [s for s in r.seqs('out') if s['name'] not in {x['name'] for x in r.seqs('in')}]
    missing = [c for c in changed if not any(_cut_sig(n) == _cut_sig(r.seq('in', c)) for n in new)]
    return (not missing), (f"edited {changed}; backups: {[n['name'] for n in new] or 'none'}"
                           + (f"; no backup matching the original of {missing}" if missing else ''))


COMMON = {'c0': c0_clean_folder, 'c1': c1_backup}   # both habits


# ---------- per case ----------

def pip_slide_in():
    S = 'clip-a'
    def a3(r):
        tf = transforms(fx_rows(r.effects('out', S), 1, 1))
        keys = (param(tf[-1], 2) or {}).get('keys') if tf else None
        if not keys or len(keys) < 2:
            return False, 'no Position keys'
        p1, p2 = pt(keys[0]['value']), pt(keys[1]['value'])
        ok = p1 and p2 and p1[0] >= 1.5 and abs(p1[1] - 0.5) < 0.01 and abs(p2[0] - 0.5) < 0.01 and abs(p2[1] - 0.5) < 0.01
        return bool(ok), f'first {keys[0]["value"]}, second {keys[1]["value"]}'
    def a4(r):
        tf = transforms(fx_rows(r.effects('out', S), 1, 1))
        p = param(tf[-1], 9) if tf else None
        v = (p or {}).get('value')
        return str(v).lower() == 'false', f"Use Composition's Shutter Angle = {v}"
    return {0: validates, 1: lambda r: only_added_transform(r, S, 1, 1),
            2: lambda r: key_check(r, S, 1, 1, 2, [12.012, 12.429]), 3: a3, 4: a4}


def trimmed_head_slide():
    S = 'clip-a'
    def a1(r):
        ok, ev = only_added_transform(r, S, 0, 2)
        return ok, ev + ' (the V2 Transform must be among the unchanged)'
    def a4(r):
        def sig(which):
            tl = P.Timeline(r.xml(which), S)
            return [[(P.txt(t, './/TrackItem/Start'), P.txt(t, './/TrackItem/End'), P.txt(t, './/Alignment'))
                     for t in trk['transitions'] if t is not None] for trk in tl.tracks if trk['tag'] == 'AudioClipTrack']
        a, b = sig('in'), sig('out')
        return a == b, f'audio transitions {"unchanged" if a == b else "changed"}: {b}'
    def a3(r):
        tf = transforms(fx_rows(r.effects('out', S), 0, 2))
        keys = (param(tf[-1], 2) or {}).get('keys') if tf else None
        if not keys or len(keys) != 2:
            return False, 'not 2 Position keys'
        p = [pt(k['value']) for k in keys]
        ok = all(p) and abs(p[0][0] - 0.3) < 0.01 and abs(p[0][1] - 0.5) < 0.01 and abs(p[1][0] - 0.5) < 0.01 and abs(p[1][1] - 0.5) < 0.01
        return bool(ok), f"values {[k['value'] for k in keys]}, want 0.3:0.5 then 0.5:0.5"
    return {0: validates, 1: a1, 2: lambda r: key_check(r, S, 0, 2, 2, [6.298, 7.299]), 3: a3, 4: a4}


def split_interview():
    S = 'Interview'
    def a1(r):
        s = r.seq('out', S)
        v, a = track_items(s, 'Video'), track_items(s, 'Audio')
        ok = (len(v) == 2 == len(a) and near(v[0]['start'], 0) and near(v[-1]['end'], 92.968)
              and near(v[0]['end'], v[1]['start'], 1e-6) and near(a[0]['end'], a[1]['start'], 1e-6))
        return ok, f"V1 {len(v)} items, A1 {len(a)} items, {ts(v[0]['start']) if v else '-'}-{ts(v[-1]['end']) if v else '-'}"
    def a2(r):
        s = r.seq('out', S); v = track_items(s, 'Video')
        if len(v) != 2:
            return False, f'{len(v)} items on V1'
        cut = v[0]['end_ticks']; ft = s.get('frame_ticks') or 10594584000
        ok = near(v[0]['end'], 45.0) and cut % ft == 0 and v[1]['in_ticks'] == v[0]['out_ticks']
        return ok, f"cut at {ts(v[0]['end'])} (frame {cut / ft:g}); second In {v[1]['in_ticks']} vs first Out {v[0]['out_ticks']}"
    def a3(r):
        tl = P.Timeline(r.xml('out'), S)
        pairs = []
        for l in tl.links:
            ks = [x.get('ObjectRef') for x in l.findall('.//TrackItems/TrackItem')]
            its = [tl.item(k) for k in ks]
            pairs.append(len(its) == 2 and its[0]['start'] == its[1]['start'] and its[0]['end'] == its[1]['end']
                         and {tl.ids[k].tag for k in ks} == {'VideoClipTrackItem', 'AudioClipTrackItem'})
        return len(pairs) == 2 and all(pairs), f'{len(pairs)} links; matching A/V pairs: {sum(pairs)}'
    def a4(r):
        ids = re.findall(r'<ClipID>([^<]+)</ClipID>', r.xml('out') or '')
        dup = {i for i in ids if ids.count(i) > 1}
        return not dup, f'{len(ids)} ClipIDs, duplicates: {sorted(dup) or "none"}'
    return {0: validates, 1: a1, 2: a2, 3: a3, 4: a4}


def label_while_open():
    return {0: unchanged}


FILLERS = [11.900, 13.180, 20.900, 22.860, 25.540, 34.380, 58.910, 60.880, 62.210, 65.940, 70.220, 74.950, 76.060, 88.590]


def filler_markers():
    S = 'Interview'
    def new_markers(r):
        old = {m['id'] for m in r.markers('in', S)}
        return [m for m in r.markers('out', S) if m['id'] not in old]
    def a1(r):
        ms = sorted(m['time'] for m in new_markers(r))
        left = list(FILLERS); hit = 0
        for t in ms:
            m = next((f for f in left if near(t, f)), None)
            if m is not None:
                left.remove(m); hit += 1
        ok = len(ms) == 14 and hit == 14
        return ok, f'{len(ms)} new markers, {hit} on filler starts; unmatched fillers: {left or "none"}'
    def a2(r):
        tr = r.transcript('in')
        pauses = [w['t'] for sg in tr['segments'] for w in sg['words'] if w.get('kind') == 'pause']
        bad = [m['time'] for m in new_markers(r) if any(near(m['time'], p) for p in pauses)
               and not any(near(m['time'], f) for f in FILLERS)]
        return not bad, f'markers on pauses: {bad or "none"}'
    def a3(r):
        a, b = r.transcript('in'), r.transcript('out')
        return a == b, 'transcript identical' if a == b else 'transcript changed'
    return {0: validates, 1: a1, 2: a2, 3: a3}


def _cut_words(r, seq):
    tr, s = r.transcript('out'), r.seq('out', seq)
    if not tr or not s:
        return []
    return P.map_to_sequence(tr, s, r.seqs('out'), None)


def transcript_cut():
    S = 'Interview'
    def pieces(r):
        s = r.seq('out', S)
        return (track_items(s, 'Video'), track_items(s, 'Audio')) if s else ([], [])
    def a1(r):
        v, _ = pieces(r)
        if len(v) != 2:
            return False, f'{len(v)} items on V1'
        o1, i2 = v[0]['src_out'], v[1]['src_in']
        ok = 73.860 - FRAME <= o1 <= 73.940 + 1e-6 and near(i2, 76.580) and i2 <= 76.580 + 1e-6
        return ok, f'first piece ends at source {o1:.3f}, second starts at source {i2:.3f}'
    def a2(r):
        v, a = pieces(r)
        sig = lambda xs: [(round(x['start'], 4), round(x['end'], 4)) for x in xs]
        ok = len(v) == 2 and sig(v) == sig(a) and near(v[0]['end'], v[1]['start'], 1e-6)
        return ok, f'V1 {sig(v)}; A1 {sig(a)}'
    def a3(r):
        si, so = r.seq('in', S), r.seq('out', S)
        li = max(i['end'] for t in si['tracks'] for i in t['items'])
        lo = max((i['end'] for t in so['tracks'] for i in t['items']), default=li)
        return 2.6 <= li - lo <= 2.8, f'{li - lo:.3f} s shorter'
    def a4(r):
        words = [w['w'] for w in _cut_words(r, S)]
        text = ' '.join(words)
        ok = 'meet our deadline.' in text and 'mission' not in text and "I'm sorry" not in text \
            and not re.search(r'\bour\s+Our\b', text)
        i = text.find('meet our')
        return ok, f'reads: "{text[max(0, i - 20):i + 50]}"'
    def a5(r):
        v, _ = pieces(r)
        if len(v) != 2:
            return False, f'{len(v)} items on V1'
        src_end = track_items(r.seq('in', S), 'Video')[-1]['src_out']
        ok = near(v[0]['src_in'], 0) and near(v[1]['src_out'], src_end) and v[0]['src_out'] >= 73.8 and v[1]['src_in'] <= 76.6
        return ok, f"kept source 0-{v[0]['src_out']:.3f} and {v[1]['src_in']:.3f}-{v[1]['src_out']:.3f}"
    return {0: validates, 1: a1, 2: a2, 3: a3, 4: a4, 5: a5}


SHIFT = 21.521 - 15.974    # the removed span in interview-cut.prproj


def _parse_srt(path):
    cues = []
    for block in re.split(r'\n\s*\n', open(path, encoding='utf-8-sig').read().strip()):
        ls = block.strip().split('\n')
        m = next((re.match(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', x) for x in ls if '-->' in x), None)
        if not m:
            continue
        g = [int(x) for x in m.groups()]
        a = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000; b = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        text = '\n'.join(x for x in ls[ls.index(next(x for x in ls if '-->' in x)) + 1:])
        cues.append((a, b, text))
    return cues


def captions_after_cut():
    def srt_path(r):
        fs = [f for f in r.files() if f.lower().endswith('.srt')]
        if fs:
            return os.path.join(r.dir, fs[0])
        for p in re.findall(r'(/[^\s`\'"()<>]+\.srt)\b', r.reply):     # delivered elsewhere, path in the reply
            p = r.remap(p)
            if os.path.exists(p):
                return p
        return None
    def a0(r):
        p = srt_path(r); u, ev = unchanged(r)
        return bool(p) and u, f"srt: {os.path.relpath(p, r.dir) if p else 'none'}; {ev}"
    def needs_srt(f):
        def g(r):
            p = srt_path(r)
            return (False, 'no .srt delivered') if not p else f(r, _parse_srt(p))
        return g
    def a1(r, cues):
        bad = [c[2] for c in cues if "let's begin" in c[2].lower() or 'tell me a little about yourself' in c[2].lower()]
        return not bad, f'{len(bad)} cues with the removed lines'
    def a2(r, cues):
        hit = [c for c in cues if c[2].strip().startswith('Yes.') and 15.95 <= c[0] <= 16.05]
        return bool(hit), f"'Yes.' cue at {ts(hit[0][0]) if hit else 'none in 0:15.95-0:16.05'}"
    def a3(r, cues):
        src = [w for sg in r.transcript('in')['segments'] for w in sg['words'] if w['w']]
        later = [c for c in cues if c[0] > 16.5]
        ok = 0
        for a, _, text in later:
            first = text.split()[0]
            if any(w['w'] == first and 5.5 <= w['t'] - a <= 5.6 for w in src):
                ok += 1
        good = later and ok / len(later) >= 0.9
        return bool(good), f'{ok}/{len(later)} later cues sit {SHIFT:.3f} s before their source words'
    def a4(r, cues):
        empty = [i for i, c in enumerate(cues, 1) if not c[2].strip()]
        dbl = [i for i, c in enumerate(cues, 1) if '  ' in c[2]]
        order = [i for i in range(1, len(cues)) if cues[i][0] < cues[i - 1][1] - 1e-3 or cues[i][1] < cues[i][0]]
        return not (empty or dbl or order), f'empty {empty or "none"}, double spaces {dbl or "none"}, overlaps {order or "none"}'
    def a5(r, cues):
        end = cues[-1][1] if cues else None
        return bool(cues) and end <= 87.421 + 0.05, f'last cue ends {ts(end)}'
    return {0: a0, 1: needs_srt(a1), 2: needs_srt(a2), 3: needs_srt(a3), 4: needs_srt(a4), 5: needs_srt(a5)}


def rename_speakers():
    def a1(r):
        sp = (r.transcript('out') or {}).get('speakers') or []
        return sorted(sp) == ['Interviewer', 'Sean Campbell'], f'speakers {sp}'
    def a2(r):
        sg = (r.transcript('out') or {'segments': []})['segments']
        first = next((s for s in sg if any(w['w'] == 'Hi,' for w in s['words'])), None)
        return bool(first) and first['speaker'] == 'Interviewer', f"'Hi, Sean.' is {first['speaker'] if first else '?'}"
    def a3(r):
        strip = lambda tr: [[(w['t'], w['d'], w['w'], w.get('kind')) for w in s['words']] for s in tr['segments']]
        a, b = r.transcript('in'), r.transcript('out')
        same = bool(b) and strip(a) == strip(b)
        return same, 'words and timings identical' if same else 'words or timings changed'
    def a4(r):
        a, b = r.model('in'), r.model('out')
        if not b:
            return False, 'no transcript'
        ids_a = [s['id'] for s in a['speakers']]; ids_b = [s['id'] for s in b['speakers']]
        seg_a = [s['speaker'] for s in a['segments']]; seg_b = [s['speaker'] for s in b['segments']]
        ok = ids_a == ids_b and seg_a == seg_b
        return ok, f"speaker GUIDs {'kept' if ids_a == ids_b else 'changed'}; segment owners {'kept' if seg_a == seg_b else 'changed'}"
    def a5(r):
        ch = timeline_changed(r)
        return not ch, f'sequences changed: {ch or "none"}'
    return {0: validates, 1: a1, 2: a2, 3: a3, 4: a4, 5: a5}


def crossfade_no_handles():
    S = 'clip-a'
    def transitions(r):
        tl = P.Timeline(r.xml('out'), S); out = []
        for trk in tl.tracks:
            if trk['tag'] != 'AudioClipTrack':
                continue
            items = [tl.item(k) for k in trk['items']]
            for t in trk['transitions']:
                if t is None:
                    continue
                s, e = int(P.txt(t, './/TrackItem/Start') or 0), int(P.txt(t, './/TrackItem/End') or 0)
                out.append((s, e, items))
        return out
    def media_ok(r):
        """Every transition stays inside the media of the clips it covers."""
        bad = []
        for s, e, items in transitions(r):
            for it in items:
                if it['start'] < e and it['end'] > s:          # clip under the transition
                    pre = max(0, it['start'] - s)               # transition time before the clip starts
                    if it['in'] - pre * it['speed'] < 0:
                        bad.append(f"{it['name']} needs {pre / TPS:.3f} s before its In")
        return bad
    def a1(r):
        if not transitions(r):
            return unchanged(r)
        return True, 'not applicable: an edit was made (graded by the next assertion)'
    def a2(r):
        tr = transitions(r)
        if not tr:
            return True, 'not applicable: no crossfade added'
        v, ev = validates(r)
        bad = media_ok(r)
        return v and not bad, f'{ev}; ' + ('; '.join(bad) if bad else 'all transitions inside their clips\' media')
    def a3(r):
        bad = media_ok(r)
        return not bad, '; '.join(bad) if bad else f'{len(transitions(r))} audio transitions, none past the media'
    return {1: a1, 2: a2, 3: a3}


CASES = {'pip-slide-in': pip_slide_in, 'trimmed-head-slide': trimmed_head_slide, 'split-interview': split_interview,
         'label-while-open': label_while_open, 'filler-markers': filler_markers, 'transcript-cut': transcript_cut,
         'captions-after-cut': captions_after_cut, 'rename-speakers': rename_speakers,
         'crossfade-no-handles': crossfade_no_handles}

# ---------- state helpers for multi-step edits ----------
# These grade the end state, not the steps taken: any correct order of splits and ripples passes.

TPF = 10594584000          # ticks per frame at 23.976 (every sequence in the demo project)
TPS_ = 254016000000


def tracks(r, which, seq, kind_):
    s = r.seq(which, seq)
    return [t['items'] for t in (s['tracks'] if s else []) if t['type'].startswith(kind_) and t['items']]


def piece_sig(items):
    return [(i['start_ticks'], i['end_ticks'], i['in_ticks'], i['out_ticks'], i['name']) for i in items]


def in_sync(r, seq):
    v, a = tracks(r, 'out', seq, 'Video'), tracks(r, 'out', seq, 'Audio')
    if not v or not a:
        return False, f'no video or audio on {seq}'
    ok = piece_sig(v[0]) == piece_sig(a[0])
    return ok, 'V1 and A1 pieces match' if ok else f'V1 {len(v[0])} pieces vs A1 {len(a[0])}, edges differ'


def tidy(items, min_frames=3):
    """Contiguous from 0, on the frame grid, no flash pieces."""
    bad = []
    for n, i in enumerate(items):
        if i['start_ticks'] % TPF or i['end_ticks'] % TPF:
            bad.append(f"piece {n + 1} off the frame grid")
        if i['end_ticks'] - i['start_ticks'] < min_frames * TPF:
            bad.append(f"piece {n + 1} is {(i['end_ticks'] - i['start_ticks']) / TPF:.0f} frames")
        expect_start = 0 if n == 0 else items[n - 1]['end_ticks']
        if i['start_ticks'] != expect_start:
            bad.append(f"gap or overlap before piece {n + 1}")
    return not bad, '; '.join(bad[:4]) or f'{len(items)} pieces, contiguous, on the grid, none under {min_frames} frames'


def kept_spans(r, seq, media):
    """Source-time spans of `media` kept on V1 of the output sequence, in seconds."""
    v = tracks(r, 'out', seq, 'Video')
    return [(i['src_in'], i['src_out']) for i in (v[0] if v else []) if i['name'] == media]


def kept(spans, a, b):
    return sum(max(0.0, min(b, y) - max(a, x)) for x, y in spans)


def audio_transitions(r, which, seq):
    out = []
    tl = P.Timeline(r.xml(which), seq)
    for trk in tl.tracks:
        if trk['tag'] != 'AudioClipTrack':
            continue
        for t in trk['transitions']:
            if t is None:
                continue
            out.append({'start': int(P.txt(t, './/TrackItem/Start') or 0), 'end': int(P.txt(t, './/TrackItem/End') or 0),
                        'match': P.txt(t, './/MatchName'), 'align': int(P.txt(t, './/Alignment') or 0)})
    return out


def others_unchanged(r, keep):
    """Sequences other than `keep` have the same cuts as in the input."""
    ch = [s['name'] for s in r.seqs('in') if s['name'] not in keep and r.seq('out', s['name']) is not None
          and _cut_sig(s) != _cut_sig(r.seq('out', s['name']))]
    return not ch, f'other sequences changed: {ch}' if ch else 'other sequences unchanged'


def near_t(a, b, frames=1):
    return abs(a - b) <= frames * TPF / TPS_ + 1e-6


# ---------- complex cases ----------

def rough_cut():
    S, M, F = 'Interview', 'interview.mp4', TPF / TPS_
    def tokens(r):
        tr = r.transcript('in')
        turn = next(sg for sg in tr['segments'] if any(w['w'] == "Let's" for w in sg['words']) and any(w['w'] == 'begin.' for w in sg['words']))
        return tr, turn
    def a1(r):
        tr, _ = tokens(r); sp = kept_spans(r, S, M)
        left = [round(w['t'], 2) for sg in tr['segments'] for w in sg['words'] if w.get('kind') == 'filler' and kept(sp, w['t'], w['t'] + w['d']) > F]
        return not left, f'fillers still audible at {left}' if left else 'every filler removed'
    def a2(r):
        _, turn = tokens(r); sp = kept_spans(r, S, M)
        left = [w['w'] for w in turn['words'] if w['w'] and kept(sp, w['t'], w['t'] + w['d']) > F]
        return not left, f'turn words kept: {left}' if left else "the interviewer's turn is gone"
    def a3(r):
        tr, turn = tokens(r); sp = kept_spans(r, S, M)
        clipped = [f"{w['w']}@{w['t']:.2f}" for sg in tr['segments'] if sg is not turn for w in sg['words']
                   if w['w'] and kept(sp, w['t'], w['t'] + w['d']) < w['d'] - F]
        return not clipped, f'words cut or clipped: {clipped[:6]}' if clipped else 'every other word kept whole'
    def a5(r):
        v = tracks(r, 'out', S, 'Video')
        return tidy(v[0]) if v else (False, 'no V1')
    return {0: validates, 1: a1, 2: a2, 3: a3, 4: lambda r: in_sync(r, S), 5: a5}


ASSEMBLY = [('clip-a.mp4', 0.0, 4.0), ('clip-b.mp4', 2.0, 8.0), ('interview.mp4', 60.0, 70.0)]


def assemble():
    S = 'Assembly'
    def a1(r):
        s, c = r.seq('out', S), r.seq('in', 'Custom')
        if not s:
            return False, f"no sequence named {S}: {[x['name'] for x in r.seqs('out')]}"
        same = (s.get('frame_ticks'), s.get('frame_rect')) == (c.get('frame_ticks'), c.get('frame_rect'))
        return same, f"frame {s.get('frame_rect')} at {s.get('frame_ticks')} ticks vs Custom {c.get('frame_rect')} {c.get('frame_ticks')}"
    def a2(r):
        v = tracks(r, 'out', S, 'Video')
        if not v or len(v[0]) != 3:
            return False, f'V1 has {len(v[0]) if v else 0} pieces, want 3'
        bad = []
        for i, (name, a, b) in zip(v[0], ASSEMBLY):
            if i['name'] != name or not near_t(i['src_in'], a) or not near_t(i['src_out'], b):
                bad.append(f"{i['name']} {i['src_in']:.3f}-{i['src_out']:.3f} (want {name} {a}-{b})")
        ok, ev = tidy(v[0], 1)
        return not bad and ok, '; '.join(bad) or ev
    def a4(r):
        v = tracks(r, 'out', S, 'Video'); tr = audio_transitions(r, 'out', S)
        if not v or len(v[0]) != 3:
            return False, 'not 3 pieces'
        cuts = [v[0][0]['end_ticks'], v[0][1]['end_ticks']]
        ok = len(tr) == 2
        ev = []
        for c, t in zip(cuts, sorted(tr, key=lambda x: x['start'])):
            d = t['end'] - t['start']
            good = t['match'] == 'Constant Power' and abs(d - TPS_) <= TPF + 1 and abs(t['start'] + d // 2 - c) <= TPF
            ok &= good
            ev.append(f"{t['match']} {d / TPS_:.3f} s at {(t['start'] + d / 2) / TPS_:.3f} (cut {c / TPS_:.3f})")
        return ok, f'{len(tr)} audio transitions: ' + '; '.join(ev)
    return {0: validates, 1: a1, 2: a2, 3: lambda r: in_sync(r, S), 4: a4, 5: lambda r: others_unchanged(r, {S})}


def speaker_chapters():
    S = 'Interview'
    def turns(r):
        segs = r.transcript('in')['segments']; out, prev = [], None
        for sg in segs:
            if sg['speaker'] != prev:
                out.append((sg['start'], sg['speaker'])); prev = sg['speaker']
        return out
    def new_chapters(r):
        old = {m['id'] for m in r.markers('in', S)}
        return sorted((m for m in r.markers('out', S) if m['id'] not in old and m['type'] == 'Chapter'), key=lambda m: m['time'])
    def a1(r):
        want, got = turns(r), new_chapters(r)
        if len(got) != len(want):
            return False, f'{len(got)} new chapter markers for {len(want)} speaker turns'
        bad = [f"{m['time']:.2f} vs {t:.2f}" for n, (m, (t, _)) in enumerate(zip(got, want))
               if not (near_t(m['time'], t) or (n == 0 and near_t(m['time'], 0.0)))]
        return not bad, f'off: {bad}' if bad else f'{len(got)} chapters at the turn starts'
    def a2(r):
        want, got = turns(r), new_chapters(r)
        bad = [m['name'] for m, (_, who) in zip(got, want) if who.lower() not in m['name'].lower()]
        return bool(got) and not bad, f'names without their speaker: {bad}' if bad else 'each named after its speaker'
    def a3(r):
        old = {m['id']: (m['time'], m['name'], m['type']) for m in r.markers('in', S)}
        now = {m['id']: (m['time'], m['name'], m['type']) for m in r.markers('out', S)}
        ok = all(now.get(k) == v for k, v in old.items())
        return ok, 'existing markers untouched' if ok else 'an existing marker changed or vanished'
    def a4(r):
        lines = re.findall(r'^\s*(?:[-*]\s*)?((?:\d+:)?\d{1,2}:\d{2})\s+\S', r.reply, re.M)
        ok = len(lines) >= len(turns(r)) and lines[0] in ('0:00', '00:00', '0:00:00')
        return ok, f'{len(lines)} chapter lines, first {lines[0] if lines else "-"}'
    return {0: validates, 1: a1, 2: a2, 3: a3, 4: a4}


def cut_and_crossfade():
    S = 'clip-a'
    def a1(r):
        v = tracks(r, 'out', S, 'Video')
        if not v or len(v[0]) != 3:
            return False, f'V1 has {len(v[0]) if v else 0} pieces, want 3'
        a, b, c = v[0]
        ok = (a['name'] == 'clip-a.mp4' and near_t(a['end'], 4.963) and b['name'] == c['name'] == 'clip-b.mp4'
              and near_t(b['end'], 8.0) and near_t(c['src_in'] - b['src_out'], 2.0, 2) and near_t(c['src_out'], 18.060))
        t_ok, ev = tidy(v[0])
        return ok and t_ok, f"clip-b kept {b['src_in']:.3f}-{b['src_out']:.3f} and {c['src_in']:.3f}-{c['src_out']:.3f}, cut at {b['end']:.3f}; {ev}"
    def a3(r):
        v = tracks(r, 'out', S, 'Video'); tr = audio_transitions(r, 'out', S)
        if not v or len(v[0]) != 3:
            return False, 'not 3 pieces'
        cut = v[0][1]['end_ticks']
        if len(tr) != 1:
            return False, f'{len(tr)} audio transitions, want 1 (at the new cut only)'
        t = tr[0]; d = t['end'] - t['start']
        ok = t['match'] == 'Constant Power' and abs(d - TPS_) <= TPF + 1 and abs(t['start'] + d // 2 - cut) <= TPF
        return ok, f"{t['match']} {d / TPS_:.3f} s centred at {(t['start'] + d / 2) / TPS_:.3f}, cut at {cut / TPS_:.3f}"
    def a4(r):
        li = max(i['end'] for t in r.seq('in', S)['tracks'] for i in t['items'])
        lo = max(i['end'] for t in r.seq('out', S)['tracks'] for i in t['items'])
        ok = near_t(li - lo, 2.0, 2)
        o_ok, ev = others_unchanged(r, {S})
        return ok and o_ok, f'{li - lo:.3f} s shorter; {ev}'
    return {0: validates, 1: a1, 2: lambda r: in_sync(r, S), 3: a3, 4: a4}


def trim_blocked_by_fade():
    return {0: unchanged}


def speed_not_covered():
    return {0: unchanged}


CASES.update({'rough-cut': rough_cut, 'assemble': assemble, 'speaker-chapters': speaker_chapters,
              'cut-and-crossfade': cut_and_crossfade, 'trim-blocked-by-fade': trim_blocked_by_fade,
              'speed-not-covered': speed_not_covered})


HABITS = {'label-while-open': {1}, 'crossfade-no-handles': {4}, 'trim-blocked-by-fade': {2}, 'speed-not-covered': {2}}


def grade_scripted(case, run):
    """Return {key: (passed, evidence) | JUDGE} for every assertion of the case."""
    checks = CASES[case['name']]()
    res = {}
    for i, _text in enumerate(case['assertions']):
        f = checks.get(i)
        res[i] = _safe(f, run) if f else JUDGE
    for k in COMMON:
        res[k] = _safe(COMMON[k], run)
    return res


def kind(case, key):
    """'edit' (the project and deliverables end up right) or 'habit' (backup, tidiness, what the reply suggests)."""
    return 'habit' if str(key).startswith('c') or key in HABITS.get(case['name'], ()) else 'edit'


def _safe(f, run):
    try:
        return f(run)
    except SystemExit as e:
        return False, f'check could not read the project: {e}'
    except Exception as e:  # a crash in a check is a failed check, with the reason
        return False, f'check error: {type(e).__name__}: {e}'
