#!/usr/bin/env python3
"""prproj.py - read/inspect/edit Adobe Premiere Pro .prproj files (stdlib only).

Usage:
  prproj.py unpack  FILE.prproj OUT.xml
  prproj.py pack    IN.xml OUT.prproj
  prproj.py summary FILE.prproj|.xml
  prproj.py cuts    FILE [--seq NAME] [--json]
  prproj.py transcript FILE [--json] [--index N]     (--index -1 lists transcripts)
  prproj.py cut-transcript FILE --seq NAME [--index N] [--srt | --json]
        Words that survive in SEQ's edit, timed on SEQ's timeline (nested
        sequences resolved; auto-picks the transcript that maps the most words).
  prproj.py srt-from-words WORDS.json            (list of {t,d,w}; e.g. corrected
        output of cut-transcript --json) -> SRT on stdout, caption cue rules below
  prproj.py set-label FILE OUT.prproj --seq NAME [--track N] (--item N[,N] | --at SEC[,SEC]) --label Rose
        With --track, only that track's item and its linked partner are labelled.
        OUT may equal FILE (the source is fully read first).
  prproj.py validate FILE [--orig ORIGINAL]      exit 1 on errors, 0 otherwise
  prproj.py backup-seq FILE OUT --seq NAME [--name COPY]
        Duplicate a sequence (all tracks, items, effects, links) inside the project,
        in the same bin; default name "NAME (backup YYYY-MM-DD HHMM)".
  prproj.py split FILE OUT --seq NAME --at TIME [--track N]
        Razor at TIME on every unlocked track, or on track N and its linked partners.
  prproj.py trim FILE OUT --seq NAME --track N --item N [--start TIME] [--end TIME]
        Move a clip's (and its linked partners') edges; neighbours stay put.
  prproj.py delete FILE OUT --seq NAME --track N --item N [--ripple] [--force]
        Remove a clip and its linked partners; --ripple closes the gap on every track.
        TIME is seconds (4.5), frames (119f) or timecode (00:00:04:23), snapped to a frame.
  prproj.py place FILE OUT --seq NAME --clip NAME --at TIME [--track N] [--audio-track N]
        [--in TIME] [--out TIME | --duration TIME] [--video-only | --audio-only]
        Put a media clip from the bins on free space in the timeline (linked A/V).
  prproj.py fade-in|fade-out FILE OUT --seq NAME --track N --item N --duration TIME
        Fade an audio clip in from its first frame, or out to its last.
  prproj.py crossfade FILE OUT --seq NAME --track N --item N [--duration TIME]
        Constant Power crossfade centred on the cut after item N (default 2 s); both
        clips need half the duration of unused media (handles) beyond the cut.
  prproj.py compare-transcript FILE --ref REFERENCE.srt [--index N] [--ignore-fillers] [--json]
        [--seq NAME --markers OUT]
        Line Premiere's Speech-to-Text words up against another transcript (SRT, VTT
        or a words JSON such as Whisper's) and list every difference with its time;
        --markers also writes OUT with a sequence marker at each difference.
  prproj.py speakers FILE [--index N] [--json]
        Who speaks when, from the Speech-to-Text transcript (one line per turn).
  prproj.py rename-speaker FILE OUT --from NAME --to NAME [--index N]
  prproj.py set-speaker FILE OUT --at SECONDS --speaker NAME [--index N]
        Give the turn at SECONDS (media time of the transcribed clip) to an existing speaker.
  prproj.py markers FILE --seq NAME [--json | --chapters]
        Sequence markers in time order; --chapters prints YouTube chapter lines.
  prproj.py add-marker FILE OUT --seq NAME --at TIME --name NAME [--type Comment|Chapter]
        [--comment TEXT] [--colour orange|pink|#RRGGBB]
  prproj.py set-track FILE OUT --seq NAME --track N [--name NAME] [--lock on|off] [--mute on|off]
        --name '' restores the default name. --mute is for audio tracks.
  prproj.py diff OLD NEW [--json] [--all]
        What changed between two saves of a project. Objects are matched by their place
        in the graph (ObjectIDs are renumbered on save); view state is hidden unless --all.
  prproj.py effects FILE --seq NAME [--track N] [--item N] [--json]
        Effect stack of each item; keyframes shown at timeline times.
  prproj.py add-transform FILE OUT --seq NAME --track N --item N [--first]
        [--set PARAM=VALUE ...] [--motion-blur on|off] [--keys PARAM SPEC ...]
  prproj.py set-transform FILE OUT --seq NAME --track N --item N [--transform K]
        [--set PARAM=VALUE ...] [--motion-blur on|off] [--keys PARAM SPEC ...] [--clear PARAM]
        PARAMs: anchor position uniform scale scale-width skew skew-axis rotation
        opacity use-comp-shutter shutter-angle sampling. Points are x:y fractions of
        the frame (0.5:0.5 = centre). SPEC = "SEC=VALUE[@ease|@ease:NN|@linear], ..." with SEC
        from the item's start (or the sequence's with --time-base sequence); "12f"
        = frames; with item times, negative counts back from the last frame ("-1f").
        e.g. --keys position "0=1.55:0.5@linear, 0.5=0.5:0.5"
        Track/item numbers are the ones cuts prints.

Write commands (set-label, add-transform, set-transform, backup-seq) accept --dry-run.
add-transform refuses an item that already has a Transform unless --force.
Exit status: 0 ok; 1 error (message on stderr says what and why; validate: invalid);
2 bad arguments.

Cue rules (srt, srt-from-words): break at sentence ends and pauses > 0.8s;
<= 84 chars and <= 6.5s per cue; wrapped to <= 2 lines of <= 42 chars.
Data goes to stdout, diagnostics to stderr.
"""
import sys, os, gzip, json, re, base64, struct, argparse, math, uuid, datetime
import xml.etree.ElementTree as ET

TICKS = 254016000000  # Premiere ticks per second


def load_xml(path):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return raw.decode('utf-8')


def index(root):
    # Only top-level children of <PremiereData> are global objects.
    # Nested elements (e.g. inside ProjectViewState) reuse ObjectIDs in a local scope.
    ids = {}
    for e in root:
        k = e.get('ObjectID') or e.get('ObjectUID')
        if k:
            ids[k] = e
    return ids


def deref(ids, el):
    if el is None:
        return None
    return ids.get(el.get('ObjectRef') or el.get('ObjectURef'))


def txt(e, path):
    x = e.find(path) if e is not None else None
    return x.text if x is not None else None


def ts(sec):
    sign = '-' if sec < 0 else ''; sec = abs(sec)
    m, s = divmod(sec, 60)
    h, m = divmod(int(m), 60)
    return sign + (f"{h}:{m:02d}:{s:06.3f}" if h else f"{m}:{s:06.3f}")


def fps_from_ticks(t):
    return round(TICKS / int(t), 3)


# ---------- labels ----------
# Premiere's 16 default label slots (Preferences > Labels). The INDEX in
# asl.clip.label.name ("BE.Prefs.LabelColors.N") is what Premiere uses; when the user
# changes a label in the UI, Premiere rewrites only the name and leaves the
# asl.clip.label.color integer stale. So set the name; leave the color int alone.
LABELS = ['Violet', 'Iris', 'Caribbean', 'Lavender', 'Cerulean', 'Forest', 'Rose', 'Mango',
          'Purple', 'Blue', 'Teal', 'Magenta', 'Tan', 'Green', 'Brown', 'Yellow']


def label_of(clip):
    n = txt(clip, './/asl.clip.label.name') if clip is not None else None
    m = re.search(r'LabelColors\.(\d+)$', n or '')
    return LABELS[int(m.group(1))] if m and int(m.group(1)) < len(LABELS) else None


def label_index(name):
    if str(name).isdigit():
        return int(name)
    low = [l.lower() for l in LABELS]
    if name.lower() not in low:
        raise SystemExit(f"unknown label '{name}'. Options: {', '.join(LABELS)}")
    return low.index(name.lower())


def set_label_text(xml, object_ids, idx):
    """Targeted text edit: inside each top-level object block with these ObjectIDs,
    set asl.clip.label.name to slot idx (adding the property if missing). Everything
    else in the file stays byte-identical."""
    changed = 0
    for oid in object_ids:
        m = re.search(r'\n\t<(\w+) ObjectID="%s" [^>]*>' % oid, xml)
        if not m:
            continue
        tag = m.group(1); a = m.start()
        b = xml.index('\n\t</%s>' % tag, a)
        block = xml[a:b]
        new = 'BE.Prefs.LabelColors.%d' % idx
        if '<asl.clip.label.name>' in block:
            block2 = re.sub(r'<asl.clip.label.name>[^<]*</asl.clip.label.name>',
                            '<asl.clip.label.name>%s</asl.clip.label.name>' % new, block, count=1)
        elif '<Properties Version="1">' in block:
            block2 = block.replace('<Properties Version="1">',
                                   '<Properties Version="1">\n\t\t\t\t\t<asl.clip.label.name>%s</asl.clip.label.name>' % new, 1)
        else:
            continue
        if block2 != block:
            xml = xml[:a] + block2 + xml[b:]; changed += 1
    return xml, changed


def items_at(seq, when=None, idx=None, track=None):
    """Track items covering timeline time `when` (sec), or the idx-th item (1-based)
    of `track` (default: the first non-empty track). Without `track`, every track's
    item at that time is returned (linked A/V halves, but also anything stacked there);
    with `track`, only that item and the item on a track whose Link pairs it."""
    if idx is not None:
        if track is not None and not 0 <= track < len(seq['tracks']):
            raise SystemExit(f"error: no track index {track}; run cuts --seq to see indices")
        tr = seq['tracks'][track] if track is not None else next(t for t in seq['tracks'] if t['items'])
        if not 1 <= idx <= len(tr['items']):
            raise SystemExit(f"error: that track has {len(tr['items'])} items, no #{idx}")
        first = tr['items'][idx - 1]
        if track is not None:
            # same-range items on other tracks = its linked partner(s)
            return [first] + [it for i, t in enumerate(seq['tracks']) if i != track for it in t['items']
                              if it['start_ticks'] == first['start_ticks'] and it['end_ticks'] == first['end_ticks']]
        when = (first['start'] + first['end']) / 2
    tracks = [seq['tracks'][track]] if track is not None else seq['tracks']
    return [it for t in tracks for it in t['items'] if it['start'] <= when < it['end']]


# ---------- timeline ----------
def sequences(root, ids):
    out = []
    for s in root.findall('Sequence'):
        name = txt(s, 'Name') or txt(s, './/Name')
        seq = {'name': name, 'tracks': []}
        for tg in s.findall('.//TrackGroups/TrackGroup/Second'):
            grp = deref(ids, tg)
            if grp is None:
                continue
            for tr in grp.findall('.//Tracks/Track'):
                trk = deref(ids, tr)
                if trk is None:
                    continue
                items = []
                for it in trk.findall('ClipTrack/ClipItems/TrackItems/TrackItem'):  # not TransitionItems
                    ti = deref(ids, it)
                    st = int(txt(ti, './/TrackItem/Start') or 0)
                    en = int(txt(ti, './/TrackItem/End') or 0)
                    sc = deref(ids, ti.find('.//SubClip'))
                    clip = deref(ids, sc.find('.//Clip')) if sc is not None else None
                    ip = txt(clip, './/InPoint'); op = txt(clip, './/OutPoint')
                    spd = txt(clip, './/PlaybackSpeed')
                    own = ti.find('.//ComponentOwner/Components')
                    items.append({'clip_id': clip.get('ObjectID') if clip is not None else None,
                                  'item_id': ti.get('ObjectID'),
                                  'chain_id': own.get('ObjectRef') if own is not None else None,
                                  'start_ticks': st, 'end_ticks': en,
                                  'in_ticks': int(ip) if ip else 0, 'out_ticks': int(op) if op else 0,
                                  'speed': float(spd) if spd else 1.0,
                                  'label': label_of(clip),
                                  'start': st / TICKS, 'end': en / TICKS,
                                  'src_in': int(ip) / TICKS if ip else None,
                                  'src_out': int(op) / TICKS if op else None,
                                  'name': txt(sc, 'Name'), 'kind': ti.tag})
                seq['tracks'].append({'type': trk.tag, 'items': items})
            if grp.tag == 'VideoTrackGroup':
                fr = txt(grp, './/FrameRate'); rect = txt(grp, './/FrameRect')
                seq['frame_ticks'] = int(fr) if fr and fr.isdigit() else None
                seq['frame_rect'] = rect
        out.append(seq)
    return out


def summary(root, ids):
    print('Media:')
    seen = set()
    for p in root.iter('ActualMediaFilePath'):
        if p.text and ('/' in p.text or '\\' in p.text):
            if p.text not in seen:
                seen.add(p.text); print('  ', p.text)
    print('Bins:', [txt(b, './/Name') for b in root.findall('BinProjectItem')])
    rates = {}
    for fr in root.iter('FrameRate'):
        if fr.text and fr.text.isdigit():
            rates[fps_from_ticks(fr.text)] = rates.get(fps_from_ticks(fr.text), 0) + 1
    print('Frame/sample rates seen (per sec):', rates)
    rects = {r.text for r in root.iter('FrameRect')}
    print('Frame rects:', rects)
    for s in sequences(root, ids):
        print(f"Sequence '{s['name']}':")
        for i, t in enumerate(s['tracks']):
            n = len(t['items'])
            end = max((x['end'] for x in t['items']), default=0)
            print(f"   {t['type']}[{i}] {n} items, ends {ts(end)}")
    n = len(root.findall('ExternallyProvidedTranscriptDocument'))
    print('Embedded transcripts:', n)


