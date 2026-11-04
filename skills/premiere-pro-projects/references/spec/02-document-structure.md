# 2. Document structure

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

## 2.1 Objects

1. Every **direct child** of `<PremiereData>` is an *object*, except the first, the pointer `<Project ObjectRef="1"/>` [O: steps 00–23 #doc.top-level-objects].
2. Identity is one attribute, fixed per class [O: steps 00–23 #doc.identity-attribute]: `ObjectUID="guid"` (referenced by `ObjectURef`) on `Sequence`, `Media`, `MasterClip`, `RootProjectItem`, `BinProjectItem`, `ClipProjectItem`, `FileProjectItem`, `VideoClipTrack`, `AudioClipTrack`; `ObjectID="n"` (positive integer, referenced by `ObjectRef`) on all others.
3. `ClassID` (a GUID naming the class) and `Version` are constant per class, except that `VideoComponentParam` and `AudioComponentParam` have one ClassID per value type ([§12.2](12-effects-and-keyframes.md#122-components-and-params)) [O: steps 00–23 #doc.classid-version-constant]; a writer MUST copy them from [`prproj-classes.md`](../prproj-classes.md) and never invent them. Inner elements' `Version`s (`Clip Version="18"`, `ClipTrackItem Version="8"`, `Items Version="1"`) are schema too: copy them.
4. Objects are never nested in objects, except inside `Project` ([§2.3](#23-local-scope-inside-project)) [O: steps 00–23 #doc.no-nesting].

## 2.2 References

1. A reference is an element with an `ObjectRef` or `ObjectURef` attribute and no content. Outside `Project`, every reference MUST resolve to a top-level object [O: steps 00–23 #doc.refs-resolve], and every top-level object except `Project` MUST be referenced by at least one other object [O: steps 00–23 #doc.every-object-referenced].
2. Lists are repeated elements with a contiguous `Index` from 0 (`<Item Index="0" ObjectURef=…/>`, `<Clip Index="0" ObjectRef=…/>`, `<Param Index="0" …/>`, `<TrackItem Index="0" …/>`, `<Track Index="0" …/>`, `<Link Index="0" …/>`), and track items are listed in time order [O: steps 00–23 #doc.list-index]. A writer MUST keep each list contiguous and SHOULD keep Premiere's order.
3. Referrers (references from other top-level objects):
   - **One:** chains, components, params, SubClips, clips, SecondaryContent, unlinked track items, video tracks, a sequence's Markers object and each `Marker` [O: step 15 #doc.referrers-one].
   - **Two:** a linked track item (track, Link); an audio fade (`TransitionItems`, its track item's `HeadTransition` or `TailTransition`); an audio track (group, master's `AudioTrackInlet`); a Sequence (its two sequence sources) [O: step 15 #doc.referrers-two]. **Three:** a crossfade (`TransitionItems`, both track items) [O: step 15 #doc.referrers-three].
   - **Shared:** a MasterClip (its ClipProjectItem, every SubClip of it); a media or sequence source (its MasterClip's clip, every timeline clip of it and their `SecondaryContent`s); Media (its sources); a media clip's Markers object (the master clip's clips, every timeline clip of that media) [O: steps 03–23 #doc.referrers-shared].

## 2.3 Local scope inside `Project`

`Project/Node/Properties/ProjectViewState.List` (global ObjectID 2) is written inline, holding nested objects (ProjectViewState, ColumnList, `*Column`) with **local** `ObjectID`s (1–60 in the steps) that collide with global IDs [O: steps 00–23 #doc.local-scope]. They MUST NOT be resolved against the top-level index. A reader MUST index only the direct children of `<PremiereData>`.

## 2.4 Allocating identities

- **ObjectID:** dense (1…max, with 2 the `ProjectViewState.List`), increasing in document order, separate from ObjectUIDs [O: steps 00–11, 15, 19, 21–22 #doc.objectid-dense]. `1 + max(every ObjectID="n" in the file)` is a safe new ID [V: steps 11→12-gen #doc.new-objectid].
- **ObjectUID** and `ClipID`: random v4 UUIDs [O: steps 00–23 #doc.uids-v4]. In steps 00–11 every ObjectUID survives each save except the `RootProjectItem`'s, new each time [O: steps 00–11 #doc.root-uid-changes]; Speech to Text with speaker labelling gave every Media a new one [O: steps 20-gen→21 #doc.media-uids-regenerated]. Reach the root bin through `Project`'s `RootProjectItem` reference; match objects across saves by name and tree position.
- **Node IDs:** `Project/NextID` = 1 + max(`Node/ID`); `RootProjectItem` is always 1000000 [O: steps 00–23 #doc.nextid]. A media MasterClip takes `NextID` (which then goes up by one) when first placed in a sequence, not on import [O: steps 00→01, 02→03, 04→05 #doc.node-id-on-placement]. Sequence MasterClips and New Bin bins have none [O: steps 01→02, 02→03, 03→04 #doc.no-node-id]. A script taking `NextID` on placement and incrementing it opened fine [V: steps 04→18-gen #doc.script-node-id].
- **Regenerate on any clone:** `ClipID`, `AudioClipTrackItem/ID`, `AudioClipTrack/AudioTrack/ID`, `AudioMixTrack/AudioTrack/ID`, `AudioTrackGroup/ID` [V: step 17-gen #doc.clone-regenerate]; all five are unique [O: steps 03–23 #doc.ids-unique]. One `DefMappingID` is shared by six MasterClips [O: step 01 #doc.defmappingid-shared].
- **Constants** that MUST NOT be regenerated: media-type GUIDs ([§7.2](07-sequences.md#72-media-types)), `EditingModeGUID`, `PreviewFormatIdentifier` (per format: [§7.3](07-sequences.md#73-settings)), `ESP.PresetGuid`, the importer `ImplementationID` [O: steps 03–23 #doc.constants].

## 2.5 Object order

Premiere writes objects **breadth-first from `Project`, in reference order**, each at its first reference [O: steps 00–11, 15, 19, 21–22 #doc.bfs-order]. Order doesn't matter on load as far as tested: objects inserted right after a related one (a clone after its original) loaded [V: step 17-gen #doc.order-free]. A writer SHOULD do the same, which keeps diffs local.
