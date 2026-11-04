# 4. Object graph

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

```
Project ─ settings objects (ProjectSettings, CompileSettings×5, ScratchDiskSettings, IngestSettings, WorkspaceSettings, …)
   └─ RootProjectItem ─Items→ BinProjectItem ─Items→ (BinProjectItem | ClipProjectItem | FileProjectItem)
                                                        ClipProjectItem ─→ MasterClip
MasterClip ─→ ClipLoggingInfo
           ─→ AudioComponentChain (clip-level audio defaults)
           ─→ ClipChannelGroupVectorSerializer ─→ ClipChannelVectorSerializer ─→ ClipChannelSerializer×channels
           ─Clips→ VideoClip | AudioClip | TranscriptClip
                     Clip/Source ─→ VideoMediaSource | AudioMediaSource | DataMediaSource ─→ Media ─→ VideoStream | AudioStream | DataStream
                                 ─→ VideoSequenceSource | AudioSequenceSource ─→ Sequence          (a sequence used as a clip)
                     Clip/MarkerOwner ─→ Markers
                     AudioClip/SecondaryContents ─→ SecondaryContent×channels ─→ (the same source)
Sequence ─TrackGroups→ VideoTrackGroup | AudioTrackGroup | DataTrackGroup
   VideoTrackGroup ─Tracks→ VideoClipTrack ─ClipItems→ VideoClipTrackItem ─→ VideoComponentChain ─→ VideoFilterComponent ─→ params
                                                                             ─→ SubClip ─→ (MasterClip, VideoClip)
   AudioTrackGroup ─Tracks→ AudioClipTrack ─ClipItems→ AudioClipTrackItem ─→ AudioComponentChain ─→ AudioFilterComponent ─→ params
                                           ─TransitionItems→ AudioTransitionTrackItem
                   ─MasterTrack→ AudioMixTrack ─Inlet→ AudioTrackInlet ─Sources→ (the AudioClipTracks)
   Sequence/PersistentGroupContainer/LinkContainer ─Links→ Link ─→ (linked track items)
   Sequence/MarkerOwner ─→ Markers ─Markers→ Marker×markers                    (sequence markers, [§13](13-markers.md#13-markers))
```

A timeline clip owns its own `VideoClip`/`AudioClip` (its in/out range) whose `Source` is the shared media or sequence source [O: steps 03–23 #graph.timeline-clip-owns-clip].

# 5. Project and settings

- `Project` (ObjectID 1) holds `Node/Properties` and references to the settings objects; its last child is `NextID` ([§2.4](02-document-structure.md#24-allocating-identities)) [O: steps 00–23 #project.structure].
- Properties: `MZ.BuildVersion.Created` / `MZ.BuildVersion.Modified` (`26.5.2x5 - <date>`); `MZ.Project.GUID`, kept by Save a Copy [O: steps 00–23 #project.properties]; `MZ.PrefixKey.OpenSequenceGuidList.N`, the ObjectUIDs of open timeline tabs, which a new sequence joins [O: steps 02→03, 03→04 #project.open-sequence-list]; `MZ.NextSequenceIndex`, the counter behind "Sequence 02", added as 2 with the second sequence [O: steps 03→04 #project.next-sequence-index].
- Rewritten on every save [O: steps 00–11 #project.rewritten-on-save]: `MZ.BuildVersion.Modified`, `project.settings.lastknowngoodprojectpath` (the absolute path written, the copy's for Save a Copy) and `project.settings.lastknownparentdirectorypathaboveprojectpath` (its folder's parent).
- `DefaultSequenceSettings` holds presets for *new* sequences only. `VideoSettings`/`AudioSettings` belong to project and compile settings, not to sequences [O: steps 00–23 #project.settings-owners].
