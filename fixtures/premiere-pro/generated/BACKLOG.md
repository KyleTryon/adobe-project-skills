# Backlog: claims waiting for proof

Everything here was believed about the format but isn't proven by a step, so it's kept out of the skill. Each item says where it came from and the step that would prove it. To work on one, record that step in Premiere or generate it and check it there ([`CONTRIBUTING.md`](../../../CONTRIBUTING.md), "Recording a step" and "Generating a step instead"), then write the rule into the spec with its tag and check, and delete the item here. If the step shows the claim was wrong, write what it does show and delete the item anyway.

Things the skill must not attempt until then are listed in the spec's [§18 Not covered](../../../skills/premiere-pro-projects/references/spec/18-not-observed.md).

## Commands and options

These are implemented in `prproj.py` but refuse to run without `--unproven` (`UNPROVEN` in `prproj.py`), and `SKILL.md` doesn't offer them.

- `set-label`: set a clip's label (`asl.clip.label.name` = `BE.Prefs.LabelColors.N`, leaving `asl.clip.label.color` alone; a clip with no `<Node>` needs one inserted).
  prove with: in Premiere, label clip-b's V1 and A1 pieces Mango in step 08, Save a Copy; then a `-gen-` step from step 08 with `set-label --label Mango`, opened and checked in Premiere.
- `set-transform`: change an existing Transform's values or keys.
  prove with: a `-gen-` step from step 12-gen moving the PiP's second Position key and turning motion blur off, opened in Premiere; compare with a Premiere Save a Copy of the same change.
- `place --audio-only`: place only a clip's audio.
  prove with: in Premiere, drag only the audio of `sfx-pop.wav`'s source (or Alt-drag clip-a's audio) to A2 in step 11, Save a Copy; replay it with `place --audio-only`.
- `add-marker --colour` other than orange and pink: the `0xAABBGGRR` formula is proven for two swatches only.
  prove with: in Premiere, one marker in each of the other six colours on `clip-a` in step 11, Save a Copy.

## Format claims

### Spec 01–04: claims to prove

- `&#10;` is expected only inside escaped export-preset XML in `Project` and `Sequence` properties.
  from: spec/01-container.md §1.5 · prove with: record a step that names a clip and a sequence `A & B <1>`, gives a clip a two-line description, then diff; check which entities Premiere writes.
- Text uses `&lt; &gt; &amp;` (was tagged observed for steps 00–22, but no step contains any entity reference).
  from: spec/01-container.md §1.5 · prove with: the same step as above.
- Premiere writes `<name>.prin` beside the project, and beside a Save a Copy (was tagged observed for steps 01–11; the `.prin` files are git-ignored, so no committed evidence exists).
  from: spec/01-container.md §1.7 · prove with: a local-only check run against a recording session, or accept as a boundary.
- Premiere-made bins (`Recovered Clips`, `Motion Graphics Template Media`) are expected to have no `Node/ID`.
  from: spec/02-document-structure.md §2.4 · prove with: record a step that imports a .mogrt (creates the Motion Graphics Template Media bin), and a `-gen-` step with an orphaned MasterClip opened and re-saved by Premiere (creates Recovered Clips); check `ProjectItem/Node/ID` on both bins.
- Whether any action gives a bin a `Node/ID` (not observed).
  from: spec/02-document-structure.md §2.4 · prove with: record steps that drag a bin onto the timeline and that create a bin from a selection; diff Node IDs.
- `Media/FileKey` and `DefMappingID` must be regenerated when cloning media.
  from: spec/02-document-structure.md §2.4 · prove with: record Edit › Duplicate on a clip in the Project panel and diff (all MasterClips in the steps share one `DefMappingID`, so this may be wrong for it).
- Duplicate Media of one file may share a `FileKey`.
  from: spec/02-document-structure.md §2.4 · prove with: record importing the same file a second time and diff.
- Effect and provider IDs are constants that must not be regenerated (narrowed to the importer `ImplementationID`; no step shows what "provider IDs" are, and effect MatchNames are strings).
  from: spec/02-document-structure.md §2.4 · prove with: a step adding a second Transform in Premiere; compare its component's identifying fields with the first.
- Computed tick rates: 24 = `10584000000`, 30 = `8467200000`, 50 = `5080320000`, 59.94 = `4237833600`, 60 = `4233600000`.
  from: spec/03-value-encodings.md §3 · prove with: record steps creating sequences at 24, 30, 50, 59.94 and 60 fps (and import ffmpeg clips at those rates); read `FrameRate`.
