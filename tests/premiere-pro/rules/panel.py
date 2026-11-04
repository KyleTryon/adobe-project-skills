"""Checks for references/spec/06-project-panel.md."""
from _lib import rule, expect, P

ITEM_TAGS = ('ClipProjectItem', 'BinProjectItem', 'FileProjectItem')
FILE_PI_CID = 'b28f14fe-793f-45be-bb28-fb82644995f4'


def bins(s):
    return s.objs('RootProjectItem') + s.objs('BinProjectItem')


def items_of(b):
    return b.findall('ProjectItemContainer/Items/Item')


def file_media(s):
    """Media of imported files (not the synthetic transcript Media)."""
    return [m for m in s.objs('Media') if m.find('VideoStream') is not None or m.find('AudioStream') is not None]


def clips_of(s, mc):
    return [s.ref(c) for c in mc.findall('Clips/Clip')]


def is_sequence_mc(s, mc):
    srcs = [s.ref(c, 'Clip/Source') for c in clips_of(s, mc) if c.tag in ('VideoClip', 'AudioClip')]
    return bool(srcs) and all(x is not None and x.tag.endswith('SequenceSource') for x in srcs)


@rule('panel.tree')
def _(ev):
    for s in ev.steps:
        n = 0
        for b in bins(s):
            expect(b.find('ProjectItemContainer') is not None, f'{s}: a bin has no ProjectItemContainer')
            for it in items_of(b):
                expect(it.get('ObjectURef') and not it.get('ObjectRef'), f'{s}: an Items entry is not an ObjectURef')
                tgt = s.ref(it)
                expect(tgt is not None and tgt.tag in ITEM_TAGS, f'{s}: an Items entry points at {tgt.tag if tgt is not None else None}')
                n += 1
        expect(n, f'{s}: no bin lists any items')
        bin_keys = {b.get('ObjectUID') for b in bins(s)}
        for tag in ITEM_TAGS:
            for e in s.objs(tag):
                own = {x for c in e for x in c.iter()} - ({x for x in e.find('ProjectItemContainer').iter()} if e.find('ProjectItemContainer') is not None else set())
                expect(not any(x.get('ObjectURef') in bin_keys or x.get('ObjectRef') in bin_keys for x in own), f'{s}: a {tag} points at a bin')


@rule('panel.clip-item-once')
def _(ev):
    for s in ev.steps:
        listed = [it.get('ObjectURef') for b in bins(s) for it in items_of(b)]
        cpis = [e.get('ObjectUID') for e in s.objs('ClipProjectItem')]
        expect(cpis, f'{s}: no ClipProjectItems')
        bad = [k for k in cpis if listed.count(k) != 1]
        expect(not bad, f'{s}: {len(bad)} ClipProjectItem(s) not listed exactly once')


@rule('panel.empty-bin-no-items')
def _(ev):
    for s in ev.steps:
        empty = [b for b in bins(s) if not items_of(b)]
        expect(empty, f'{s}: no empty bin')
        for b in empty:
            expect(b.find('ProjectItemContainer/Items') is None, f'{s}: an empty bin has an Items element')


@rule('panel.move-item')
def _(ev):
    for a, b in ev.pairs:
        d = P.diff_projects(a.xml, b.xml)
        expect(d['moved'] and all(m['class'] == 'ClipProjectItem' for m in d['moved']), f'{a}→{b}: no ClipProjectItem moved')
        moved = {m['name'] for m in d['moved']}
        expect(not d['removed'] and all(x['class'] == 'BinProjectItem' for x in d['added']), f'{a}→{b}: objects other than the new bin added or removed')
        for c in d['changed']:
            if c['class'] in ('RootProjectItem', 'BinProjectItem'):
                expect(all(f[0].startswith('/ProjectItemContainer/Items/') for f in c['fields']), f'{c["where"]}: changed outside Items')
                continue
            expect(c['class'] in ('ClipProjectItem', 'FileProjectItem'), f'{a}→{b}: {c["class"]} changed')
            expect(all(f[0] == '/ProjectItem/Node/Properties/project.icon.view.grid.order' for f in c['fields']), f'{c["where"]}: changed beyond grid order')
            name = c['where'].split(' › ')[-1]
            if name in moved:
                expect(all(f[2] is None for f in c['fields']), f'{name}: moved item kept its grid order')
            else:
                expect(all(f[1] is not None and f[2] is not None for f in c['fields']), f'{name}: grid order not rewritten')


