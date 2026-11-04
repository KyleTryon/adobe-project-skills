# Adding, cloning and splitting objects in a .prproj

Status of every rule here: [the spec](spec/README.md) (§0 for the tags). Prefer the commands, which make these edits and validate the result: `split`, `backup-seq` and `place` write exactly what the recipes below describe. For a hand edit, use targeted string edits: insert cloned top-level blocks right after the originals ([§2.5](spec/02-document-structure.md#25-object-order)) and leave everything else byte-identical, then run `prproj.py validate FILE --orig ORIGINAL`.

## Rules for every new object

From spec [§2.4](spec/02-document-structure.md#24-allocating-identities):

- **ObjectID:** `1 + max(every ObjectID="n" in the file)` (including the local-scope IDs inside `Project`), then increment.
- **ObjectUID:** a new uuid4. Remap every `ObjectRef`/`ObjectURef` inside the cloned blocks to the new IDs.
- **Regenerate on clones:** `<ClipID>` (clips) and the `<ID>` of `AudioClipTrackItem`, `AudioClipTrack/AudioTrack`, `AudioMixTrack/AudioTrack` and `AudioTrackGroup`.
- **Never change** the constants: media-type GUIDs (TrackGroup `First`, `MediaType`), `EditingModeGUID`, `PreviewFormatIdentifier`, `ESP.PresetGuid`, the importer `ImplementationID`.
- **Node IDs:** a media MasterClip gets one (take `<NextID>`, then increment it) the first time it's placed in a sequence, not at import. Sequence MasterClips and bins made with New Bin have none; don't add one.

## Splitting one track item

`prproj.py split` does this. What it writes is what Premiere's razor writes (spec [§9.4](spec/09-track-items-and-links.md#94-premieres-edits), "Split"):

- The left piece keeps its objects: change only its `TrackItem/End` (→ T) and `Clip/OutPoint` (→ the source time at T), on both items of the pair.
- The right piece is 11 new objects per A/V pair: per side the `*ClipTrackItem`, its chain, the `SubClip` and the `*Clip` (new `ClipID`; audio items a new `ID`), the audio clip's `SecondaryContent` objects (one per channel), and one new `Link`. Nothing in a chain is shared between items ([§2.2](spec/02-document-structure.md#22-references)), so a chain's components and params are cloned with it. The MasterClip, the clip's `Source`, Media and track are shared, never cloned.
- The right piece: `Start` = T, `InPoint` = the left piece's new `OutPoint`, the original `End`/`OutPoint`, and copies of the label, Essential Sound properties and the shared `MarkerOwner`.
- Wire up: insert each new item into its track's `ClipItems/TrackItems` **in time order** and renumber `Index` so it stays contiguous ([§9.3](spec/09-track-items-and-links.md#93-per-track-invariants)); write `<Start>` only when it isn't 0; insert the new `Link` into `PersistentGroupContainer/LinkContainer/Links` at its pair's time position ([§10](spec/09-track-items-and-links.md#10-links)). The sequence length doesn't change, and `MZ.WorkOutPoint` is never moved by edits ([§7.4](spec/07-sequences.md#74-length)).
- Splitting a clip that has keyframes isn't covered; see spec [§18](spec/18-not-observed.md), and do it in Premiere.

## Backing up a sequence

`prproj.py backup-seq FILE OUT --seq NAME` duplicates a sequence inside the project, in the same bin (verified, spec [§6](spec/06-project-panel.md#6-project-panel-bins-project-items-master-clips-media) item 3 and [§13](spec/13-markers.md#13-markers)): every track, item, link and sequence marker is cloned with new ObjectIDs and ObjectUIDs, new `ClipID`s and audio IDs, and new marker GUIDs, while the media MasterClips are shared, not copied. Use it rather than a hand clone.

Nesting one sequence inside another, creating a bin, and importing a media file by hand aren't covered; see spec [§18](spec/18-not-observed.md). Ask the user to do those in Premiere.

## Placing a clip on a track

`prproj.py place` does this (spec [§9.4](spec/09-track-items-and-links.md#94-premieres-edits), "Place" and "Place only the video"):

- Per side: a new `*ClipTrackItem`, its chain in the default form (video: `DefaultMotion`/`DefaultOpacity` true; audio: `DefaultVol` true; spec [§12.1](spec/12-effects-and-keyframes.md#121-chains)), a `SubClip` → the media's MasterClip, and a `*Clip` whose `Source` is the media's source; the audio clip also gets its `SecondaryContent` objects. A linked A/V placement adds one `Link`; video only adds none.
- `Start`/`End` on the sequence frame grid ([§9.2](spec/09-track-items-and-links.md#92-timing)). The MasterClip takes a Node ID on its first placement (above).
- An empty track has no `TrackItems` in its `ClipItems`: insert one before that container's own `MediaType` ([§8](spec/08-tracks.md#8-tracks), item 6). The `Track` block has its own `MediaType` earlier, so anchor on `<ClipItems Version="3">` or you'll insert into the wrong place.
- To move or scale the placed clip, add a Transform afterwards with `prproj.py add-transform` ([effects.md](effects.md)).
