# 18. Not covered

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

Nothing in the spec describes these, so don't write XML for them: tell the user and suggest doing that part in Premiere. Each needs a step first: record one in Premiere, or generate one with the scripts and check it in Premiere (`fixtures/premiere-pro/README.md`, "Adding a step"), then write the rule into the right part of the spec with its tag and check. The repo's backlog says which step would prove each.

**File and values**
- Entity escaping in text (`&lt;`, `&gt;`, `&amp;`, `&#10;`) ([§1](01-container.md#1-container)).
- The `.prin` sidecar: ignore it; don't edit or commit it.
- Frame and sample rates other than 23.976, 25, 29.97 fps and 48 kHz ([§3](03-value-encodings.md#3-value-encodings)); non-square pixels.
- Deduplicated (self-closing) base64 blobs, and base64 in other elements.
- Premiere versions other than 26.5; Windows paths.

**Project panel and media**
- Image sequences, and stills beyond their object count ([§6](06-project-panel.md#6-project-panel-bins-project-items-master-clips-media)).
- Importing media by hand, renaming or relinking items; media without probe caches; project-panel subclips; merged clips; multicam.
- Creating a bin by hand, and how a user-made bin gets a Node ID.

**Sequences and tracks**
- Nesting a sequence inside another ([§7.5](07-sequences.md#75-nesting)); exported sequences.
- Sequence field type, start timecode, VR and solo settings; `PreviewFormatIdentifier` for formats other than 1920×1080 23.976.
- Adding, removing or reordering tracks, and moving clips between tracks ([§8](08-tracks.md#8-tracks)).
- A sequence from scratch, emptying a copied one, or changing its frame size, frame rate or audio settings (copying one with `backup-seq` is covered).
- Locking an audio track, sync lock, the track output toggle, solo, track effects, submixes, mono/5.1/adaptive tracks.

**Clips and edits**
- Speed changes, speed ramps, reverse speed, frame blending, time remapping; disabling a clip ([§9.2](09-track-items-and-links.md#92-timing)).
- Ripple trim, lift (delete leaving a gap), move, slip, slide, closing gaps, insert edits; splitting a clip that has keyframes or a transition; trimming the head of a clip with a fade.
- Audio clip gain; Essential Graphics (MOGRT) items.
- Deleting one member of a link; links of more than two items ([§10](09-track-items-and-links.md#10-links)).
- Video transitions; moving or removing a transition; audio transitions other than Custom Fade and Constant Power; a Premiere-made fade-out or head trim (the script-written forms are verified: [§11](11-transitions.md#11-transitions)).

**Effects**
- Effects other than Transform; explicit Motion or Opacity ([§12](12-effects-and-keyframes.md#12-effects-and-keyframes)).
- Clip volume (the intrinsic Volume and Channel Volume components), audio Level keyframes, animated audio params, and keyframes on scalar params (Scale, Rotation, Opacity, …): only Position and Anchor Point keys are covered.
- Changing an existing Transform; clip labels.

**Markers, transcripts and captions**
- Deleting a marker; clip markers with entries, marker durations, marker types other than Comment and Chapter, marker colours other than orange and pink ([§13](13-markers.md#13-markers)).
- Editing transcript words or timings: treat them as read-only; speaker names and turns are covered ([§14](14-transcripts-and-captions.md#14-transcripts-speech-to-text)).
- Caption tracks and items: deliver captions as an SRT for the user to import ([§15](14-transcripts-and-captions.md#15-captions)).

For a feature the demo media can't show, run `scripts/schema_dump.py` on the smallest project that has it and compare with [`prproj-classes.md`](../prproj-classes.md).
