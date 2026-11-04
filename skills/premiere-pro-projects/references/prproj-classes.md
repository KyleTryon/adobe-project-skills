# .prproj class catalogue

Generated from [`prproj-schema.json`](prproj-schema.json) by `scripts/schema_dump.py --write`; don't edit by hand. Read [the spec](spec/README.md) for the rules; this is the structure: for each top-level object class, its ClassID, Version, identity attribute, how many were seen and in which steps, which classes reference it, and every element path under it in the order Premiere writes them, with how often it was present and what kind of value it holds (`int`, `int64`, `guid`, `path`, `base64`, …, plus the values seen when there were few). Nothing from the projects' content is included. `→ X` is a reference to class X.

Evidence: steps 00–23 in `fixtures/premiere-pro/steps/` (24 files). Premiere 26.5.2x5. A class or path that isn't here hasn't been seen in the steps, which doesn't mean Premiere never writes it; `prproj.py validate` warns when a project has one.


## Index

| Class | What it is | Explained in |
|---|---|---|
| [`AudioClip`](#audioclip) | audio clip instance: Source, ClipID, In/OutPoint, SecondaryContents, channel layout | [04](spec/04-object-graph-and-project.md), [09](spec/09-track-items-and-links.md) |
| [`AudioClipTrack`](#audiocliptrack) | audio track (A1, A2, …) | [02](spec/02-document-structure.md), [08](spec/08-tracks.md) |
| [`AudioClipTrackItem`](#audiocliptrackitem) | audio item on a track: Start/End, component chain, `<ID>` GUID | [02](spec/02-document-structure.md), [09](spec/09-track-items-and-links.md) |
| [`AudioCompileSettings`](#audiocompilesettings) | audio side of a compile setting | — |
| [`AudioComponentChain`](#audiocomponentchain) | audio stack (item, MasterClip, track) | [08](spec/08-tracks.md), [12](spec/12-effects-and-keyframes.md) |
| [`AudioComponentParam`](#audiocomponentparam) | audio effect parameter: float (Level, Balance, Volume) or bool (Mute, Bypass) | [02](spec/02-document-structure.md), [12](spec/12-effects-and-keyframes.md) |
| [`AudioFader`](#audiofader) | track fader | [08](spec/08-tracks.md), [12](spec/12-effects-and-keyframes.md) |
| [`AudioMediaSource`](#audiomediasource) | Clip source → Media (audio) | [06](spec/06-project-panel.md) |
| [`AudioMeter`](#audiometer) | track meter | [08](spec/08-tracks.md), [12](spec/12-effects-and-keyframes.md) |
| [`AudioMixTrack`](#audiomixtrack) | sequence master bus | [02](spec/02-document-structure.md), [08](spec/08-tracks.md) |
| [`AudioSequenceSource`](#audiosequencesource) | Clip source → Sequence (a sequence used as a clip), audio | [06](spec/06-project-panel.md) |
| [`AudioSettings`](#audiosettings) | audio settings shell owned by project/compile settings | [04](spec/04-object-graph-and-project.md) |
| [`AudioStream`](#audiostream) | duration, layout, peak/conform cache paths | [06](spec/06-project-panel.md) |
| [`AudioTrackGroup`](#audiotrackgroup) | audio tracks + MasterTrack | [02](spec/02-document-structure.md), [07](spec/07-sequences.md) |
| [`AudioTrackInlet`](#audiotrackinlet) | master inlet listing the source tracks | [02](spec/02-document-structure.md), [08](spec/08-tracks.md), [16](spec/16-checklist.md) |
| [`AudioTransitionTrackItem`](#audiotransitiontrackitem) | audio fade or crossfade on a track (`TransitionItems`, `HeadTransition`/`TailTransition`) | [11](spec/11-transitions.md) |
| [`BinProjectItem`](#binprojectitem) | bin | [02](spec/02-document-structure.md), [06](spec/06-project-panel.md) |
| [`ClipChannelGroupVectorSerializer`](#clipchannelgroupvectorserializer) | MasterClip audio channel groups (empty if no audio) | — |
| [`ClipChannelSerializer`](#clipchannelserializer) | one channel: `mSourceChannelIndex`, `SourceClipIndex` | — |
| [`ClipChannelVectorSerializer`](#clipchannelvectorserializer) | one group; `ChannelType` 1 stereo / 0 mono | — |
| [`ClipLoggingInfo`](#cliplogginginfo) | ClipName, media in/out, frame rate, timecode format | — |
| [`ClipProjectItem`](#clipprojectitem) | project-panel entry → MasterClip | [02](spec/02-document-structure.md) |
| [`CompileSettings`](#compilesettings) | export/compile presets (movie, still, audio, custom, video preview) | — |
| [`DataMediaSource`](#datamediasource) | TranscriptClip source | [14](spec/14-transcripts-and-captions.md) |
| [`DataStream`](#datastream) | stream of the synthetic transcript Media | [06](spec/06-project-panel.md), [14](spec/14-transcripts-and-captions.md) |
| [`DataTrackGroup`](#datatrackgroup) | caption/data tracks group | [07](spec/07-sequences.md), [14](spec/14-transcripts-and-captions.md) |
| [`DefaultPanProcessor`](#defaultpanprocessor) | master panner | [08](spec/08-tracks.md) |
| [`DefaultSequenceSettings`](#defaultsequencesettings) | defaults for new sequences | [04](spec/04-object-graph-and-project.md) |
| [`DummyCaptureSettings`](#dummycapturesettings) | capture settings placeholder | — |
| [`ExternallyProvidedTranscriptDocument`](#externallyprovidedtranscriptdocument) | FlatBuffer `TranscriptData` | [14](spec/14-transcripts-and-captions.md) |
| [`FileProjectItem`](#fileprojectitem) | project item for a non-media file (e.g. a .txt) | [02](spec/02-document-structure.md), [06](spec/06-project-panel.md) |
| [`IngestSettings`](#ingestsettings) | ingest options | — |
| [`Link`](#link) | ties the linked A/V track items | [09](spec/09-track-items-and-links.md) |
| [`Marker`](#marker) | one marker: a DVAMarker JSON string (name, comment, type, start time, colour) | [02](spec/02-document-structure.md), [13](spec/13-markers.md), [16](spec/16-checklist.md) |
| [`Markers`](#markers) | marker list of a master clip (empty until a marker is added) or a sequence | [13](spec/13-markers.md), [16](spec/16-checklist.md) |
| [`MasterClip`](#masterclip) | clip identity: Clips list, logging, channel map | [02](spec/02-document-structure.md), [06](spec/06-project-panel.md), [09](spec/09-track-items-and-links.md), [14](spec/14-transcripts-and-captions.md) |
| [`Media`](#media) | one file on disk: paths, importer, streams | [02](spec/02-document-structure.md), [14](spec/14-transcripts-and-captions.md), [17](spec/17-load-and-save.md) |
| [`PointComponentParam`](#pointcomponentparam) | 2-D point parameter (Position, Anchor Point) | [12](spec/12-effects-and-keyframes.md) |
| [`Project`](#project) | root: properties, settings refs, `NextID` | [02](spec/02-document-structure.md), [04](spec/04-object-graph-and-project.md), [06](spec/06-project-panel.md), [16](spec/16-checklist.md) |
| [`ProjectSettings`](#projectsettings) | project-wide settings | — |
| [`RootProjectItem`](#rootprojectitem) | "Root Bin" | [02](spec/02-document-structure.md), [06](spec/06-project-panel.md) |
| [`ScratchDiskSettings`](#scratchdisksettings) | scratch disk locations | — |
| [`SecondaryContent`](#secondarycontent) | per-channel ref from an AudioClip to its source | [02](spec/02-document-structure.md), [09](spec/09-track-items-and-links.md) |
| [`Sequence`](#sequence) | timeline: TrackGroups, Links, view state | [02](spec/02-document-structure.md), [07](spec/07-sequences.md), [09](spec/09-track-items-and-links.md) |
| [`StereoToStereoPanProcessor`](#stereotostereopanprocessor) | track panner | [08](spec/08-tracks.md) |
| [`SubClip`](#subclip) | track item → (MasterClip, Clip); `Name` shown on the timeline | [09](spec/09-track-items-and-links.md), [11](spec/11-transitions.md) |
| [`TranscriptClip`](#transcriptclip) | Speech-to-Text clip in a MasterClip | [14](spec/14-transcripts-and-captions.md) |
| [`VideoClip`](#videoclip) | video clip instance: Source, ClipID, In/OutPoint, label | [04](spec/04-object-graph-and-project.md), [09](spec/09-track-items-and-links.md) |
| [`VideoClipTrack`](#videocliptrack) | video track (V1, V2, …) | [02](spec/02-document-structure.md), [08](spec/08-tracks.md) |
| [`VideoClipTrackItem`](#videocliptrackitem) | video item on a track: Start/End, component chain | [09](spec/09-track-items-and-links.md) |
| [`VideoCompileSettings`](#videocompilesettings) | video side of a compile setting | — |
| [`VideoComponentChain`](#videocomponentchain) | video effect stack (track item or track group) | [12](spec/12-effects-and-keyframes.md) |
| [`VideoComponentParam`](#videocomponentparam) | video effect parameter: float, bool, enum or colour (Scale, Rotation, Opacity, Skew, …) | [02](spec/02-document-structure.md), [12](spec/12-effects-and-keyframes.md) |
| [`VideoFilterComponent`](#videofiltercomponent) | one effect; `MatchName` e.g. `AE.ADBE Geometry2` (Transform) | [12](spec/12-effects-and-keyframes.md) |
| [`VideoMediaSource`](#videomediasource) | Clip source → Media (video) | [06](spec/06-project-panel.md) |
| [`VideoSequenceSource`](#videosequencesource) | Clip source → Sequence (a sequence used as a clip), video | [06](spec/06-project-panel.md) |
| [`VideoSettings`](#videosettings) | video settings shell owned by project/compile settings | [04](spec/04-object-graph-and-project.md) |
| [`VideoStream`](#videostream) | duration, fps, size, codec FourCC, alpha | [06](spec/06-project-panel.md) |
| [`VideoTrackGroup`](#videotrackgroup) | video tracks, sequence FrameRate/FrameRect | [07](spec/07-sequences.md), [09](spec/09-track-items-and-links.md) |
| [`WorkspaceSettings`](#workspacesettings) | workspace state | — |

## Classes

### AudioClip

Audio clip instance: Source, ClipID, In/OutPoint, SecondaryContents, channel layout.

ClassID `b8830d03-de02-41ee-84ec-fe566dc70cd9` · Version 8 · ObjectID · 231 seen, in steps 01–23
Referenced by: MasterClip (186), SubClip (45)

| Path | Present | Holds |
|---|---|---|
| `Clip/Node/Properties/asl.clip.label.color` | always | int (19005, 480554, 6769408) |
| `Clip/Node/Properties/asl.clip.label.name` | always | string |
| `Clip/MarkerOwner/Markers@ObjectRef` | 183/231 | → Markers |
| `Clip/Source@ObjectRef` | always | → AudioMediaSource, AudioSequenceSource |
| `Clip/ClipID` | always | guid |
| `Clip/InPoint` | 45/231 | int×39, int64×6 |
| `Clip/OutPoint` | 45/231 | int64 |
| `Clip/InUse` | 186/231 | bool (false) |
| `SecondaryContents/SecondaryContentItem@ObjectRef` | always | → SecondaryContent |
| `SecondaryContents/SecondaryContentItem@Index` | always | index |
| `AudioChannelLayout` | always | json |

### AudioClipTrack

Audio track (A1, A2, …).

ClassID `097f6203-99ae-11d5-84f2-8cf14bde7040` · Version 7 · ObjectUID · 170 seen, in steps 03–23
Referenced by: AudioTrackGroup (170), AudioTrackInlet (170)

| Path | Present | Holds |
|---|---|---|
| `ClipTrack/Track/Node/Properties/TL.SQTrackExpanded` | always | int (0) |
| `ClipTrack/Track/Node/Properties/TL.SQTrackExpandedHeight` | always | int (41, 210) |
| `ClipTrack/Track/Node/Properties/MZ.SourceTrackState` | 147/170 | int (0, 2) |
| `ClipTrack/Track/Node/Properties/MZ.SourceTrackNumber` | 147/170 | int (0, -1) |
| `ClipTrack/Track/Node/Properties/TL.SQTrackAudioKeyframeStyle` | always | int (0) |
| `ClipTrack/Track/Node/Properties/TL.SQTrackShy` | always | int (0) |
| `ClipTrack/Track/Node/Properties/CM.KeyframeMode` | always | bool (true) |
| `ClipTrack/Track/Node/Properties/MZ.TrackTargeted` | always | int (1) |
| `ClipTrack/Track/Node/Properties/MZ.TrackName` | 1/170 | string |
| `ClipTrack/Track/ID` | always | int (2, 3, 4, 5) |
| `ClipTrack/Track/MediaType` | always | guid |
| `ClipTrack/Track/Index` | always | int (0, 1, 2, 3) |
| `ClipTrack/ClipItems/TrackItems/TrackItem@ObjectRef` | 28/170 | → AudioClipTrackItem |
| `ClipTrack/ClipItems/TrackItems/TrackItem@Index` | 28/170 | index |
| `ClipTrack/ClipItems/MediaType` | always | guid |
| `ClipTrack/ClipItems/Index` | always | int (0, 1, 2, 3) |
| `ClipTrack/TransitionItems/TrackItems/TrackItem@ObjectRef` | 4/170 | → AudioTransitionTrackItem |
| `ClipTrack/TransitionItems/TrackItems/TrackItem@Index` | 4/170 | index |
| `ClipTrack/TransitionItems/MediaType` | always | guid |
| `ClipTrack/TransitionItems/Index` | always | int (0, 1, 2, 3) |
| `AudioTrack/ComponentOwner/Components@ObjectRef` | always | → AudioComponentChain |
| `AudioTrack/Panner@ObjectRef` | always | → StereoToStereoPanProcessor |
| `AudioTrack/ID` | always | guid |
| `AudioTrack/NextPannerID` | always | int64 |

### AudioClipTrackItem

Audio item on a track: Start/End, component chain, `<ID>` GUID.

ClassID `064ec682-9ba6-11d5-af2d-9ca32c7d6164` · Version 11 · ObjectID · 45 seen, in steps 03–23
Referenced by: Link (45), AudioClipTrack (45)

| Path | Present | Holds |
|---|---|---|
| `ClipTrackItem/ComponentOwner/Components@ObjectRef` | always | → AudioComponentChain |
| `ClipTrackItem/TrackItem/Node/Properties/MZ.AudioCategorization.AudioCategorizationAdjustmentMode` | 44/45 | string |
| `ClipTrackItem/TrackItem/Node/Properties/ESP.AdjustmentsModeID` | 44/45 | string |
| `ClipTrackItem/TrackItem/Node/Properties/monitor.show.audio.waveform` | 2/45 | bool (false) |
| `ClipTrackItem/TrackItem/Node/Properties/monitor.take.audio.linked` | 2/45 | bool (true) |
| `ClipTrackItem/TrackItem/Node/Properties/ESP.ClipMixTypeID` | 44/45 | int (1, 4) |
| `ClipTrackItem/TrackItem/Node/Properties/ESP.Tag` | 44/45 | string |
| `ClipTrackItem/TrackItem/Node/Properties/ESP.PresetGuid` | 44/45 | guid |
| `ClipTrackItem/TrackItem/Node/Properties/MZ.EssentialSound.AdjustmentModeWorkflowType` | 44/45 | int (2) |
| `ClipTrackItem/TrackItem/Node/Properties/ESP.RestorationSection.4` | 5/45 | float |
| `ClipTrackItem/TrackItem/Node/Properties/ESP.RestorationSection.9` | 5/45 | int (60) |
| `ClipTrackItem/TrackItem/Node/Properties/ESP.ClaritySection.2` | 5/45 | int (3) |
| `ClipTrackItem/TrackItem/Node/Properties/ESP.SoundEffectsSection.3` | 5/45 | int (2) |
| `ClipTrackItem/TrackItem/Start` | 17/45 | int64 |
| `ClipTrackItem/TrackItem/End` | always | int64 |
| `ClipTrackItem/SubClip@ObjectRef` | always | → SubClip |
| `ClipTrackItem/HeadTransition@ObjectRef` | 4/45 | → AudioTransitionTrackItem |
| `ClipTrackItem/TailTransition@ObjectRef` | 5/45 | → AudioTransitionTrackItem |
| `ID` | always | guid |
| `PreRenderComponentChainHashVersion` | always | int (1) |

### AudioCompileSettings

Audio side of a compile setting.

ClassID `34b10007-ab6d-49a7-bac5-7b60d919e387` · Version 6 · ObjectID · 144 seen, in steps 00–23
Referenced by: CompileSettings (120), ProjectSettings (24)

| Path | Present | Holds |
|---|---|---|
| `AudioSettings@ObjectRef` | always | → AudioSettings |
| `Interleave` | always | int (1) |
| `SampleType` | always | int (3) |
| `Compressor` | always | int64 |

### AudioComponentChain

Audio stack (item, MasterClip, track).

ClassID `3cb131d1-d3c0-47ae-a19a-bdf75ea11674` · Version 4 · ObjectID · 449 seen, in steps 01–23
Referenced by: MasterClip (186), AudioClipTrack (170), AudioMixTrack (48), AudioClipTrackItem (45)

| Path | Present | Holds |
|---|---|---|
| `DefaultVol` | 231/449 | bool (true) |
| `DefaultVolumeComponentID` | 231/449 | int (1) |
| `DefaultChannelVolumeComponentID` | 231/449 | int (2) |
| `ComponentChain` | always | empty |
| `ComponentChain/Components/Component@ObjectRef` | 218/449 | → AudioFader, AudioMeter |
| `ComponentChain/Components/Component@Index` | 218/449 | index |
| `ComponentChain/Node/Properties/MZ.ComponentChain.ActiveComponentID` | 92/449 | int (1) |
| `ComponentChain/Node/Properties/MZ.ComponentChain.ActiveComponentParamIndex` | 92/449 | int64 |
| `AudioChannelLayout` | always | json |
| `ChannelType` | always | int (1) |

### AudioComponentParam

Audio effect parameter: float (Level, Balance, Volume) or bool (Mute, Bypass).

ClassID `a714635e-a628-4b27-9d59-77eba47dbc1a`, `32657501-3aa4-445f-a49b-d09ecb9fa1ae` · Version 10 · ObjectID · 606 seen, in steps 03–23
Referenced by: AudioFader (436), StereoToStereoPanProcessor (170)

| Path | Present | Holds |
|---|---|---|
| `StartKeyframe` | 175/606 | keyframes |
| `CurrentValue` | 175/606 | float×170, bool×5 (true) |
| `Name` | always | string |
| `RangeLocked` | 436/606 | bool (false) |
| `UnitsString` | 218/606 | string |
| `UpperBound` | 218/606 | float |
| `IsInverted` | 170/606 | bool (true) |

### AudioFader

Track fader.

ClassID `1a38c583-ed5c-11d5-abc4-c1cbf61ec590` · Version 3 · ObjectID · 218 seen, in steps 03–23
Referenced by: AudioComponentChain (218)

| Path | Present | Holds |
|---|---|---|
| `AudioComponent/Component/Params/Param@ObjectRef` | always | → AudioComponentParam |
| `AudioComponent/Component/Params/Param@Index` | always | index |
| `AudioComponent/Component/ID` | always | int (1) |
| `AudioComponent/AudioChannelLayout` | always | json |
| `AudioComponent/AudioComponentType` | always | int (1) |
| `AudioComponent/FrameRate` | always | int (5292000) |
| `AudioComponent/ChannelType` | always | int (1) |

### AudioMediaSource

Clip source → Media (audio).

ClassID `f588da05-fc2a-4fbc-9383-74d653b379e3` · Version 2 · ObjectID · 138 seen, in steps 01–23
Referenced by: SecondaryContent (366), AudioClip (183)

| Path | Present | Holds |
|---|---|---|
| `MediaSource/Content` | always | empty |
| `MediaSource/Media@ObjectURef` | always | → Media |
| `OriginalDuration` | always | int64 |

### AudioMeter

Track meter.

ClassID `72ea4700-f615-11d5-abc4-c186585e63e0` · Version 2 · ObjectID · 218 seen, in steps 03–23
Referenced by: AudioComponentChain (218)

| Path | Present | Holds |
|---|---|---|
| `AudioComponent/Component/ID` | always | int (2) |
| `AudioComponent/AudioChannelLayout` | always | json |
| `AudioComponent/AudioComponentType` | always | int (2) |
| `AudioComponent/FrameRate` | always | int (5292000) |
| `AudioComponent/ChannelType` | always | int (1) |

### AudioMixTrack

Sequence master bus.

ClassID `4b1d8400-e89e-11d5-abc4-a1a13b1e80a0` · Version 4 · ObjectID · 48 seen, in steps 03–23
Referenced by: AudioTrackGroup (48)

| Path | Present | Holds |
|---|---|---|
| `AudioTrack/ComponentOwner/Components@ObjectRef` | always | → AudioComponentChain |
| `AudioTrack/Panner@ObjectRef` | always | → DefaultPanProcessor |
| `AudioTrack/ID` | always | guid |
| `AudioTrack/SubType` | always | int (3) |
| `AudioTrack/Assign` | always | int (0) |
| `AudioTrack/NextPannerID` | always | int64 |
| `Track/Node/Properties/TL.SQTrackExpanded` | always | int (0) |
| `Track/Node/Properties/TL.SQTrackExpandedHeight` | always | int (41) |
| `Track/Node/Properties/TL.SQTrackAudioKeyframeStyle` | always | int (2) |
| `Track/Node/Properties/TL.SQTrackShy` | always | int (0) |
| `Track/ID` | always | int (1) |
| `Track/MediaType` | always | guid |
| `Track/Index` | always | int (0) |
| `Inlet@ObjectRef` | always | → AudioTrackInlet |

### AudioSequenceSource

Clip source → Sequence (a sequence used as a clip), audio.

ClassID `e8d4cc83-38cb-491f-9d94-e5f7e3b205ee` · Version 7 · ObjectID · 48 seen, in steps 03–23
Referenced by: SecondaryContent (96), AudioClip (48)

| Path | Present | Holds |
|---|---|---|
| `SequenceSource/Content` | always | empty |
| `SequenceSource/Sequence@ObjectURef` | always | → Sequence |
| `OriginalDuration` | always | int64×28, int×20 |

### AudioSettings

Audio settings shell owned by project/compile settings.

ClassID `6baf5521-b132-4634-840e-13cec5bc86a4` · Version 8 · ObjectID · 168 seen, in steps 00–23
Referenced by: AudioCompileSettings (144), ProjectSettings (24)

(no children)

### AudioStream

Duration, layout, peak/conform cache paths.

ClassID `0b5cf52f-2b85-4863-890b-8844b64ecfe9` · Version 8 · ObjectID · 138 seen, in steps 01–23
Referenced by: Media (138)

| Path | Present | Holds |
|---|---|---|
| `AudioChannelLayout` | always | json |
| `Duration` | always | int64 |
| `SampleType` | always | int (3, 7) |
| `ConformedAudioPath` | always | path |
| `PeakFilePath` | always | path |
| `FrameRate` | always | int (5292000) |

### AudioTrackGroup

Audio tracks + MasterTrack.

ClassID `9b9238b9-53a8-4cc3-b03f-b36246d052e6` · Version 6 · ObjectID · 48 seen, in steps 03–23
Referenced by: Sequence (48)

| Path | Present | Holds |
|---|---|---|
| `TrackGroup/Tracks/Track@ObjectURef` | always | → AudioClipTrack |
| `TrackGroup/Tracks/Track@Index` | always | index |
| `TrackGroup/NextTrackID` | always | int (5, 6) |
| `TrackGroup/FrameRate` | always | int (5292000) |
| `MasterTrack@ObjectRef` | always | → AudioMixTrack |
| `ID` | always | guid |
| `AutomationSafeFlags` | always | int (0) |
| `NumAdaptiveChannels` | always | int (2) |

### AudioTrackInlet

Master inlet listing the source tracks.

ClassID `be3af080-e8c6-11d5-abc4-a1c6d5dee670` · Version 4 · ObjectID · 48 seen, in steps 03–23
Referenced by: AudioMixTrack (48)

| Path | Present | Holds |
|---|---|---|
| `Sources/Source@ObjectURef` | always | → AudioClipTrack |
| `Sources/Source@Index` | always | index |
| `AudioChannelLayout` | always | json |

### AudioTransitionTrackItem

Audio fade or crossfade on a track (`TransitionItems`, `HeadTransition`/`TailTransition`).

ClassID `23f687b6-9c5a-42f4-bea1-e7b3e28e7082` · Version 4 · ObjectID · 7 seen, in steps 13–16
Referenced by: AudioClipTrackItem (9), AudioClipTrack (7)

| Path | Present | Holds |
|---|---|---|
| `TransitionTrackItem/TrackItem/Start` | always | int64 |
| `TransitionTrackItem/TrackItem/End` | always | int64 |
| `TransitionTrackItem/HasOutgoingClip` | always | bool (true, false) |
| `TransitionTrackItem/HasIncomingClip` | always | bool (true, false) |
| `TransitionTrackItem/DisplayName` | always | string |
| `TransitionTrackItem/MatchName` | always | string |
| `TransitionTrackItem/Alignment` | always | int64×5, int×2 |
| `AudioChannelLayout` | always | json |
| `FadeShapeValue` | 5/7 | int (0) |

### BinProjectItem

Bin.

ClassID `dbfd6653-24da-480e-a35e-ba45e9504e4b` · Version 1 · ObjectUID · 22 seen, in steps 02–23
Referenced by: RootProjectItem (22)

| Path | Present | Holds |
|---|---|---|
| `ProjectItem/Node/Properties/project.icon.view.grid.order` | always | int (6) |
| `ProjectItem/Node/Properties/Column.PropertyText.Label` | always | string |
| `ProjectItem/Node/Properties/list.view.expanded.state.<guid>` | always | bool (true, false) |
| `ProjectItem/Name` | always | string |
| `ProjectItemContainer/Items/Item@ObjectURef` | always | → ClipProjectItem |
| `ProjectItemContainer/Items/Item@Index` | always | index |

### ClipChannelGroupVectorSerializer

MasterClip audio channel groups (empty if no audio).

ClassID `a3127a8c-95d4-456e-a7f5-171b3f922426` · Version 1 · ObjectID · 255 seen, in steps 01–23
Referenced by: MasterClip (255)

| Path | Present | Holds |
|---|---|---|
| `ClipChannelVectors/ClipChannelVectorItem@ObjectRef` | 186/255 | → ClipChannelVectorSerializer |
| `ClipChannelVectors/ClipChannelVectorItem@Index` | 186/255 | index |

### ClipChannelSerializer

One channel: `mSourceChannelIndex`, `SourceClipIndex`.

ClassID `5c89aa7a-89a6-4483-becd-f2b1def42316` · Version 1 · ObjectID · 372 seen, in steps 01–23
Referenced by: ClipChannelVectorSerializer (372)

| Path | Present | Holds |
|---|---|---|
| `mSourceChannelIndex` | always | int (0, 1) |
| `SourceClipIndex` | always | int (0) |

### ClipChannelVectorSerializer

One group; `ChannelType` 1 stereo / 0 mono.

ClassID `333d203b-3a53-4195-8894-fc7523ff3dc7` · Version 1 · ObjectID · 186 seen, in steps 01–23
Referenced by: ClipChannelGroupVectorSerializer (186)

| Path | Present | Holds |
|---|---|---|
| `ClipChannels/ClipChannelItem@ObjectRef` | always | → ClipChannelSerializer |
| `ClipChannels/ClipChannelItem@Index` | always | index |
| `ChannelType` | always | int (1) |

### ClipLoggingInfo

ClipName, media in/out, frame rate, timecode format.

ClassID `77ab7fdd-dcdf-465d-9906-7a330ca1e738` · Version 10 · ObjectID · 255 seen, in steps 01–23
Referenced by: MasterClip (255)

| Path | Present | Holds |
|---|---|---|
| `CaptureMode` | 138/255 | int (1, 2) |
| `ClipName` | 207/255 | string |
| `MediaInPoint` | 161/255 | int (0) |
| `MediaOutPoint` | 161/255 | int64 |
| `MediaFrameRate` | 207/255 | int64×138, int×69 |
| `TimecodeFormat` | 207/255 | int (101, 103, 110, 200) |

### ClipProjectItem

Project-panel entry → MasterClip.

ClassID `cb4e0ed7-aca1-4171-8525-e3658dec06dd` · Version 1 · ObjectUID · 255 seen, in steps 01–23
Referenced by: RootProjectItem (145), BinProjectItem (110)

| Path | Present | Holds |
|---|---|---|
| `ProjectItem/Node/Properties/project.icon.view.grid.order` | 145/255 | int |
| `ProjectItem/Node/Properties/Column.PropertyText.Label` | always | string |
| `ProjectItem/Name` | always | string |
| `MasterClip@ObjectURef` | always | → MasterClip |

### CompileSettings

Export/compile presets (movie, still, audio, custom, video preview).

ClassID `18a35d66-597e-4157-b783-938b5bec3547` · Version 4 · ObjectID · 120 seen, in steps 00–23
Referenced by: Project (120)

| Path | Present | Holds |
|---|---|---|
| `VideoCompileSettings@ObjectRef` | always | → VideoCompileSettings |
| `AudioCompileSettings@ObjectRef` | always | → AudioCompileSettings |
| `CompilerClassIDFourCC` | always | int×96, int64×24 |
| `CompilerFourCC` | always | int×96, int64×24 |
| `ExportVideo` | always | bool (true) |
| `ExportAudio` | always | bool (true) |
| `AddToProjectWhenFinished` | always | bool (true) |
| `BeepWhenFinished` | always | bool (false) |
| `ExportWorkAreaOnly` | always | bool (false) |
| `EmbedProjectLink` | always | bool (false) |

### DataMediaSource

TranscriptClip source.

ClassID `ff36343e-4ece-4d37-ab61-e99b758f9d30` · Version 1 · ObjectID · 5 seen, in steps 19–23
Referenced by: TranscriptClip (5)

| Path | Present | Holds |
|---|---|---|
| `MediaSource/Content` | always | empty |
| `MediaSource/Media@ObjectURef` | always | → Media |
| `OriginalDuration` | always | int (0) |

### DataStream

Stream of the synthetic transcript Media.

ClassID `9e4e76eb-b72f-4b9b-9ea8-2887b1cc24fd` · Version 1 · ObjectID · 5 seen, in steps 19–23
Referenced by: Media (5)

| Path | Present | Holds |
|---|---|---|
| `Duration` | always | int (0) |
| `FrameRate` | always | int64 |

### DataTrackGroup

Caption/data tracks group.

ClassID `b714b71d-6838-48dd-9b77-db19088ced7e` · Version 1 · ObjectID · 48 seen, in steps 03–23
Referenced by: Sequence (48)

| Path | Present | Holds |
|---|---|---|
| `TrackGroup/NextTrackID` | always | int (1) |
| `TrackGroup/FrameRate` | always | int64 |

### DefaultPanProcessor

Master panner.

ClassID `33a94282-ee2c-11d5-abc4-c1cd7f9e3c10` · Version 2 · ObjectID · 48 seen, in steps 03–23
Referenced by: AudioMixTrack (48)

| Path | Present | Holds |
|---|---|---|
| `PanProcessor/AudioComponent/Component/ID` | always | int64 |
| `PanProcessor/AudioComponent/AudioChannelLayout` | always | json |
| `PanProcessor/AudioComponent/AudioComponentType` | always | int (0) |
| `PanProcessor/AudioComponent/FrameRate` | always | int (5292000) |
| `PanProcessor/AudioComponent/ChannelType` | always | int (1) |
| `DefaultPannerOutputChannelType` | always | int (1) |
| `DefaultPannerInputChannelType` | always | int (1) |

### DefaultSequenceSettings

Defaults for new sequences.

ClassID `567bdf53-d6d9-4d61-b2f1-f4834bebea9b` · Version 2 · ObjectID · 24 seen, in steps 00–23
Referenced by: ProjectSettings (24)

| Path | Present | Holds |
|---|---|---|
| `TotalVideoTracks` | always | int (1) |
| `DefaultAudioStandardMonoTracks` | always | int (0) |
| `DefaultAudioStandardStereoTracks` | always | int (1) |
| `DefaultAudioStandard51Tracks` | always | int (0) |
| `DefaultAudioSubmixMonoTracks` | always | int (0) |
| `DefaultAudioSubmixStereoTracks` | always | int (0) |
| `DefaultAudioSubmix51Tracks` | always | int (0) |

### DummyCaptureSettings

Capture settings placeholder.

ClassID `328c2aa2-47f9-4211-805b-b6a6dbd4ca29` · Version 1 · ObjectID · 24 seen, in steps 00–23
Referenced by: ProjectSettings (24)

(no children)

### ExternallyProvidedTranscriptDocument

FlatBuffer `TranscriptData`.

ClassID `e58c3975-8126-4176-92ec-2b4001983faf` · Version 1 · ObjectID · 5 seen, in steps 19–23
Referenced by: TranscriptClip (5)

| Path | Present | Holds |
|---|---|---|
| `TranscriptProvider` | always | guid |
| `TranscriptData@Encoding` | always | string (base64) |
| `TranscriptData@BinaryHash` | always | guid |
| `TranscriptData` | always | base64 |

### FileProjectItem

Project item for a non-media file (e.g. a .txt).

ClassID `b28f14fe-793f-45be-bb28-fb82644995f4` · Version 1 · ObjectUID · 23 seen, in steps 01–23
Referenced by: RootProjectItem (23)

| Path | Present | Holds |
|---|---|---|
| `ProjectItem/Node/Properties/project.icon.view.grid.order` | always | int (5, 9) |
| `ProjectItem/Node/Properties/Column.PropertyText.Label` | always | string |
| `ProjectItem/Name` | always | string |
| `FullPath` | always | path |

### IngestSettings

Ingest options.

ClassID `2db8f76b-2c37-48ee-925d-9a4f7278152d` · Version 2 · ObjectID · 24 seen, in steps 00–23
Referenced by: Project (24)

| Path | Present | Holds |
|---|---|---|
| `Action` | always | string |
| `Enabled` | always | bool (false) |

### Link

Ties the linked A/V track items.

ClassID `149d4ea5-a7d4-4b34-9bb7-16d783904bf2` · Version 1 · ObjectID · 45 seen, in steps 03–23
Referenced by: Sequence (45)

| Path | Present | Holds |
|---|---|---|
| `TrackItemGroup/TrackItems/TrackItem@ObjectRef` | always | → VideoClipTrackItem, AudioClipTrackItem |
| `TrackItemGroup/TrackItems/TrackItem@Index` | always | index |

### Marker

One marker: a DVAMarker JSON string (name, comment, type, start time, colour).

ClassID `a45508e0-3ff7-4d04-90a7-2e0dfff4c910` · Version 3 · ObjectID · 54 seen, in steps 11–17, 20–23
Referenced by: Markers (54)

| Path | Present | Holds |
|---|---|---|
| `DVAMarker` | always | json |

### Markers

Marker list of a master clip (empty until a marker is added) or a sequence.

ClassID `bee50706-b524-416c-9f03-b596ce5f6866` · Version 4 · ObjectID · 219 seen, in steps 01–23
Referenced by: VideoClip (188), AudioClip (183), Sequence (12)

| Path | Present | Holds |
|---|---|---|
| `Markers/Marker@Index` | 12/219 | index |
| `Markers/Marker/First` | 12/219 | guid |
| `Markers/Marker/Second@ObjectRef` | 12/219 | → Marker |
| `ByGUID` | always | string |
| `LastMetadataState` | always | guid |
| `LastContentState` | always | guid |

### MasterClip

Clip identity: Clips list, logging, channel map.

ClassID `fb11c33a-b0a9-4465-aa94-b6d5db2628cf` · Version 12 · ObjectUID · 255 seen, in steps 01–23
Referenced by: ClipProjectItem (255), SubClip (95)

| Path | Present | Holds |
|---|---|---|
| `Node/Properties/BE.MasterClip.ChannelIndexToTranscribe` | 3/255 | int (-1) |
| `Node/Properties/AMM.CurrentSolo` | 2/255 | json |
| `Node/Properties/monitor.edit.time` | 2/255 | int (0) |
| `Node/Properties/monitor.show.audio.waveform` | 2/255 | bool (false) |
| `Node/Properties/monitor.take.audio` | 2/255 | bool (true) |
| `Node/Properties/monitor.take.video` | 2/255 | bool (true) |
| `Node/Properties/monitor.zoom.in.time` | 2/255 | int (0) |
| `Node/Properties/monitor.zoom.out.time` | 2/255 | int64 |
| `Node/ID` | 40/255 | int (1000001, 1000002) |
| `LoggingInfo@ObjectRef` | always | → ClipLoggingInfo |
| `AudioComponentChains/AudioComponentChain@ObjectRef` | 186/255 | → AudioComponentChain |
| `AudioComponentChains/AudioComponentChain@Index` | 186/255 | index |
| `Clips/Clip@ObjectRef` | always | → VideoClip, AudioClip, TranscriptClip |
| `Clips/Clip@Index` | always | index |
| `AudioClipChannelGroups@ObjectRef` | always | → ClipChannelGroupVectorSerializer |
| `Name` | always | string |
| `DefMappingID` | 138/255 | guid |
| `MasterClipChangeVersion` | always | int |

### Media

One file on disk: paths, importer, streams.

ClassID `7a5c103e-f3ac-4391-b6b4-7cc3d2f9a7ff` · Version 30 · ObjectUID · 212 seen, in steps 01–23
Referenced by: VideoMediaSource (138), AudioMediaSource (138), DataMediaSource (5)

| Path | Present | Holds |
|---|---|---|
| `DataStream@ObjectRef` | 5/212 | → DataStream |
| `AudioStream@ObjectRef` | 138/212 | → AudioStream |
| `VideoStream@ObjectRef` | 138/212 | → VideoStream |
| `ModificationState@Encoding` | always | string (base64) |
| `ModificationState@BinaryHash` | always | guid |
| `ModificationState` | always | base64 |
| `RelativePath` | 207/212 | path |
| `ImplementationID` | always | guid |
| `FileKey` | 207/212 | guid |
| `Infinite` | 46/212 | bool (true) |
| `ConformedAudioRate` | 138/212 | int (5292000) |
| `ContentAndMetadataState` | 207/212 | guid |
| `ContentCredentialsInfo` | 184/212 | int (5120) |
| `CCManifestLocation` | 184/212 | int (1) |
| `CCFileModTime` | 207/212 | int64 |
| `ActualMediaFilePath` | always | path×207, int64×5 |
| `FilePath` | always | path×207, int64×5 |
| `Title` | always | string |
| `MediaFileHistory0` | 27/212 | path |

### PointComponentParam

2-D point parameter (Position, Anchor Point).

ClassID `ca81d347-309b-44d2-acc7-1c572efb973c` · Version 4 · ObjectID · 10 seen, in steps 12–16
Referenced by: VideoFilterComponent (10)

| Path | Present | Holds |
|---|---|---|
| `Name` | always | string |
| `IsTimeVarying` | 5/10 | bool (true) |
| `ParameterID` | always | int (1, 2) |
| `StartKeyframe` | always | keyframes |
| `Keyframes` | 5/10 | keyframes |

### Project

Root: properties, settings refs, `NextID`.

ClassID `62ad66dd-0dcd-42da-a660-6d8fbde94876` · Version 45 · ObjectID · 24 seen, in steps 00–23

| Path | Present | Holds |
|---|---|---|
| … | | 6 optional paths omitted; see prproj-schema.json |
| `Node/Properties/ProjectViewState.List@ObjectID` | always | local id (Project scope) |
| `Node/Properties/ProjectViewState.List/ProjectViewStates/ProjectViewState@Index` | always | index |
| `Node/Properties/ProjectViewState.List/ProjectViewStates/ProjectViewState/First` | always | guid |
| `Node/Properties/ProjectViewState.List/ProjectViewStates/ProjectViewState/Second@ObjectRef` | always | local ref (Project scope) |
| `Node/Properties/ProjectViewState.List/ProjectViewState@ObjectID` | always | local id (Project scope) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/ProjectViewState.ID` | always | guid |
| `Node/Properties/ProjectViewState.List/ProjectViewState/ColumnListContents.Version` | always | int (18) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/ProjectViewState.OriginalID` | always | guid |
| `Node/Properties/ProjectViewState.List/ProjectViewState/ProjectViewState.BinID` | always | int (1000000) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/ProjectViewState.ViewHidden` | always | bool (false) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/PreviewView.Visible` | always | bool (false) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/ContentView.LastViewed` | always | int (1) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/IconView.Thumbnail.Size` | always | int (200) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/FreeformView.Scale` | always | int (1) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/ListView.Thumbnail.Size` | always | int (0) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/IconView.Thumbnail.State` | always | bool (true) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/ListView.Thumbnail.State` | always | bool (false) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/Thumbnail.ShowsEffects.State` | always | bool (true) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/Sort.Type` | always | int (0) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/Sort.Enabled` | always | bool (true) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/Sort.ColumnIndex` | always | int (1) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/Sort.Direction` | always | int (0) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/ListView.NameColumnWidth` | always | int (0) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/IconSort.Type` | always | int (0) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/IconSort.Direction` | always | int (0) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/IconSort.ColumnIndex` | always | int (0) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/SideNav.Visible` | always | bool (true) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/SideNav.Width` | always | int (160) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/Project.IsEAProject` | always | bool (false) |
| `Node/Properties/ProjectViewState.List/ProjectViewState/Columns.List@ObjectRef` | always | local ref (Project scope) |
| `Node/Properties/ProjectViewState.List/ColumnList@ObjectID` | always | local id (Project scope) |
| `Node/Properties/ProjectViewState.List/ColumnList/Columns/Column@ObjectRef` | always | local ref (Project scope) |
| `Node/Properties/ProjectViewState.List/ColumnList/Columns/Column@Index` | always | index |
| `Node/Properties/ProjectViewState.List/LabelColumn@ObjectID` | always | local id (Project scope) |
| `Node/Properties/ProjectViewState.List/LabelColumn/Column.Name` | always | string |
| `Node/Properties/ProjectViewState.List/LabelColumn/Column.ID` | always | string |
| `Node/Properties/ProjectViewState.List/LabelColumn/Column.Type` | always | int (17) |
| `Node/Properties/ProjectViewState.List/LabelColumn/Column.Class` | always | int (1) |
| `Node/Properties/ProjectViewState.List/LabelColumn/Column.Width` | always | int (26) |
| `Node/Properties/ProjectViewState.List/LabelColumn/Column.IsHidden` | always | bool (false) |
| `Node/Properties/ProjectViewState.List/SelectedItemsColumn@ObjectID` | always | local id (Project scope) |
| `Node/Properties/ProjectViewState.List/SelectedItemsColumn/Column.Name` | always | string |
| `Node/Properties/ProjectViewState.List/SelectedItemsColumn/Column.ID` | always | string |
| `Node/Properties/ProjectViewState.List/SelectedItemsColumn/Column.Type` | always | int (0) |
| `Node/Properties/ProjectViewState.List/SelectedItemsColumn/Column.Class` | always | int (1) |
| `Node/Properties/ProjectViewState.List/SelectedItemsColumn/Column.Width` | always | int (26) |
| `Node/Properties/ProjectViewState.List/SelectedItemsColumn/Column.IsHidden` | always | bool (true) |
| `Node/Properties/ProjectViewState.List/NameColumn@ObjectID` | always | local id (Project scope) |
| `Node/Properties/ProjectViewState.List/NameColumn/Column.Name` | always | string |
| `Node/Properties/ProjectViewState.List/NameColumn/Column.ID` | always | string |
| `Node/Properties/ProjectViewState.List/NameColumn/Column.Type` | always | int (24) |
| `Node/Properties/ProjectViewState.List/NameColumn/Column.Class` | always | int (0) |
| `Node/Properties/ProjectViewState.List/NameColumn/Column.Width` | always | int (200) |
| `Node/Properties/ProjectViewState.List/NameColumn/Column.IsHidden` | always | bool (false) |
| `Node/Properties/ProjectViewState.List/StringColumn@ObjectID` | always | local id (Project scope) |
| `Node/Properties/ProjectViewState.List/StringColumn/Column.Name` | always | string |
| `Node/Properties/ProjectViewState.List/StringColumn/Column.ID` | always | string |
| `Node/Properties/ProjectViewState.List/StringColumn/Column.Type` | always | int |
| `Node/Properties/ProjectViewState.List/StringColumn/Column.Class` | always | int (0) |
| `Node/Properties/ProjectViewState.List/StringColumn/Column.Width` | always | int (100, 150) |
| `Node/Properties/ProjectViewState.List/StringColumn/Column.IsHidden` | always | bool (true, false) |
| `Node/Properties/ProjectViewState.List/TimecodeColumn@ObjectID` | always | local id (Project scope) |
| `Node/Properties/ProjectViewState.List/TimecodeColumn/Column.Name` | always | string |
| `Node/Properties/ProjectViewState.List/TimecodeColumn/Column.ID` | always | string |
| `Node/Properties/ProjectViewState.List/TimecodeColumn/Column.Type` | always | int |
| `Node/Properties/ProjectViewState.List/TimecodeColumn/Column.Class` | always | int (0) |
| `Node/Properties/ProjectViewState.List/TimecodeColumn/Column.Width` | always | int (100) |
| `Node/Properties/ProjectViewState.List/TimecodeColumn/Column.IsHidden` | always | bool (true, false) |
| `Node/Properties/ProjectViewState.List/EditTextColumn@ObjectID` | always | local id (Project scope) |
| `Node/Properties/ProjectViewState.List/EditTextColumn/Column.Name` | always | string |
| `Node/Properties/ProjectViewState.List/EditTextColumn/Column.ID` | always | string |
| `Node/Properties/ProjectViewState.List/EditTextColumn/Column.Type` | always | int |
| `Node/Properties/ProjectViewState.List/EditTextColumn/Column.Class` | always | int (0, 1) |
| `Node/Properties/ProjectViewState.List/EditTextColumn/Column.Width` | always | int (100) |
| `Node/Properties/ProjectViewState.List/EditTextColumn/Column.IsHidden` | always | bool (true, false) |
| `Node/Properties/ProjectViewState.List/BoolPropertyColumn@ObjectID` | always | local id (Project scope) |
| `Node/Properties/ProjectViewState.List/BoolPropertyColumn/Column.Name` | always | string |
| `Node/Properties/ProjectViewState.List/BoolPropertyColumn/Column.ID` | always | string |
| `Node/Properties/ProjectViewState.List/BoolPropertyColumn/Column.Type` | always | int (0) |
| `Node/Properties/ProjectViewState.List/BoolPropertyColumn/Column.Class` | always | int (2) |
| `Node/Properties/ProjectViewState.List/BoolPropertyColumn/Column.Width` | always | int (100) |
| `Node/Properties/ProjectViewState.List/BoolPropertyColumn/Column.IsHidden` | always | bool (false) |
| `Node/Properties/ProjectViewState.List/BoolPropertyColumn/Column.Property.Key` | always | string |
| `Node/Properties/ProjectViewState.List/BoolPropertyColumn/Column.Editable.Key` | always | bool (true) |
| `Node/Properties/BE.Prefs.AcceleratedRenderer.LastUsedIdentifier` | always | guid |
| `Node/Properties/BE.Prefs.AcceleratedRenderer.LastUsedDisplayName` | always | string |
| `Node/Properties/BE.Prefs.kPrefsAcceleratedRenderer.OverridenIdentifier` | always | guid |
| `Node/Properties/AM.PJShowWellState` | always | int (0) |
| `Node/Properties/MZ.Project.WorkspaceName` | always | string |
| `Node/Properties/ProjectViewState.Version` | always | int (2) |
| `Node/Properties/project.settings.lastknowngoodprojectpath` | always | path |
| `Node/Properties/project.settings.lastknownparentdirectorypathaboveprojectpath` | always | path |
| `Node/Properties/MZ.Project.GUID` | always | guid |
| `Node/Properties/MZ.BuildVersion.Created` | always | string |
| `Node/Properties/MZ.BuildVersion.Modified` | always | string |
| `Node/Properties/MZ.Project.ApplicationID` | always | string |
| `Node/Properties/TL.PJSnappingState` | always | int (1) |
| `Node/Properties/PPro.UHB.ShowWorkspaceLabel` | always | bool (false) |
| `RootProjectItem@ObjectURef` | always | → RootProjectItem |
| `ProjectSettings@ObjectRef` | always | → ProjectSettings |
| `MovieCompileSettings@ObjectRef` | always | → CompileSettings |
| `StillCompileSettings@ObjectRef` | always | → CompileSettings |
| `AudioCompileSettings@ObjectRef` | always | → CompileSettings |
| `CustomCompileSettings@ObjectRef` | always | → CompileSettings |
| `VideoPreviewCompileSettings@ObjectRef` | always | → CompileSettings |

### ProjectSettings

Project-wide settings.

ClassID `50c16708-a1a1-4d2f-98d5-4e283ae28353` · Version 21 · ObjectID · 24 seen, in steps 00–23
Referenced by: Project (24)

| Path | Present | Holds |
|---|---|---|
| `VideoSettings@ObjectRef` | always | → VideoSettings |
| `AudioSettings@ObjectRef` | always | → AudioSettings |
| `VideoCompileSettings@ObjectRef` | always | → VideoCompileSettings |
| `AudioCompileSettings@ObjectRef` | always | → AudioCompileSettings |
| `CaptureSettings@ObjectRef` | always | → DummyCaptureSettings |
| `DefaultSequenceSettings@ObjectRef` | always | → DefaultSequenceSettings |
| `ColorManagementSettings` | always | json |
| `AudioTimeDisplay` | always | int (200) |
| `VideoTimeDisplay` | always | int (102) |
| `VideoTimeDisplayInitial` | always | int (102) |
| `ActionSafeWidth` | always | int (10) |
| `ActionSafeHeight` | always | int (10) |
| `TitleSafeWidth` | always | int (20) |
| `TitleSafeHeight` | always | int (20) |
| `ShouldScaleMedia` | always | bool (false) |
| `EditingModeID` | always | guid |
| `PreviewFileFormatID` | always | guid |
| `UsePreviewCache` | always | bool (false) |
| `ColorAwareEffectsEnabled` | always | int (0) |

### RootProjectItem

"Root Bin".

ClassID `1c307a89-9318-47d7-a583-bf2553736543` · Version 1 · ObjectUID · 24 seen, in steps 00–23
Referenced by: Project (24)

| Path | Present | Holds |
|---|---|---|
| `ProjectItem/Node/Properties/ProjectViewState.ID` | always | guid |
| `ProjectItem/Node/Properties/list.view.expanded.state.<guid>` | always | bool (true) |
| `ProjectItem/Node/ID` | always | int (1000000) |
| `ProjectItem/Name` | always | string |
| `ProjectItemContainer` | always | empty |
| `ProjectItemContainer/Items/Item@ObjectURef` | 23/24 | → ClipProjectItem, FileProjectItem, BinProjectItem |
| `ProjectItemContainer/Items/Item@Index` | 23/24 | index |

### ScratchDiskSettings

Scratch disk locations.

ClassID `4c6ed82b-a81c-4df1-8bd0-750504c4b560` · Version 4 · ObjectID · 24 seen, in steps 00–23
Referenced by: Project (24)

| Path | Present | Holds |
|---|---|---|
| `AudioPreviewLocation0` | always | string |
| `VideoPreviewLocation0` | always | string |
| `AutoSaveLocation0` | always | string |
| `CapturedVideoLocation0` | always | string |
| `TransferMediaLocation0` | always | string |
| `CapsuleMediaLocation0` | always | string |
| `DVDEncodingLocation0` | always | string |
| `CCLibrariesLocation0` | always | string |

### SecondaryContent

Per-channel ref from an AudioClip to its source.

ClassID `f9d004b5-cb04-4e2f-af6f-64fadc2c4be9` · Version 1 · ObjectID · 462 seen, in steps 01–23
Referenced by: AudioClip (462)

| Path | Present | Holds |
|---|---|---|
| `Content@ObjectRef` | always | → AudioMediaSource, AudioSequenceSource |
| `ChannelIndex` | always | int (0, 1) |

### Sequence

Timeline: TrackGroups, Links, view state.

ClassID `6a15d903-8739-11d5-af2d-9b7855ad8974` · Version 12 · ObjectUID · 48 seen, in steps 03–23
Referenced by: AudioSequenceSource (48), VideoSequenceSource (48)

| Path | Present | Holds |
|---|---|---|
| `Node/Properties/MZ.InPoint` | 5/48 | int64 |
| `Node/Properties/MZ.OutPoint` | 5/48 | int64 |
| `Node/Properties/AMM.CurrentSolo` | always | json |
| `Node/Properties/AM.TrackScrollPosition` | 27/48 | int (0) |
| `Node/Properties/AM.TrackVScrollPosition` | 27/48 | int (0) |
| `Node/Properties/MZ.EditLine` | always | int×33, int64×15 |
| `Node/Properties/MZ.Sequence.AudioTimeDisplayFormat` | always | int (200) |
| `Node/Properties/MZ.Sequence.VideoTimeDisplayFormat` | always | int (110) |
| `Node/Properties/MZ.WorkInPoint` | always | int (0) |
| `Node/Properties/MZ.WorkOutPoint` | always | int64 |
| `Node/Properties/Monitor.ProgramZoomIn` | always | int (0) |
| `Node/Properties/Monitor.ProgramZoomOut` | always | int64×28, int×20 |
| `Node/Properties/TL.SQAVDividerPosition` | always | float |
| `Node/Properties/TL.SQAudioVisibleBase` | always | int (0) |
| `Node/Properties/TL.SQDataVisibleBase` | always | int (0) |
| `Node/Properties/TL.SQHeaderWidth` | always | int (204) |
| `Node/Properties/TL.SQHideShyTracks` | always | int (0) |
| `Node/Properties/TL.SQTimePerPixel` | always | float |
| `Node/Properties/TL.SQVideoVisibleBase` | always | int (0) |
| `Node/Properties/TL.SQVisibleBaseTime` | always | int×47, int64×1 |
| `Node/Properties/MZ.Sequence.EditingModeGUID` | always | guid |
| `Node/Properties/MZ.Sequence.PreviewUseMaxBitDepth` | always | bool (false) |
| `Node/Properties/MZ.Sequence.PreviewUseMaxRenderQuality` | always | bool (false) |
| `Node/Properties/MZ.Sequence.PreviewRenderingPresetPath` | always | path |
| `Node/Properties/MZ.Sequence.PreviewRenderingPresetCodec` | always | int64 |
| `Node/Properties/MZ.Sequence.PreviewRenderingClassID` | always | int64 |
| `Node/Properties/MZ.Sequence.PreviewFrameSizeWidth` | always | int (1920) |
| `Node/Properties/MZ.Sequence.PreviewFrameSizeHeight` | always | int (1080) |
| `Node/Properties/HSL.TimelinePatchingAndTargeting.AudioPatches<guid>` | 42/48 | json |
| `Node/Properties/HSL.TimelinePatchingAndTargeting.VideoPatches<guid>` | 40/48 | json |
| `MarkerOwner/Markers@ObjectRef` | 12/48 | → Markers |
| `PersistentGroupContainer/LinkContainer` | always | empty |
| `PersistentGroupContainer/LinkContainer/Links/Link@ObjectRef` | 28/48 | → Link |
| `PersistentGroupContainer/LinkContainer/Links/Link@Index` | 28/48 | index |
| `TrackGroups/TrackGroup@Index` | always | index |
| `TrackGroups/TrackGroup/First` | always | guid |
| `TrackGroups/TrackGroup/Second@ObjectRef` | always | → VideoTrackGroup, AudioTrackGroup, DataTrackGroup |
| `Name` | always | string |
| `PreviewFormatIdentifier` | always | guid |

### StereoToStereoPanProcessor

Track panner.

ClassID `7bf86a01-efbe-11d5-abc4-c1ce2b1e9090` · Version 1 · ObjectID · 170 seen, in steps 03–23
Referenced by: AudioClipTrack (170)

| Path | Present | Holds |
|---|---|---|
| `PanProcessor/AudioComponent/Component/Params/Param@ObjectRef` | always | → AudioComponentParam |
| `PanProcessor/AudioComponent/Component/Params/Param@Index` | always | index |
| `PanProcessor/AudioComponent/Component/ID` | always | int64 |
| `PanProcessor/AudioComponent/AudioChannelLayout` | always | json |
| `PanProcessor/AudioComponent/AudioComponentType` | always | int (0) |
| `PanProcessor/AudioComponent/FrameRate` | always | int (5292000) |
| `PanProcessor/AudioComponent/ChannelType` | always | int (1) |

### SubClip

Track item → (MasterClip, Clip); `Name` shown on the timeline.

ClassID `e0c58dc9-dbdd-4166-aef7-5db7e3f22e84` · Version 6 · ObjectID · 95 seen, in steps 03–23
Referenced by: VideoClipTrackItem (50), AudioClipTrackItem (45)

| Path | Present | Holds |
|---|---|---|
| `Clip@ObjectRef` | always | → VideoClip, AudioClip |
| `MasterClip@ObjectURef` | always | → MasterClip |
| `Name` | always | string |
| `OrigChGrp` | always | int (0) |

### TranscriptClip

Speech-to-Text clip in a MasterClip.

ClassID `9e0179bb-153c-4884-b34b-eb7082f34384` · Version 2 · ObjectID · 5 seen, in steps 19–23
Referenced by: MasterClip (5)

| Path | Present | Holds |
|---|---|---|
| `DataClip/Clip/Source@ObjectRef` | always | → DataMediaSource |
| `DataClip/Clip/ClipID` | always | guid |
| `DataClip/Clip/InUse` | always | bool (false) |
| `TranscriptTextSegments@ObjectRef` | always | → ExternallyProvidedTranscriptDocument |

### VideoClip

Video clip instance: Source, ClipID, In/OutPoint, label.

ClassID `9308dbef-2440-4acb-9ab2-953b9a4e82ec` · Version 11 · ObjectID · 236 seen, in steps 01–23
Referenced by: MasterClip (186), SubClip (50)

| Path | Present | Holds |
|---|---|---|
| `Clip/Node/Properties/asl.clip.label.color` | always | int (19005, 6769408, 8851829, 11405886) |
| `Clip/Node/Properties/BE.Prefs.StillImages.DefaultIsDropFrame` | 46/236 | bool (true) |
| `Clip/Node/Properties/asl.clip.label.name` | always | string |
| `Clip/MarkerOwner/Markers@ObjectRef` | 188/236 | → Markers |
| `Clip/Source@ObjectRef` | always | → VideoMediaSource, VideoSequenceSource |
| `Clip/ClipID` | always | guid |
| `Clip/InUse` | 186/236 | bool (false) |
| `Clip/PlaybackSpeed` | 18/236 | int (1) |
| `Clip/InPoint` | 96/236 | int×86, int64×10 |
| `Clip/OutPoint` | 96/236 | int64 |

### VideoClipTrack

Video track (V1, V2, …).

ClassID `f68dcd81-8805-11d5-af2d-9bfa89d4ddd4` · Version 1 · ObjectUID · 144 seen, in steps 03–23
Referenced by: VideoTrackGroup (144)

| Path | Present | Holds |
|---|---|---|
| `ClipTrack/Track/Node/Properties/TL.SQTrackExpanded` | always | int (0) |
| `ClipTrack/Track/Node/Properties/TL.SQTrackExpandedHeight` | always | int (41, 144) |
| `ClipTrack/Track/Node/Properties/MZ.SourceTrackState` | 120/144 | int (0, 2) |
| `ClipTrack/Track/Node/Properties/MZ.SourceTrackNumber` | 120/144 | int (0, -1) |
| `ClipTrack/Track/Node/Properties/TL.SQTrackShy` | always | int (0) |
| `ClipTrack/Track/Node/Properties/MZ.TrackName` | 9/144 | string |
| `ClipTrack/Track/Node/Properties/MZ.TrackTargeted` | always | int (0, 1) |
| `ClipTrack/Track/ID` | always | int (1, 2, 3) |
| `ClipTrack/Track/MediaType` | always | guid |
| `ClipTrack/Track/Index` | always | int (0, 1, 2) |
| `ClipTrack/Track/IsLocked` | 8/144 | bool (true) |
| `ClipTrack/ClipItems/TrackItems/TrackItem@ObjectRef` | 33/144 | → VideoClipTrackItem |
| `ClipTrack/ClipItems/TrackItems/TrackItem@Index` | 33/144 | index |
| `ClipTrack/ClipItems/MediaType` | always | guid |
| `ClipTrack/ClipItems/Index` | always | int (0, 1, 2) |
| `ClipTrack/TransitionItems/MediaType` | always | guid |
| `ClipTrack/TransitionItems/Index` | always | int (0, 1, 2) |

### VideoClipTrackItem

Video item on a track: Start/End, component chain.

ClassID `368b0406-29e3-4923-9fcd-094fbf9a1089` · Version 8 · ObjectID · 50 seen, in steps 03–23
Referenced by: VideoClipTrack (50), Link (45)

| Path | Present | Holds |
|---|---|---|
| `ClipTrackItem/ComponentOwner/Components@ObjectRef` | always | → VideoComponentChain |
| `ClipTrackItem/TrackItem/Node/Properties/monitor.edit.time` | 2/50 | int64 |
| `ClipTrackItem/TrackItem/Node/Properties/monitor.take.video.linked` | 2/50 | bool (true) |
| `ClipTrackItem/TrackItem/Node/Properties/monitor.zoom.in.time` | 2/50 | int (0) |
| `ClipTrackItem/TrackItem/Node/Properties/monitor.zoom.out.time` | 2/50 | int64 |
| `ClipTrackItem/TrackItem/Start` | 22/50 | int64 |
| `ClipTrackItem/TrackItem/End` | always | int64 |
| `ClipTrackItem/SubClip@ObjectRef` | always | → SubClip |
| `ToneMapSettings` | always | json |
| `FrameRect` | always | csv-numbers |
| `PixelAspectRatio` | always | csv-numbers |

### VideoCompileSettings

Video side of a compile setting.

ClassID `db372db5-7de2-4d3c-98ae-f42659d77b22` · Version 9 · ObjectID · 144 seen, in steps 00–23
Referenced by: CompileSettings (120), ProjectSettings (24)

| Path | Present | Holds |
|---|---|---|
| `VideoSettings@ObjectRef` | always | → VideoSettings |
| `Compressor` | always | int64 |
| `VideoCompilerClassIDFourCC` | always | int64 |
| `VideoFileTypeFourCC` | always | int64 |
| `Depth` | always | int (24) |
| `RenderDepth` | always | int (0) |
| `Aspect43` | always | bool (false) |
| `Quality` | always | int (100) |
| `UseDataRate` | always | bool (false) |
| `DataRate` | always | int (3500) |
| `ForceRecompress` | always | bool (true) |
| `ForceRecompressValue` | always | int (2) |
| `Deinterlace` | always | bool (false) |
| `IgnoreVideoFilters` | always | bool (false) |
| `OptimizeStills` | always | bool (false) |
| `FramesAtMarkers` | always | bool (false) |
| `RealTimePreview` | always | bool (true) |
| `VideoFieldType` | always | int (0) |
| `DoKeyframeEveryNFrames` | always | bool (false) |
| `DoKeyframeEveryNFramesValue` | always | int (0) |
| `AddKeyframesAtMarkers` | always | bool (false) |
| `AddKeyframesAtEdits` | always | bool (false) |
| `RelativeFrameSize` | always | int (1) |

### VideoComponentChain

Video effect stack (track item or track group).

ClassID `0970e08a-f58f-4108-b29a-1a717b8e12e2` · Version 3 · ObjectID · 98 seen, in steps 03–23
Referenced by: VideoClipTrackItem (50), VideoTrackGroup (48)

| Path | Present | Holds |
|---|---|---|
| `DefaultMotion` | 50/98 | bool (true) |
| `DefaultOpacity` | 50/98 | bool (true) |
| `DefaultMotionComponentID` | 50/98 | int (1) |
| `DefaultOpacityComponentID` | 50/98 | int (2) |
| `ComponentChain` | always | empty |
| `ComponentChain/Components/Component@ObjectRef` | 5/98 | → VideoFilterComponent |
| `ComponentChain/Components/Component@Index` | 5/98 | index |
| `ComponentChain/Node/Properties/MZ.ComponentChain.ActiveComponentID` | 41/98 | int (2) |
| `ComponentChain/Node/Properties/MZ.ComponentChain.ActiveComponentParamIndex` | 41/98 | int64 |

### VideoComponentParam

Video effect parameter: float, bool, enum or colour (Scale, Rotation, Opacity, Skew, …).

ClassID `cc12343e-f113-4d3b-ae05-b287db77d461`, `fe47129e-6c94-4fc0-95d5-c056a517aaf3`, `6e02e8bb-2569-46b2-8ab1-4ab11c43e9c8` · Version 10 · ObjectID · 50 seen, in steps 12–16
Referenced by: VideoFilterComponent (50)

| Path | Present | Holds |
|---|---|---|
| `Name` | 40/50 | string |
| `DiscontinuousInterpolate` | 5/50 | bool (true) |
| `ParameterControlType` | 10/50 | int (3) |
| `LowerUIBound` | 10/50 | int (-200) |
| `ParameterID` | always | int |
| `UpperUIBound` | 10/50 | int (200) |
| `StartKeyframe` | always | keyframes |
| `CurrentValue` | 5/50 | int (240) |
| `LowerBound` | 40/50 | int (0, -70, -30000, -32768) |
| `UpperBound` | 40/50 | int (1, 70, 100, 360, 30000, 32767) |

### VideoFilterComponent

One effect; `MatchName` e.g. `AE.ADBE Geometry2` (Transform).

ClassID `d10da199-beea-4dd1-b941-ed3a78766d50` · Version 9 · ObjectID · 5 seen, in steps 12–16
Referenced by: VideoComponentChain (5)

| Path | Present | Holds |
|---|---|---|
| `Component/Params/Param@ObjectRef` | always | → VideoComponentParam, PointComponentParam |
| `Component/Params/Param@Index` | always | index |
| `Component/ID` | always | int (3) |
| `Component/DisplayName` | always | string |
| `VideoFilterType` | always | int (2) |
| `MatchName` | always | string |

### VideoMediaSource

Clip source → Media (video).

ClassID `e64ddf74-8fac-4682-8aa8-0e0ca2248949` · Version 2 · ObjectID · 138 seen, in steps 01–23
Referenced by: VideoClip (188)

| Path | Present | Holds |
|---|---|---|
| `MediaSource/Content` | always | empty |
| `MediaSource/Media@ObjectURef` | always | → Media |
| `OriginalDuration` | always | int64 |

### VideoSequenceSource

Clip source → Sequence (a sequence used as a clip), video.

ClassID `4752dfa9-7a7e-4a3b-a25b-cafde1a8d036` · Version 3 · ObjectID · 48 seen, in steps 03–23
Referenced by: VideoClip (48)

| Path | Present | Holds |
|---|---|---|
| `SequenceSource/Content` | always | empty |
| `SequenceSource/Sequence@ObjectURef` | always | → Sequence |
| `OriginalDuration` | always | int64×28, int×20 |

### VideoSettings

Video settings shell owned by project/compile settings.

ClassID `58474264-30c4-43a2-bba5-dc0812df8a3a` · Version 10 · ObjectID · 168 seen, in steps 00–23
Referenced by: VideoCompileSettings (144), ProjectSettings (24)

(no children)

### VideoStream

Duration, fps, size, codec FourCC, alpha.

ClassID `a36e4719-3ec6-4a0c-ab11-8b4aab377aa5` · Version 23 · ObjectID · 138 seen, in steps 01–23
Referenced by: Media (138)

| Path | Present | Holds |
|---|---|---|
| `Duration` | always | int64 |
| `IgnoreAlpha` | 92/138 | bool (true) |
| `CodecType` | always | int64 |
| `IsStill` | 46/138 | bool (true) |
| `OriginalColorSpace` | always | json |
| `FieldTypeIsUncertain` | always | bool (true) |
| `OriginalImageOrientationType` | 92/138 | int (1) |
| `FrameRate` | always | int64 |
| `FrameRect` | always | csv-numbers |
| `AlphaType` | 115/138 | int (1, 3) |

### VideoTrackGroup

Video tracks, sequence FrameRate/FrameRect.

ClassID `9e9abf7a-0918-49c2-91ae-991b5dde77bb` · Version 13 · ObjectID · 48 seen, in steps 03–23
Referenced by: Sequence (48)

| Path | Present | Holds |
|---|---|---|
| `TrackGroup/Tracks/Track@ObjectURef` | always | → VideoClipTrack |
| `TrackGroup/Tracks/Track@Index` | always | index |
| `TrackGroup/NextTrackID` | always | int (4) |
| `TrackGroup/FrameRate` | always | int64 |
| `ColorManagementSettings` | always | json |
| `AutoInputGamutCompressionEnabled` | always | bool (true) |
| `ToneMappingDesaturation` | always | float |
| `IsGraphicsWhiteSameAsProject` | always | bool (false) |
| `IsColorAwareEffectsEnabledSameAsProject` | always | bool (false) |
| `FrameRect` | always | csv-numbers |
| `OutputColorSpace` | always | json |
| `ComponentOwner/Components@ObjectRef` | always | → VideoComponentChain |

### WorkspaceSettings

Workspace state.

ClassID `c4372273-e1aa-4683-98aa-a2ceadf3066c` · Version 1 · ObjectID · 24 seen, in steps 00–23
Referenced by: Project (24)

(no children)
