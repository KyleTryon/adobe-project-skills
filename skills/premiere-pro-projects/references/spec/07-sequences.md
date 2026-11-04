# 7. Sequences

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

Recipes and settings values: [`sequences.md`](../sequences.md).

## 7.1 The Sequence object

`Sequence` (ObjectUID) holds [O: steps 03–23 #seq.object]: `Node/Properties` ([§7.3](#73-settings)), `MarkerOwner` once it has markers ([§13](13-markers.md#13-markers)), `PersistentGroupContainer/LinkContainer/Links` ([§10](09-track-items-and-links.md#10-links)), `TrackGroups/TrackGroup[Index]` (`First` = media-type GUID, `Second` → the group), `Name`, `PreviewFormatIdentifier`. Only its two sequence sources reference it: find it by `Name`.

## 7.2 Media types

| Media | GUID (constant) | Group |
|---|---|---|
| video | `228cda18-3625-4d2d-951e-348879e4ed93` | `VideoTrackGroup` |
| audio | `80b8e3d5-6dca-4195-aefb-cb5f407ab009` | `AudioTrackGroup` |
| data (captions) | `d8143ffe-eec4-4d2a-a909-d5f7bf094dc5` | `DataTrackGroup` (always present, always empty here) |

The same GUIDs are the `MediaType` of every track and its `ClipItems`/`TransitionItems` [O: steps 03–23 #seq.media-types].

## 7.3 Settings

Where each setting lives, with observed values: [`sequences.md`](../sequences.md), Settings table. The rules:

- Frame size is `VideoTrackGroup/FrameRect` (`0,0,1920,1080` in the steps), repeated in `MZ.Sequence.PreviewFrameSizeWidth/Height` and, in a Premiere save, on every VideoClipTrackItem, even one holding a 1280×720 clip; pixel aspect is per item. Frame rate is `VideoTrackGroup/TrackGroup/FrameRate` = `DataTrackGroup/TrackGroup/FrameRate`; audio rate `AudioTrackGroup/TrackGroup/FrameRate` [O: steps 03–17, 19–23 #seq.frame-size-rate].
- `MZ.Sequence.EditingModeGUID` is a constant (`795454d9-d3c2-429d-9474-923ab13b7018`) [O: steps 03–23 #seq.editing-mode-guid]. `Sequence/PreviewFormatIdentifier` follows the format: `fc3cd4d9-d839-8259-9276-05c5000000ea` on every 1920×1080 23.976 sequence Premiere made [O: steps 02→03, 03→04 #seq.preview-format]. Copy it from a sequence of the same format; never generate one. Other formats aren't covered ([§18](18-not-observed.md)).
- `MZ.WorkInPoint` / `MZ.WorkOutPoint` are the work area, **not** the length ([§7.4](#74-length)). `MZ.EditLine` is the playhead, view state that Premiere moves during edits [O: steps 06→07, 07→08 #seq.edit-line].
- Field type, start timecode, VR and solo settings are not covered; see [§18](18-not-observed.md).

## 7.4 Length

A sequence's length MUST be computed as the largest `ClipTrackItem/TrackItem/End` among the clip items (not transitions) of all its tracks. `Monitor.ProgramZoomOut` equalled it after every step (0 when empty), and a writer SHOULD keep it equal [O: steps 03–23 #seq.length-zoomout]. As edits change the length (values per step in `sequences.md`):

- `Monitor.ProgramZoomOut` follows it both ways [O: steps 03–08 #seq.zoomout-follows].
- `MZ.WorkOutPoint` is set when the sequence is made ([§7.6](#76-new-sequences)) and never moved by later edits [O: steps 03–08 #seq.workout-fixed].
- Both `*SequenceSource/OriginalDuration` values rise with it and never fall [O: steps 03–08 #seq.original-duration-rises].
- The sequence MasterClip's `MasterClipChangeVersion` goes up on every edit (16 → 28 → 35 → 41 → 47 over steps 03–08) [O: steps 03–08 #seq.change-version]. Script edits that leave it alone open in Premiere [V: steps 11→12-gen #seq.change-version-script].

## 7.5 Nesting

Not covered yet: no step places a sequence inside another. See [§18](18-not-observed.md); don't nest sequences by hand.

## 7.6 New sequences

What Premiere writes; the full comparison is in [`sequences.md`](../sequences.md), "What Premiere writes":

- **New Sequence from Clip** goes in the clip's bin, named after the clip without extension, with its settings, 3 video and 3 audio tracks and the clip linked on V1/A1 at 0: 65 top-level objects (54 + 11 for the clip, [§9.4](09-track-items-and-links.md#94-premieres-edits)). `Monitor.ProgramZoomOut`, `MZ.WorkOutPoint` and `OriginalDuration` = the clip's end [O: steps 02→03 #seq.new-from-clip].
- **File › New › Sequence** goes in the root bin with the chosen settings; the custom preset gave 3 video and 4 audio tracks, empty: 62 objects. `Monitor.ProgramZoomOut` and `OriginalDuration` 0; `MZ.WorkOutPoint` `15235011792000` (1438 frames at 23.976, about 60 s) [O: steps 03→04 #seq.new-sequence-dialog].
- An empty 3+3 sequence is 54 objects; each further audio track adds 8 ([§8](08-tracks.md#8-tracks)). Empty means `MZ.EditLine` and `MZ.WorkInPoint` 0, an empty `LinkContainer` ([§10](09-track-items-and-links.md#10-links)), no `TrackItems` ([§8](08-tracks.md#8-tracks)), a MasterClip with no `Node` and clips with no In/Out [O: steps 02→03, 03→04 #seq.empty-sequence].
- **Cloning an empty sequence** with `backup-seq` and placing a clip into it makes a working new sequence [V: steps 04→18-gen #seq.clone-empty-new]; it's the scripts' way to create one.
