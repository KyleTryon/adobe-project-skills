# 8. Tracks

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

Recipes and mixer objects: [`tracks.md`](../tracks.md).

1. A group lists its tracks in `TrackGroup/Tracks/Track[Index]` (ObjectURef); **Index 0 is V1 / A1**, video and audio numbered separately [O: steps 03–23 #tracks.order].
2. A track's position is written four times and all four MUST agree: `Track@Index` in the group, `ClipTrack/Track/Index`, `ClipTrack/ClipItems/Index`, `ClipTrack/TransitionItems/Index` [O: steps 03–23 #tracks.index-four-times].
3. `ClipTrack/Track/ID` is a small integer unique in the group. Audio clip-track IDs start at 2 (the master is 1), so a new sequence's `NextTrackID` is the track count + 1 for video, + 2 for audio [O: steps 02→03, 03→04 #tracks.ids]. Adding or removing tracks isn't covered ([§18](18-not-observed.md)).
4. A **video track** is one object (`VideoClipTrack`). An **audio track** is eight: `AudioClipTrack`, its `AudioComponentChain`, an `AudioFader` with Volume and Mute params, an `AudioMeter`, a `StereoToStereoPanProcessor` and its Balance param [O: steps 03→04 #tracks.object-counts].
5. One master per sequence: `AudioMixTrack`, chain, fader with 2 params, meter, `DefaultPanProcessor`, and an `AudioTrackInlet` whose `Sources` list MUST equal the group's `Tracks` list, in order [O: steps 03–23 #tracks.master].
6. **Empty tracks** have no `TrackItems` in `ClipItems` or `TransitionItems`; a populated list goes before that container's `MediaType` [O: steps 03–23 #tracks.empty-no-trackitems].
7. View state: `TL.SQTrackExpandedHeight` [O: steps 03–23 #tracks.expanded-height]; `MZ.TrackTargeted` (0/1), which changes when a header is clicked [O: steps 08→09 #tracks.track-targeted]; `MZ.SourceTrackNumber`/`State` on the audio tracks and the sequence's `HSL.TimelinePatchingAndTargeting.AudioPatches<GUID>`, added when another sequence is opened [O: steps 03→04 #tracks.patching-state]. Track settings, absent at their defaults:
   - **Name:** `ClipTrack/Track/Node/Properties/MZ.TrackName` [O: steps 09→10 #tracks.name]; the scripts also name an audio track this way [V: steps 11→17-gen #tracks.name-script].
   - **Lock:** `ClipTrack/Track/IsLocked` = `true`, the last child of `Track` [O: steps 08→09 #tracks.lock]; unlocking removes it [V: steps 12-gen→16-gen, 11→17-gen #tracks.unlock-script].
   - **Mute:** the track fader's `Mute` param ([§12.6](12-effects-and-keyframes.md#126-audio-effects)): `StartKeyframe` `-91445760000000000,true,0,0,0,0,0,0` then `CurrentValue` `true`, before `Name` [O: steps 08→09 #tracks.mute].

   Lock is seen on video tracks only. Locking an audio track, sync lock, the output toggle (eye), solo, track effects, submixes and non-stereo tracks are not covered; see [§18](18-not-observed.md).