- `Media/Start` 0 is omitted (no Media in any step has a `Start`, so omission can't be told apart from the field not existing).
  from: spec/03-value-encodings.md §3 (defaults) · prove with: import a clip with a non-zero start timecode (`ffmpeg … -timecode 01:00:00:00`) and diff.
- `PremiereFilterPrivateData`, `StartKeyframeValue` and `ImporterPrefs` are binary blobs in the same form (by their declared encoding).
  from: spec/03-value-encodings.md §3.10 · prove with: a step applying an effect that stores private data, and media whose importer writes `ImporterPrefs`; check `Encoding`/`BinaryHash`.
- **Deduplication:** a repeated blob is written in full only at its first occurrence; later ones are self-closing with the same `BinaryHash`. Deleting or moving the object holding the full copy MUST move the data to the next occurrence. (MUST rule moved here.)
  from: spec/03-value-encodings.md §3.10 · prove with: record duplicating a transcribed sequence or media item in Premiere, look for self-closing blobs, then a `-gen-` step deleting the first holder that Premiere opens.
- **Float quirk.** Premiere sometimes truncates a tiny float's exponent (`6.766e-10` written `6.766e-1`), and later saves keep it. Recompute derived values (keyframe speeds); don't copy them.
  from: spec/03-value-encodings.md §3 · prove with: search steps 15 and later Premiere saves for keyframe speeds with truncated exponents; if none, record a step with an eased Transform on a long clip.
- `MZ.NextBinIndex` is a project property (it appears in no step).
  from: spec/04-object-graph-and-project.md §5 · prove with: record creating a second and a third New Bin.
- Drop a `MZ.PrefixKey.OpenSequenceGuidList.N` entry when deleting its sequence.
  from: spec/04-object-graph-and-project.md §5 · prove with: record deleting a sequence in Premiere and diff the Project properties.

### Project panel, sequences, tracks (spec 06–08)

- The MasterClip `Name` and `ClipLoggingInfo/ClipName` can differ from the panel name (`ProjectItem/Name`).
  from: spec/06-project-panel.md §6.2
  prove with: in Premiere, rename clip-a.mp4 in the Project panel and Save a Copy; diff against the step before.
- A MasterClip no ClipProjectItem points at is adopted into `Recovered Clips` on load.
  from: spec/06-project-panel.md §6.3
  prove with: a `-gen-` step from 05 with clip-b's ClipProjectItem removed from the bin by hand (its MasterClip still used on the timeline); open in Premiere and Save a Copy.
- `Media/Start` is the timecode origin (omitted when 0). Clip `InPoint`/`OutPoint` count from the media's first frame, not from `Media/Start`.
  from: spec/06-project-panel.md §6.4
  prove with: add a clip with a 01:00:00:00 start timecode to `make_media.sh`, import it, place it with an In point, Save a Copy.
- Media written without probe caches (`ModificationState`, `ContentAndMetadataState`, `CCFileModTime`, cache paths) are re-probed on load.
  from: spec/06-project-panel.md §6.4
  prove with: a `-gen-` step from 01 with those fields stripped from one Media; open in Premiere and Save a Copy.
- A ProRes 4444 alpha render may have an AudioStream but no AudioClip.
  from: spec/06-project-panel.md §6.5
  prove with: add a ProRes 4444 clip with alpha (and one with silent audio) to `make_media.sh`, import, Save a Copy.
- `41384a52-7e4a-3c48-e0ad-4939000000ea` is the `PreviewFormatIdentifier` of 3840×2160 23.976 sequences.
  from: spec/07-sequences.md §7.3
  prove with: File › New › Sequence at 3840×2160 23.976 (and 24, 25, 29.97, 59.94 at 1080p), Save a Copy after each.
- Exported sequences carry `Seq.ExportID` and `ExportSettings.*`; copies SHOULD drop them.
  from: spec/07-sequences.md §7.3 (a SHOULD rule)
  prove with: File › Export › Media on clip-a, Save a Copy; then `backup-seq` on that step as a `-gen-` step with and without the keys, open both.
- Whether leaving `MasterClipChangeVersion` unchanged after a script edit matters anywhere (it opens fine).
  from: spec/07-sequences.md §7.4
  prove with: after a script edit, use the sequence in Premiere (render, export, Undo) and Save a Copy.
- A nested sequence is a track item whose `SubClip/MasterClip` is the nested sequence's MasterClip, `SubClip/Name` its name, and whose clip `Source` is that sequence's own `VideoSequenceSource`/`AudioSequenceSource`, shared, never cloned. In/Out are nested-timeline times; the item doesn't follow later changes to the child's length.
  from: spec/07-sequences.md §7.5
  prove with: in Premiere, drag the clip-a sequence into Custom and Save a Copy; then shorten clip-a and Save a Copy.
- `MZ.WorkOutPoint` of a sequence made with File › New › Sequence at frame rates other than 23.976.
  from: spec/07-sequences.md §7.6
  prove with: the same New Sequence steps as the preview-format item.
- `ClipTrack/Track/ID` is unrelated to position (in every step it is Index + 1 for video, Index + 2 for audio). A new track takes `TrackGroup/NextTrackID`, which is then incremented, never decremented; IDs are not reused.
  from: spec/08-tracks.md §8.3
  prove with: in Premiere, Add Track (video and audio), Save a Copy; delete a middle track, Save a Copy; add another, Save a Copy.
- Lock on audio tracks is written like video (`ClipTrack/Track/IsLocked`).
  from: spec/08-tracks.md §8.7
  prove with: lock A2 in Premiere, Save a Copy.

### Track items, links and transitions (spec 09, 11)

- `AudioClip` has an optional linear `Gain` (1.4142 = +3 dB).
  from: spec/09-track-items-and-links.md §9.1
  prove with: in Premiere, Audio Gain +3 dB on clip-b's A1 piece in step 08's `clip-a` sequence, Save a Copy; then a `-gen-` step setting it from step 08 to compare.
- MOGRT (Essential Graphics) items carry `ClipTrackItem/VSMOffset`, `VSMSpeed`, `VSMDuration`; `VSMSpeed` is not a playback speed, and source time starts at 1 hour.
  from: spec/09-track-items-and-links.md §9.1
  prove with: in Premiere, add a stock Essential Graphics title to V2 of `clip-a` (from step 11), Save a Copy.
- A timeline `VideoClip`/`AudioClip` may hold `PlaybackSpeed` (the steps only show it, as 1, on master-clip clips, never on a timeline clip).
  from: spec/09-track-items-and-links.md §9.1
  prove with: the speed-change step below.
- Speed formulas: `End − Start = (OutPoint − InPoint) / PlaybackSpeed` (absent = 1); `source = InPoint + (timeline − Start) · PlaybackSpeed`; `timeline = Start + (source − InPoint) / PlaybackSpeed`.
  from: spec/09-track-items-and-links.md §9.2
  prove with: in Premiere, Speed/Duration 200% on clip-b (video and audio linked) in step 08, Save a Copy; then 50% unlinked video only.
- An audio `End` may be off the frame grid only where the clip runs to the end of its media. (Note: this was an exception to the MUST that `Start`/`End` lie on the grid; the MUST stays, proven on steps 03–23, which have no such clip.)
  from: spec/09-track-items-and-links.md §9.2
  prove with: in Premiere, place `tone-1k.wav` (or another file whose length isn't whole frames) on A2 and let it run to its end, Save a Copy.
- Source In/Out may be off-grid for media at other rates.
  from: spec/09-track-items-and-links.md §9.2
  prove with: in Premiere, place `clip-c-720p2997.mp4` in the 23.976 `clip-a` sequence and razor it, Save a Copy.
- Premiere stores a non-terminating speed (e.g. `1.9958183892609278`) so a clip fills whole frames; the equation then holds to half a tick.
  from: spec/09-track-items-and-links.md §9.2
  prove with: in Premiere, set clip-b's duration by Speed/Duration to a frame count that isn't a round speed (e.g. 9 s for 18 s of media at 23.976), Save a Copy.
- Timeline speed changes (`PlaybackSpeed` ≠ 1) are expected only on unlinked video clips; a linked audio half's speed is unknown.
  from: spec/09-track-items-and-links.md §9.2
  prove with: the 200% linked speed-change step above shows whether the audio half gets `PlaybackSpeed`.
- A speed ramp is expected as split pieces with different speeds.
  from: spec/09-track-items-and-links.md §9.2
  prove with: in Premiere, time-remap a speed ramp on clip-b, Save a Copy.
- Separate-audio recordings (camera + external WAV) are not linked.
  from: spec/09-track-items-and-links.md §10
  prove with: in Premiere, place clip-a's video and `tone-1k.wav` together, synchronise them (Merge Clips or Synchronize), Save a Copy.

### Effects and keyframes (spec 12)

- Once changed, the flag goes and an explicit `VideoFilterComponent` (`AE.ADBE Motion` ID 1 or `AE.ADBE Opacity` ID 2, `Intrinsic` true, a `PremiereFilterPrivateData` blob) joins the list.
  from: spec/12-effects-and-keyframes.md §12.1
  prove with: in Premiere, from step 11, set clip-b's Motion Scale to 50% and Opacity to 80%, Save a Copy.
- `ComponentChain/Components/Component[Index]` is the stack, taken to be Effect Controls order with 0 at the top and explicit Motion at 0.
  from: spec/12-effects-and-keyframes.md §12.1
  prove with: a `-gen-` step from 12-gen with a second Transform on the PiP (`add-transform --force`); open it, then change Motion Scale on the same clip in Premiere and Save a Copy.
- IDs need not follow stack order.
  from: spec/12-effects-and-keyframes.md §12.1
  prove with: in Premiere, reorder the two Transforms of the step above in Effect Controls, Save a Copy.
- `MatchName` `AE.ADBE Capsule` (Graphic Parameters) and `AE.ADBE AEMask2` (Mask) on a `VideoFilterComponent`.
  from: spec/12-effects-and-keyframes.md §12.2
  prove with: in Premiere, add an Essential Graphics text layer on V2 and an ellipse mask on clip-b's Opacity, Save a Copy.
- Param classes: `VideoComponentParam` `a4ff2d6e-7ac2-44f8-9d52-17d9ca50e542` float (mask), `0fde4e9f-f895-4ba3-b0fe-9a6feafda583` colour, `ArbVideoComponentParam` `313e54d4-6903-49ad-b0bf-8262cdd10f4e` opaque blob (`StartKeyframeValue`).
  from: spec/12-effects-and-keyframes.md §12.2
  prove with: the graphic-and-mask step above (text colour, mask feather).
- `AudioComponentParam` float also holds Level, and bool also holds Bypass.
  from: spec/12-effects-and-keyframes.md §12.2 (table rows narrowed to Volume, Balance and Mute)
  prove with: in Premiere, set clip-a's A1 clip Volume Level to −6 dB and toggle its Bypass, Save a Copy.
- Audio Level params order their children `StartKeyframe`, `CurrentValue`, `Keyframes`, `Name`, `UnitsString`, `Timestamp`.
  from: spec/12-effects-and-keyframes.md §12.2
  prove with: in Premiere, add two Level keyframes to clip-a's A1 clip volume, Save a Copy.
- Animated audio Level params have no `IsTimeVarying`, and `Keyframes` follows `CurrentValue`.
  from: spec/12-effects-and-keyframes.md §12.4
  prove with: the Level-keyframe step above.
- To remove animation, delete both (`IsTimeVarying`, `Keyframes`) and set `StartKeyframe`.
  from: spec/12-effects-and-keyframes.md §12.4
  prove with: a `-gen-` step from 12-gen: `set-transform --clear position` on the PiP; open in Premiere and check Position is static.
- `scalar key = t "," value "," interp ",0," speedIn "," inflIn "," speedOut "," inflOut`, with speeds as the signed value change per second of source time. Keyed scalar params (audio Level, Scale, Rotation, …).
  from: spec/12-effects-and-keyframes.md §12.4
  prove with: a `-gen-` step from 16-gen: `add-transform --track 0 --item 2 --keys scale "0f=80, 24f=100"` (eval 2's edit), open in Premiere and Save a Copy so the re-save shows Premiere's own scalar keys.
- Users can change key influences (eased keys are not always 1/3 and 1/6).
  from: spec/12-effects-and-keyframes.md §12.4
  prove with: in Premiere, drag one Bezier handle of step 15's Position keys, Save a Copy.
- Shutter Angle [10] is 240 by default (the steps only show the scripts' 240, kept by Premiere).
  from: spec/12-effects-and-keyframes.md §12.5
  prove with: in Premiere, drag Transform onto a clip from the Effects panel without changing it, Save a Copy (shows all 12 default values).
- Clip volume is an intrinsic `AudioFilterComponent` (`FilterMatchName` `Internal Volume Stereo`, Bypass + Level params) plus Channel Volume (one Level per channel).
  from: spec/12-effects-and-keyframes.md §12.6
  prove with: the −6 dB clip volume step above.
- Level is linear gain, 0 dB = `0.177827941`: `dB = 20·log10(v) + 15`.
  from: spec/12-effects-and-keyframes.md §12.6
  prove with: two Level values in Premiere (−6 dB and +3 dB on two clips), Save a Copy; then a `-gen-` step writing −3 dB, checked in Premiere's Effect Controls.

### Transcripts and captions (spec 14–15)

- Transcript times are the owner media's source time, not sequence time (the steps only show a clip placed at 0 with In 0, where the two agree).
  from: spec/14-transcripts-and-captions.md §14
  prove with: in Premiere, place interview.mp4 at 0:10 with In 0:05 in a new sequence and run Speech to Text on it, Save a Copy.
- The transcript belongs to the media: every sequence using the clip reads it.
  from: spec/14-transcripts-and-captions.md §14.1 (narrowed to "owned by the media's MasterClip")
  prove with: the step above, opening its transcript from a second sequence that uses interview.mp4, Save a Copy.

### Conformance checklist (spec 16)

- Audio Level keys need not lie within their clip's source range (split pieces keep the whole key list).
  from: spec/16-checklist.md item 10
  prove with: in Premiere, add Level keyframes to a clip's volume, razor the clip between keys, Save a Copy.
- MUST: Deduplicated blobs: each self-closing `BinaryHash` has a full copy earlier in the file (no step has a self-closing blob).
  from: spec/16-checklist.md item 11
  prove with: a `-gen-` step from 21: `backup-seq --seq Interview` (it writes self-closing copies of the cloned blobs), open in Premiere and Save a Copy.

### Load and save (spec 17)

- Load re-probes Media missing its cache fields and adopts orphaned MasterClips into `Recovered Clips`.
  from: spec/17-load-and-save.md
  prove with: two `-gen-` steps from 11: one with a Media's stream cache fields removed, one with a ClipProjectItem removed but its MasterClip kept; open each and Save a Copy.
- Re-saving with no edits adds `Clip/PlaybackSpeed` 1 and `MediaFileHistory0` to media clips, `BE.MasterClip.ChannelIndexToTranscribe` -1 and bin `list.view.expanded.state.<GUID>` keys, and raises every `MasterClipChangeVersion`. (The steps show these only on saves of script-written files, `MediaFileHistory0` on Media rather than clips, and the first three only in 20-gen→21.)
  from: spec/17-load-and-save.md
  prove with: open step 22 and Save a Copy with no changes.
- Auto-save writes `Adobe Premiere Pro Auto-Save/<name>--<GUID>-<YYYY-MM-DD>_<HH-MM-SS>.prproj` beside the project (e.g. `demo--fd346586-…-2026-11-03_21-50-05.prproj`). The GUID is not `MZ.Project.GUID`; what it is is unknown. (The auto-save that showed this was deleted from the fixtures.)
  from: spec/17-load-and-save.md
  prove with: let one auto-save happen while recording, scrub it and commit it as evidence (or record its name in the steps table).
- Save a Copy writes a `.prin` beside the copy (no `.prin` is committed, so no test can see it).
  from: spec/17-load-and-save.md (now points to §1)
  prove with: decide in §1; a test could only check this on the recorder's machine.

### Task guides: cutting, effects, object surgery, transcripts

- Splitting a clip that has keyframes: the cloned keys stay correct for each piece without retiming, because keys live in source time.
  from: references/object-surgery.md "Splitting one track item into N pieces"
  prove with: a `-gen-` step from step 12-gen splitting the PiP on V2 at 0:14 with `prproj.py split --track 1`, opened in Premiere: both pieces should keep the Position keys that fall inside them.
- Creating a bin by copying a `BinProjectItem`: new ObjectUID, minimal Node Properties (drop `ProjectViewState.ID` and freeform coordinates), no Node ID, new `Name`; add it to the parent's `Items`.
  from: references/object-surgery.md "Creating a sequence from another", step 7
  prove with: a `-gen-` step from step 02 adding a bin `seq` next to `footage`, opened in Premiere; compare with Premiere's New Bin (steps 01→02).
- Importing a media file by cloning an item of the same kind: set paths, `RelativePath`, `Title`, names, new `FileKey`/`ClipID`s/`DefMappingID`; remove the probe caches; set durations and rates; `Media/Start` 0; drop a cloned `TranscriptClip`; remove `AutoCloned`; add to the `src` bin.
  from: references/object-surgery.md "Importing a media file"
  prove with: a `-gen-` step from step 01 importing `sfx-slide.wav` again under a new name by cloning `sfx-pop.wav`'s objects, opened in Premiere; compare with Premiere's own import of the same file.
- Transcript field meanings: Document f1 and Segment f4 are the language (`"en-us"`), Document f3 a document GUID (not found in the XML), Word f3 the confidence 0–1 (1.0 on empty tokens).
  from: references/transcripts-and-captions.md §2
  prove with: Speech to Text in another language on clip-c in Premiere (language field), and a check comparing Word f3 with Premiere's low-confidence highlighting in the Text panel.
- Transcript tokens (words, pauses, fillers) tile the timeline without overlaps; Segment start/duration equal its first token's start and last token's end; word starts sit on multiples of 10 ms.
  from: references/transcripts-and-captions.md §2
  prove with: a check over steps 19–22 (no new step needed); then they can be cited from spec §14.
- A transcript of separate audio (a WAV synced to a camera file) is in the WAV's media time, offset from the camera by the sync offset.
  from: references/transcripts-and-captions.md §1
  prove with: in Premiere, place `tone-1k.wav`-style separate audio (or the interview's audio extracted to a WAV) under clip-a at an offset, run Speech to Text on the WAV, Save a Copy.
- The owner MasterClip and the synthetic Media keep their ObjectUIDs across saves (false as stated: step 21 gave every Media a new ObjectUID).
  from: references/transcripts-and-captions.md §1
  prove with: nothing; dropped. Kept here only so it isn't reintroduced.
- `cut-transcript` maps through nested sequences: it recurses into items whose `SubClip/Name` is a sequence name, clips the inner spans to the item's in/out and shifts them by `start − src_in`.
  from: references/transcripts-and-captions.md §5
  prove with: in Premiere, nest `Interview` into a new sequence and razor the nested clip (step from 19), Save a Copy; `cut-transcript` on the outer sequence should then match the inner words.
- Captions enter a project as a caption project item (File › Import of an `.srt`, or the Text panel's caption import) and become a caption track when dragged onto the sequence; `<DoCaptions>true</DoCaptions>` in exported sequences' preset XML is an export option.
  from: references/transcripts-and-captions.md §4
  prove with: in Premiere, import `interview.srt` and add it to `Interview` (step from 19), Save a Copy; diff to learn the caption track XML.
- Overwriting a word's text in place with a replacement of identical UTF-8 byte length (or overwriting int64 times) moves no offsets.
  from: references/transcripts-and-captions.md §3
  prove with: a `-gen-` step from step 21 replacing one word with an equal-length spelling fix, opened in Premiere (Text panel shows the fix).
- Labelling a clip with no label: such a clip has no `<Node>` at all, so insert a whole `<Node Version="1"><Properties Version="1">…</Properties></Node>` as the first child of `<Clip>`.
  from: references/cutting-and-editing.md §1 "Labels"
  prove with: the `set-label` steps in "Commands and options" above, on a clip whose label was cleared (Premiere: Label › none, if offered) first.
- Trim head with a head fade: move the `HeadTransition`'s `Start`/`End` with the clip, or delete the transition if it no longer fits; keyframes stay in source time, so keys before the new In fall outside the clip.
  from: references/cutting-and-editing.md §5 "Trim head"
  prove with: in Premiere, trim the head of clip-b's A1 piece by 12 frames in step 13-gen (which has a fade-in) and, separately, of the PiP in step 12-gen (which has Position keys), Save a Copy each.
- Ripple trim: a tail trim that also shifts every later item on every track by −Δ.
  from: references/cutting-and-editing.md §5 "Trim tail"
  prove with: in Premiere, ripple-trim clip-a's tail by 24 frames in step 06 (B key / Shift-drag), Save a Copy.
- Ripple delete of a range [a, b) across all tracks: split items straddling a or b, delete the items inside (with their transitions), shift every later item and its transitions by −(b − a); clamp `MZ.WorkOutPoint` if it lies past the new end; `ExportSettings.Info.*` keeps the old end as stale UI state.
  from: references/cutting-and-editing.md §5 "Ripple delete"
  prove with: in Premiere, mark In/Out over 0:06–0:09 in step 11's `clip-a` (crossing V1, V2 and A1) and Extract, Save a Copy.
- Lift [a, b): delete the items in the range and leave a gap (there is no gap object).
  from: references/cutting-and-editing.md §5 "Lift"
  prove with: in Premiere, Lift 0:06–0:09 in step 08's `clip-a`, Save a Copy.
- Move an item by Δ (`Start`/`End` on the item, its partner and its transitions, re-sorting the list), and slip (shift In and Out together).
  from: references/cutting-and-editing.md §5 "Move an item"
  prove with: in Premiere, drag clip-b 1 s later in step 08, and separately slip it 12 frames (Y tool), Save a Copy each.
- Close all gaps: ripple-shift everything later on all tracks by each gap, so A/V and the tracks stay in sync.
  from: references/cutting-and-editing.md §5 "Close all gaps"
  prove with: in Premiere, Close Gap on the gap made by the Lift step above, Save a Copy.
- Insert at T (ripple): split items straddling T and shift every item with `Start ≥ T`; a new nested range is a clone of an existing pair with new Start/End/In/Out.
  from: references/cutting-and-editing.md §5 "Insert at T"
  prove with: in Premiere, insert clip-c at 0:05 in step 08's `clip-a` (comma key), Save a Copy.
- Change speed: insert `<PlaybackSpeed>v</PlaybackSpeed>` between `ClipID` and `InPoint`; keep the content (`End = Start + snap((Out − In)/v)`, then re-derive v) or keep the duration (`Out = In + (End − Start)·v`); ripple later items; keys move with the footage.
  from: references/cutting-and-editing.md §5 "Change speed" and references/effects.md
  prove with: the speed-change steps under "Track items, links and transitions" above.
- Delete a sequence marker: remove its list entry and its `Marker` object and re-index; with no markers left, remove the inner list; whether Premiere then drops the `MarkerOwner` is unknown.
  from: references/cutting-and-editing.md §7
  prove with: in Premiere, delete `Marker_Test` in step 11, then the other marker, Save a Copy after each.
- A nested item doesn't follow changes to its child sequence: if the child gets shorter or longer, the parent's In/Out and everything placed against it stay where they were; a rough cut is a run of abutting split pieces of one nested pair with monotonic source order.
  from: references/cutting-and-editing.md §4 and §8
  prove with: the nesting step under "Project panel, sequences, tracks" above, then ripple-delete 2 s inside the child and Save a Copy.
- Moving or trimming a clip moves its fade; deleting the clip deletes the fade.
  from: references/cutting-and-editing.md §6
  prove with: in Premiere, in step 13-gen move clip-b's A1 piece 1 s later, then delete it, Save a Copy after each.
- Transform positions: x ≥ ~1.54 or ≤ ~−0.54 is fully off-screen horizontally and y ≥ ~1.55 fully below, for clips whose frame matches the sequence; for a clip whose frame differs, the fractions are of the clip's frame.
  from: references/effects.md "Positions"
  prove with: `-gen-` steps from step 11 placing full-frame clip-a on V2 at Position 1.54:0.5 and clip-c (1280×720) at 1.0:0.5, opened in Premiere: check where each edge sits in the Program monitor.
- Transform params: Shutter Angle is 0 when the user disables blur that way; Sampling 0 = Bilinear, 1 = Bicubic; some Transforms name param [3] `Scale` (index 4 then named `" "`); a Transform applied in Premiere starts with Use Composition's Shutter Angle ticked.
  from: references/effects.md, Transform table
  prove with: in Premiere, apply Transform to clip-b in step 08, set Sampling to Bicubic and Shutter Angle 0, Save a Copy.
- Graphic Parameters, Mask and third-party effects can be read and their simple params edited in place, or cloned from an item that already has one (new ObjectIDs everywhere); chains on Essential Graphics layers or sequence master clips may lack the `Default*` flags.
  from: references/effects.md "Other effects", "Component IDs and order"
  prove with: in Premiere, add a Gaussian Blur to clip-b in step 08, Save a Copy; then a `-gen-` step changing its Blurriness, opened in Premiere.
- Easing semantics: Premiere's Ease In on the second key gives the off-screen `@linear` → on-screen `@ease` shape; `@ease:16.67` reproduces hand-adjusted 1/6 influences.
  from: references/effects.md "Common moves", "Key strings"
  prove with: in Premiere, key Position on clip-b in step 08 with Ease In on the second key, Save a Copy; compare with the script's `@ease` key.
- Clip gain advice: for one-off level changes prefer clip `Gain`; turning a default (`DefaultVol`) chain into an explicit one means creating both intrinsic components and all their params.
  from: references/effects.md "Audio volume"
  prove with: the clip gain and clip volume steps above.

### Task guides: media and bins, sequences, tracks

- Default labels per kind: bins Label 7 (Mango), sequences 5 (Forest), placed clips 1 (Iris) beyond `.mp4`.
  from: references/media-and-bins.md "Tree", "ClipProjectItem"
  prove with: in Premiere, New Bin and New Sequence in step 11, then place `sfx-pop.wav`, `still.jpg` and `lower-third.png` on a timeline, Save a Copy; read every `Column.PropertyText.Label` and `asl.clip.label.name`.
- `AutoCloned`=`true` may appear on an item; drop it on clones.
  from: references/media-and-bins.md "ClipProjectItem"
  prove with: a Premiere save where an item carries `AutoCloned` (duplicate a clip in the project panel in step 11, Save a Copy).
- Relinking a `FileProjectItem` means changing `FullPath`.
  from: references/media-and-bins.md "FileProjectItem"
  prove with: in Premiere, move `interview.txt`, relink the item when prompted, Save a Copy; diff against step 11.
- MOGRT master clips have a VideoClip plus a `BlueprintVideoComponentChain`; `.aegraphic` media use ImplementationID `ec341e53-60c2-4d89-abfc-bdb5c0ff2e0b` with an `ImporterPrefs` blob and `TimeDisplay`, CodecType `DLYM`, `Title` `Name/Name.aegraphic`; Premiere puts them in a `Motion Graphics Template Media` bin.
  from: references/media-and-bins.md "MasterClip", "Media", "Streams"
  prove with: in Premiere, drag a stock Essential Graphics title onto V2 of `clip-a` in step 11, Save a Copy.
- Mono audio: the MasterClip's chain has no `DefaultChannelVolumeComponentID`, `AudioChannelLayout` or `ChannelType`; a mono WAV's layout is `[{"channellabel":0}]`; a mono clip keeps its layout on a stereo track.
  from: references/media-and-bins.md "MasterClip", "Streams"; references/tracks.md "Track properties"
  prove with: add a mono WAV to `fixtures/premiere-pro/media/` (make_media.sh), import it in Premiere and place it on A2, Save a Copy.
- ClipLoggingInfo for media with a timecode start (CaptureMode and TimecodeFormat omitted, `MediaInPoint` = `Media/Start`, `MediaOutPoint` = in + duration) and for ProRes alpha renders (`MediaFrameRate` 10584000000).
  from: references/media-and-bins.md "ClipLoggingInfo"
  prove with: add a short MP4 with a 01:00:00:00 timecode and a ProRes 4444 alpha .mov to the fixture media, import both in Premiere, Save a Copy.
- Sequence master clips carry `InPoint`/`OutPoint` (the sequence's in/out marks) and the MasterClip's own clips may carry source in/out marks; `asl.clip.label.color` is optional.
  from: references/media-and-bins.md "Clips inside a MasterClip"; references/sequences.md "Nested sequences"
  prove with: in Premiere, set In and Out marks on the `clip-a` sequence and on `clip-b.mp4` in the Source Monitor in step 11, Save a Copy.
- After re-probing, Premiere writes `RelativePath` twice (also after `ContentAndMetadataState`).
  from: references/media-and-bins.md "Media"
  prove with: identify the step-19 Media that shows it and add a rule with a check, or rename a media file on disk and let Premiere relink it, Save a Copy.
- `FileKey` is unique per Media.
  from: references/media-and-bins.md "Media"
  prove with: a check over steps 01–23 (no new step needed) once a spec rule states it.
- Building a Media by hand: set `Duration`, `FrameRate`, `FrameRect` from ffprobe; round audio durations to whole samples and video to whole frames; omit `OriginalColorSpace` and the `*Uncertain` flags; omit the cache fields so Premiere re-probes.
  from: references/media-and-bins.md "Streams", "Import a media file"
  prove with: a `-gen-` step importing `tone-1k.wav` and `still.jpg` by script from step 11, opened in Premiere; Save a Copy to see what Premiere fills in.
- Import a media file by hand (the 18/15/9-object recipe with VideoClip/AudioClip/sources/SecondaryContent/channel serializers, optional Node ID, `Project/NextID`).
  from: references/media-and-bins.md "Import a media file"
  prove with: the `-gen-` import step above.
- Rename a bin, a media item or a sequence: `ProjectItem/Name`, plus `MasterClip/Name`, `ClipLoggingInfo/ClipName` and `Sequence/Name`; timeline instances keep their `SubClip/Name`.
  from: references/media-and-bins.md "Rename"
  prove with: in Premiere, rename the `footage` bin, `clip-b.mp4` and the `clip-a` sequence in step 11, Save a Copy; then a `-gen-` rename from step 11.
- Relink media to a new path: change `FilePath`, `ActualMediaFilePath`, every `RelativePath` and `Title`; drop the probe caches so Premiere re-probes; keep FileKey and ClipIDs; update streams, `OriginalDuration` and `MediaOutPoint` if the file differs.
  from: references/media-and-bins.md "Relink media to a new path"
  prove with: in Premiere, Replace Footage on `clip-b.mp4` with `clip-c-720p2997.mp4` in step 11, Save a Copy; then a `-gen-` relink of the same.
- Sequence Node keys and their values: `MZ.Sequence.VideoTimeDisplayFormat` 110 at 23.976 (media logging 104 for 30p, 102 for 29.97), `AudioTimeDisplayFormat` 200, preview codec `apcs` / class `????` / `QuickTime.epr`, `PreviewUseMaxBitDepth`/`RenderQuality` false, colour settings on `VideoTrackGroup`, `AudioTrackGroup/NumAdaptiveChannels` 2 with master `SubType` 3.
  from: references/sequences.md "Settings table"
  prove with: rule checks over steps 03–23 (no new step needed) once the spec states them.
- Changing a sequence's frame size or frame rate: `VideoTrackGroup/FrameRect`, preview size and every item's `FrameRect`; both group `FrameRate`s, the time display format, re-snapping Starts/Ends, In/Out and keyframes, and recomputing work area, zoom and `OriginalDuration`.
  from: references/sequences.md "Changing frame size or frame rate"
  prove with: in Premiere, Sequence Settings on `Custom` in step 11: 1280×720, then 25 fps, Save a Copy after each.
- Emptying a copy of a populated sequence by hand (drop TrackItems and Links, set the empty-sequence values, remove the MasterClip clips' In/Out).
  from: references/sequences.md "Clone an existing sequence"
  prove with: a `-gen-` step from step 11 that copies `clip-a` and empties it, opened in Premiere.
- A sequence from scratch: the 54 objects with group skeletons (`VideoTrackGroup` colour settings, `NextTrackID` 2/3, `DataTrackGroup`, the sequence MasterClip side with Forest labels and `monitor.edit.time`).
  from: references/sequences.md "From scratch"
  prove with: a `-gen-` step from step 00 that writes a new empty sequence, opened in Premiere.
- Add an audio track (clone an empty `AudioClipTrack` and its 7 owned objects, take `NextTrackID`, append to `Tracks` and the master's `Inlet/Sources`) or a video track (one object).
  from: references/tracks.md "Add an audio track", "Add a video track"
  prove with: in Premiere, Add Track (one video, one audio) to `clip-a` in step 11, Save a Copy; then a `-gen-` add from step 11.
- Reorder tracks (permute `Tracks` and `Inlet/Sources`, rewrite the four Index values), and move clips from one track to another.
  from: references/tracks.md "Reorder tracks"
  prove with: in Premiere, drag clip-a's V1 piece to V3 in step 11, Save a Copy; then reorder audio tracks in the Audio Track Mixer, Save a Copy.
- Delete an empty track (remove its entries and objects, re-index later tracks, keep `NextTrackID`).
  from: references/tracks.md "Delete an empty track"
  prove with: in Premiere, Delete Track on the empty V3 of `clip-a` in step 11, Save a Copy.
- Solo (`AMM.CurrentSolo`), sync lock, the track output toggle, track volume and pan values and keyframes, track effects, submixes (`DefaultAudioSubmix*`), output assignment other than `Assign` 0, mono/5.1/adaptive tracks.
  from: references/tracks.md "Track properties", "Master track and mixer"
  prove with: in Premiere on `clip-a` in step 11, one Save a Copy per change: solo A1; sync lock off on V1; eye off on V2; A2 volume −6 dB; A2 pan left; add a submix.
- Source patch values: `MZ.SourceTrackNumber` 0 on V1/A1 and −1 elsewhere, `MZ.SourceTrackState` 0 or 2.
  from: references/tracks.md "Track properties"
  prove with: rule checks over steps 03–23 (no new step needed) once the spec states them.
