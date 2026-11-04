"""Checks for references/spec/17-load-and-save.md (save.*)."""
import os, re
from _lib import rule, expect, P

VIEW = {'playhead': r'MZ\.EditLine', 'zoom and scroll': r'TL\.SQ', 'track targeting': r'MZ\.TrackTargeted',
        'patching': r'HSL\.TimelinePatching|MZ\.SourceTrack', 'track heights': r'TL\.SQTrackExpandedHeight|AM\.Track',
        'active Effect Controls component': r'MZ\.ComponentChain\.Active'}
PROJ_PATH = 'Node/Properties/project.settings.lastknowngoodprojectpath'


def uids(s):
    return {e.get('ObjectUID'): e.tag for e in s.root if e.get('ObjectUID')}


def clip_ids(s):
    return set(re.findall(r'<ClipID>([^<]+)</ClipID>', s.xml))


def file_keys(s):
    return set(re.findall(r'<FileKey>([^<]+)</FileKey>', s.xml))


def node_ids(s):
    return {n.find('ID').text for n in s.root.iter('Node') if n.find('ID') is not None}


def by_clip_id(s):
    out = {}
    for e in s.root:
        c = e.find('.//Clip/ClipID')
        if c is not None and e.get('ObjectID'):
            out[c.text] = e.get('ObjectID')
    return out


def project(s):
    return next(e for e in s.root if e.tag == 'Project' and e.get('ObjectID'))


def consecutive(ev):
    st = ev.steps
    expect(len(st) > 1, 'cite a run of successive saves')
    return list(zip(st, st[1:]))


@rule('save.renumbers')
def _(ev):
    for a, b in ev.pairs:
        ma, mb = by_clip_id(a), by_clip_id(b)
        moved = [k for k in ma if k in mb and ma[k] != mb[k]]
        expect(moved, f'no object kept its ClipID under a new ObjectID from {a} to {b}')
        expect([e.tag for e in a.root] != [e.tag for e in b.root], f'object order unchanged from {a} to {b}')


@rule('save.stable-identities')
def _(ev):
    for a, b in ev.pairs:
        ua, ub = uids(a), uids(b)
        lost = [t for u, t in ua.items() if u not in ub]
        expect(lost == ['RootProjectItem'], f'{a}→{b}: ObjectUIDs lost {lost}')
        for name, f in (('ClipID', clip_ids), ('FileKey', file_keys), ('Node ID', node_ids)):
            gone = f(a) - f(b)
            expect(not gone, f'{a}→{b}: {len(gone)} {name}s lost')


@rule('save.media-uids-renewed')
def _(ev):
    for a, b in ev.pairs:
        ma = {u for u, t in uids(a).items() if t == 'Media'}; mb = {u for u, t in uids(b).items() if t == 'Media'}
        expect(len(ma) == len(mb) and ma and not (ma & mb), f'{a}→{b}: {len(ma & mb)} of {len(ma)} Media kept their ObjectUID')


@rule('save.rewrites-paths-and-view-state')
def _(ev):
    seen = set()
    for a, b in consecutive(ev):
        pa, pb = P.txt(project(a), PROJ_PATH), P.txt(project(b), PROJ_PATH)
        expect(pa != pb and pb.endswith('.prproj'), f'{a}→{b}: project path not rewritten ({pb})')
        d = P.diff_projects(a.xml, b.xml, noise=True)
        quiet = P.diff_projects(a.xml, b.xml)
        paths = [f[0] for ch in d['changed'] for f in ch['fields']]
        shown = [f[0] for ch in quiet['changed'] for f in ch['fields']]
        for k, rx in VIEW.items():
            if any(re.search(rx, p) for p in paths):
                seen.add(k)
            expect(not any(re.search(rx, p) for p in shown), f'{a}→{b}: prproj.py diff shows {k} without --all')
        expect(not any('lastknown' in p for p in shown), f'{a}→{b}: diff shows the project path without --all')
    expect(seen == set(VIEW), f'view state never changed in the evidence: {sorted(set(VIEW) - seen)}')
    # Save a Copy writes the copy's own location; step 04 was saved one folder up, which rewrote every RelativePath
    nmed = 0
    for s in ev.steps:
        d = os.path.basename(os.path.dirname(P.txt(project(s), PROJ_PATH)))
        rel = set(re.findall(r'<RelativePath>([^<]*)</RelativePath>', s.xml))
        want_dir, want_rel = ('premiere-pro', './') if s.n == '04' else ('steps', '../')
        expect(d == want_dir, f'{s}: saved in {d}, expected {want_dir}')
        expect(all(r.startswith(want_rel + 'media/') for r in rel), f'{s}: RelativePaths {sorted(rel)[:2]}')
        nmed += bool(rel)
    expect(nmed > 1 and any(s.n == '04' for s in ev.steps), 'evidence needs step 04 and other steps with media')


@rule('save.script-file-resave')
def _(ev):
    for a, b in ev.pairs:
        expect(a.generated and not b.generated, f'{a}→{b} is not a Premiere save of a script-written file')
        va = {P.txt(m, 'Name'): int(P.txt(m, './/MasterClipChangeVersion') or -1) for m in a.objs('MasterClip')}
        vb = {P.txt(m, 'Name'): int(P.txt(m, './/MasterClipChangeVersion') or -1) for m in b.objs('MasterClip')}
        common = set(va) & set(vb)
        expect(common and all(vb[k] > va[k] for k in common), f'{a}→{b}: not every MasterClipChangeVersion went up')
        ka = len(re.findall(r'list\.view\.expanded\.state\.', a.xml)); kb = len(re.findall(r'list\.view\.expanded\.state\.', b.xml))
        expect(kb > ka, f'{a}→{b}: no bin expanded-state keys added ({ka}→{kb})')


@rule('save.media-history-added')
def _(ev):
    for a, b in ev.pairs:
        expect('MediaFileHistory0' not in a.xml and not [c for c in a.objs('VideoClip') if c.find('Clip/PlaybackSpeed') is not None], f'{a} already has them')
        meds = [m for m in b.objs('Media') if P.txt(m, 'FilePath') and '/' in P.txt(m, 'FilePath')]
        expect(meds and all(P.txt(m, 'MediaFileHistory0') == P.txt(m, 'FilePath') for m in meds), f'{b}: MediaFileHistory0 missing or not the path')
        ps = [c for c in b.objs('VideoClip') if c.find('Clip/PlaybackSpeed') is not None]
        expect(ps and all(P.txt(c, 'Clip/PlaybackSpeed') == '1' for c in ps), f'{b}: Clip/PlaybackSpeed 1 not added')
        expect('ChannelIndexToTranscribe' not in a.xml and '<BE.MasterClip.ChannelIndexToTranscribe>-1<' in b.xml, f'{b}: ChannelIndexToTranscribe -1 not added')
