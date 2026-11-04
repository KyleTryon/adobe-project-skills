"""Helpers shared by document.py and graph.py (objects, references, Node IDs)."""
import collections, re
from _lib import P

UID_CLASSES = {'Sequence', 'Media', 'MasterClip', 'RootProjectItem', 'BinProjectItem', 'ClipProjectItem',
               'FileProjectItem', 'VideoClipTrack', 'AudioClipTrack'}
LOCAL = 'Node/Properties/ProjectViewState.List'
V4 = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
PER_TYPE_CLASSIDS = {'VideoComponentParam', 'AudioComponentParam'}     # one ClassID per value type (§12.2)


def objects(s):
    return list(s.root)[1:]


def project(s):
    return next(e for e in s.root if e.tag == 'Project' and e.get('ObjectID'))


def local(s):
    lst = project(s).find(LOCAL)
    return set(lst.iter()) if lst is not None else set()


def key(e):
    return e.get('ObjectID') or e.get('ObjectUID')


def refmap(s):
    """key -> [referring top-level object], references inside Project's local scope skipped."""
    loc, m = local(s), collections.defaultdict(list)
    for e in objects(s):
        for x in e.iter():
            if x in loc:
                continue
            k = x.get('ObjectRef') or x.get('ObjectURef')
            if k and s.ids.get(k) is not e:
                m[k].append(e)
    return m


def node_ids(s):
    """{object: Node/ID} for every object that has one (MasterClip Node/ID, RootProjectItem ProjectItem/Node/ID, ...)."""
    out = {}
    for e in objects(s):
        for path in ('Node/ID', 'ProjectItem/Node/ID'):
            v = P.txt(e, path)
            if v:
                out[e] = int(v)
    return out


def is_sequence_masterclip(s, mc):
    srcs = [s.ref(c, 'Clip/Source') for c in (s.ref(x) for x in mc.findall('Clips/Clip')) if c is not None]
    return bool(srcs) and all(x is not None and x.tag.endswith('SequenceSource') for x in srcs)