@rule('panel.sequence-item')
def _(ev):
    for s in ev.steps:
        seq_names = {P.txt(e, 'Name') for e in s.objs('Sequence')}
        found = 0
        for cpi in s.objs('ClipProjectItem'):
            mc = s.ref(cpi, 'MasterClip')
            seq = is_sequence_mc(s, mc)
            expect(seq == (P.txt(cpi, 'ProjectItem/Name') in seq_names), f'{s}: {P.txt(cpi, "ProjectItem/Name")} sequence-ness disagrees with its sources')
            found += seq
            fields = sorted({x.tag for x in cpi.iter()} - {'project.icon.view.grid.order'})
            expect(fields == sorted(['ClipProjectItem', 'ProjectItem', 'Node', 'Properties', 'Column.PropertyText.Label', 'Name', 'MasterClip']),
                   f'{s}: ClipProjectItem has fields {fields}')
        expect(found, f'{s}: no sequence item')


@rule('panel.file-project-item')
def _(ev):
    for a, b in ev.pairs:
        expect(not a.objs('FileProjectItem'), f'{a} already has a FileProjectItem')
        fs = b.objs('FileProjectItem')
        expect(len(fs) == 1, f'{b}: {len(fs)} FileProjectItems')
        f = fs[0]
        expect(f.get('ObjectUID') and f.get('ClassID') == FILE_PI_CID, f'{b}: FileProjectItem identity {f.attrib}')
        expect(P.txt(f, 'ProjectItem/Node/Properties/Column.PropertyText.Label') == 'BE.Prefs.LabelColors.Unknown', 'label')
        expect(P.txt(f, 'ProjectItem/Name').endswith('.txt') and P.txt(f, 'FullPath').startswith('/'), 'name/FullPath')
        expect(sorted(c.tag for c in f) == ['FullPath', 'ProjectItem'], f'children {[c.tag for c in f]}')
        expect(not any(x.get('ObjectRef') or x.get('ObjectURef') for x in f.iter()), 'it references other objects')


@rule('panel.masterclip-clips-order')
def _(ev):
    for s in ev.steps:
        for mc in s.objs('MasterClip'):
            tags = [c.tag for c in clips_of(s, mc)]
            core = [t for t in tags if t != 'TranscriptClip']
            expect(tags[len(core):] == ['TranscriptClip'] * (len(tags) - len(core)), f'{s}: TranscriptClip not last: {tags}')
            if is_sequence_mc(s, mc):
                expect(core == ['AudioClip', 'VideoClip'], f'{s}: sequence MasterClip clips {tags}')
            else:
                expect(core in (['VideoClip', 'AudioClip'], ['VideoClip'], ['AudioClip']), f'{s}: media MasterClip clips {tags}')


@rule('panel.clone-shares-masterclips')
def _(ev):
    for s in ev.steps:
        mcs = [mc for mc in s.objs('MasterClip') if not is_sequence_mc(s, mc)]
        listed = {s.ref(c, 'MasterClip').get('ObjectUID') for c in s.objs('ClipProjectItem')}
        expect(all(mc.get('ObjectUID') in listed for mc in mcs), f'{s}: a media MasterClip has no project item (copied?)')
        names = [P.txt(mc, 'Name') for mc in mcs]
        expect(len(names) == len(set(names)), f'{s}: a media MasterClip appears twice')
        used = {}
        for sq in s.seqs:
            used[sq['name']] = {s.ref(s.ref(s.ids[i['item_id']], './/SubClip'), 'MasterClip').get('ObjectUID')
                                for t in sq['tracks'] for i in t['items'] if i['src_in'] is not None and i['name'] not in {x['name'] for x in s.seqs}}
        media_mcs = {mc.get('ObjectUID') for mc in mcs}
        users = [n for n, u in used.items() if u and u <= media_mcs]
        expect(len(users) >= 2, f'{s}: fewer than two sequences use the shared media MasterClips ({users})')


@rule('panel.media-one-file')
def _(ev):
    for s in ev.steps:
        ms = file_media(s)
        expect(ms and all(m.get('ObjectUID') for m in ms), f'{s}: no file Media with ObjectUID')
        paths = [P.txt(m, 'FilePath') for m in ms]
        expect(len(paths) == len(set(paths)), f'{s}: two Media for one file')


@rule('panel.media-paths')
def _(ev):
    for s in ev.steps:
        ms = file_media(s)
        expect(ms, f'{s}: no file Media')
        for m in ms:
            fp = P.txt(m, 'FilePath')
            expect(P.txt(m, 'ActualMediaFilePath') == fp and fp.startswith('/'), f'{s}: ActualMediaFilePath/FilePath {fp}')
            rp = P.txt(m, 'RelativePath')
            expect(rp and rp.split('/')[-1] == fp.split('/')[-1], f'{s}: RelativePath {rp} for {fp}')


