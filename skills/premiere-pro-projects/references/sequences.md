# Sequences: structure, settings, length, creation

Recipes for sequences. The rules are in spec [§7](spec/07-sequences.md#7-sequences), each proven on the steps it cites ([§0](spec/README.md#0-conventions)). The steps have two 1920×1080 23.976 sequences with 48 kHz stereo audio, one made from a clip (02→03) and one empty with custom settings (03→04), then edited, plus script-written copies (17-gen, 18-gen). Track internals: `tracks.md`. Effect chains: `effects.md`. Cloning rules: `object-surgery.md`.

## Object graph

```
BinProjectItem (seq) Items/Item ─► ClipProjectItem ─► MasterClip ─┬─ Clips/Clip 0 AudioClip ─► AudioSequenceSource ─► Sequence
                                                                 │                 └─ SecondaryContents ─► SecondaryContent x2 (ChannelIndex 0,1) ─► AudioSequenceSource
                                                                 ├─ Clips/Clip 1 VideoClip ─► VideoSequenceSource ─► Sequence
                                                                 ├─ LoggingInfo ─► ClipLoggingInfo (ClipName only)
                                                                 ├─ AudioComponentChains ─► AudioComponentChain (DefaultVol, empty)
                                                                 └─ AudioClipChannelGroups ─► ClipChannelGroupVectorSerializer ─► ClipChannelVectorSerializer (ChannelType 1) ─► ClipChannelSerializer x2
Sequence ─► TrackGroups: VideoTrackGroup, AudioTrackGroup (─► MasterTrack AudioMixTrack), DataTrackGroup
         ─► PersistentGroupContainer/LinkContainer/Links ─► Link (one per linked A/V pair)
         ─► MarkerOwner ─► Markers ─► Marker (only once it has sequence markers)
```

- `Sequence` has an `ObjectUID` and is referenced only by its two `*SequenceSource` objects; find a sequence by `Name`, never by ID (spec [§7.1](spec/07-sequences.md#71-the-sequence-object)). `Project`'s `MZ.PrefixKey.OpenSequenceGuidList.N` lists open timelines by UID, as text [O: steps 02→03, 03→04 #project.open-sequence-list].
- An empty 3+3 sequence is 54 top-level objects: 65 for New Sequence from Clip (54 + 11 for the placed clip) and 62 for an empty one with 3 video and 4 audio tracks (54 + 8 for the extra audio track) [O: steps 02→03, 03→04 #seq.empty-sequence].

ClassIDs and Versions (from [`prproj-classes.md`](prproj-classes.md)):

| Object | ClassID | Ver |
|---|---|---|
| Sequence | `6a15d903-8739-11d5-af2d-9b7855ad8974` | 12 |
| VideoTrackGroup | `9e9abf7a-0918-49c2-91ae-991b5dde77bb` | 13 |
| AudioTrackGroup | `9b9238b9-53a8-4cc3-b03f-b36246d052e6` | 6 |
| DataTrackGroup | `b714b71d-6838-48dd-9b77-db19088ced7e` | 1 |
| VideoSequenceSource | `4752dfa9-7a7e-4a3b-a25b-cafde1a8d036` | 3 |
| AudioSequenceSource | `e8d4cc83-38cb-491f-9d94-e5f7e3b205ee` | 7 |
| SecondaryContent | `f9d004b5-cb04-4e2f-af6f-64fadc2c4be9` | 1 |
| ClipProjectItem / MasterClip | `cb4e0ed7-aca1-4171-8525-e3658dec06dd` / `fb11c33a-b0a9-4465-aa94-b6d5db2628cf` | 1 / 12 |
| ClipLoggingInfo | `77ab7fdd-dcdf-465d-9906-7a330ca1e738` | 10 |
| AudioClip / VideoClip | `b8830d03-de02-41ee-84ec-fe566dc70cd9` / `9308dbef-2440-4acb-9ab2-953b9a4e82ec` | 8 / 11 |
| ClipChannelGroupVectorSerializer / ClipChannelVectorSerializer / ClipChannelSerializer | `a3127a8c-95d4-456e-a7f5-171b3f922426` / `333d203b-3a53-4195-8894-fc7523ff3dc7` / `5c89aa7a-89a6-4483-becd-f2b1def42316` | 1 |
| Link | `149d4ea5-a7d4-4b34-9bb7-16d783904bf2` | 1 |

## The Sequence object

Trimmed, as Premiere writes it (spec [§7.1](spec/07-sequences.md#71-the-sequence-object)):

```xml
<Sequence ObjectUID="{SEQ_UID}" ClassID="6a15d903-8739-11d5-af2d-9b7855ad8974" Version="12">
	<Node Version="1">
		<Properties Version="1">
			<AMM.CurrentSolo>[]</AMM.CurrentSolo>
			<MZ.EditLine>{PLAYHEAD_TICKS}</MZ.EditLine>
			<MZ.Sequence.AudioTimeDisplayFormat>200</MZ.Sequence.AudioTimeDisplayFormat>
			<MZ.Sequence.VideoTimeDisplayFormat>110</MZ.Sequence.VideoTimeDisplayFormat>
			<MZ.WorkInPoint>0</MZ.WorkInPoint>
			<MZ.WorkOutPoint>{TICKS}</MZ.WorkOutPoint>
			<Monitor.ProgramZoomIn>0</Monitor.ProgramZoomIn>
			<Monitor.ProgramZoomOut>{TICKS}</Monitor.ProgramZoomOut>
			<TL.SQTimePerPixel>0.40053404539385845</TL.SQTimePerPixel>
			<!-- TL.SQ* / AM.* scroll and layout keys omitted -->
			<MZ.Sequence.EditingModeGUID>795454d9-d3c2-429d-9474-923ab13b7018</MZ.Sequence.EditingModeGUID>
			<MZ.Sequence.PreviewUseMaxBitDepth>false</MZ.Sequence.PreviewUseMaxBitDepth>
			<MZ.Sequence.PreviewUseMaxRenderQuality>false</MZ.Sequence.PreviewUseMaxRenderQuality>
			<MZ.Sequence.PreviewRenderingPresetPath>EncoderPresets/SequencePreview/795454d9-d3c2-429d-9474-923ab13b7018/QuickTime.epr</MZ.Sequence.PreviewRenderingPresetPath>
			<MZ.Sequence.PreviewRenderingPresetCodec>1634755443</MZ.Sequence.PreviewRenderingPresetCodec>
			<MZ.Sequence.PreviewRenderingClassID>1061109567</MZ.Sequence.PreviewRenderingClassID>
			<MZ.Sequence.PreviewFrameSizeWidth>1920</MZ.Sequence.PreviewFrameSizeWidth>
			<MZ.Sequence.PreviewFrameSizeHeight>1080</MZ.Sequence.PreviewFrameSizeHeight>
			<HSL.TimelinePatchingAndTargeting.AudioPatches{GUID}>[{"mNumber":0,"mState":2},{"mNumber":-1,"mState":0},{"mNumber":-1,"mState":0}]</HSL.TimelinePatchingAndTargeting.AudioPatches{GUID}>
		</Properties>
	</Node>
	<!-- <MarkerOwner Version="1"><Markers ObjectRef="{MK}"/></MarkerOwner> here, once the sequence has markers -->
	<PersistentGroupContainer Version="1"><LinkContainer Version="1"><Links Version="1">
		<Link Index="0" ObjectRef="{LINK}"/>
	</Links></LinkContainer></PersistentGroupContainer>
	<TrackGroups Version="1">
		<TrackGroup Version="1" Index="0"><First>228cda18-3625-4d2d-951e-348879e4ed93</First><Second ObjectRef="{VTG}"/></TrackGroup>
		<TrackGroup Version="1" Index="1"><First>80b8e3d5-6dca-4195-aefb-cb5f407ab009</First><Second ObjectRef="{ATG}"/></TrackGroup>
		<TrackGroup Version="1" Index="2"><First>d8143ffe-eec4-4d2a-a909-d5f7bf094dc5</First><Second ObjectRef="{DTG}"/></TrackGroup>
	</TrackGroups>
	<Name>{NAME}</Name>
	<PreviewFormatIdentifier>fc3cd4d9-d839-8259-9276-05c5000000ea</PreviewFormatIdentifier>
</Sequence>
```

- `First` = the media-type GUID: video `228cda18-…`, audio `80b8e3d5-…`, data `d8143ffe-…`. The same GUIDs are every track's and every `ClipItems`/`TransitionItems` `MediaType`. Constants; never regenerate them [O: steps 03–23 #seq.media-types].
- `HSL.TimelinePatchingAndTargeting.*Patches…` is source-patching view state, added when another sequence is opened. Leave it as is [O: steps 03→04 #tracks.patching-state].

## Settings

| Setting | Element path | Rule |
|---|---|---|
| Frame size | `VideoTrackGroup/FrameRect` (`0,0,1920,1080`), repeated in Node `MZ.Sequence.PreviewFrameSizeWidth`/`Height` and on every `VideoClipTrackItem` in a Premiere save, even one holding a 1280×720 clip | spec [§7.3](spec/07-sequences.md#73-settings) |
| Frame rate | `VideoTrackGroup/TrackGroup/FrameRate` = `DataTrackGroup/TrackGroup/FrameRate` (`10594584000` ticks per frame = 23.976) | spec §7.3; tick values in [§3](spec/03-value-encodings.md#3-value-encodings) |
| Pixel aspect | `VideoClipTrackItem/PixelAspectRatio` (`1,1`), per item, not on the sequence | spec §7.3 |
| Audio sample rate | `AudioTrackGroup/TrackGroup/FrameRate` (`5292000` ticks per sample = 48 kHz) | spec §7.3 |
| Editing mode | Node `MZ.Sequence.EditingModeGUID` (`795454d9-d3c2-429d-9474-923ab13b7018`), a constant | [O: steps 03–23 #seq.editing-mode-guid] |
| Preview file format | `Sequence/PreviewFormatIdentifier`; `fc3cd4d9-d839-8259-9276-05c5000000ea` on every 1920×1080 23.976 sequence Premiere made. Copy it from a sequence of the same format; never generate one | [O: steps 02→03, 03→04 #seq.preview-format] |
| Work area, playhead | Node `MZ.WorkInPoint`/`MZ.WorkOutPoint` (not the length), `MZ.EditLine` (view state) | spec §7.3, §7.4 |
| Sequence markers | `Sequence/MarkerOwner` → `Markers` → `Marker` | spec [§13](spec/13-markers.md#13-markers) |
| New-sequence defaults | `DefaultSequenceSettings` under `ProjectSettings`: presets for new sequences, not a description of any existing one | [O: steps 00–23 #project.settings-owners] |

Copy every other Node key (time display formats, preview codec and quality, colour settings on `VideoTrackGroup`) unchanged with the sequence. Changing frame size, frame rate or audio rate, and field type, start timecode and VR settings, aren't covered ([§18](spec/18-not-observed.md)): ask the user to change them in Premiere (Sequence › Sequence Settings).

## Length and track listing

Length, work area and `OriginalDuration` rules: spec [§7.4](spec/07-sequences.md#74-length). `Start` is omitted when 0, so read it as `int(Start or 0)`. What Premiere did to each value as the `clip-a` sequence was edited [O: steps 03–08 #seq.zoomout-follows] [O: steps 03–08 #seq.workout-fixed] [O: steps 03–08 #seq.original-duration-rises]:

| Step | Clips end at | `Monitor.ProgramZoomOut` | `MZ.WorkOutPoint` | `*SequenceSource/OriginalDuration` |
|---|---|---|---|---|
| 03 new from clip | 0:19.978 | 0:19.978 | 0:19.978 | 0:19.978 |
| 05 add a clip | 0:39.957 | 0:39.957 | 0:19.978 | 0:39.957 |
| 06 razor | 0:39.957 | 0:39.957 | 0:19.978 | 0:39.957 |
| 07 trim | 0:38.038 | 0:38.038 | 0:19.978 | 0:39.957 |
| 08 ripple delete | 0:23.023 | 0:23.023 | 0:19.978 | 0:39.957 |

```python
seq = next(e for e in root if e.tag == 'Sequence' and e.findtext('Name') == NAME)
for tg in seq.findall('TrackGroups/TrackGroup'):
    grp = ids[tg.find('Second').get('ObjectRef')]          # Video/Audio/DataTrackGroup
    for n, t in enumerate(grp.findall('TrackGroup/Tracks/Track')):   # Index 0 = V1 / A1
        trk = ids[t.get('ObjectURef')]
        items = trk.findall('ClipTrack/ClipItems/TrackItems/TrackItem')   # NOT './/TrackItems'
        ends = [int(ids[i.get('ObjectRef')].findtext('ClipTrackItem/TrackItem/End')) for i in items]
```

`prproj.py cuts` numbers tracks across both groups (`VideoClipTrack[0..3]`, then `AudioClipTrack[4..]`). It reads only `ClipTrack/ClipItems/TrackItems/TrackItem`, so transitions (in `TransitionItems`) don't appear as items.

Using a sequence as a clip in another sequence (nesting) isn't covered ([§18](spec/18-not-observed.md)): ask the user to nest in Premiere.

## Creating a sequence

### What Premiere writes

- **New Sequence from Clip** goes in the clip's bin, named after the clip without its extension, with 3 video and 3 audio tracks and the clip linked on V1/A1 at 0; `Monitor.ProgramZoomOut`, `MZ.WorkOutPoint` and `OriginalDuration` = the clip's end [O: steps 02→03 #seq.new-from-clip].
- **File › New › Sequence** goes in the root bin with the chosen settings, empty: the custom preset gave 3 video and 4 audio tracks; `Monitor.ProgramZoomOut` and `OriginalDuration` 0, `MZ.WorkOutPoint` `15235011792000` (1438 frames at 23.976, about 60 s) [O: steps 03→04 #seq.new-sequence-dialog].
- An empty sequence has `MZ.EditLine` and `MZ.WorkInPoint` 0, an empty `LinkContainer`, no `TrackItems`, and a MasterClip with no `Node` whose clips have no In/Out [O: steps 02→03, 03→04 #seq.empty-sequence]. The new sequence's UID joins `MZ.PrefixKey.OpenSequenceGuidList.N`, and `MZ.NextSequenceIndex` counts sequences for default names (spec [§5](spec/04-object-graph-and-project.md#5-project-and-settings)).

### With the scripts: copy an existing sequence

`prproj.py backup-seq FILE OUT --seq NAME --name COPY` duplicates a sequence inside the project, in the same bin, with new IDs and GUIDs; the copy shares the media MasterClips [V: step 17-gen #panel.clone-shares-masterclips]. To make a new sequence, copy an empty one with the settings you need and place clips into it [V: steps 04→18-gen #seq.clone-empty-new]. If the project has no sequence with the right settings, ask the user to make one in Premiere (File › New › Sequence) and save.

Building a sequence from scratch, or emptying a copy of a populated sequence by hand, isn't covered ([§18](spec/18-not-observed.md)).