# ---------- transcript (FlatBuffer inside base64) ----------
class FB:
    def __init__(self, b): self.b = b
    def u32(self, o): return struct.unpack_from('<I', self.b, o)[0]
    def i32(self, o): return struct.unpack_from('<i', self.b, o)[0]
    def i64(self, o): return struct.unpack_from('<q', self.b, o)[0]
    def u16(self, o): return struct.unpack_from('<H', self.b, o)[0]
    def fields(self, o):
        vt = o - self.i32(o); vl = self.u16(vt)
        return [self.u16(vt + 4 + 2 * k) for k in range(vl // 2 - 2)]
    def ref(self, a): return a + self.u32(a)
    def vec(self, a):
        v = self.ref(a); n = self.u32(v)
        return [self.ref(v + 4 + 4 * j) for j in range(n)]
    def s(self, o):
        L = self.u32(o); return self.b[o + 4:o + 4 + L].decode('utf-8', 'replace')


def parse_transcript_blob(b):
    """Layout observed (Premiere 2024-26, provider 9a139944...):
    root -> doc table; doc.f0 = vector<Segment>; doc.f1 = language string
    Segment: f0 start(int64 ticks), f1 duration(int64 ticks), f2 -> speaker Guid, f3 vector<Word>
    Speaker: f0 name, f1 -> Guid (doc f2 and f5 point at the same vector of speakers)
    Word:    f0 start(int64 ticks), f1 duration(int64 ticks), f2 text(string), f3 confidence(float),
             f4 bool (punctuation follows / token boundary), f5 bool (sentence end),
             f6 = 3 pause, f7 = 1 filler word; pauses and fillers have empty text
    Words/segments are stored in reverse order -> sort by time."""
    fb = FB(b)
    root = fb.u32(0)
    doc = fb.ref(root + fb.fields(root)[0])
    df = fb.fields(doc)
    lang = fb.s(fb.ref(doc + df[1])) if len(df) > 1 and df[1] else None
    # speakers: doc f2 -> [Speaker{f0 name, f1 -> Guid table (16 bytes after its soffset)}]
    def guid_at(t):
        return b[t + 4:t + 20].hex()
    speakers = {}
    if len(df) > 2 and df[2]:
        for sp in fb.vec(doc + df[2]):
            sf = fb.fields(sp)
            speakers[guid_at(fb.ref(sp + sf[1]))] = fb.s(fb.ref(sp + sf[0]))
    segs = []
    for sg in fb.vec(doc + df[0]):
        f = fb.fields(sg)
        spk = speakers.get(guid_at(fb.ref(sg + f[2]))) if len(f) > 2 and f[2] else None
        words = []
        for w in fb.vec(sg + f[3]):
            wf = fb.fields(w)
            conf = struct.unpack_from('<f', b, w + wf[3])[0] if len(wf) > 3 and wf[3] else None
            flag = lambda k: b[w + wf[k]] if len(wf) > k and wf[k] else 0
            text = fb.s(fb.ref(w + wf[2]))
            # f6 = 3: a pause; f7 = 1: a filler word (uh, um); both have empty text
            # (steps/19: fillers sit within 0.3 s of the official transcript's uh/um)
            kind = 'pause' if not text and flag(6) == 3 else 'filler' if not text and flag(7) == 1 else \
                'word' if text else 'empty'
            words.append({'t': fb.i64(w + wf[0]) / TICKS, 'd': fb.i64(w + wf[1]) / TICKS,
                          'w': text, 'conf': conf, 'kind': kind,
                          'sentence_end': bool(flag(5)), 'phrase_end': bool(flag(4)) and bool(text)})
        words.sort(key=lambda x: x['t'])
        for w in words:
            w['speaker'] = spk
        segs.append({'start': fb.i64(sg + f[0]) / TICKS, 'dur': fb.i64(sg + f[1]) / TICKS,
                     'speaker': spk, 'words': words})
    segs.sort(key=lambda x: x['start'])
    return {'language': lang, 'speakers': list(speakers.values()), 'segments': segs}


def transcript_owners(root, ids):
    """Map each ExternallyProvidedTranscriptDocument ObjectID -> owning clip name.
    TranscriptClip sits in a MasterClip's <Clips> list next to the Audio/VideoClips;
    the MasterClip's <Name> tells you which media or nested sequence it transcribes."""
    owner = {}
    for mc in root.findall('MasterClip'):
        name = txt(mc, './/Name')
        for c in mc.findall('.//Clips/Clip'):
            tc = deref(ids, c)
            if tc is not None and tc.tag == 'TranscriptClip':
                doc = tc.find('TranscriptTextSegments')
                if doc is not None:
                    owner[doc.get('ObjectRef')] = name
    return owner


def transcripts(xml, root=None, ids=None):
    """Return list of {'owner','language','segments'} in file order."""
    root = root if root is not None else ET.fromstring(xml)
    ids = ids or index(root)
    own = transcript_owners(root, ids)
    out = []
    for d in root.findall('ExternallyProvidedTranscriptDocument'):
        blob = d.find('TranscriptData').text.strip()
        tr = parse_transcript_blob(base64.b64decode(blob))
        tr['owner'] = own.get(d.get('ObjectID'))
        out.append(tr)
    return out


def flatten(seq, media, seqs, track=None, depth=0):
    """Return [(tl_start, tl_end, media_in)] spans of `media` as it appears on `seq`'s
    timeline, resolving nested sequences (a track item whose name is a sequence name).
    Nested-sequence item src_in/src_out are times on the NESTED timeline, not media time."""
    by_name = {s['name']: s for s in seqs}
    spans = []
    tracks = [seq['tracks'][track]] if track is not None else seq['tracks']
    for t in tracks:
        for it in t['items']:
            if it['src_in'] is None:
                continue
            if it['name'] == media:
                spans.append((it['start'], it['end'], it['src_in']))
            elif it['name'] in by_name and depth < 5 and it['name'] != seq['name']:
                for (ns, ne, nin) in flatten(by_name[it['name']], media, seqs, None, depth + 1):
                    a, b = max(ns, it['src_in']), min(ne, it['src_out'])
                    if a < b:
                        off = it['start'] - it['src_in']
                        spans.append((a + off, b + off, nin + (a - ns)))
    return spans


def map_to_sequence(tr, seq, seqs, track=0):
    """Map a transcript (media time) onto `seq`'s timeline. Words whose midpoint falls
    in a removed range are dropped."""
    spans = flatten(seq, tr['owner'], seqs, track)
    out = []
    for sg in tr['segments']:
        for w in sg['words']:
            if not w['w']:          # pauses and filler words carry no text
                continue
            mid = w['t'] + w['d'] / 2
            for (s, e, mi) in spans:
                if mi <= mid < mi + (e - s):
                    out.append({**w, 't': max(0.0, w['t'] - mi + s)})
                    break
    out.sort(key=lambda x: x['t'])
    return out


def _wrap(text, width=42):
    """Split a cue into at most 2 lines of <= width chars, as balanced as possible."""
    if len(text) <= width:
        return text
    words = text.split(' ')
    best = None
    for k in range(1, len(words)):
        a, b = ' '.join(words[:k]), ' '.join(words[k:])
        if len(a) <= width and len(b) <= width:
            score = abs(len(a) - len(b))
            if best is None or score < best[0]:
                best = (score, a + '\n' + b)
    return best[1] if best else text


def cues(words, max_chars=84, max_dur=6.5, gap=0.8):
    """Group words into caption cues: break at sentence ends, pauses, length and duration."""
    words = [w for w in words if (w.get('w') or '').strip()]  # drop silence tokens
    out, cur = [], []
    for w in words:
        if cur:
            text = ' '.join(x['w'] for x in cur + [w])
            end = w['t'] + w['d']
            if (cur[-1]['w'].rstrip('"\')').endswith(('.', '?', '!'))
                    or w['t'] - (cur[-1]['t'] + cur[-1]['d']) > gap
                    or len(text) > max_chars or end - cur[0]['t'] > max_dur):
                out.append(cur); cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out


def srt(words):
    f = lambda s: f"{int(s//3600):02d}:{int(s%3600//60):02d}:{int(s%60):02d},{int(round(s*1000))%1000:03d}"
    return '\n'.join(f"{i}\n{f(c[0]['t'])} --> {f(c[-1]['t']+c[-1]['d'])}\n{_wrap(' '.join(x['w'] for x in c))}\n"
                     for i, c in enumerate(cues(words), 1))


def find_seq(seqs, name):
    for s in seqs:
        if s['name'] == name:
            return s
    raise SystemExit(f"error: no sequence named '{name}'. Sequences: {', '.join(repr(s['name']) for s in seqs)}")


# ---------- effects: component chains, Transform, keyframes ----------
# See references/effects.md. Everything below was read from Premiere 2026 (26.x)
# projects; the Transform object layout is copied verbatim from Premiere output.
FOREVER = '-91445760000000000'          # StartKeyframe time: "since forever"
FILTER_CID = 'd10da199-beea-4dd1-b941-ed3a78766d50'   # VideoFilterComponent
POINT_CID = 'ca81d347-309b-44d2-acc7-1c572efb973c'    # PointComponentParam
BOOL_CID = 'cc12343e-f113-4d3b-ae05-b287db77d461'     # VideoComponentParam (bool)
FLOAT_CID = 'fe47129e-6c94-4fc0-95d5-c056a517aaf3'    # VideoComponentParam (float)
ENUM_CID = '6e02e8bb-2569-46b2-8ab1-4ab11c43e9c8'     # VideoComponentParam (popup)
TRANSFORM_MATCH = 'AE.ADBE Geometry2'

# Transform's 12 params in file order: (cli key, tag, ClassID, Version, kind, default,
# children before StartKeyframe, children after StartKeyframe).
_B = ('LowerBound', 'UpperBound')
TRANSFORM_PARAMS = [
    ('anchor', 'PointComponentParam', POINT_CID, 4, 'point', (0.5, 0.5),
     [('Name', 'Anchor Point'), ('ParameterID', '1')], []),
    ('position', 'PointComponentParam', POINT_CID, 4, 'point', (0.5, 0.5),
     [('Name', 'Position'), ('ParameterID', '2')], []),
    ('uniform', 'VideoComponentParam', BOOL_CID, 10, 'bool', True,
     [('ParameterID', '11')], []),
    ('scale', 'VideoComponentParam', FLOAT_CID, 10, 'float', 100.0,
     [('Name', 'Scale Height'), ('LowerUIBound', '-200'), ('ParameterID', '3'), ('UpperUIBound', '200')],
     [('LowerBound', '-30000'), ('UpperBound', '30000')]),
    ('scale-width', 'VideoComponentParam', FLOAT_CID, 10, 'float', 100.0,
     [('Name', 'Scale Width'), ('LowerUIBound', '-200'), ('ParameterID', '4'), ('UpperUIBound', '200')],
     [('LowerBound', '-30000'), ('UpperBound', '30000')]),
    ('skew', 'VideoComponentParam', FLOAT_CID, 10, 'float', 0.0,
     [('Name', 'Skew'), ('ParameterID', '5')], [('LowerBound', '-70'), ('UpperBound', '70')]),
    ('skew-axis', 'VideoComponentParam', FLOAT_CID, 10, 'float', 0.0,
     [('Name', 'Skew Axis'), ('ParameterControlType', '3'), ('ParameterID', '6')],
     [('LowerBound', '-32768'), ('UpperBound', '32767')]),
    ('rotation', 'VideoComponentParam', FLOAT_CID, 10, 'float', 0.0,
     [('Name', 'Rotation'), ('ParameterControlType', '3'), ('ParameterID', '7')],
     [('LowerBound', '-32768'), ('UpperBound', '32767')]),
    ('opacity', 'VideoComponentParam', FLOAT_CID, 10, 'float', 100.0,
     [('Name', 'Opacity'), ('ParameterID', '8')], [('LowerBound', '0'), ('UpperBound', '100')]),
    ('use-comp-shutter', 'VideoComponentParam', BOOL_CID, 10, 'bool', True,
     [('ParameterID', '9')], []),
    ('shutter-angle', 'VideoComponentParam', FLOAT_CID, 10, 'float', 240.0,
     [('Name', 'Shutter Angle'), ('ParameterID', '10')],
     [('CurrentValue', '240'), ('LowerBound', '0'), ('UpperBound', '360')]),
    ('sampling', 'VideoComponentParam', ENUM_CID, 10, 'enum', 0,
     [('Name', 'Sampling'), ('DiscontinuousInterpolate', 'true'), ('ParameterID', '12')],
     [('LowerBound', '0'), ('UpperBound', '1')]),
]
TKEYS = [p[0] for p in TRANSFORM_PARAMS]
UNNAMED = {(TRANSFORM_MATCH, '11'): 'Uniform Scale', (TRANSFORM_MATCH, '4'): 'Scale Width',
           (TRANSFORM_MATCH, '9'): "Use Composition's Shutter Angle", ('AE.ADBE Motion', '4'): 'Uniform Scale'}


def fnum(v):
    """Premiere's float style: integral values as '100.', others at full precision."""
    v = float(v)
    return '%d.' % v if v.is_integer() and abs(v) < 1e15 else '%.17g' % v


def fpt(v):
    v = float(v)
    return '0' if v == 0 else '%.17g' % v


def static_value(kind, v):
    if kind == 'point':
        return f"{FOREVER},{fpt(v[0])}:{fpt(v[1])},0,0,0,0,0,0,5,4,0,0,0,0"
    if kind == 'bool':
        return f"{FOREVER},{'true' if v else 'false'},0,0,0,0,0,0"
    if kind == 'enum':
        return f"{FOREVER},{int(v)},0,0,0,0,0,0"
    return f"{FOREVER},{fnum(v)},0,0,0,0,0,0"


# ParameterID -> StartKeyframe string of an untouched Transform param
TDEFAULTS = {dict(pre)['ParameterID']: static_value(kind, d)
             for _k, _t, _c, _v, kind, d, pre, _p in TRANSFORM_PARAMS}


def parse_value(kind, s):
    s = str(s).strip()
    try:
        return _parse_value(kind, s)
    except (ValueError, TypeError):
        want = {'point': 'x:y (e.g. 0.5:0.5)', 'bool': 'true/false', 'enum': 'an integer',
                'float': 'a number'}[kind]
        raise SystemExit(f"error: '{s}' is not a valid value; expected {want}")


def _parse_value(kind, s):
    if kind == 'point':
        x, y = s.split(':'); return (float(x), float(y))
    if kind == 'bool':
        if s.lower() not in ('true', 'false', 'on', 'off', '1', '0'):
            raise SystemExit(f"expected true/false, got '{s}'")
        return s.lower() in ('true', 'on', '1')
    if kind == 'enum':
        return int(s)
    return float(s)


def next_object_id(xml):
    """Max of every ObjectID anywhere in the file (local scopes included) + 1."""
    return max(int(m) for m in re.findall(r'ObjectID="(\d+)"', xml)) + 1


def block_span(xml, oid):
    """(start, end, tag) of the top-level object with this ObjectID; start is the
    newline before it, end is just past its closing tag."""
    m = re.search(r'\n\t<(\w+) ObjectID="%s"[^>]*?(/?)>' % re.escape(str(oid)), xml)
    if not m:
        raise SystemExit(f"error: no top-level object with ObjectID {oid}")
    if m.group(2) == '/':
        return m.start(), m.end(), m.group(1)
    close = '\n\t</%s>' % m.group(1)
    b = xml.index(close, m.end())
    return m.start(), b + len(close), m.group(1)


def transform_xml(fid, pids, comp_id, values):
    """Text of a Transform VideoFilterComponent + its 12 params, in Premiere's layout."""
    v = dict(zip(TKEYS, [p[5] for p in TRANSFORM_PARAMS])); v.update(values)
    out = [f'\n\t<VideoFilterComponent ObjectID="{fid}" ClassID="{FILTER_CID}" Version="9">',
           '\t\t<Component Version="7">', '\t\t\t<Params Version="1">']
    out += [f'\t\t\t\t<Param Index="{i}" ObjectRef="{pid}"/>' for i, pid in enumerate(pids)]
    out += ['\t\t\t</Params>', f'\t\t\t<ID>{comp_id}</ID>', '\t\t\t<DisplayName>Transform</DisplayName>',
            '\t\t</Component>', '\t\t<VideoFilterType>2</VideoFilterType>',
            f'\t\t<MatchName>{TRANSFORM_MATCH}</MatchName>', '\t</VideoFilterComponent>']
    for (key, tag, cid, ver, kind, _d, pre, post), pid in zip(TRANSFORM_PARAMS, pids):
        # Premiere named these 'Scale Height'/'Scale Width' in 158 of 160 Transforms seen
        # (uniform on or off); the other 2 were 'Scale'/' '. Premiere loads both.
        out.append(f'\t<{tag} ObjectID="{pid}" ClassID="{cid}" Version="{ver}">')
        out += [f'\t\t<{k}>{t}</{k}>' for k, t in pre]
        out.append(f'\t\t<StartKeyframe>{static_value(kind, v[key])}</StartKeyframe>')
        out += [f'\t\t<{k}>{t}</{k}>' for k, t in post]
        out.append(f'\t</{tag}>')
    return '\n'.join(out)


def chain_components(root, ids, chain_id):
    ch = ids.get(chain_id)
    if ch is None:
        raise SystemExit(f"error: component chain {chain_id} not found")
    comps = []
    for c in ch.findall('ComponentChain/Components/Component'):
        comps.append(ids.get(c.get('ObjectRef')))
    return ch, comps


def component_name(c):
    return txt(c, './/DisplayName') or txt(c, 'MatchName') or txt(c, './/FilterMatchName') or c.tag


def add_transform(xml, chain_id, values, first=False):
    """Append (or prepend) a Transform to a video track item's component chain.
    Returns (new_xml, filter_object_id)."""
    root = ET.fromstring(xml); ids = index(root)
    ch, comps = chain_components(root, ids, chain_id)
    if ch.tag != 'VideoComponentChain':
        raise SystemExit(f"error: {chain_id} is a {ch.tag}, not a VideoComponentChain")
    if ch.find('DefaultMotion') is None and not any(txt(c, 'MatchName') == 'AE.ADBE Motion' for c in comps):
        raise SystemExit("error: this chain has no Motion (not a clip's chain?); refusing to guess")
    used = {1, 2}
    for c in comps:
        i = txt(c, './/ID')
        if i and i.isdigit():
            used.add(int(i))
    comp_id = max(used) + 1
    fid = next_object_id(xml); pids = list(range(fid + 1, fid + 13))
    a, b, _ = block_span(xml, chain_id)
    block = xml[a:b]
    if '<Components Version="1">' in block:
        refs = re.findall(r'\t\t\t\t<Component Index="\d+" ObjectRef="(\d+)"\s*/>\n', block)
        refs = ([str(fid)] + refs) if first else (refs + [str(fid)])
        body = ''.join(f'\t\t\t\t<Component Index="{i}" ObjectRef="{r}"/>\n' for i, r in enumerate(refs))
        block2 = re.sub(r'(<Components Version="1">\n)(?:\t\t\t\t<Component Index="\d+" ObjectRef="\d+"\s*/>\n)*',
                        lambda m: m.group(1) + body, block, count=1)
    elif '\n\t\t</ComponentChain>' in block:
        block2 = block.replace('\n\t\t</ComponentChain>',
                               f'\n\t\t\t<Components Version="1">\n\t\t\t\t<Component Index="0" ObjectRef="{fid}"/>'
                               '\n\t\t\t</Components>\n\t\t</ComponentChain>', 1)
    else:
        raise SystemExit("error: unexpected chain layout (no </ComponentChain>); edit by hand")
    new = xml[:a] + block2 + transform_xml(fid, pids, comp_id, values) + xml[b:]
    ET.fromstring(new)
    return new, fid


def transforms_of(root, ids, chain_id):
    _, comps = chain_components(root, ids, chain_id)
    return [c for c in comps if c is not None and txt(c, 'MatchName') == TRANSFORM_MATCH]


def param_objects(ids, comp):
    return [ids.get(p.get('ObjectRef')) for p in comp.findall('Component/Params/Param')]


def _replace_param_block(xml, pid, fn):
    a, b, _ = block_span(xml, pid)
    return xml[:a] + fn(xml[a:b]) + xml[b:]


def set_static(xml, pid, kind, value):
    """Set a param's static value and drop any animation on it."""
    def fn(block):
        block = re.sub(r'\n\t\t<IsTimeVarying>[^<]*</IsTimeVarying>', '', block)
        block = re.sub(r'\n\t\t<Keyframes>[^<]*</Keyframes>', '', block)
        return re.sub(r'<StartKeyframe>[^<]*</StartKeyframe>',
                      f'<StartKeyframe>{static_value(kind, value)}</StartKeyframe>', block, count=1)
    return _replace_param_block(xml, pid, fn)


def keyframe_string(kind, keys):
    """keys: [(ticks, value, interp)] sorted; interp 'ease' (Bezier, speed 0),
    'ease:NN' (Bezier, NN% influence) or 'linear'. Influence 1/3 on a side whose segment changes value, 1/6 otherwise
    (Premiere's own output). Point params also get spatial tangents of
    +-(delta / 6) per segment and use path speed (frame fractions per second)."""
    n = len(keys); out = []
    def delta(i):  # segment i -> i+1
        a, b = keys[i][1], keys[i + 1][1]
        return (b[0] - a[0], b[1] - a[1]) if kind == 'point' else (b - a,)
    def seg_speed(i):
        d = delta(i); dt = (keys[i + 1][0] - keys[i][0]) / TICKS
        if dt <= 0:
            raise SystemExit('error: keyframe times must increase')
        return (math.hypot(*d) if kind == 'point' else d[0]) / dt
    for i, (t, v, interp) in enumerate(keys):
        din = delta(i - 1) if i > 0 else None
        dout = delta(i) if i < n - 1 else None
        moving_in = din is not None and any(abs(x) > 1e-12 for x in din)
        moving_out = dout is not None and any(abs(x) > 1e-12 for x in dout)
        if interp == 'linear':
            a = 0
            s_in = seg_speed(i - 1) if i > 0 else 0
            s_out = seg_speed(i) if i < n - 1 else 0
            i_in = i_out = 1 / 6
        else:  # 'ease' = Premiere's Ease In/Out (33%); 'ease:NN' = NN% influence
            a = 5; s_in = s_out = 0
            infl = float(interp.split(':', 1)[1]) / 100 if ':' in interp else 1 / 3
            i_in = infl if moving_in else 1 / 6
            i_out = infl if moving_out else 1 / 6
        f = lambda x: '0' if abs(x) < 1e-15 else '%.17g' % x
        if kind == 'point':
            tin = (-din[0] / 6, -din[1] / 6) if din else (0, 0)
            tout = (dout[0] / 6, dout[1] / 6) if dout else (0, 0)
            out.append(f"{t},{fpt(v[0])}:{fpt(v[1])},{a},0,{f(s_in)},{f(i_in)},{f(s_out)},{f(i_out)},5,4,"
                       f"{f(tin[0])},{f(tin[1])},{f(tout[0])},{f(tout[1])}")
        else:
            out.append(f"{t},{fnum(v)},{a},0,{f(s_in)},{f(i_in)},{f(s_out)},{f(i_out)}")
    return ';'.join(out) + ';'


def set_keyframes(xml, pid, kind, keys):
    ks = keyframe_string(kind, keys)
    def fn(block):
        block = re.sub(r'\n\t\t<IsTimeVarying>[^<]*</IsTimeVarying>', '', block)
        block = re.sub(r'\n\t\t<Keyframes>[^<]*</Keyframes>', '', block)
        # IsTimeVarying goes after Name (or first when there is no Name), Keyframes after StartKeyframe
        if '\n\t\t<Name>' in block:
            block = re.sub(r'(\n\t\t<Name>[^<]*</Name>)', r'\1\n\t\t<IsTimeVarying>true</IsTimeVarying>', block, count=1)
        else:
            block = re.sub(r'(\n\t<\w+ ObjectID="\d+"[^>]*>)', r'\1\n\t\t<IsTimeVarying>true</IsTimeVarying>', block, count=1)
        return re.sub(r'(<StartKeyframe>[^<]*</StartKeyframe>)', r'\1\n\t\t<Keyframes>%s</Keyframes>' % ks, block, count=1)
    return _replace_param_block(xml, pid, fn)


def decode_value(s):
    if ':' in s:
        x, y = s.split(':'); return f"{float(x):.4f}:{float(y):.4f}"
    try:
        return f"{float(s):g}"
    except ValueError:
        return s


def chain_json(root, ids, item):
    """Structured effect stack of a track item (for effects --json)."""
    out = {'implicit': [], 'components': []}
    if not item.get('chain_id'):
        return out
    ch, comps = chain_components(root, ids, item['chain_id'])
    out['implicit'] = [n for t, n in (('DefaultMotion', 'Motion'), ('DefaultOpacity', 'Opacity'),
                                      ('DefaultVol', 'Volume')) if ch.find(t) is not None]
    sp = item.get('speed') or 1.0
    for idx, c in enumerate(comps):
        if c is None:
            continue
        params = []
        for p in param_objects(ids, c):
            if p is None:
                continue
            sk = txt(p, 'StartKeyframe') or ''
            entry = {'name': (txt(p, 'Name') or '').strip() or UNNAMED.get((txt(c, 'MatchName'), txt(p, 'ParameterID'))),
                     'parameter_id': txt(p, 'ParameterID'), 'object_id': p.get('ObjectID'),
                     'value': sk.split(',')[1] if sk.count(',') >= 1 else None}
            kf = txt(p, 'Keyframes')
            if kf and txt(p, 'IsTimeVarying') != 'false':
                entry['keys'] = []
                for k in kf.strip(';').split(';'):
                    f = k.split(',')
                    tl = (item['start_ticks'] + (int(f[0]) - item['in_ticks']) / sp) / TICKS
                    entry['keys'].append({'timeline_sec': round(tl, 6), 'source_ticks': int(f[0]),
                                          'value': f[1], 'interp': 'ease' if f[2] == '5' else 'linear'})
            params.append(entry)
        out['components'].append({'index': idx, 'name': component_name(c), 'component_id': txt(c, './/ID'),
                                  'match_name': txt(c, 'MatchName') or txt(c, './/FilterMatchName'),
                                  'object_id': c.get('ObjectID'), 'params': params})
    return out


def describe_chain(root, ids, item, frame_ticks=None):
    """Human-readable effect stack of a track item, keyframes on the timeline."""
    lines = []
    if not item.get('chain_id'):
        return ['    (no component chain)']
    ch, comps = chain_components(root, ids, item['chain_id'])
    implicit = [n for t, n in (('DefaultMotion', 'Motion'), ('DefaultOpacity', 'Opacity'),
                               ('DefaultVol', 'Volume')) if ch.find(t) is not None]
    if implicit:
        lines.append(f"    defaults (unchanged): {', '.join(implicit)}")
    sp = item.get('speed') or 1.0
    to_tl = lambda k: item['start_ticks'] + (k - item['in_ticks']) / sp
    for idx, c in enumerate(comps):
        if c is None:
            continue
        lines.append(f"    [{idx}] {component_name(c)}  (component ID {txt(c, './/ID')}, {txt(c, 'MatchName') or txt(c, './/FilterMatchName') or c.tag})")
        for p in param_objects(ids, c):
            if p is None:
                continue
            name = (txt(p, 'Name') or '').strip() or UNNAMED.get((txt(c, 'MatchName'), txt(p, 'ParameterID'))) \
                or f"param {txt(p, 'ParameterID')}"
            sk = txt(p, 'StartKeyframe') or ''
            val = decode_value(sk.split(',')[1]) if sk.count(',') >= 1 else '?'
            kf = txt(p, 'Keyframes')
            if kf and txt(p, 'IsTimeVarying') != 'false':
                ks = []
                for k in kf.strip(';').split(';'):
                    f = k.split(',')
                    ks.append(f"{ts(to_tl(int(f[0])) / TICKS)}={decode_value(f[1])}{'' if f[2] == '5' else '(lin)'}")
                lines.append(f"        {name.strip() or '(unnamed)'}: {len(ks)} keys  " + '  '.join(ks))
            elif c.tag == 'VideoFilterComponent' and txt(c, 'MatchName') in (TRANSFORM_MATCH, 'AE.ADBE Motion', 'AE.ADBE Opacity'):
                if txt(c, 'MatchName') == TRANSFORM_MATCH and sk == TDEFAULTS.get(txt(p, 'ParameterID')):
                    continue  # unchanged from Premiere's default; keep the listing short
                lines.append(f"        {name.strip() or '(unnamed)'} = {val}")
            elif txt(p, 'IsTimeVarying') == 'true':
                lines.append(f"        {name.strip() or '(unnamed)'}: animated")
        if txt(c, 'MatchName') == TRANSFORM_MATCH:
            sh = {txt(p, 'ParameterID'): txt(p, 'StartKeyframe') for p in param_objects(ids, c) if p is not None}
            blur = (sh.get('9') or '').split(',')[1:2] == ['false']
            lines.append(f"        motion blur: {'on (own shutter angle)' if blur else 'off (uses sequence shutter)'}")
    if not comps:
        lines.append('    (no effects beyond defaults)')
    return lines


def pick_item(seq, track, item):
    try:
        if track < 0:
            raise IndexError
        t = seq['tracks'][track]
    except IndexError:
        raise SystemExit(f"error: no track index {track}; run cuts --seq to see indices")
    if not 1 <= item <= len(t['items']):
        raise SystemExit(f"error: track {track} has {len(t['items'])} items")
    return t, t['items'][item - 1]


def parse_keys(spec, kind, item, frame_ticks, base, force=False):
    """'0=1.5:0.5@linear, 0.5=0.5:0.5' -> [(ticks, value, interp)].
    Times are seconds from the item's start on the timeline (base='item') or on the
    sequence (base='sequence'); converted to the clip's source time, the time base
    Premiere stores keyframes in, and snapped to the sequence frame grid.
    A time ending in 'f' is frames ('12f'). With base='item', a negative time counts
    back from the clip's last frame ('-1f' = last frame, '-12f' = 11 frames before it)."""
    keys = []
    dur = item['end_ticks'] - item['start_ticks']
    for part in [p.strip() for p in re.split(r'[;,]', spec) if p.strip()]:
        interp = 'ease'
        if '@' in part:
            part, interp = part.split('@', 1); interp = interp.strip()
            if not re.fullmatch(r'ease(:\d+(\.\d+)?)?|linear', interp):
                raise SystemExit(f"error: interpolation must be ease, ease:NN or linear, got '{interp}'")
        if '=' not in part:
            raise SystemExit(f"error: keyframe '{part}' needs TIME=VALUE, e.g. 0.5=0.5:0.5 or 12f=100")
        t, v = part.split('=', 1); t = t.strip()
        if not re.fullmatch(r'-?\d+(\.\d+)?f?', t):
            raise SystemExit(f"error: keyframe time '{t}' must be seconds (0.5) or frames (12f)")
        if t.endswith('f'):
            if not frame_ticks:
                raise SystemExit('error: sequence frame rate unknown; give times in seconds')
            rel = float(t[:-1]) * frame_ticks
        else:
            rel = float(t) * TICKS
        if base == 'sequence':
            rel -= item['start_ticks']
        elif t.startswith('-'):
            rel = dur + rel  # -1f -> start of the last frame
        if frame_ticks:
            rel = round(rel / frame_ticks) * frame_ticks
        rel = int(round(rel))
        if (rel < 0 or rel > dur) and not force:
            raise SystemExit(f"error: key at {t} falls outside the clip ({ts(item['start'])}-{ts(item['end'])} on the "
                             "timeline); use --force if that's intended")
        keys.append((item['in_ticks'] + int(round(rel * item.get('speed', 1.0))), parse_value(kind, v), interp))
    keys.sort(key=lambda k: k[0])
    if len(keys) < 2:
        raise SystemExit('error: give at least two keyframes')
    for a_, b_ in zip(keys, keys[1:]):
        if a_[0] == b_[0]:
            raise SystemExit(f"error: two keys land on the same frame ({ts(item['start'] + (a_[0] - item['in_ticks']) / item.get('speed', 1.0) / TICKS)}); "
                             "space them at least one frame apart")
    return keys


# ---------- duplicating a sequence (backup) ----------
# references/object-surgery.md "Creating a sequence from another", step 6 (backup:
# keep every item). Verified in Premiere 2026 by the recipe; this is its code form.
REGEN_GUID = {('VideoClip', 'ClipID'), ('AudioClip', 'ClipID'), ('AudioClipTrackItem', 'ID'),
              ('AudioClipTrack', 'ID'), ('AudioMixTrack', 'ID'), ('AudioTrackGroup', 'ID')}
GUID_RE = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'


def _refs(e):
    return [x.get('ObjectRef') or x.get('ObjectURef') for x in e.iter()
            if x.get('ObjectRef') or x.get('ObjectURef')]


def _reach(ids, starts, stop=()):
    """Top-level objects reachable from starts, never entering Project or `stop`."""
    seen, todo = set(), list(starts)
    while todo:
        k = todo.pop()
        if k in seen or k in stop or k not in ids or ids[k].tag == 'Project':
            continue
        seen.add(k)
        todo += _refs(ids[k])
    return seen


def sequence_item(root, ids, name):
    """(ClipProjectItem uid, Sequence uid) of the sequence called `name`. Found through
    MasterClip -> clip Source -> *SequenceSource -> Sequence, because a project item's
    own name can be stale."""
    seqs = [e for e in root.findall('Sequence') if txt(e, 'Name') == name]
    if not seqs:
        raise SystemExit(f"error: no sequence named '{name}'. Sequences: "
                         + ', '.join(repr(txt(e, 'Name')) for e in root.findall('Sequence')))
    if len(seqs) > 1:
        raise SystemExit(f"error: {len(seqs)} sequences are named '{name}'; rename one in Premiere first")
    suid = seqs[0].get('ObjectUID')
    for cpi in root.findall('ClipProjectItem'):
        mc = deref(ids, cpi.find('.//MasterClip'))
        for c in (mc.findall('.//Clips/Clip') if mc is not None else []):
            clip = deref(ids, c)
            src = deref(ids, clip.find('.//Source')) if clip is not None else None
            if src is not None and src.tag.endswith('SequenceSource'):
                sq = src.find('.//Sequence')
                if sq is not None and sq.get('ObjectURef') == suid:
                    return cpi.get('ObjectUID'), suid
    raise SystemExit(f"error: sequence '{name}' has no project item; can't duplicate it")


def duplicate_sequence(xml, name, new_name):
    """Clone a sequence with all its tracks, items, effects and links as `new_name`,
    in the same bin. Media, master clips of media and nested sequences stay shared."""
    root = ET.fromstring(xml); ids = index(root)
    if any(txt(e, 'Name') == new_name for e in root.findall('Sequence')):
        raise SystemExit(f"error: a sequence named '{new_name}' already exists")
    cpi, _suid = sequence_item(root, ids, name)
    # the sequence's own wrapper: its project item, master clip, that clip list, sources
    own = _reach(ids, [cpi], stop={_suid})
    others = [e.get('ObjectUID') for e in root.findall('ClipProjectItem') if e.get('ObjectUID') != cpi]
    shared = _reach(ids, others, stop=own)        # media, other sequences (and what they own)
    clone = _reach(ids, [cpi]) - shared
    nid = next_object_id(xml); idmap = {}
    for k in sorted(clone, key=lambda k: (not k.isdigit(), int(k) if k.isdigit() else 0, k)):
        if k.isdigit():
            idmap[k] = str(nid); nid += 1
        else:
            idmap[k] = str(uuid.uuid4())

    # sequence markers come along; give the copies their own marker GUIDs
    mmap = {}
    for k in clone:
        if ids[k].tag == 'Marker':
            for g in re.findall(r'(?:mMarkerID&quot;:&quot;|mMarkerID":"|keywordExtDVAv1_)(%s)' % GUID_RE,
                                xml[slice(*block_span_any(xml, k))]):
                mmap.setdefault(g, str(uuid.uuid4()))

    def remap(block, k):
        tag = ids[k].tag
        if tag in ('Marker', 'Markers') and mmap:
            block = re.sub(GUID_RE, lambda m: mmap.get(m.group(0), m.group(0)), block)
        block = re.sub(r'(Object(?:ID|UID|Ref|URef))="([^"]+)"',
                       lambda m: f'{m.group(1)}="{idmap.get(m.group(2), m.group(2))}"', block)
        for t, el in REGEN_GUID:
            if t == tag:
                block = re.sub(r'(\n\t\t+<%s>)%s(</%s>)' % (el, GUID_RE, el),
                               lambda m: m.group(1) + str(uuid.uuid4()) + m.group(2), block)
        # base64 blobs are deduplicated by BinaryHash: the clone comes after its
        # original, so its copy becomes the self-closing kind
        block = re.sub(r'<(\w+) Encoding="base64" BinaryHash="([^"]+)">[^<]*</\1>',
                       r'<\1 Encoding="base64" BinaryHash="\2"/>', block)
        if tag in ('Sequence', 'MasterClip', 'ClipProjectItem'):
            block = re.sub(r'(<Name>)[^<]*(</Name>)', lambda m: m.group(1) + xesc(new_name) + m.group(2), block, count=1) \
                if tag != 'Sequence' else re.sub(r'(\n\t\t<Name>)[^<]*(</Name>)',
                                                 lambda m: m.group(1) + xesc(new_name) + m.group(2), block, count=1)
        if tag == 'ClipLoggingInfo':
            block = re.sub(r'(<ClipName>)[^<]*(</ClipName>)', lambda m: m.group(1) + xesc(new_name) + m.group(2), block, count=1)
        if tag == 'Sequence':
            block = re.sub(r'\n\t+<(Seq\.ExportID|ExportSettings\.[^>]*)>.*?</\1>', '', block, flags=re.S)
        return block

    spans = sorted(block_span_any(xml, k) + (k,) for k in clone)
    out, pos = [], 0
    for a, b, k in spans:
        out += [xml[pos:b], remap(xml[a:b], k)]
        pos = b
    out.append(xml[pos:])
    new = ''.join(out)
    # list the new project item in the bin that holds the original
    m = re.search(r'(<Items Version="1">(?:(?!</Items>).)*?<Item Index="\d+" ObjectURef="%s"\s*/>(?:(?!</Items>).)*?)(\n\t+</Items>)'
                  % re.escape(cpi), new, re.S)
    if not m:
        raise SystemExit("error: couldn't find the bin holding the sequence's project item")
    n = len(re.findall(r'<Item Index=', m.group(1)))
    indent = re.search(r'\n(\t+)<Item Index=', m.group(1)).group(1)
    new = new[:m.end(1)] + f'\n{indent}<Item Index="{n}" ObjectURef="{idmap[cpi]}"/>' + new[m.end(1):]
    return new, len(clone)


def block_span_any(xml, k):
    attr = 'ObjectID' if str(k).isdigit() else 'ObjectUID'
    m = re.search(r'\n\t<(\w+) %s="%s"[^>]*?(/?)>' % (attr, re.escape(str(k))), xml)
    if not m:
        raise SystemExit(f"error: no top-level object {k}")
    if m.group(2) == '/':
        return m.start(), m.end()
    close = '\n\t</%s>' % m.group(1)
    return m.start(), xml.index(close, m.end()) + len(close)


def xesc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ---------- validation ----------
def validate(xml, orig_xml=None):
    """Structural checks after an edit. Returns (errors, warnings)."""
    errors, warnings = [], []
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        return [f"XML does not parse: {e}"], []
    seen = {}
    for e in root:
        k = e.get('ObjectID') or e.get('ObjectUID')
        if k:
            seen[k] = seen.get(k, 0) + 1
    dups = [k for k, n in seen.items() if n > 1]
    if dups:
        errors.append(f"duplicate top-level ObjectID/ObjectUID: {dups[:20]}")
    refd, unresolved = set(), []
    for top in root:
        if top.tag == 'Project':
            continue
        for el in top.iter():
            r = el.get('ObjectRef') or el.get('ObjectURef')
            if r:
                refd.add(r)
                if r not in seen:
                    unresolved.append((top.tag, top.get('ObjectID') or top.get('ObjectUID'), el.tag, r))
    if unresolved:
        errors.append(f"{len(unresolved)} unresolved refs (outside Project), first: {unresolved[:5]}")

    def unref_count(r):
        rs = set()
        for el in r.iter():
            v = el.get('ObjectRef') or el.get('ObjectURef')
            if v: rs.add(v)
        return sum(1 for e in r if (e.get('ObjectID') or e.get('ObjectUID')) and
                   (e.get('ObjectID') or e.get('ObjectUID')) not in rs and e.tag != 'Project')
    n_unref = unref_count(root)
    if orig_xml is not None:
        n0 = unref_count(ET.fromstring(orig_xml))
        if n_unref > n0:
            errors.append(f"{n_unref - n0} new unreferenced top-level objects ({n0} -> {n_unref})")
    else:
        warnings.append(f"{n_unref} unreferenced top-level objects (pass --orig to compare; settings objects are normal)")
    clip_ids = [c.text for c in root.iter('ClipID') if c.text]
    from collections import Counter
    cdup = sorted(c for c, n in Counter(clip_ids).items() if n > 1)
    if cdup:
        errors.append(f"{len(cdup)} ClipID GUIDs shared between clips (Premiere gives every clip, split pieces included, "
                      f"its own; regenerate them on clones): {cdup[:3]}")
    try:
        trs = transcripts(xml, root, index(root))
        warnings.append(f"{len(trs)} transcripts parse OK")
    except Exception as e:  # noqa
        errors.append(f"transcript parse failed: {e}")
    return errors, warnings



# ---------------------------------------------------------------- timeline edits
# split / trim / delete, written to reproduce what Premiere saves for the same edit
# (fixtures/premiere-pro/steps 05->06 razor, 06->07 trim, 07->08 ripple delete).

# Objects a track item points at but doesn't own: never cloned or deleted with it.
ITEM_SHARED = {'MasterClip', 'Media', 'VideoMediaSource', 'AudioMediaSource', 'VideoSequenceSource',
               'AudioSequenceSource', 'Markers', 'Sequence', 'VideoStream', 'AudioStream',
               'ClipLoggingInfo', 'ClipProjectItem', 'VideoClipTrack', 'AudioClipTrack', 'Link',
               'ClipChannelGroupVectorSerializer', 'ClipChannelVectorSerializer', 'ClipChannelSerializer'}


def _k(e):
    return e.get('ObjectID') or e.get('ObjectUID')


def item_owned(ids, item):
    """Top-level objects owned by one track item: the item, its effect chain (components,
    params), SubClip, clip and the clip's SecondaryContent."""
    seen, todo = set(), [item]
    while todo:
        k = todo.pop()
        if k in seen or k not in ids or (k != item and ids[k].tag in ITEM_SHARED):
            continue
        seen.add(k)
        todo += _refs(ids[k])
    return seen


def parse_time(s, frame_ticks):
    """'4.5' seconds, '119f' frames or '00:00:04:23' timecode -> ticks, snapped to a frame."""
    s = str(s).strip()
    if re.fullmatch(r'\d+:\d\d:\d\d[:;]\d\d', s):
        h, m, sec, f = (int(x) for x in re.split('[:;]', s))
        fps = round(TICKS / frame_ticks)
        t = ((h * 3600 + m * 60 + sec) * fps + f) * frame_ticks
    elif s.endswith('f'):
        t = int(s[:-1]) * frame_ticks
    else:
        t = float(s) * TICKS
    return int(round(t / frame_ticks)) * frame_ticks


class Timeline:
    """Read model of one sequence for editing: tracks with items in order, links, locks."""

    def __init__(self, xml, seq_name):
        self.xml = xml
        self.root = ET.fromstring(xml); self.ids = ids = index(self.root)
        seqs = [e for e in self.root.findall('Sequence') if txt(e, 'Name') == seq_name]
        if len(seqs) != 1:
            raise SystemExit(f"error: {'no' if not seqs else len(seqs)} sequence named '{seq_name}'. Sequences: "
                             + ', '.join(repr(txt(e, 'Name')) for e in self.root.findall('Sequence')))
        self.seq = seqs[0]
        self.tracks = []      # [{'key','tag','locked','items':[item ids in list order]}]
        self.frame = None
        for tg in self.seq.findall('.//TrackGroups/TrackGroup/Second'):
            grp = deref(ids, tg)
            if grp is None:
                continue
            if grp.tag == 'VideoTrackGroup':
                fr = txt(grp, './/FrameRate')
                self.frame = int(fr) if fr and fr.isdigit() else None
            for tr in grp.findall('.//Tracks/Track'):
                trk = deref(ids, tr)
                if trk is None:
                    continue
                self.tracks.append({'key': _k(trk), 'tag': trk.tag,
                                    'locked': txt(trk, 'ClipTrack/Track/IsLocked') == 'true',
                                    'transitions': [deref(ids, t) for t in trk.findall('ClipTrack/TransitionItems/TrackItems/TrackItem')],
                                    'items': [_k(deref(ids, it)) for it in trk.findall('ClipTrack/ClipItems/TrackItems/TrackItem')]})
        self.frame = self.frame or 10594584000
        self.links = [deref(ids, l) for l in self.seq.findall('PersistentGroupContainer/LinkContainer/Links/Link')]

    def item(self, k):
        e = self.ids[k]
        sc = deref(self.ids, e.find('.//SubClip'))
        clip = deref(self.ids, sc.find('Clip')) if sc is not None else None
        spd = txt(clip, './/PlaybackSpeed')
        return {'key': k, 'el': e, 'clip': _k(clip) if clip is not None else None,
                'start': int(txt(e, './/TrackItem/Start') or 0), 'end': int(txt(e, './/TrackItem/End') or 0),
                'in': int(txt(clip, './/InPoint') or 0), 'out': int(txt(clip, './/OutPoint') or 0),
                'speed': float(spd) if spd else 1.0, 'name': txt(sc, 'Name') if sc is not None else '?'}

    def track_of(self, k):
        return next(i for i, t in enumerate(self.tracks) if k in t['items'])

    def label(self, ti):
        kind = 'V' if self.tracks[ti]['tag'].startswith('Video') else 'A'
        return f"{kind}{1 + sum(1 for t in self.tracks[:ti] if t['tag'][0] == self.tracks[ti]['tag'][0])}"

    def pick(self, track, n):
        """Track/item numbers as `cuts` prints them (item numbers start at 1)."""
        if track is None or track < 0 or track >= len(self.tracks):
            raise SystemExit(f"error: --track must be 0-{len(self.tracks) - 1} (the indices `cuts` prints)")
        its = sorted(self.tracks[track]['items'], key=lambda k: self.item(k)['start'])
        if n is None or not 1 <= n <= len(its):
            raise SystemExit(f"error: --item must be 1-{len(its)} on track {track}")
        return its[n - 1]

    def link_of(self, k):
        for l in self.links:
            if l is not None and any(r.get('ObjectRef') == k for r in l.findall('.//TrackItems/TrackItem')):
                return l
        return None

    def partners(self, k):
        l = self.link_of(k)
        return [r.get('ObjectRef') for r in l.findall('.//TrackItems/TrackItem')] if l is not None else [k]

    def check_unlocked(self, keys):
        for k in keys:
            ti = self.track_of(k)
            if self.tracks[ti]['locked']:
                raise SystemExit(f"error: track {self.label(ti)} is locked; unlock it first (set-track --track N --lock off)")

    def check_transitions(self, keys, at=None):
        for k in keys:
            ti = self.track_of(k); it = self.item(k)
            if it['el'].find('.//HeadTransition') is not None or it['el'].find('.//TailTransition') is not None:
                raise SystemExit(f"error: {it['name']} on {self.label(ti)} has a transition; remove it in Premiere "
                                 "first (transition edits aren't supported yet)")
            for tr in self.tracks[ti]['transitions']:
                if tr is None:
                    continue
                s = int(txt(tr, './/TrackItem/Start') or 0); e = int(txt(tr, './/TrackItem/End') or 0)
                if s <= it['end'] and e >= it['start']:
                    raise SystemExit(f"error: a transition touches {it['name']} on {self.label(ti)}; "
                                     "remove it in Premiere first")


def _set_child(block, tag, value, before=None):
    """Set <tag>value</tag> inside a block (first occurrence); insert before <before> if absent."""
    if re.search(r'<%s>[^<]*</%s>' % (tag, tag), block):
        return re.sub(r'(<%s>)[^<]*(</%s>)' % (tag, tag), lambda m: m.group(1) + str(value) + m.group(2), block, count=1)
    m = re.search(r'\n(\t+)<%s>' % before, block)
    if not m:
        raise SystemExit(f"error: can't place <{tag}> (no <{before}>)")
    return block[:m.start()] + f"\n{m.group(1)}<{tag}>{value}</{tag}>" + block[m.start():]


def _drop_child(block, tag):
    return re.sub(r'\n\t+<%s>[^<]*</%s>' % (tag, tag), '', block, count=1)


def _set_start(block, ticks):
    # <Start> is omitted when it's 0
    return _drop_child(block, 'Start') if ticks == 0 else _set_child(block, 'Start', ticks, before='End')


def _edit_list(block, container, entry, fn):
    """Rewrite the entries of <container> (e.g. 'TrackItems' inside ClipItems) in a block:
    fn(list of refs) -> new list of refs. Indices are renumbered; an emptied list is removed."""
    m = re.search(r'(\n(\t+)<%s Version="(\d+)">)(.*?)(\n\2</%s>)' % (container, container), block, re.S)
    refs = re.findall(r'<%s Index="\d+" (Object(?:U)?Ref)="([^"]+)"\s*/>' % entry, m.group(4)) if m else []
    attr = refs[0][0] if refs else 'ObjectRef'
    new = fn([r for _, r in refs])
    if m is None:
        return None, new
    if not new:
        return block[:m.start()] + block[m.end():], new
    ind = m.group(2) + '\t'
    body = ''.join(f'\n{ind}<{entry} Index="{i}" {attr}="{r}"/>' for i, r in enumerate(new))
    return block[:m.start()] + m.group(1) + body + m.group(5) + block[m.end():], new


class Editor:
    """Text-level editor: replaces/inserts/removes whole top-level blocks, keeping every
    other byte of the file as Premiere wrote it."""

    def __init__(self, xml):
        self.xml = xml; self.nid = next_object_id(xml)
        self.replace = {}; self.after = {}; self.delete = set()

    def block(self, k):
        if k in self.replace:
            return self.replace[k]
        a, b = block_span_any(self.xml, k)
        return self.xml[a:b]

    def set(self, k, text):
        self.replace[k] = text

    def insert_after(self, k, text):
        self.after.setdefault(k, []).append(text)

    def new_id(self):
        self.nid += 1
        return str(self.nid - 1)

    def render(self):
        spans = sorted((block_span_any(self.xml, k) + (k,) for k in set(self.replace) | set(self.after) | self.delete))
        out, pos = [], 0
        for a, b, k in spans:
            out.append(self.xml[pos:a])
            if k not in self.delete:
                out.append(self.replace.get(k, self.xml[a:b]))
            out += self.after.get(k, [])
            pos = b
        out.append(self.xml[pos:])
        return ''.join(out)


def _clone_item(tl, ed, k):
    """Clone the objects one track item owns, with new IDs/GUIDs. Returns {old: new} and
    {old: new block text}; nothing is placed yet."""
    owned = item_owned(tl.ids, k)
    idmap = {}
    for o in sorted(owned, key=lambda x: int(x) if x.isdigit() else 0):
        idmap[o] = ed.new_id() if o.isdigit() else str(uuid.uuid4())
    blocks = {}
    for o in owned:
        tag = tl.ids[o].tag
        b = ed.block(o)
        b = re.sub(r'(Object(?:ID|UID|Ref|URef))="([^"]+)"', lambda m: f'{m.group(1)}="{idmap.get(m.group(2), m.group(2))}"', b)
        for t, el in REGEN_GUID:
            if t == tag:
                b = re.sub(r'(\n\t\t+<%s>)%s(</%s>)' % (el, GUID_RE, el), lambda m: m.group(1) + str(uuid.uuid4()) + m.group(2), b)
        b = re.sub(r'<(\w+) Encoding="base64" BinaryHash="([^"]+)">[^<]*</\1>', r'<\1 Encoding="base64" BinaryHash="\2"/>', b)
        blocks[o] = b
    return idmap, blocks


def _track_list(tl, ed, ti, fn):
    k = tl.tracks[ti]['key']
    b = ed.block(k)
    i = b.index('<ClipItems')
    head, tail = b[:i], b[i:]
    j = tail.index('</ClipItems>')
    sect, rest = tail[:j], tail[j:]
    new_sect, refs = _edit_list(sect, 'TrackItems', 'TrackItem', fn)
    if new_sect is None:      # empty track: create the list before ClipItems' MediaType
        ind = re.search(r'\n(\t+)<MediaType>', sect).group(1)
        body = ''.join(f'\n{ind}\t<TrackItem Index="{n}" ObjectRef="{r}"/>' for n, r in enumerate(refs))
        mt = sect.index(f'\n{ind}<MediaType>')
        new_sect = sect[:mt] + f'\n{ind}<TrackItems Version="1">{body}\n{ind}</TrackItems>' + sect[mt:]
    ed.set(k, head + new_sect + rest)


def _seq_links(tl, ed, fn):
    k = _k(tl.seq)
    b = ed.block(k)
    new, refs = _edit_list(b, 'Links', 'Link', fn)
    if new is None:
        m = re.search(r'(\n(\t+)<LinkContainer Version="1">)', b)
        ind = m.group(2) + '\t'
        body = ''.join(f'\n{ind}\t<Link Index="{n}" ObjectRef="{r}"/>' for n, r in enumerate(refs))
        new = b[:m.end()] + f'\n{ind}<Links Version="1">{body}\n{ind}</Links>' + b[m.end():] if refs else b
    ed.set(k, new)


def _set_length(tl, ed, xml_len):
    k = _k(tl.seq)
    b = ed.block(k)
    if '<Monitor.ProgramZoomOut>' in b:
        b = _set_child(b, 'Monitor.ProgramZoomOut', xml_len)
    ed.set(k, b)


def _clip_block_times(ed, clip, inp=None, out=None):
    b = ed.block(clip)
    if inp is not None:
        b = _set_child(b, 'InPoint', inp)
    if out is not None:
        b = _set_child(b, 'OutPoint', out)
    ed.set(clip, b)


def _item_block_times(ed, k, start=None, end=None):
    b = ed.block(k)
    if start is not None:
        b = _set_start(b, start)
    if end is not None:
        b = _set_child(b, 'End', end)
    ed.set(k, b)


def _length_after(tl, changes):
    """Largest End over all tracks, given {item key: new end} and deletions (None)."""
    best = 0
    for t in tl.tracks:
        for k in t['items']:
            e = changes.get(k, tl.item(k)['end'])
            if e is not None:
                best = max(best, e)
    return best


def split_items(xml, seq_name, at, track=None):
    """Razor at `at` (sequence time): on `track` (and its linked partners), or on every
    unlocked track. Left halves keep their objects; right halves are clones."""
    tl = Timeline(xml, seq_name)
    at = parse_time(at, tl.frame)
    tracks = [track] if track is not None else [i for i, t in enumerate(tl.tracks) if not t['locked']]
    if track is not None and not 0 <= track < len(tl.tracks):
        raise SystemExit(f"error: --track must be 0-{len(tl.tracks) - 1}")
    targets = []
    for ti in tracks:
        for k in tl.tracks[ti]['items']:
            it = tl.item(k)
            if it['start'] < at < it['end']:
                targets.append(k)
    if track is not None:
        targets = list(dict.fromkeys(p for k in targets for p in tl.partners(k)
                                     if tl.item(p)['start'] < at < tl.item(p)['end']))
    if not targets:
        raise SystemExit(f"error: nothing to split at {ts(at / TICKS)}"
                         + (f" on track {track}" if track is not None else '') + " (a cut must fall inside a clip)")
    tl.check_unlocked(targets); tl.check_transitions(targets)
    ed = Editor(xml); right = {}
    for k in targets:
        it = tl.item(k)
        if it['speed'] < 0:
            raise SystemExit(f"error: {it['name']} is reversed; splitting reversed clips isn't supported")
        src = it['in'] + int(round((at - it['start']) * it['speed']))
        idmap, blocks = _clone_item(tl, ed, k)
        new_item, new_clip = idmap[k], idmap[it['clip']]
        blocks[k] = _set_child(_set_start(blocks[k], at), 'End', it['end'])
        blocks[it['clip']] = _set_child(blocks[it['clip']], 'InPoint', src)
        _item_block_times(ed, k, end=at)
        _clip_block_times(ed, it['clip'], out=src)
        for o, b in sorted(blocks.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else 0):
            ed.insert_after(o, b)
        right[k] = new_item
        ti = tl.track_of(k)
        _track_list(tl, ed, ti, lambda refs, k=k, n=new_item: refs[:refs.index(k) + 1] + [n] + refs[refs.index(k) + 1:])
    # links: one new link per old link, holding the right halves of its members
    new_links = []
    for l in tl.links:
        if l is None:
            continue
        mem = [r.get('ObjectRef') for r in l.findall('.//TrackItems/TrackItem')]
        halves = [right[m] for m in mem if m in right]
        if len(halves) < 2:
            continue
        lid = ed.new_id()
        lb = ed.block(_k(l))
        lb = re.sub(r'ObjectID="%s"' % _k(l), f'ObjectID="{lid}"', lb, count=1)
        lb = re.sub(r'(<TrackItems Version="\d+">).*?(\n\t+</TrackItems>)',
                    lambda m: m.group(1) + ''.join(f'\n\t\t\t\t<TrackItem Index="{i}" ObjectRef="{h}"/>'
                                                   for i, h in enumerate(halves)) + m.group(2), lb, flags=re.S)
        ed.insert_after(_k(l), lb)
        new_links.append((_k(l), lid))
    if new_links:
        def addl(refs):
            for old, new in new_links:
                refs = refs[:refs.index(old) + 1] + [new] + refs[refs.index(old) + 1:]
            return refs
        _seq_links(tl, ed, addl)
    return ed.render(), [(tl.label(tl.track_of(k)), tl.item(k)['name']) for k in targets], at


def trim_item(xml, seq_name, track, n, start=None, end=None):
    """Move an item's (and its linked partners') start and/or end on the timeline,
    adjusting source in/out; neighbours don't move."""
    tl = Timeline(xml, seq_name)
    k = tl.pick(track, n)
    keys = tl.partners(k)
    tl.check_unlocked(keys); tl.check_transitions(keys)
    it0 = tl.item(k)
    ns = parse_time(start, tl.frame) if start is not None else it0['start']
    ne = parse_time(end, tl.frame) if end is not None else it0['end']
    if ne <= ns:
        raise SystemExit("error: the clip would end before it starts")
    ed = Editor(xml); ends = {}; moved = []
    for p in keys:
        it = tl.item(p)
        # a partner's edge moves with the clip's only where the two edges line up; in a
        # split edit (J/L cut, steps/15) the partner's other edge stays where it is
        ds = ns - it0['start'] if it['start'] == it0['start'] else 0
        de = ne - it0['end'] if it['end'] == it0['end'] else 0
        if not ds and not de:
            continue
        moved.append(p)
        s2, e2 = it['start'] + ds, it['end'] + de
        i2 = it['in'] + int(round(ds * it['speed'])); o2 = it['out'] + int(round(de * it['speed']))
        if i2 < 0:
            raise SystemExit(f"error: {it['name']} would start {ts(-i2 / TICKS)} before its media begins")
        ti = tl.track_of(p)
        for q in tl.tracks[ti]['items']:
            if q == p:
                continue
            o = tl.item(q)
            if o['start'] < e2 and o['end'] > s2:
                raise SystemExit(f"error: {it['name']} would overlap {o['name']} on {tl.label(ti)}; "
                                 "trim or move that clip first")
        _item_block_times(ed, p, start=s2 if ds else None, end=e2 if de else None)
        _clip_block_times(ed, it['clip'], inp=i2 if ds else None, out=o2 if de else None)
        ends[p] = e2
    _set_length(tl, ed, _length_after(tl, ends))
    return ed.render(), [(tl.label(tl.track_of(p)), tl.item(p)['name']) for p in moved], (ns, ne)


def delete_item(xml, seq_name, track, n, ripple=False, force=False):
    """Remove an item and its linked partners; with ripple, close the gap on every track."""
    tl = Timeline(xml, seq_name)
    k = tl.pick(track, n)
    keys = tl.partners(k)
    tl.check_unlocked(keys); tl.check_transitions(keys)
    s = min(tl.item(p)['start'] for p in keys); e = max(tl.item(p)['end'] for p in keys)
    gone = e - s
    ed = Editor(xml)
    for p in keys:
        ed.delete |= item_owned(tl.ids, p)
        ti = tl.track_of(p)
        _track_list(tl, ed, ti, lambda refs, p=p: [r for r in refs if r != p])
    l = tl.link_of(k)
    if l is not None:
        ed.delete.add(_k(l))
        _seq_links(tl, ed, lambda refs: [r for r in refs if r != _k(l)])
    ends = {p: None for p in keys}
    if ripple:
        for ti, t in enumerate(tl.tracks):
            for q in t['items']:
                if q in keys:
                    continue
                o = tl.item(q)
                if o['end'] > s and o['start'] < e and not force:
                    raise SystemExit(f"error: {o['name']} on {tl.label(ti)} overlaps the deleted range, so "
                                     "rippling would knock tracks out of sync; delete without --ripple, or --force")
                if o['start'] >= e:
                    if t['locked']:
                        raise SystemExit(f"error: track {tl.label(ti)} is locked and has clips after the deletion")
                    _item_block_times(ed, q, start=o['start'] - gone, end=o['end'] - gone)
                    ends[q] = o['end'] - gone
    _set_length(tl, ed, _length_after(tl, ends))
    return ed.render(), [(tl.label(tl.track_of(p)), tl.item(p)['name']) for p in keys], (s, e)


# ---------------------------------------------------------------- markers
# Observed in fixtures/premiere-pro/steps/10->11. Colour is 0xAABBGGRR.
MARKERS_CID = 'bee50706-b524-416c-9f03-b596ce5f6866'
MARKER_CID = 'a45508e0-3ff7-4d04-90a7-2e0dfff4c910'
MARKER_COLOURS = {'orange': 0xFF246FE9, 'pink': 0xFFB18BAF}     # the two observed so far
MARKER_TYPES = ('Comment', 'Chapter')                           # observed; others aren't yet


def colour_rgb(n):
    return '#%02X%02X%02X' % (n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF)


def colour_value(spec):
    s = spec.strip().lower()
    if s in MARKER_COLOURS:
        return MARKER_COLOURS[s], True
    m = re.fullmatch(r'#?([0-9a-f]{6})', s)
    if not m:
        raise SystemExit(f"error: colour must be {' or '.join(MARKER_COLOURS)} or #RRGGBB")
    r, g, b = (int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4))
    return 0xFF000000 | (b << 16) | (g << 8) | r, False


def read_markers(root, ids, owner):
    """Markers on a Sequence (or clip) element: list of dicts in time order."""
    mo = owner.find('MarkerOwner/Markers') if owner is not None else None
    ms = deref(ids, mo) if mo is not None else None
    out = []
    for pair in (ms.findall('Markers/Marker') if ms is not None else []):
        m = deref(ids, pair.find('Second'))
        raw = txt(m, 'DVAMarker')
        if not raw:
            continue
        d = json.loads(raw).get('DVAMarker', {})
        col = None
        for cp in d.get('mCuePointList', []):
            try:
                col = json.loads(cp.get('mValue', '{}')).get('color', col)
            except ValueError:
                pass
        t = int(d.get('mStartTime', {}).get('ticks', 0))
        dur = d.get('mDuration', {}).get('ticks') if isinstance(d.get('mDuration'), dict) else None
        out.append({'time': t / TICKS, 'ticks': t, 'type': d.get('mType'), 'name': d.get('mName', ''),
                    'comment': d.get('mComment', ''), 'colour': colour_rgb(col) if col is not None else None,
                    'duration': int(dur) / TICKS if dur else 0.0, 'id': d.get('mMarkerID')})
    return sorted(out, key=lambda m: m['ticks'])


def youtube_chapters(markers):
    ch = [m for m in markers if m['type'] == 'Chapter']
    lines = []
    for m in ch:
        s = int(m['time']); h, r = divmod(s, 3600); mi, se = divmod(r, 60)
        lines.append((f"{h}:{mi:02d}:{se:02d}" if h else f"{mi}:{se:02d}") + ' ' + (m['name'] or 'Chapter'))
    return lines


def add_marker(xml, seq_name, at, name, comment='', mtype='Comment', colour='orange'):
    tl = Timeline(xml, seq_name)
    if mtype not in MARKER_TYPES:
        raise SystemExit(f"error: --type must be {' or '.join(MARKER_TYPES)} (the types seen in a Premiere save); "
                         "add other kinds in Premiere")
    t = parse_time(at, tl.frame)
    col, known = colour_value(colour)
    mid = str(uuid.uuid4())
    d = {'mComment': comment, 'mCuePointList': [{'mKey': f'keywordExtDVAv1_{uuid.uuid4()}',
                                                  'mValue': json.dumps({'color': col}, separators=(',', ':'))}],
         'mMarkerID': mid, 'mName': name, 'mStartTime': {'ticks': t}, 'mType': mtype}
    js = json.dumps({'DVAMarker': d}, separators=(',', ':'), sort_keys=True, ensure_ascii=False)
    ed = Editor(xml)
    sk = _k(tl.seq)
    mk = ed.new_id()
    marker = (f'\n\t<Marker ObjectID="{mk}" ClassID="{MARKER_CID}" Version="3">'
              f'\n\t\t<DVAMarker>{xesc(js)}</DVAMarker>\n\t</Marker>')
    entry = lambda n: f'\n\t\t\t<Marker Version="1" Index="{n}">\n\t\t\t\t<First>{mid}</First>\n\t\t\t\t<Second ObjectRef="{mk}"/>\n\t\t\t</Marker>'
    mo = tl.seq.find('MarkerOwner/Markers')
    if mo is None:
        msid = ed.new_id()
        ed.insert_after(sk, f'\n\t<Markers ObjectID="{msid}" ClassID="{MARKERS_CID}" Version="4">'
                            f'\n\t\t<Markers Version="1">{entry(0)}\n\t\t</Markers>'
                            '\n\t\t<ByGUID>byGUID</ByGUID>'
                            '\n\t\t<LastMetadataState>00000000-0000-0000-0000-000000000000</LastMetadataState>'
                            '\n\t\t<LastContentState>00000000-0000-0000-0000-000000000000</LastContentState>'
                            '\n\t</Markers>' + marker)
        b = ed.block(sk)
        m = re.search(r'\n\t\t<PersistentGroupContainer', b)
        ed.set(sk, b[:m.start()] + f'\n\t\t<MarkerOwner Version="1">\n\t\t\t<Markers ObjectRef="{msid}"/>\n\t\t</MarkerOwner>' + b[m.start():])
    else:
        msk = mo.get('ObjectRef')
        b = ed.block(msk)
        n = len(re.findall(r'<Marker Version="1" Index=', b))
        if n:
            i = b.rindex('\n\t\t</Markers>')
            b = b[:i] + entry(n) + b[i:]
        else:
            i = b.index('\n\t\t<ByGUID>')
            b = b[:i] + f'\n\t\t<Markers Version="1">{entry(0)}\n\t\t</Markers>' + b[i:]
        ed.set(msk, b)
        ed.insert_after(msk, marker)
    return ed.render(), t, known


# ---------------------------------------------------------------- track settings
def set_track(xml, seq_name, track, name=None, lock=None, mute=None):
    """Rename (MZ.TrackName), lock (Track/IsLocked) and mute (fader Mute param) a track.
    Observed in fixtures/premiere-pro/steps 08->09->10."""
    tl = Timeline(xml, seq_name)
    if track is None or not 0 <= track < len(tl.tracks):
        raise SystemExit(f"error: --track must be 0-{len(tl.tracks) - 1} (the indices `cuts` prints)")
    t = tl.tracks[track]; k = t['key']
    ed = Editor(xml); b = ed.block(k); done = []
    if name is not None:
        b = re.sub(r'\n\t+<MZ\.TrackName>[^<]*</MZ\.TrackName>', '', b, count=1)
        if name:
            i = b.index('\n\t\t\t\t\t</Properties>')
            b = b[:i] + f'\n\t\t\t\t\t\t<MZ.TrackName>{xesc(name)}</MZ.TrackName>' + b[i:]
        done.append(f"name {name!r}" if name else 'default name')
    if lock is not None:
        b = re.sub(r'\n\t+<IsLocked>[^<]*</IsLocked>', '', b, count=1)
        if lock:
            i = b.index('\n\t\t\t</Track>')
            b = b[:i] + '\n\t\t\t\t<IsLocked>true</IsLocked>' + b[i:]
        done.append('locked' if lock else 'unlocked')
    ed.set(k, b)
    if mute is not None:
        if not t['tag'].startswith('Audio'):
            raise SystemExit("error: --mute is for audio tracks (to hide a video track, use Premiere's eye toggle)")
        ch = deref(tl.ids, tl.ids[k].find('AudioTrack/ComponentOwner/Components'))
        param = None
        for c in (ch.findall('.//Components/Component') if ch is not None else []):
            comp = deref(tl.ids, c)
            if comp is not None and comp.tag == 'AudioFader':
                for p in comp.findall('.//Params/Param'):
                    pe = deref(tl.ids, p)
                    if pe is not None and txt(pe, 'Name') == 'Mute':
                        param = _k(pe)
        if param is None:
            raise SystemExit("error: couldn't find this track's fader Mute param")
        pb = ed.block(param)
        pb = re.sub(r'\n\t+<(StartKeyframe|CurrentValue)>[^<]*</\1>', '', pb)
        if mute:
            i = pb.index('\n\t\t<Name>')
            pb = pb[:i] + f'\n\t\t<StartKeyframe>{FOREVER},true,0,0,0,0,0,0</StartKeyframe>\n\t\t<CurrentValue>true</CurrentValue>' + pb[i:]
        ed.set(param, pb)
        done.append('muted' if mute else 'unmuted')
    return ed.render(), tl.label(track), done


# ---------------------------------------------------------------- place a clip / audio fade
# Shapes from Premiere's own saves: placing clip-b (steps 04->05) and the audio fade-ins
# (AudioTransitionTrackItem "Custom Fade", HasIncomingClip; steps/13-gen, 15).
TRACKITEM_CID = {'Video': '368b0406-29e3-4923-9fcd-094fbf9a1089', 'Audio': '064ec682-9ba6-11d5-af2d-9ca32c7d6164'}
SUBCLIP_CID = 'e0c58dc9-dbdd-4166-aef7-5db7e3f22e84'
VCHAIN_CID = '0970e08a-f58f-4108-b29a-1a717b8e12e2'
LINK_CID = '149d4ea5-a7d4-4b34-9bb7-16d783904bf2'
AUDIO_TRANSITION_CID = '23f687b6-9c5a-42f4-bea1-e7b3e28e7082'


def _master_by_name(root, ids, name):
    cands = [e for e in root.findall('MasterClip') if txt(e, 'Name') == name]
    media = []
    for mc in cands:
        clips = [deref(ids, c) for c in mc.findall('Clips/Clip')]
        src = [deref(ids, c.find('.//Source')) for c in clips if c is not None]
        if any(s is not None and s.tag.endswith('MediaSource') for s in src):
            media.append(mc)
    if len(media) != 1:
        raise SystemExit(f"error: {'no' if not media else len(media)} media clip named '{name}' in the project "
                         "(sequences can't be placed with this command yet)")
    return media[0]


def place_clip(xml, seq_name, clip_name, at, vtrack=None, atrack=None, src_in=None, src_out=None,
               duration=None, video=True, audio=True):
    tl = Timeline(xml, seq_name)
    ids = tl.ids
    mc = _master_by_name(tl.root, ids, clip_name)
    clips = [deref(ids, c) for c in mc.findall('Clips/Clip')]
    vclip = next((c for c in clips if c is not None and c.tag == 'VideoClip'), None)
    aclips = [c for c in clips if c is not None and c.tag == 'AudioClip']
    if not video: vclip = None
    if not audio: aclips = []
    if len(aclips) > 1:
        raise SystemExit("error: media with more than one audio clip (multi-channel layouts) isn't supported yet")
    aclip = aclips[0] if aclips else None
    if vclip is None and aclip is None:
        raise SystemExit("error: nothing to place (no video or audio left)")
    srcs = [deref(ids, c.find('.//Source')) for c in (vclip, aclip) if c is not None]
    lens = [int(txt(s, 'OriginalDuration') or 0) for s in srcs]
    if vclip is not None and lens[0] > 100 * 3600 * TICKS:
        raise SystemExit("error: still images aren't supported yet (their timing hasn't been seen in a Premiere save)")
    media_len = min(lens)
    i0 = parse_time(src_in, tl.frame) if src_in is not None else 0
    if src_out is not None:
        o0 = parse_time(src_out, tl.frame)
    elif duration is not None:
        o0 = i0 + parse_time(duration, tl.frame)
    else:
        o0 = media_len // tl.frame * tl.frame       # whole sequence frames (clip-b: exact)
    if not 0 <= i0 < o0 <= media_len:
        raise SystemExit(f"error: source range {ts(i0 / TICKS)}-{ts(o0 / TICKS)} is outside the media (0-{ts(media_len / TICKS)})")
    start = parse_time(at, tl.frame); end = start + (o0 - i0)
    vt = [i for i, t in enumerate(tl.tracks) if t['tag'].startswith('Video')]
    at_ = [i for i, t in enumerate(tl.tracks) if t['tag'].startswith('Audio')]
    want = []
    if vclip is not None:
        ti = vt[0] if vtrack is None else vtrack
        if ti not in vt: raise SystemExit(f"error: --track {ti} isn't a video track (video tracks: {vt})")
        want.append(('Video', ti, vclip))
    if aclip is not None:
        ti = at_[0] if atrack is None else atrack
        if ti not in at_: raise SystemExit(f"error: --audio-track {ti} isn't an audio track (audio tracks: {at_})")
        want.append(('Audio', ti, aclip))
    for kind, ti, _ in want:
        if tl.tracks[ti]['locked']:
            raise SystemExit(f"error: track {tl.label(ti)} is locked")
        for q in tl.tracks[ti]['items']:
            o = tl.item(q)
            if o['start'] < end and o['end'] > start:
                raise SystemExit(f"error: {o['name']} is already on {tl.label(ti)} at {ts(o['start'] / TICKS)}-"
                                 f"{ts(o['end'] / TICKS)}; overwriting isn't supported, pick a free spot")
    ed = Editor(xml); new_items = []
    for kind, ti, mclip in want:
        mk = _k(mclip)
        # the clip: a copy of the master clip's clip with a new ClipID and the source range
        cid = ed.new_id(); cb = ed.block(mk)
        cb = re.sub(r'ObjectID="%s"' % mk, f'ObjectID="{cid}"', cb, count=1)
        cb = re.sub(r'(<ClipID>)%s(</ClipID>)' % GUID_RE, lambda m: m.group(1) + str(uuid.uuid4()) + m.group(2), cb)
        cb = re.sub(r'\n\t+<InUse>[^<]*</InUse>', '', cb)
        cb = re.sub(r'(\n(\t+)<ClipID>[^<]*</ClipID>)', lambda m: m.group(1) + f'\n{m.group(2)}<InPoint>{i0}</InPoint>\n{m.group(2)}<OutPoint>{o0}</OutPoint>', cb, count=1)
        extra = []
        for sc in mclip.findall('.//SecondaryContents/SecondaryContentItem'):
            sk = sc.get('ObjectRef'); nk = ed.new_id()
            extra.append(re.sub(r'ObjectID="%s"' % sk, f'ObjectID="{nk}"', ed.block(sk), count=1))
            cb = cb.replace(f'<SecondaryContentItem Index="{sc.get("Index")}" ObjectRef="{sk}"', f'<SecondaryContentItem Index="{sc.get("Index")}" ObjectRef="{nk}"')
        sid = ed.new_id(); chid = ed.new_id(); iid = ed.new_id()
        sub = (f'\n\t<SubClip ObjectID="{sid}" ClassID="{SUBCLIP_CID}" Version="6">\n\t\t<Clip ObjectRef="{cid}"/>'
               f'\n\t\t<MasterClip ObjectURef="{_k(mc)}"/>\n\t\t<Name>{xesc(clip_name)}</Name>\n\t\t<OrigChGrp>0</OrigChGrp>\n\t</SubClip>')
        tstart = '' if start == 0 else f'\n\t\t\t\t<Start>{start}</Start>'
        if kind == 'Video':
            # the item's FrameRect is the sequence's frame, not the clip's: Premiere rewrote a
            # 1280x720 clip's item to the 1920x1080 sequence size on save (steps 18-gen→19)
            rect = None
            for tg in tl.seq.findall('.//TrackGroups/TrackGroup/Second'):
                g = deref(ids, tg)
                if g is not None and g.tag == 'VideoTrackGroup' and txt(g, './/FrameRect'):
                    rect = txt(g, './/FrameRect')
            if not rect:
                raise SystemExit("error: the sequence has no video frame size (VideoTrackGroup FrameRect)")
            chain = (f'\n\t<VideoComponentChain ObjectID="{chid}" ClassID="{VCHAIN_CID}" Version="3">'
                     '\n\t\t<DefaultMotion>true</DefaultMotion>\n\t\t<DefaultOpacity>true</DefaultOpacity>'
                     '\n\t\t<DefaultMotionComponentID>1</DefaultMotionComponentID>\n\t\t<DefaultOpacityComponentID>2</DefaultOpacityComponentID>'
                     '\n\t\t<ComponentChain Version="3">\n\t\t</ComponentChain>\n\t</VideoComponentChain>')
            item = (f'\n\t<VideoClipTrackItem ObjectID="{iid}" ClassID="{TRACKITEM_CID["Video"]}" Version="8">'
                    f'\n\t\t<ClipTrackItem Version="8">\n\t\t\t<ComponentOwner Version="1">\n\t\t\t\t<Components ObjectRef="{chid}"/>'
                    f'\n\t\t\t</ComponentOwner>\n\t\t\t<TrackItem Version="4">{tstart}\n\t\t\t\t<End>{end}</End>\n\t\t\t</TrackItem>'
                    f'\n\t\t\t<SubClip ObjectRef="{sid}"/>\n\t\t</ClipTrackItem>\n\t\t<ToneMapSettings>{{"peak":-1,"version":3}}</ToneMapSettings>'
                    f'\n\t\t<FrameRect>{rect}</FrameRect>\n\t\t<PixelAspectRatio>1,1</PixelAspectRatio>\n\t</VideoClipTrackItem>')
        else:
            mch = deref(ids, mc.find('AudioComponentChains/AudioComponentChain'))
            if mch is None:
                raise SystemExit("error: the master clip has no audio component chain to copy")
            chain = re.sub(r'ObjectID="%s"' % _k(mch), f'ObjectID="{chid}"', ed.block(_k(mch)), count=1)
            item = (f'\n\t<AudioClipTrackItem ObjectID="{iid}" ClassID="{TRACKITEM_CID["Audio"]}" Version="11">'
                    f'\n\t\t<ClipTrackItem Version="8">\n\t\t\t<ComponentOwner Version="1">\n\t\t\t\t<Components ObjectRef="{chid}"/>'
                    f'\n\t\t\t</ComponentOwner>\n\t\t\t<TrackItem Version="4">{tstart}\n\t\t\t\t<End>{end}</End>\n\t\t\t</TrackItem>'
                    f'\n\t\t\t<SubClip ObjectRef="{sid}"/>\n\t\t</ClipTrackItem>\n\t\t<ID>{uuid.uuid4()}</ID>'
                    f'\n\t\t<PreRenderComponentChainHashVersion>1</PreRenderComponentChainHashVersion>\n\t</AudioClipTrackItem>')
        ed.insert_after(_k(tl.seq), item + chain + sub + cb + ''.join(extra))
        new_items.append((iid, ti))

        def ins(refs, iid=iid):
            ks = sorted(refs + [iid], key=lambda k: start if k == iid else tl.item(k)['start'])
            return ks
        _track_list(tl, ed, ti, ins)
    if len(new_items) == 2:
        lid = ed.new_id()
        ed.insert_after(_k(tl.seq), f'\n\t<Link ObjectID="{lid}" ClassID="{LINK_CID}" Version="1">\n\t\t<TrackItemGroup Version="1">'
                        f'\n\t\t\t<TrackItems Version="1">\n\t\t\t\t<TrackItem Index="0" ObjectRef="{new_items[0][0]}"/>'
                        f'\n\t\t\t\t<TrackItem Index="1" ObjectRef="{new_items[1][0]}"/>\n\t\t\t</TrackItems>'
                        '\n\t\t</TrackItemGroup>\n\t</Link>')

        def lins(refs):
            first = lambda l: min(tl.item(r.get('ObjectRef'))['start'] for r in tl.ids[l].findall('.//TrackItems/TrackItem'))
            return sorted(refs + [lid], key=lambda l: start if l == lid else first(l))
        _seq_links(tl, ed, lins)
    # the media's master clip gets a Node ID on first use (steps 02->03, 04->05)
    mb = ed.block(_k(mc))
    if not re.search(r'<Node Version="1">\s*<ID>', mb):
        pk = next(_k(e) for e in tl.root if e.tag == 'Project' and e.get('ObjectID'))
        pb = ed.block(pk); nid = int(re.search(r'<NextID>(\d+)</NextID>', pb).group(1))
        ed.set(pk, re.sub(r'<NextID>\d+</NextID>', f'<NextID>{nid + 1}</NextID>', pb, count=1))
        if '<Node Version="1">' in mb.split('<LoggingInfo')[0]:
            mb = re.sub(r'<Node Version="1">', f'<Node Version="1">\n\t\t\t<ID>{nid}</ID>', mb, count=1)
        else:
            mb = re.sub(r'(\n\t\t<LoggingInfo)', f'\n\t\t<Node Version="1">\n\t\t\t<ID>{nid}</ID>\n\t\t</Node>\\1', mb, count=1)
        ed.set(_k(mc), mb)
    # sequence length bookkeeping: ZoomOut = length; *SequenceSource/OriginalDuration grows
    length = max(_length_after(tl, {}), end)
    _set_length(tl, ed, length)
    for e in tl.root:
        if e.tag in ('VideoSequenceSource', 'AudioSequenceSource'):
            sq = e.find('.//Sequence')
            if sq is not None and sq.get('ObjectURef') == _k(tl.seq):
                b = ed.block(_k(e)); od = int(txt(e, 'OriginalDuration') or 0)
                if length > od:
                    ed.set(_k(e), _set_child(b, 'OriginalDuration', length))
    return ed.render(), [(tl.label(ti), clip_name) for _, ti in new_items], (start, end)


def add_audio_fade_in(xml, seq_name, track, n, dur, out=False):
    """Fade an audio clip in from its first frame: an AudioTransitionTrackItem 'Custom Fade'
    with HasIncomingClip, as Premiere saves a fade-in (steps/13-gen, 15).
    out=True: the mirror image at the clip's last frame (HasOutgoingClip, referenced as
    TailTransition): derived from the fade-in, not yet seen in a Premiere save."""
    tl = Timeline(xml, seq_name)
    if not tl.tracks[track]['tag'].startswith('Audio'):
        raise SystemExit("error: fades are only supported on audio tracks so far (video transitions haven't been seen in a save)")
    k = tl.pick(track, n); it = tl.item(k)
    tl.check_unlocked([k])
    if it['el'].find('.//TailTransition' if out else './/HeadTransition') is not None:
        raise SystemExit(f"error: {it['name']} already has a fade {'out' if out else 'in'}")
    d = parse_time(dur, tl.frame)
    if not 0 < d < it['end'] - it['start']:
        raise SystemExit("error: the fade must be shorter than the clip")
    for tr in tl.tracks[track]['transitions']:
        if tr is None: continue
        s0 = int(txt(tr, './/TrackItem/Start') or 0); e0 = int(txt(tr, './/TrackItem/End') or 0)
        a0, b0 = (it['end'] - d, it['end']) if out else (it['start'], it['start'] + d)
        if s0 < b0 and e0 > a0:
            raise SystemExit("error: another transition is already there")
    ed = Editor(xml); tid = ed.new_id()
    layout = txt(tl.ids[deref(tl.ids, deref(tl.ids, it['el'].find('.//SubClip')).find('Clip')).get('ObjectID')],
                 'AudioChannelLayout') if True else None
    a0, b0 = (it['end'] - d, it['end']) if out else (it['start'], it['start'] + d)
    tstart = '' if a0 == 0 else f'\n\t\t\t\t<Start>{a0}</Start>'
    ed.insert_after(k, f'\n\t<AudioTransitionTrackItem ObjectID="{tid}" ClassID="{AUDIO_TRANSITION_CID}" Version="4">'
                       f'\n\t\t<TransitionTrackItem Version="3">\n\t\t\t<TrackItem Version="4">{tstart}\n\t\t\t\t<End>{b0}</End>'
                       f'\n\t\t\t</TrackItem>\n\t\t\t<HasOutgoingClip>{"true" if out else "false"}</HasOutgoingClip>\n\t\t\t<HasIncomingClip>{"false" if out else "true"}</HasIncomingClip>'
                       '\n\t\t\t<DisplayName>Custom Fade</DisplayName>\n\t\t\t<MatchName>Custom Fade</MatchName>'
                       f'\n\t\t\t<Alignment>{d if out else 0}</Alignment>'
                       f'\n\t\t</TransitionTrackItem>\n\t\t<AudioChannelLayout>{layout or "[{&quot;channellabel&quot;:100},{&quot;channellabel&quot;:101}]"}</AudioChannelLayout>'
                       '\n\t\t<FadeShapeValue>0</FadeShapeValue>\n\t</AudioTransitionTrackItem>')
    b = ed.block(k)
    if out:
        anchor = r'(\n(\t+)<HeadTransition ObjectRef="[^"]+"/>)' if '<HeadTransition' in b else r'(\n(\t+)<SubClip ObjectRef="[^"]+"/>)'
        b = re.sub(anchor, lambda m: m.group(1) + f'\n{m.group(2)}<TailTransition ObjectRef="{tid}"/>', b, count=1)
    else:
        b = re.sub(r'(\n(\t+)<SubClip ObjectRef="[^"]+"/>)', lambda m: m.group(1) + f'\n{m.group(2)}<HeadTransition ObjectRef="{tid}"/>', b, count=1)
    ed.set(k, b)
    tb = ed.block(tl.tracks[track]['key'])
    i = tb.index('<TransitionItems'); j = tb.index('</TransitionItems>', i)
    sect = tb[i:j]
    def tins(refs):
        when = lambda r: int(txt(tl.ids[r], './/TrackItem/Start') or 0) if r in tl.ids else a0
        return sorted(refs + [tid], key=lambda r: a0 if r == tid else when(r))
    new, _ = _edit_list(sect, 'TrackItems', 'TrackItem', tins)
    if new is None:
        ind = re.search(r'\n(\t+)<MediaType>', sect).group(1)
        mt = sect.index(f'\n{ind}<MediaType>')
        new = sect[:mt] + f'\n{ind}<TrackItems Version="1">\n{ind}\t<TrackItem Index="0" ObjectRef="{tid}"/>\n{ind}</TrackItems>' + sect[mt:]
    ed.set(tl.tracks[track]['key'], tb[:i] + new + tb[j:])
    return ed.render(), tl.label(track), it['name'], d


def add_audio_crossfade(xml, seq_name, track, n, dur):
    """Constant Power crossfade centred on the cut after item n, as Premiere saved one
    (steps/15-handles_and_crossfade): one AudioTransitionTrackItem with HasOutgoingClip and HasIncomingClip,
    Start = cut - d/2, End = cut + d/2, Alignment = cut - Start; the left clip references it
    as TailTransition, the right as HeadTransition. Both clips need d/2 of unused media
    (handles) beyond the cut; the items themselves don't change."""
    tl = Timeline(xml, seq_name)
    if not tl.tracks[track]['tag'].startswith('Audio'):
        raise SystemExit("error: crossfades are only supported on audio tracks so far")
    its = sorted(tl.tracks[track]['items'], key=lambda k: tl.item(k)['start'])
    if not 1 <= n < len(its):
        raise SystemExit(f"error: --item must be 1-{len(its) - 1}: the clip before the cut")
    L, R = tl.item(its[n - 1]), tl.item(its[n])
    if L['end'] != R['start']:
        raise SystemExit(f"error: {L['name']} and {R['name']} don't touch on {tl.label(track)} (a gap or overlap at the cut)")
    tl.check_unlocked([L['key'], R['key']])
    if L['el'].find('.//TailTransition') is not None or R['el'].find('.//HeadTransition') is not None:
        raise SystemExit("error: there's already a transition at this cut")
    d = parse_time(dur, tl.frame); half = (d // 2 // tl.frame) * tl.frame; d = 2 * half
    if half <= 0:
        raise SystemExit("error: the crossfade must be at least 2 frames")
    cut = L['end']
    # handles: unused media after the left clip's out, before the right clip's in
    lsrc = deref(tl.ids, deref(tl.ids, deref(tl.ids, L['el'].find('.//SubClip')).find('Clip')).find('.//Source'))
    llen = int(txt(lsrc, 'OriginalDuration') or 0)
    if L['out'] + half * L['speed'] > llen:
        raise SystemExit(f"error: {L['name']} has only {ts(max(0, llen - L['out']) / TICKS)} of media after its out point; "
                         f"a {d / TICKS:.3f}s crossfade needs {half / TICKS:.3f}s. Trim it shorter first (or use a shorter --duration)")
    if R['in'] - half * R['speed'] < 0:
        raise SystemExit(f"error: {R['name']} has only {ts(R['in'] / TICKS)} of media before its in point; "
                         f"a {d / TICKS:.3f}s crossfade needs {half / TICKS:.3f}s. Trim its start later first (or use a shorter --duration)")
    lay = txt(deref(tl.ids, deref(tl.ids, L['el'].find('.//SubClip')).find('Clip')), 'AudioChannelLayout')
    ed = Editor(xml); tid = ed.new_id()
    ed.insert_after(L['key'], f'\n\t<AudioTransitionTrackItem ObjectID="{tid}" ClassID="{AUDIO_TRANSITION_CID}" Version="4">'
                    f'\n\t\t<TransitionTrackItem Version="3">\n\t\t\t<TrackItem Version="4">\n\t\t\t\t<Start>{cut - half}</Start>'
                    f'\n\t\t\t\t<End>{cut + half}</End>\n\t\t\t</TrackItem>\n\t\t\t<HasOutgoingClip>true</HasOutgoingClip>'
                    '\n\t\t\t<HasIncomingClip>true</HasIncomingClip>\n\t\t\t<DisplayName>Constant Power</DisplayName>'
                    f'\n\t\t\t<MatchName>Constant Power</MatchName>\n\t\t\t<Alignment>{half}</Alignment>'
                    f'\n\t\t</TransitionTrackItem>\n\t\t<AudioChannelLayout>{xesc(lay) if lay else ""}</AudioChannelLayout>'
                    '\n\t</AudioTransitionTrackItem>')
    for k, tag in ((L['key'], 'TailTransition'), (R['key'], 'HeadTransition')):
        b = ed.block(k)
        anchor = r'(\n(\t+)<HeadTransition ObjectRef="[^"]+"/>)' if tag == 'TailTransition' and '<HeadTransition' in b \
            else r'(\n(\t+)<SubClip ObjectRef="[^"]+"/>)'
        ed.set(k, re.sub(anchor, lambda m: m.group(1) + f'\n{m.group(2)}<{tag} ObjectRef="{tid}"/>', b, count=1))
    tb = ed.block(tl.tracks[track]['key'])
    i = tb.index('<TransitionItems'); j = tb.index('</TransitionItems>', i); sect = tb[i:j]
    when = lambda r: int(txt(tl.ids[r], './/TrackItem/Start') or 0) if r in tl.ids else cut - half
    new, _ = _edit_list(sect, 'TrackItems', 'TrackItem', lambda refs: sorted(refs + [tid], key=lambda r: when(r)))
    if new is None:
        ind = re.search(r'\n(\t+)<MediaType>', sect).group(1); mt = sect.index(f'\n{ind}<MediaType>')
        new = sect[:mt] + f'\n{ind}<TrackItems Version="1">\n{ind}\t<TrackItem Index="0" ObjectRef="{tid}"/>\n{ind}</TrackItems>' + sect[mt:]
    ed.set(tl.tracks[track]['key'], tb[:i] + new + tb[j:])
    return ed.render(), tl.label(track), (L['name'], R['name']), cut, d


# ---------------------------------------------------------------- transcript comparison
FILLERS = {'uh', 'um', 'er', 'ah', 'eh', 'hmm', 'mm', 'uhm'}


def _norm_word(w):
    w = w.lower().replace('’', "'")
    w = re.sub(r"[^\w'$%]", '', w).strip("'")
    if w in FILLERS:
        return 'uh'
    return {'ok': 'okay'}.get(w, w)


EXPAND = {'gonna': ['going', 'to'], 'wanna': ['want', 'to'], 'gotta': ['got', 'to']}


def _expand(words):
    out = []
    for w in words:
        parts = EXPAND.get(_norm_word(w['w']))
        out += [dict(w, w=p) for p in parts] if parts else [w]
    return out


def read_srt_words(path):
    """Words of an SRT (or WebVTT) file, each timed by spreading its cue evenly."""
    txt_ = open(path, encoding='utf-8-sig').read().replace('\r', '')
    out = []
    for a, b, body in re.findall(r'(\d[\d:.,]+)\s*-->\s*(\d[\d:.,]+)[^\n]*\n(.*?)(?:\n\n|\Z)', txt_, re.S):
        def sec(s):
            p = s.replace(',', '.').split(':')
            return sum(float(x) * 60 ** i for i, x in enumerate(reversed(p)))
        t0, t1 = sec(a), sec(b)
        ws = [w for w in body.split() if re.search(r'\w', w)]
        for i, w in enumerate(ws):
            out.append({'t': t0 + (t1 - t0) * i / max(1, len(ws)), 'w': w})
    return out


def compare_words(hyp, ref, ignore_fillers=False):
    """Align two word lists (dicts with t, w) and classify every difference."""
    import difflib
    H = [w for w in _expand(hyp) if not (ignore_fillers and _norm_word(w['w']) == 'uh')]
    R = [w for w in _expand(ref) if not (ignore_fillers and _norm_word(w['w']) == 'uh')]
    hn, rn = [_norm_word(w['w']) for w in H], [_norm_word(w['w']) for w in R]
    sm = difflib.SequenceMatcher(a=rn, b=hn, autojunk=False)
    diffs, S, D, I = [], 0, 0, 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            continue
        r, h = R[i1:i2], H[j1:j2]
        kind = {'replace': 'changed', 'delete': 'missing', 'insert': 'extra'}[op]
        if op != 'insert' and all(_norm_word(w['w']) == 'uh' for w in r) and not h:
            kind = 'filler dropped'
        elif op == 'insert' and all(_norm_word(w['w']) == 'uh' for w in h):
            kind = 'filler added'
        t = (h[0]['t'] if h else r[0]['t'])
        diffs.append({'t': t, 'kind': kind, 'official': ' '.join(w['w'] for w in r), 'premiere': ' '.join(w['w'] for w in h)})
        if op == 'replace':
            S += min(len(r), len(h)); D += max(0, len(r) - len(h)); I += max(0, len(h) - len(r))
        elif op == 'delete':
            D += len(r)
        else:
            I += len(h)
    # timing: offset between matched words
    offs = [H[b + k]['t'] - R[a + k]['t'] for a, b, n in sm.get_matching_blocks() for k in range(n)]
    offs.sort()
    stats = {'ref_words': len(R), 'hyp_words': len(H), 'substitutions': S, 'deletions': D, 'insertions': I,
             'wer': round((S + D + I) / max(1, len(R)), 4),
             'median_offset_s': round(offs[len(offs) // 2], 3) if offs else None,
             'max_abs_offset_s': round(max(abs(o) for o in offs), 3) if offs else None}
    return diffs, stats


# ---------------------------------------------------------------- transcript writer
# Full model of the Speech-to-Text FlatBuffer (references/transcripts-and-captions.md §2)
# and a builder that writes it back. Byte layout differs from Premiere's builder; the
# content (every field, including unknown ones) is kept.
WORD_SLOTS = {0: 'i64', 1: 'i64', 2: 'str', 3: 'f32', 4: 'bool', 5: 'bool', 6: 'u32', 7: 'u32'}


def transcript_model(b):
    fb = FB(b)
    def guid(t):
        f = fb.fields(t)
        return b[t + f[0]:t + f[0] + 8] + b[t + f[1]:t + f[1] + 8]
    def string(a):
        return fb.s(fb.ref(a))
    root = fb.u32(0); rf = fb.fields(root); doc = fb.ref(root + rf[0]); df = fb.fields(doc)
    has = lambda f, k: len(f) > k and f[k]
    spk_vec = fb.ref(doc + df[2]) if has(df, 2) else None
    speakers = []
    for sp in (fb.vec(doc + df[2]) if has(df, 2) else []):
        sf = fb.fields(sp)
        speakers.append({'name': string(sp + sf[0]), 'id': guid(fb.ref(sp + sf[1]))})
    segs = []
    for sg in fb.vec(doc + df[0]):
        sf = fb.fields(sg)
        words = []
        for w in fb.vec(sg + sf[3]):
            wf = fb.fields(w); fields = {}
            for k, kind in WORD_SLOTS.items():
                if not has(wf, k):
                    continue
                a = w + wf[k]
                fields[k] = (fb.i64(a) if kind == 'i64' else string(a) if kind == 'str' else
                             struct.unpack_from('<f', b, a)[0] if kind == 'f32' else b[a] if kind == 'bool' else fb.u32(a))
            words.append(fields)
        segs.append({'start': fb.i64(sg + sf[0]), 'dur': fb.i64(sg + sf[1]),
                     'speaker': guid(fb.ref(sg + sf[2])) if has(sf, 2) else None, 'words': words,
                     'lang': string(sg + sf[4]) if has(sf, 4) else None})
    return {'segments': segs, 'language': string(doc + df[1]) if has(df, 1) else None, 'speakers': speakers,
            'doc_id': guid(fb.ref(doc + df[3])) if has(df, 3) else None,
            'f4': string(doc + df[4]) if has(df, 4) else None,
            'f5_same': has(df, 5) and spk_vec is not None and fb.ref(doc + df[5]) == spk_vec}


class _FBW:
    """Front-to-back FlatBuffer writer: an object's children are written after it, so
    every uoffset points forward; vtables sit just before their tables."""

    def __init__(self):
        self.b = bytearray(4); self.todo = []; self.done = {}; self.vtables = {}

    def pad(self, n):
        while len(self.b) % n:
            self.b.append(0)

    def table(self, fields):
        """fields: list of (slot, kind, value); kind i64/u64/f32/u32/bool or 'obj' (value = callable writing a child)."""
        size = {'i64': 8, 'u64': 8, 'f32': 4, 'u32': 4, 'obj': 4, 'bool': 1}
        order = sorted(fields, key=lambda f: -size[f[1]])
        offs, o = {}, 4
        for slot, kind, _v in order:
            offs[slot] = o; o += size[kind]
        objsize = (o + 3) // 4 * 4
        nslots = max(s for s, _k, _v in fields) + 1
        vt = [4 + 2 * nslots, objsize] + [offs.get(s, 0) for s in range(nslots)]
        vbytes = struct.pack('<%dH' % len(vt), *vt)
        vpos = self.vtables.get(vbytes)          # identical vtables are shared, as Premiere does
        if vpos is None:
            pad = (4 - (len(self.b) + len(vbytes))) % 8
            self.b += bytes(pad)
            vpos = len(self.b); self.b += vbytes; self.vtables[vbytes] = vpos
        else:
            self.b += bytes((4 - len(self.b)) % 8)
        t = len(self.b)
        self.b += struct.pack('<i', t - vpos) + bytes(objsize - 4)
        for slot, kind, v in fields:
            a = t + offs[slot]
            if kind in ('i64', 'u64'):
                struct.pack_into('<q' if kind == 'i64' else '<Q', self.b, a, v)
            elif kind == 'f32':
                struct.pack_into('<f', self.b, a, v)
            elif kind == 'u32':
                struct.pack_into('<I', self.b, a, v)
            elif kind == 'bool':
                self.b[a] = v
            else:
                self.todo.append((a, v))
        return t

    def string(self, s):
        self.pad(4); a = len(self.b); e = s.encode('utf-8')
        self.b += struct.pack('<I', len(e)) + e + b'\0'; self.pad(4)
        return a

    def vector(self, items):
        self.pad(4); a = len(self.b)
        self.b += struct.pack('<I', len(items)) + bytes(4 * len(items))
        for i, it in enumerate(items):
            self.todo.append((a + 4 + 4 * i, it))
        return a

    def run(self, root):
        self.todo.append((0, root))
        while self.todo:
            slot, make = self.todo.pop(0)
            key = getattr(make, 'key', None)
            if key is not None and key in self.done:
                pos = self.done[key]
            else:
                pos = make(self)
                if key is not None:
                    self.done[key] = pos
            struct.pack_into('<I', self.b, slot, pos - slot)
        self.pad(8)
        return bytes(self.b)


def transcript_build(m):
    def guid(g):
        return lambda w: w.table([(0, 'u64', struct.unpack('<Q', g[:8])[0]), (1, 'u64', struct.unpack('<Q', g[8:])[0])])
    def string(s):
        return lambda w: w.string(s)
    def word(f):
        out = []
        for k, v in sorted(f.items()):
            kind = WORD_SLOTS[k]
            out.append((k, 'obj', string(v)) if kind == 'str' else (k, kind, v))
        return lambda w: w.table(out)
    def segment(s):
        fs = [(0, 'i64', s['start']), (1, 'i64', s['dur'])]
        if s['speaker'] is not None: fs.append((2, 'obj', guid(s['speaker'])))
        fs.append((3, 'obj', lambda w: w.vector([word(x) for x in s['words']])))
        if s['lang'] is not None: fs.append((4, 'obj', string(s['lang'])))
        return lambda w: w.table(fs)
    def speaker(p):
        return lambda w: w.table([(0, 'obj', string(p['name'])), (1, 'obj', guid(p['id']))])
    spk = lambda w: w.vector([speaker(p) for p in m['speakers']])
    spk.key = 'speakers'
    doc = [(0, 'obj', lambda w: w.vector([segment(s) for s in m['segments']]))]
    if m['language'] is not None: doc.append((1, 'obj', string(m['language'])))
    if m['speakers']: doc.append((2, 'obj', spk))
    if m['doc_id'] is not None: doc.append((3, 'obj', guid(m['doc_id'])))
    if m['f4'] is not None: doc.append((4, 'obj', string(m['f4'])))
    if m['f5_same']: doc.append((5, 'obj', spk))
    return _FBW().run(lambda w: w.table([(0, 'obj', lambda w2: w2.table(doc))]))


def _transcript_doc(root, ids, index=0):
    docs = root.findall('ExternallyProvidedTranscriptDocument')
    if not docs:
        raise SystemExit('no embedded transcripts (Speech to Text not run on this project)')
    if not 0 <= index < len(docs):
        raise SystemExit(f"error: --index must be 0-{len(docs) - 1} (transcript --index -1 lists them)")
    return docs[index]


def rewrite_transcript(xml, index, edit):
    """Decode transcript `index`, apply edit(model) -> description, rebuild, write back."""
    root = ET.fromstring(xml)
    d = _transcript_doc(root, None, index)
    td = d.find('TranscriptData')
    old = base64.b64decode(td.text.strip())
    m = transcript_model(old)
    what = edit(m)
    new = transcript_build(m)
    if transcript_model(new) != m:
        raise SystemExit("error: internal check failed: the rebuilt transcript doesn't read back the same")
    # BinaryHash: last 8 hex digits are len + 12 (observed 110/110); the first 24 are a content
    # hash with an unknown algorithm, so use one derived from the content (derived, unverified)
    import hashlib
    h = hashlib.md5(new).hexdigest()[:24] + '%08x' % (len(new) + 12)
    hsh = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
    k = d.get('ObjectID')
    a, bb = block_span_any(xml, k)
    blk = xml[a:bb]
    blk = re.sub(r'(<TranscriptData Encoding="base64" BinaryHash=")[^"]+(">)[^<]*(</TranscriptData>)',
                 lambda mm: mm.group(1) + hsh + mm.group(2) + base64.b64encode(new).decode() + '\n\t\t' + mm.group(3), blk, count=1)
    return xml[:a] + blk + xml[bb:], what


def rename_speaker(m, old, new):
    hit = [p for p in m['speakers'] if p['name'] == old]
    if not hit:
        raise SystemExit(f"error: no speaker '{old}'. Speakers: {', '.join(p['name'] for p in m['speakers'])}")
    if any(p['name'] == new for p in m['speakers']):
        raise SystemExit(f"error: there's already a speaker called '{new}'")
    for p in hit:
        p['name'] = new
    return f"renamed speaker '{old}' to '{new}'"


def assign_speaker(m, at_ticks, name):
    sp = next((p for p in m['speakers'] if p['name'] == name), None)
    if sp is None:
        raise SystemExit(f"error: no speaker '{name}'. Speakers: {', '.join(p['name'] for p in m['speakers'])} "
                         "(add new speakers in Premiere; only existing ones can be assigned)")
    seg = next((s for s in m['segments'] if s['start'] <= at_ticks < s['start'] + s['dur']), None)
    if seg is None:
        raise SystemExit(f"error: no transcript segment at {ts(at_ticks / TICKS)}")
    seg['speaker'] = sp['id']
    return f"segment at {ts(seg['start'] / TICKS)} is now {name}"


# ---------------------------------------------------------------- diff
# ObjectIDs are renumbered on every save, so objects are matched by where they hang in
# the graph: an ObjectUID (stable across saves) or the path of references from Project,
# with list entries keyed by the child's name or ClipID instead of position.

DIFF_BLOB = re.compile(r'^[A-Za-z0-9+/=\s]{120,}$')


def _hint(e):
    """A short stable label for an object: its name or ClipID, if it has one."""
    for p in ('Name', 'ProjectItem/Name', 'Node/Properties/Name', 'ClipID', 'ID'):
        v = txt(e, p)
        if v:
            return v
    return None


def _ghint(e, ids):
    """_hint, plus track items labelled by their clip's ClipID (stable across saves and
    across a razor cut's left half), so inserting an item doesn't shift the others."""
    if e.tag == 'Link':
        ms = [_ghint(deref(ids, r), ids) for r in e.findall('.//TrackItems/TrackItem')
              if deref(ids, r) is not None]
        if ms and all(ms):
            return '+'.join(sorted(ms))
    if e.tag.endswith('ClipTrackItem'):
        sc = deref(ids, e.find('.//SubClip'))
        clip = deref(ids, sc.find('.//Clip')) if sc is not None else None
        cid = txt(clip, './/ClipID') if clip is not None else None
        if cid:
            return cid
    return _hint(e)


def _item_locations(root, ids):
    """{track item ObjectID: 'Sequence V1'}."""
    loc = {}
    for sq in sequences(root, ids):
        n = {'Video': 0, 'Audio': 0}
        for t in sq['tracks']:
            kind = 'Video' if t['type'].startswith('Video') else 'Audio'
            n[kind] += 1
            for it in t['items']:
                loc[it['item_id']] = f"{sq['name']} {kind[0]}{n[kind]}"
    return loc


def _item_desc(e, ids, loc=None):
    """'Seq V1: name 0:01.000-0:02.000' for a track item (or each member of a Link)."""
    if e.tag == 'Link':
        ms = [_item_desc(deref(ids, r), ids, loc) for r in e.findall('.//TrackItems/TrackItem')
              if deref(ids, r) is not None]
        return ' + '.join(m for m in ms if m) or None
    if not e.tag.endswith('ClipTrackItem'):
        return None
    where = (loc or {}).get(e.get('ObjectID'))
    st = int(txt(e, './/TrackItem/Start') or 0); en = int(txt(e, './/TrackItem/End') or 0)
    sc = deref(ids, e.find('.//SubClip'))
    return (f"{where}: " if where else '') + \
        f"{txt(sc, 'Name') if sc is not None else '?'} {ts(st / TICKS)}-{ts(en / TICKS)}"


def graph_keys(root, ids):
    """Stable key for every top-level object: the path of references that first reaches
    it from Project (breadth-first), list entries labelled by the child's name or
    ClipID where it has one. ObjectUIDs aren't used: Premiere can regenerate them
    (Save a Copy gives the root bin a new one)."""
    keys, todo, parent = {}, [], {}
    proj = next((e for e in root if e.tag == 'Project' and e.get('ObjectID')), None)
    if proj is not None:
        keys[proj.get('ObjectID')] = 'Project'
        todo.append(proj.get('ObjectID'))
    seen = set()
    while todo:
        k = todo.pop(0)
        if k in seen or k not in ids:
            continue
        seen.add(k)
        e = ids[k]
        if e.tag == 'Project':   # its view state uses a local ID scope; only follow real refs
            refs = [r for r in e.iter() if r.get('ObjectURef')] + \
                   [r for r in e if r.get('ObjectRef')]
        else:
            refs = [r for r in e.iter() if r.get('ObjectRef') or r.get('ObjectURef')]
        parents = {c: p for p in e.iter() for c in p}
        counts = {}
        for r in refs:
            t = r.get('ObjectRef') or r.get('ObjectURef')
            if t not in ids:
                continue
            chain, x = [], r
            while x is not e:
                chain.append(x.tag); x = parents[x]
            field = '/'.join(reversed(chain))
            n = counts[field] = counts.get(field, 0) + 1
            h = _ghint(ids[t], ids)
            label = f"{field}[{h}]" if h else f"{field}[{n - 1}]"
            if t not in keys:
                if h and (ids[t].tag.endswith('ClipTrackItem') or ids[t].tag == 'Link'):
                    keys[t] = f"{ids[t].tag}[{h}]"     # identity anchor: path-independent
                else:
                    keys[t] = f"{keys[k]}/{label}"
                parent[keys[t]] = keys[k]
            todo.append(t)
    n = 0
    for e in root:
        k = e.get('ObjectID') or e.get('ObjectUID')
        if k and k not in keys:
            keys[k] = f"(unreachable) {e.tag}[{_hint(e) or n}]"; n += 1
    keys[None] = parent
    return keys


def _flat(e, keys, out=None, path='', top=None):
    """{leaf path: value} for one object, with references replaced by stable keys.
    Refs nested inside Project (its view state) are local IDs and are shown as such."""
    out = {} if out is None else out
    top = e if top is None else top
    seen = {}
    for c in e:
        i = seen[c.tag] = seen.get(c.tag, 0) + 1
        p = f"{path}/{c.tag}" + (f"[{i}]" if i > 1 else '')
        ref = c.get('ObjectRef') or c.get('ObjectURef')
        if ref:
            local = top.tag == 'Project' and c.get('ObjectRef') and e is not top
            out[p] = ('local ' + ref) if local else ('-> ' + keys.get(ref, '?' + ref))
        for a, v in c.attrib.items():
            if a not in ('ObjectRef', 'ObjectURef', 'ObjectID', 'ObjectUID'):
                out[f"{p}@{a}"] = v
        if len(c):
            _flat(c, keys, out, p, top)
        elif not ref:
            out[p] = (c.text or '').strip()
    if e is top:
        for a, v in e.attrib.items():
            if a not in ('ObjectID', 'ObjectUID'):
                out['@' + a] = v
    return out


DIFF_NOISE = re.compile(r'AM\.Track|HSL\.TimelinePatching|MZ\.SourceTrack|MZ\.TrackTargeted|OpenSequenceGuidList|lastknown|TL\.SQ|MZ\.BuildVersion|ProjectViewState|MZ\.EditLine|Monitor\.(?!ProgramZoomOut)|PanelState|MZ\.Sequence\.PreviewFrame|ViewState|MZ\.ComponentChain\.Active')


def _display(key):
    """Short form of a key: names along the path (deduplicated), track and item
    positions, then the last field if it isn't named."""
    m = re.fullmatch(r'(\w*?)(ClipTrackItem|Link)\[([^\]]+)\]', key)
    if m:
        ids_ = [x[:8] for x in m.group(3).split('+')]
        return ('link ' if m.group(2) == 'Link' else 'item ') + '+'.join(ids_)
    if '/' not in key:
        return key
    out = []
    for seg in re.findall(r'([A-Za-z.]+)\[([^\]]+)\]', key):
        field, lab = seg
        if re.fullmatch(GUID_RE, lab):
            if field == 'TrackItem':
                out.append('item')
            continue
        if not lab.isdigit():
            if not out or out[-1] != lab:
                out.append(lab)
        elif field in ('Track', 'TrackItem', 'Clip'):
            out.append(f"{'item' if field == 'TrackItem' else field.lower()} {lab}")
    last = key.rsplit('/', 1)[-1]
    m = re.match(r'([A-Za-z.]+)\[([^\]]+)\]$', last)
    if m and re.fullmatch(GUID_RE, m.group(2)) and m.group(1) != 'TrackItem':
        m = None
    if not m or (m.group(2).isdigit() and m.group(1) not in ('Track', 'TrackItem', 'Clip')):
        out.append(re.sub(r'\[\d+\]$', '', last))
    return ' › '.join(out)


def _short(v, n=90):
    if v is None:
        return '(none)'
    if v.startswith('-> '):
        return '-> ' + _display(v[3:])
    if DIFF_BLOB.match(v):
        return f"<base64, {len(v)} chars>"
    v = v.replace('\n', ' ')
    return v if len(v) <= n else v[:n - 1] + '…'


def diff_projects(xa, xb, noise=False):
    ra, rb = ET.fromstring(xa), ET.fromstring(xb)
    ia, ib = index(ra), index(rb)
    ka, kb = graph_keys(ra, ia), graph_keys(rb, ib)
    pa, pb = ka.pop(None), kb.pop(None)
    la, lb = _item_locations(ra, ia), _item_locations(rb, ib)
    A = {ka[k]: ia[k] for k in ia}; B = {kb[k]: ib[k] for k in ib}
    # Moves: an object that disappears from one place and appears, same class and
    # name, somewhere else (a clip dragged into a bin). Re-key A's subtree to match B.
    moved = []
    for r in sorted(set(A) - set(B), key=len):
        if r not in A or pa.get(r) not in A or pa.get(r) is None or pa[r] in (set(A) - set(B)):
            continue
        h, tag, last = _hint(A[r]), A[r].tag, r.rsplit('/', 1)[-1]
        if not h:
            continue
        cand = [n for n in set(B) - set(A) if B[n].tag == tag and _hint(B[n]) == h
                and n.rsplit('/', 1)[-1] == last]
        if len(cand) != 1:
            continue
        n = cand[0]
        moved.append({'class': tag, 'name': h, 'from': _display(r), 'to': _display(n)})
        ren = {k: n + k[len(r):] for k in list(A) if k == r or k.startswith(r + '/')}
        A = {ren.get(k, k): v for k, v in A.items()}
        pa = {ren.get(k, k): ren.get(v, v) for k, v in pa.items()}
        for i in list(ka):
            if ka[i] in ren:
                ka[i] = ren[ka[i]]
    added = set(B) - set(A); removed = set(A) - set(B)
    changed = []
    for key in sorted(set(A) & set(B)):
        fa, fb = _flat(A[key], ka), _flat(B[key], kb)
        d = [(p, fa.get(p), fb.get(p)) for p in sorted(set(fa) | set(fb))
             if fa.get(p) != fb.get(p) and (noise or not DIFF_NOISE.search(p))]
        if d:
            changed.append({'key': key, 'where': _display(key), 'class': B[key].tag, 'fields': d,
                            'desc': _item_desc(B[key], ib, lb), 'was': _item_desc(A[key], ia, la)})

    def tops(keyset, objs, parents, oids, loc):
        out = []
        for k in sorted(keyset):
            if parents.get(k) in keyset:
                continue
            sub, todo = [], [k]
            while todo:
                x = todo.pop()
                kids = [c for c, p in parents.items() if p == x and c in keyset]
                sub += kids; todo += kids
            cls = {}
            for x in sub:
                cls[objs[x].tag] = cls.get(objs[x].tag, 0) + 1
            out.append({'key': k, 'where': _display(k), 'class': objs[k].tag, 'name': _hint(objs[k]),
                        'desc': _item_desc(objs[k], oids, loc),
                        'objects': 1 + len(sub), 'contains': dict(sorted(cls.items()))})
        return out
    return {'moved': moved, 'added': tops(added, B, pb, ib, lb), 'removed': tops(removed, A, pa, ia, la), 'changed': changed,
            'counts': {'a': len(A), 'b': len(B), 'added': len(added), 'removed': len(removed),
                       'moved': len(moved), 'changed': len(changed)}}


def print_diff(d, limit=12):
    c = d['counts']
    print(f"{c['a']} -> {c['b']} objects: {c['added']} added, {c['removed']} removed, "
          f"{c['moved']} moved, {c['changed']} changed")
    if d['moved']:
        print("\nMoved:")
    for m in d['moved']:
        print(f"  {m['class']}  {m['from']}  =>  {m['to']}")
    for title, rows in (('Added', d['added']), ('Removed', d['removed'])):
        if rows:
            print(f"\n{title}:")
        for r in rows:
            inner = ', '.join(f"{v} {k}" for k, v in r['contains'].items())
            print(f"  {r['class']}  {r['where']}" + (f"  [{r['desc']}]" if r.get('desc') else ''))
            if inner:
                print(f"      + {r['objects'] - 1} inside: {inner}")
    if d['changed']:
        print("\nChanged:")
    for ch in d['changed']:
        extra = ''
        if ch.get('desc'):
            extra = f"  [{ch['desc']}]" if ch['desc'] == ch['was'] else f"  [{ch['was']}  =>  {ch['desc']}]"
        print(f"  {ch['class']}  {ch['where']}{extra}")
        for p, va, vb in ch['fields'][:limit]:
            if va is None:
                print(f"      + {p} = {_short(vb)}")
            elif vb is None:
                print(f"      - {p} (was {_short(va)})")
            else:
                print(f"      ~ {p}: {_short(va)}  ->  {_short(vb)}")
        if len(ch['fields']) > limit:
            print(f"      … {len(ch['fields']) - limit} more (use --json)")


# Writes no Premiere-checked step proves yet. They stay in the code so a generated step can
# prove them (fixtures/premiere-pro/generated/BACKLOG.md); SKILL.md doesn't offer them.
UNPROVEN = {
    'set-label': 'no step shows Premiere changing a clip label',
    'set-transform': 'no step shows a changed Transform written by the scripts and opened in Premiere',
}


def unproven_reason(a):
    if a.cmd in UNPROVEN:
        return UNPROVEN[a.cmd]
    if a.cmd == 'add-transform' and any(p.lower() not in ('position', 'anchor', 'anchor-point') for p, _ in a.keys):
        return 'only Position and Anchor Point keyframes are proven (keys on scalar params like Scale or Rotation are not)'
    if a.cmd == 'delete' and not a.ripple:
        return 'no step shows a delete that leaves a gap (lift); only --ripple is proven'
    if a.cmd == 'place' and a.audio_only:
        return 'no step shows an audio-only placement'
    if a.cmd == 'add-marker' and str(a.colour).lower() not in MARKER_COLOURS:
        return f"only {' and '.join(MARKER_COLOURS)} marker colours have been seen in a step"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['unpack', 'pack', 'summary', 'cuts', 'transcript', 'cut-transcript',
                                    'srt-from-words', 'set-label', 'validate',
                                    'effects', 'add-transform', 'set-transform', 'backup-seq', 'diff',
                                    'split', 'trim', 'delete', 'markers', 'add-marker', 'set-track',
                                    'place', 'fade-in', 'fade-out', 'crossfade', 'compare-transcript',
                                    'speakers', 'rename-speaker', 'set-speaker'])
    ap.add_argument('file'); ap.add_argument('out', nargs='?')
    ap.add_argument('--seq'); ap.add_argument('--json', action='store_true')
    ap.add_argument('--srt', action='store_true'); ap.add_argument('--index', type=int, default=None)
    ap.add_argument('--item'); ap.add_argument('--at'); ap.add_argument('--label')
    ap.add_argument('--orig', help='original file, for validate')
    ap.add_argument('--track', type=int, help='track index as printed by cuts (VideoClipTrack[N])')
    ap.add_argument('--transform', type=int, default=None, help='which Transform in the stack (1-based)')
    ap.add_argument('--set', action='append', default=[], metavar='PARAM=VALUE')
    ap.add_argument('--keys', action='append', nargs=2, default=[], metavar=('PARAM', 'SPEC'))
    ap.add_argument('--clear', action='append', default=[], metavar='PARAM')
    ap.add_argument('--first', action='store_true', help='add-transform: put it at the top of the stack')
    ap.add_argument('--motion-blur', choices=['on', 'off'])
    ap.add_argument('--time-base', choices=['item', 'sequence'], default='item')
    ap.add_argument('--force', action='store_true',
                    help='allow keys outside the clip, a second Transform on one item, reversed clips')
    ap.add_argument('--name', help='backup-seq: name for the copy (default "SEQ (backup YYYY-MM-DD HHMM)")')
    ap.add_argument('--dry-run', action='store_true', help='write commands: validate and report, write nothing')
    ap.add_argument('--unproven', action='store_true',
                    help="allow a write that no Premiere-checked step proves yet (see UNPROVEN); you own the result")
    ap.add_argument('--all', action='store_true', help='diff: include view state and build stamps')
    ap.add_argument('--start', help='trim: new timeline start (seconds, 12f or 00:00:01:12)')
    ap.add_argument('--end', help='trim: new timeline end')
    ap.add_argument('--ripple', action='store_true', help='delete: close the gap on every track')
    ap.add_argument('--clip', help='place: the media clip name as it appears in the bin')
    ap.add_argument('--audio-track', type=int, help='place: audio track index (default: the first audio track)')
    ap.add_argument('--in', dest='src_in', help='place: source in point')
    ap.add_argument('--out', dest='src_out', help='place: source out point')
    ap.add_argument('--duration', help='place: length on the timeline (instead of --out); fade-in: fade length')
    ap.add_argument('--video-only', action='store_true', help='place: leave the audio out')
    ap.add_argument('--audio-only', action='store_true', help='place: leave the video out')
    ap.add_argument('--ref', help='compare-transcript: reference transcript (.srt/.vtt, or a words .json)')
    ap.add_argument('--ignore-fillers', action='store_true', help='compare-transcript: leave uh/um out of both sides')
    ap.add_argument('--markers', metavar='OUT', help='compare-transcript: write OUT with a sequence marker at each difference (needs --seq)')
    ap.add_argument('--from', dest='from_name', help='rename-speaker: current speaker name')
    ap.add_argument('--to', dest='to_name', help='rename-speaker: new speaker name')
    ap.add_argument('--speaker', help='set-speaker: name of an existing speaker')
    ap.add_argument('--chapters', action='store_true', help='markers: YouTube chapter lines from Chapter markers')
    ap.add_argument('--type', default='Comment', help='add-marker: Comment or Chapter')
    ap.add_argument('--comment', default='', help='add-marker: marker comment')
    ap.add_argument('--colour', '--color', default='orange', help='add-marker: orange, pink or #RRGGBB')
    ap.add_argument('--lock', choices=['on', 'off'], help='set-track: lock or unlock')
    ap.add_argument('--mute', choices=['on', 'off'], help='set-track: mute or unmute an audio track')
    a = ap.parse_args()
    why = unproven_reason(a)
    if why and not a.unproven:
        ap.error(f"{why}, so this isn't proven against Premiere yet. Do it in Premiere instead, or pass "
                 "--unproven to write it anyway and check the result in Premiere before relying on it")
    if a.cmd in ('unpack', 'pack', 'set-label', 'add-transform', 'set-transform', 'backup-seq',
                 'split', 'trim', 'delete', 'add-marker', 'set-track', 'place', 'fade-in', 'fade-out', 'crossfade',
                 'rename-speaker', 'set-speaker') and not a.out:
        ap.error(f'{a.cmd} needs an OUT path')
    if a.cmd in ('cut-transcript', 'set-label', 'effects', 'add-transform', 'set-transform', 'backup-seq',
                 'split', 'trim', 'delete', 'markers', 'add-marker', 'set-track', 'place', 'fade-in', 'fade-out', 'crossfade') and not a.seq:
        ap.error(f'{a.cmd} needs --seq NAME (run summary to list sequences)')
    if a.cmd == 'pack':
        open(a.out, 'wb').write(gzip.compress(open(a.file, 'rb').read())); return
    if a.cmd == 'srt-from-words':
        print(srt(sorted(json.load(open(a.file)), key=lambda w: w['t']))); return
    if a.cmd == 'diff':
        if not a.out: ap.error('diff needs two files: diff OLD NEW')
        d = diff_projects(load_xml(a.file), load_xml(a.out), noise=a.all)
        if a.json: print(json.dumps(d, indent=1)); return
        print_diff(d); return
    xml = load_xml(a.file)
    if a.cmd == 'unpack':
        open(a.out, 'w', encoding='utf-8').write(xml); return
    if a.cmd == 'validate':
        errs, warns = validate(xml, load_xml(a.orig) if a.orig else None)
        try:   # structure the evidence never showed (references/prproj-schema.json)
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import schema_dump
            warns += ['unseen: ' + w for w in schema_dump.unseen(ET.fromstring(xml))]
        except Exception as e:  # noqa: the catalogue is advisory
            warns.append(f'could not compare with prproj-schema.json: {e}')
        for w in warns: print('ok/warn:', w, file=sys.stderr)
        for e in errs: print('ERROR:', e)
        print('VALID' if not errs else f'INVALID ({len(errs)} errors)')
        sys.exit(1 if errs else 0)
    root = ET.fromstring(xml); ids = index(root)
    if a.cmd == 'summary':
        summary(root, ids)
    elif a.cmd == 'cuts':
        seqs = sequences(root, ids)
        if a.seq: seqs = [find_seq(seqs, a.seq)]
        for s in seqs:
            if a.json: print(json.dumps(s, indent=1)); continue
            print('==', s['name'])
            for i, t in enumerate(s['tracks']):
                if not t['items']: continue
                print(f"  {t['type']}[{i}]")
                for n, x in enumerate(t['items'], 1):
                    si = f"{ts(x['src_in'])}-{ts(x['src_out'])}" if x['src_in'] is not None else '-'
                    print(f"    #{n:<3} {ts(x['start'])}-{ts(x['end'])}  src {si}  {x['name']}  [{x['label']}]")
    elif a.cmd == 'transcript':
        trs = transcripts(xml, root, ids)
        if not trs: raise SystemExit('no embedded transcripts (Speech to Text not run on this project)')
        if a.index is not None and a.index < 0:
            for i, t in enumerate(trs): print(i, t['owner'], t['language'], len(t['segments']), 'segments,',
                                              'speakers:', ', '.join(t.get('speakers') or []) or '-')
            return
        tr = trs[a.index or 0]
        if a.json: print(json.dumps(tr, indent=1)); return
        for sg in tr['segments']:
            who = f"{sg['speaker']}: " if len(tr.get('speakers') or []) > 1 else ''
            print(f"[{ts(sg['start'])}] {who}" + ' '.join('(uh)' if w.get('kind') == 'filler' else w['w']
                                                     for w in sg['words'] if w['w'] or w.get('kind') == 'filler'))
    elif a.cmd == 'cut-transcript':
        seqs = sequences(root, ids)
        seq = find_seq(seqs, a.seq)
        trs = transcripts(xml, root, ids)
        if not trs: raise SystemExit('no embedded transcripts (Speech to Text not run on this project)')
        if a.index is not None:
            pick = trs[a.index]; words = map_to_sequence(pick, seq, seqs, None)
        else:
            words, pick = max(((map_to_sequence(t, seq, seqs, None), t) for t in trs), key=lambda x: len(x[0]))
        print(f"# transcript of '{pick['owner']}': {len(words)} words on '{seq['name']}'", file=sys.stderr)
        if a.json: print(json.dumps(words, indent=0)); return
        if a.srt: print(srt(words)); return
        line, last = [], None
        for w in words:
            if last is not None and w['t'] - last > 1.0:
                print(' '.join(line)); line = []
            if not line: line.append(f"[{ts(w['t'])}]")
            line.append(w['w']); last = w['t'] + w['d']
        if line: print(' '.join(line))
    elif a.cmd == 'set-label':
        seq = find_seq(sequences(root, ids), a.seq)
        if not a.label or not (a.item or a.at):
            ap.error('set-label needs --label and --item or --at')
        targets = []
        for v in (a.item or '').split(','):
            if v: targets += items_at(seq, idx=int(v), track=a.track)
        for v in (a.at or '').split(','):
            if v: targets += items_at(seq, when=float(v), track=a.track)
        oids = sorted({t['clip_id'] for t in targets if t['clip_id']}, key=int)
        new, n = set_label_text(xml, oids, label_index(a.label))
        ET.fromstring(new)  # sanity: still parses
        if a.dry_run:
            print(f"dry run: would label {n} clip objects {oids} as {a.label}; nothing written", file=sys.stderr); return
        open(a.out, 'wb').write(gzip.compress(new.encode('utf-8')))
        print(f"labeled {n} clip objects {oids} as {a.label} -> {a.out}")
        if n < len(oids):
            print(f"warning: {len(oids) - n} clip(s) have no <Node> properties block, so no label was added "
                  "to them; label those in Premiere", file=sys.stderr)
    elif a.cmd == 'speakers':
        trs = transcripts(xml, root, ids)
        if not trs: raise SystemExit('no embedded transcripts (Speech to Text not run on this project)')
        tr = trs[a.index or 0]
        if a.json: print(json.dumps([{'speaker': sg['speaker'], 'start': sg['start'], 'end': sg['start'] + sg['dur'],
                                       'text': ' '.join(w['w'] for w in sg['words'] if w['w'])} for sg in tr['segments']], indent=1)); return
        print(f"# {tr['owner']}: speakers {', '.join(tr.get('speakers') or [])}")
        for sg in tr['segments']:
            words = ' '.join(w['w'] for w in sg['words'] if w['w'])
            print(f"{ts(sg['start'])}-{ts(sg['start'] + sg['dur'])}  {sg['speaker'] or '-':<16} {words[:70]}{'…' if len(words) > 70 else ''}")
    elif a.cmd in ('rename-speaker', 'set-speaker'):
        if a.cmd == 'rename-speaker':
            if not a.from_name or a.to_name is None: ap.error('rename-speaker needs --from NAME --to NAME')
            new, what = rewrite_transcript(xml, a.index or 0, lambda m: rename_speaker(m, a.from_name, a.to_name))
        else:
            if a.at is None or not a.speaker: ap.error('set-speaker needs --at TIME (in the media clip) --speaker NAME')
            t = int(round(float(a.at) * TICKS)) if not re.search(r'[f:]', a.at) else parse_time(a.at, 10594584000)
            new, what = rewrite_transcript(xml, a.index or 0, lambda m: assign_speaker(m, t, a.speaker))
        errs, _w = validate(new, xml)
        if errs: raise SystemExit('refusing to write, validation failed: ' + '; '.join(errs))
        if a.dry_run:
            print(f"dry run: {what}; nothing written", file=sys.stderr); return
        open(a.out, 'wb').write(gzip.compress(new.encode('utf-8')))
        print(f"{what} -> {a.out}", file=sys.stderr)
    elif a.cmd == 'compare-transcript':
        if not a.ref: ap.error('compare-transcript needs --ref REFERENCE.srt')
        trs = transcripts(xml, root, ids)
        if not trs: raise SystemExit('no embedded transcripts (Speech to Text not run on this project)')
        tr = trs[a.index or 0]
        hyp = [dict(w, w='uh') if w.get('kind') == 'filler' else w
               for sg in tr['segments'] for w in sg['words'] if w['w'] or w.get('kind') == 'filler']
        ref = json.load(open(a.ref)) if a.ref.endswith('.json') else read_srt_words(a.ref)
        diffs, st = compare_words(hyp, ref, a.ignore_fillers)
        if a.markers:
            if not a.seq: ap.error('--markers needs --seq NAME (the sequence to mark)')
            seq = find_seq(sequences(root, ids), a.seq)
            spans = flatten(seq, tr['owner'], sequences(root, ids), None)
            new, n = xml, 0
            for d in diffs:
                at = next((d['t'] - mi + s0 for s0, e0, mi in spans if mi <= d['t'] < mi + (e0 - s0)), None)
                if at is None:
                    continue            # that part of the media isn't in the sequence
                label = f"{d['kind']}: " + (f"{d['official']} → {d['premiere']}" if d['official'] and d['premiere']
                                            else d['official'] or d['premiere'])
                note = f"official: {d['official'] or '(nothing)'} / Premiere: {d['premiere'] or '(nothing)'}"
                new, _t, _k = add_marker(new, a.seq, f"{at:.6f}", label, note, 'Comment',
                                         'pink' if 'filler' in d['kind'] else 'orange')
                n += 1
            errs, _w = validate(new, xml)
            if errs: raise SystemExit('refusing to write, validation failed: ' + '; '.join(errs))
            if a.dry_run:
                print(f"dry run: would add {n} markers to '{a.seq}'; nothing written", file=sys.stderr)
            else:
                open(a.markers, 'wb').write(gzip.compress(new.encode('utf-8')))
                print(f"added {n} markers to '{a.seq}' (orange: words, pink: fillers) -> {a.markers}", file=sys.stderr)
        if a.json: print(json.dumps({'stats': st, 'diffs': diffs}, indent=1)); return
        print(f"# Premiere ({tr['owner']}, {st['hyp_words']} words) vs {os.path.basename(a.ref)} ({st['ref_words']} words)")
        print(f"# WER {st['wer']:.1%}: {st['substitutions']} changed, {st['deletions']} missing, {st['insertions']} extra; "
              f"word timing offset median {st['median_offset_s']}s, max {st['max_abs_offset_s']}s")
        for d in diffs:
            print(f"{ts(d['t'])}  {d['kind']:<15} official: {d['official'] or '-':<28} premiere: {d['premiere'] or '-'}")
    elif a.cmd == 'markers':
        tl = Timeline(xml, a.seq)
        ms = read_markers(tl.root, tl.ids, tl.seq)
        if a.json: print(json.dumps(ms, indent=1)); return
        if a.chapters:
            lines = youtube_chapters(ms)
            if not lines: raise SystemExit('no Chapter markers in this sequence')
            if not lines[0].startswith('0:00 '):
                print("# note: YouTube needs the first chapter at 0:00", file=sys.stderr)
            print('\n'.join(lines)); return
        if not ms: print('no markers'); return
        for m in ms:
            print(f"{ts(m['time'])}  {m['type']:<8} {m['colour'] or '-':8} {m['name']}" + (f"  — {m['comment']}" if m['comment'] else '')
                  + (f"  ({m['duration']:.3f}s)" if m['duration'] else ''))
    elif a.cmd in ('add-marker', 'set-track', 'place', 'fade-in', 'fade-out', 'crossfade'):
        if a.cmd == 'place':
            if not a.clip or a.at is None: ap.error('place needs --clip NAME and --at TIME')
            new, hit, (s0, e0) = place_clip(xml, a.seq, a.clip, a.at, a.track, a.audio_track, a.src_in, a.src_out,
                                            a.duration, video=not a.audio_only, audio=not a.video_only)
            what = f"placed {a.clip} on {', '.join(t for t, _ in hit)} at {ts(s0 / TICKS)}-{ts(e0 / TICKS)}"
        elif a.cmd == 'crossfade':
            if a.track is None or a.item is None: ap.error('crossfade needs --track N --item N (the clip before the cut) [--duration TIME, default 2s]')
            new, lab, (ln, rn), cut, d = add_audio_crossfade(xml, a.seq, a.track, int(a.item), a.duration or '2')
            what = f"crossfaded {ln} into {rn} on {lab} at {ts(cut / TICKS)} over {d / TICKS:.3f}s"
        elif a.cmd in ('fade-in', 'fade-out'):
            if a.track is None or a.item is None or not a.duration: ap.error(f'{a.cmd} needs --track N --item N --duration TIME')
            new, lab, nm, d = add_audio_fade_in(xml, a.seq, a.track, int(a.item), a.duration, out=a.cmd == 'fade-out')
            what = f"faded {'out' if a.cmd == 'fade-out' else 'in'} {nm} on {lab} over {d / TICKS:.3f}s"
        elif a.cmd == 'add-marker':
            if a.at is None or a.name is None: ap.error('add-marker needs --at TIME and --name NAME')
            new, t, known = add_marker(xml, a.seq, a.at, a.name, a.comment, a.type, a.colour)
            what = f"added {a.type} marker {a.name!r} at {ts(t / TICKS)}"
            if not known:
                print("note: that colour isn't one seen in a Premiere save yet; Premiere may show it as the nearest swatch", file=sys.stderr)
        else:
            if a.name is None and a.lock is None and a.mute is None: ap.error('set-track needs --name, --lock or --mute')
            new, lab, done = set_track(xml, a.seq, a.track, a.name, None if a.lock is None else a.lock == 'on',
                                       None if a.mute is None else a.mute == 'on')
            what = f"{lab}: {', '.join(done)}"
        errs, _w = validate(new, xml)
        if errs: raise SystemExit('refusing to write, validation failed: ' + '; '.join(errs))
        if a.dry_run:
            print(f"dry run: would have {what}; nothing written", file=sys.stderr); return
        open(a.out, 'wb').write(gzip.compress(new.encode('utf-8')))
        print(f"{what} -> {a.out}", file=sys.stderr)
    elif a.cmd in ('split', 'trim', 'delete'):
        if a.cmd == 'split':
            if a.at is None: ap.error('split needs --at TIME (seconds, 12f or 00:00:04:23)')
            new, hit, at = split_items(xml, a.seq, a.at, a.track)
            what = f"split {', '.join(f'{n} on {t}' for t, n in hit)} at {ts(at / TICKS)}"
        else:
            if a.track is None or a.item is None: ap.error(f'{a.cmd} needs --track N --item N (from cuts)')
            try: n = int(a.item)
            except ValueError: ap.error('--item takes one number here')
            if a.cmd == 'trim':
                if a.start is None and a.end is None: ap.error('trim needs --start and/or --end')
                new, hit, (s0, e0) = trim_item(xml, a.seq, a.track, n, a.start, a.end)
                what = f"trimmed {', '.join(f'{n_} on {t}' for t, n_ in hit)} to {ts(s0 / TICKS)}-{ts(e0 / TICKS)}"
            else:
                new, hit, (s0, e0) = delete_item(xml, a.seq, a.track, n, ripple=a.ripple, force=a.force)
                what = (f"{'ripple-' if a.ripple else ''}deleted {', '.join(f'{n_} on {t}' for t, n_ in hit)} "
                        f"({ts(s0 / TICKS)}-{ts(e0 / TICKS)})")
        errs, _w = validate(new, xml)
        if errs: raise SystemExit('refusing to write, validation failed: ' + '; '.join(errs))
        if a.dry_run:
            print(f"dry run: would have {what}; nothing written", file=sys.stderr); return
        open(a.out, 'wb').write(gzip.compress(new.encode('utf-8')))
        print(f"{what} -> {a.out}", file=sys.stderr)
    elif a.cmd == 'backup-seq':
        name = a.name or f"{a.seq} (backup {datetime.datetime.now():%Y-%m-%d %H%M})"
        new, n = duplicate_sequence(xml, a.seq, name)
        errs, _w = validate(new, xml)
        if errs: raise SystemExit('refusing to write, validation failed: ' + '; '.join(errs))
        if a.dry_run:
            print(f"dry run: would duplicate '{a.seq}' as '{name}' ({n} objects); nothing written", file=sys.stderr); return
        open(a.out, 'wb').write(gzip.compress(new.encode('utf-8')))
        print(f"duplicated '{a.seq}' as '{name}' ({n} objects) -> {a.out}", file=sys.stderr)
    elif a.cmd == 'effects':
        seq = find_seq(sequences(root, ids), a.seq)
        rows = []
        for ti, t in enumerate(seq['tracks']):
            if a.track is not None and ti != a.track: continue
            if not t['items']: continue
            if not a.json: print(f"{t['type']}[{ti}]")
            for n, x in enumerate(t['items'], 1):
                if a.item and n != int(a.item): continue
                if a.json:
                    rows.append({'track': ti, 'track_type': t['type'], 'item': n, 'name': x['name'],
                                 'start_sec': x['start'], 'end_sec': x['end'], 'speed': x['speed'],
                                 **chain_json(root, ids, x)})
                    continue
                print(f"  #{n} {ts(x['start'])}-{ts(x['end'])}  {x['name']}  (item {x['item_id']})")
                for line in describe_chain(root, ids, x, seq.get('frame_ticks')): print(line)
        if a.json: print(json.dumps(rows, indent=1))
    elif a.cmd in ('add-transform', 'set-transform'):
        seq = find_seq(sequences(root, ids), a.seq)
        if a.track is None or not a.item:
            ap.error(f'{a.cmd} needs --track N and --item N (indices from cuts)')
        if not str(a.item).isdigit():
            ap.error('--item takes one number (from cuts)')
        t, it = pick_item(seq, a.track, int(a.item))
        if t['type'] != 'VideoClipTrack':
            raise SystemExit('error: Transform goes on video track items; that track is ' + t['type'])
        if it.get('speed', 1.0) <= 0 and a.keys and not a.force:
            raise SystemExit('error: reversed clip (negative speed); keyframe mapping for that is unverified. '
                             'Use --force to proceed.')
        kinds = {p[0]: p[4] for p in TRANSFORM_PARAMS}
        sets = {}
        def check_param(k):
            if k not in kinds:
                raise SystemExit(f"error: unknown Transform param '{k}'. Options: {', '.join(TKEYS)}")
        for kv in a.set:
            if '=' not in kv:
                raise SystemExit(f"error: --set takes PARAM=VALUE, got '{kv}'")
            k, v = kv.split('=', 1); check_param(k)
            sets[k] = parse_value(kinds[k], v)
        if a.motion_blur:
            sets['use-comp-shutter'] = (a.motion_blur == 'off')
        new = xml
        if a.cmd == 'add-transform':
            have = transforms_of(root, ids, it['chain_id'])
            if have and not a.force:
                raise SystemExit(f"error: that item already has {len(have)} Transform(s); change it with set-transform "
                                 "(--transform K), or pass --force to stack another one")
            new, fid = add_transform(new, it['chain_id'], sets, first=a.first)
            done = [f"added Transform (object {fid}) to item #{a.item} on track {a.track}"]
        else:
            done = []
            trs = transforms_of(root, ids, it['chain_id'])
            if not trs: raise SystemExit('error: that item has no Transform; use add-transform')
            if a.transform is None and len(trs) > 1:
                raise SystemExit(f'error: item has {len(trs)} Transforms; pick one with --transform N (1 = top)')
            if a.transform is not None and not 1 <= a.transform <= len(trs):
                raise SystemExit(f'error: item has {len(trs)} Transform(s); --transform must be 1-{len(trs)}')
            fid = trs[(a.transform or 1) - 1].get('ObjectID')
            pids = [p.get('ObjectID') for p in param_objects(ids, ids[fid])]
            for k, v in sets.items():
                if txt(ids[pids[TKEYS.index(k)]], 'IsTimeVarying') == 'true' and k not in dict(a.keys):
                    print(f"warning: '{k}' was animated; --set replaces its keyframes with one static value", file=sys.stderr)
                new = set_static(new, pids[TKEYS.index(k)], kinds[k], v)
        # keyframes / clears apply to the (possibly new) Transform
        r2 = ET.fromstring(new); ids2 = index(r2)
        pids = [p.get('ObjectID') for p in param_objects(ids2, ids2[str(fid)])]
        for k in a.clear:
            check_param(k)
            p = ids2[pids[TKEYS.index(k)]]
            cur = parse_value(kinds[k], (txt(p, 'StartKeyframe') or '').split(',')[1])
            new = set_static(new, pids[TKEYS.index(k)], kinds[k], cur)
        for k, spec in a.keys:
            check_param(k)
            if kinds[k] in ('bool', 'enum'):
                raise SystemExit(f"error: '{k}' is a {kinds[k]} param; keyframing it isn't supported (set it with --set)")
            if kinds[k] != 'point':
                print(f"warning: keyframes on scalar Transform params ('{k}') follow the observed scalar "
                      "format but are not yet confirmed in Premiere; check the result there.", file=sys.stderr)
            keys = parse_keys(spec, kinds[k], it, seq.get('frame_ticks'), a.time_base, a.force)
            new = set_keyframes(new, pids[TKEYS.index(k)], kinds[k], keys)
            done.append(f"{k}: {len(keys)} keyframes at " + ', '.join(ts(it['start'] + (k0 - it['in_ticks']) / it.get('speed', 1.0) / TICKS) for k0, _, _ in keys))
        errs, _w = validate(new, xml)
        if errs: raise SystemExit('refusing to write, validation failed: ' + '; '.join(errs))
        if a.dry_run:
            for line in done: print('dry run: would have ' + line if line.startswith('added') else 'dry run: ' + line, file=sys.stderr)
            print(f"dry run: valid; nothing written ({len(new) - len(xml):+d} bytes of XML)", file=sys.stderr)
            return
        open(a.out, 'wb').write(gzip.compress(new.encode('utf-8')))
        for line in done: print(line, file=sys.stderr)
        print(f"wrote {a.out}", file=sys.stderr)


if __name__ == '__main__':
    try:
        main()
    except BrokenPipeError:  # output piped into head etc.: exit quietly
        import os
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