@rule('panel.relative-path')
def _(ev):
    for a, b in ev.pairs:
        ma = {P.txt(m, 'FilePath'): P.txt(m, 'RelativePath') for m in file_media(a)}
        mb = {P.txt(m, 'FilePath'): P.txt(m, 'RelativePath') for m in file_media(b)}
        expect(ma and set(ma) == set(mb), f'{a}→{b}: absolute paths changed')
        pre = lambda d: {v.rsplit('/', 1)[0] for v in d.values()}
        expect(pre(ma) != pre(mb), f'{a}→{b}: RelativePath did not change')
        for d, st in ((ma, a), (mb, b)):
            want = '../media' if st.n != '04' else './media'
            expect(pre(d) == {want}, f'{st}: RelativePath folder {pre(d)}, want {want} (step 04 was saved one folder up)')


@rule('panel.media-probe-caches')
def _(ev):
    for s in ev.steps:
        ms = file_media(s)
        expect(ms, f'{s}: no file Media')
        for m in ms:
            for k in ('ModificationState', 'ContentAndMetadataState', 'CCFileModTime'):
                expect(m.find(k) is not None, f'{s}: Media without {k}')
            if m.find('AudioStream') is not None:
                a = s.ref(m, 'AudioStream')
                expect(P.txt(a, 'ConformedAudioPath') and P.txt(a, 'PeakFilePath'), f'{s}: AudioStream without cache paths')


@rule('panel.streams')
def _(ev):
    for s in ev.steps:
        vs, aus = s.objs('VideoStream'), s.objs('AudioStream')
        expect(vs and aus, f'{s}: no streams')
        for v in vs:
            for k in ('Duration', 'FrameRate', 'FrameRect', 'CodecType'):
                expect(v.find(k) is not None, f'{s}: VideoStream without {k}')
        expect(any(v.find('AlphaType') is not None for v in vs), f'{s}: no VideoStream records alpha')
        for a in aus:
            for k in ('Duration', 'AudioChannelLayout', 'ConformedAudioPath', 'PeakFilePath'):
                expect(a.find(k) is not None, f'{s}: AudioStream without {k}')


@rule('panel.data-stream')
def _(ev):
    for s in ev.steps:
        ds = s.objs('DataStream')
        expect(ds, f'{s}: no DataStream')
        for d in ds:
            owners = [m for m in s.referrers(d) if m.tag == 'Media']
            expect(len(owners) == 1 and owners[0].find('VideoStream') is None, f'{s}: DataStream not on a transcript Media')
        expect(len(ds) == len(s.objs('ExternallyProvidedTranscriptDocument')), f'{s}: DataStreams vs transcripts')


@rule('panel.sources-original-duration')
def _(ev):
    differs = 0
    for s in ev.steps:
        for tag in ('VideoMediaSource', 'AudioMediaSource', 'VideoSequenceSource', 'AudioSequenceSource'):
            objs = s.objs(tag)
            expect(objs, f'{s}: no {tag}')
            expect(all(o.find('OriginalDuration') is not None for o in objs), f'{s}: a {tag} without OriginalDuration')
        for src in s.objs('VideoSequenceSource'):
            seq = s.ref(src, 'SequenceSource/Sequence')
            sq = s.seq(P.txt(seq, 'Name'))
            length = max((i['end_ticks'] for t in sq['tracks'] for i in t['items']), default=0)
            differs += int(P.txt(src, 'OriginalDuration')) != length
    expect(differs, 'no sequence source whose OriginalDuration differs from its length')


def _chain_size(d, name):
    return next(a['objects'] for a in d['added'] if a['name'] == name)


@rule('panel.import')
def _(ev):
    for a, b in ev.pairs:
        d = P.diff_projects(a.xml, b.xml, noise=True)
        expect(not d['removed'] and not d['moved'], f'{a}→{b}: objects removed or moved')
        expect({c['class'] for c in d['changed']} <= {'RootProjectItem', 'Project'}, f'{a}→{b}: changed {[c["class"] for c in d["changed"]]}')
        expect(all(x['class'] in ('ClipProjectItem', 'FileProjectItem') for x in d['added']), 'added something that is not an imported item')
        sizes = {}
        for cpi in b.objs('ClipProjectItem'):
            mc = b.ref(cpi, 'MasterClip')
            kinds = tuple(sorted(c.tag for c in clips_of(b, mc)))
            sizes.setdefault(kinds, set()).add(_chain_size(d, P.txt(cpi, 'ProjectItem/Name')))
            expect(mc.find('Node/ID') is None, f'{b}: an imported MasterClip has a Node ID')
            for c in clips_of(b, mc):
                mk = b.ref(c, 'Clip/MarkerOwner/Markers')
                expect(mk is not None and mk.find('Markers') is None, f'{b}: an imported clip has no empty Markers')
        expect(sizes == {('AudioClip', 'VideoClip'): {18}, ('VideoClip',): {9}, ('AudioClip',): {15}}, f'{b}: chain sizes {sizes}')
