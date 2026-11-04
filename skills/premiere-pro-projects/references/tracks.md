# Tracks: video and audio tracks, mixer objects, track settings

Recipes for tracks. The rules are in spec [§8](spec/08-tracks.md#8-tracks), each proven on the steps it cites ([§0](spec/README.md#0-conventions)).

## Where tracks live

```
Sequence/TrackGroups/TrackGroup[First=228cda18…]/Second ─► VideoTrackGroup/TrackGroup/Tracks/Track[Index=n] ─ObjectURef─► VideoClipTrack
Sequence/TrackGroups/TrackGroup[First=80b8e3d5…]/Second ─► AudioTrackGroup/TrackGroup/Tracks/Track[Index=n] ─ObjectURef─► AudioClipTrack
                                                           AudioTrackGroup/MasterTrack ─► AudioMixTrack ─Inlet─► AudioTrackInlet/Sources/Source[Index=n] ─► AudioClipTrack
```

- **`Tracks/Track Index="0"` is V1 / A1**; video and audio are numbered separately (spec [§8](spec/08-tracks.md#8-tracks), item 1).
- A track's position is written four times, and all four must agree: the `Track Index` attribute, `ClipTrack/Track/Index`, `ClipItems/Index`, `TransitionItems/Index` (item 2).
- `ClipTrack/Track/ID` is a small integer, unique in its group; audio clip tracks start at 2 because the master is 1 (item 3).
- An audio track's UID is listed twice: in its group's `Tracks` and in the master's `AudioTrackInlet/Sources`, which must equal the `Tracks` list in order (item 5).

## VideoClipTrack (one object)

As Premiere writes it (spec [§8](spec/08-tracks.md#8-tracks), item 4; field-level detail in [`prproj-classes.md`](prproj-classes.md#videocliptrack)):

```xml
<VideoClipTrack ObjectUID="{TRACK_UID}" ClassID="f68dcd81-8805-11d5-af2d-9bfa89d4ddd4" Version="1">
	<ClipTrack Version="2">
		<Track Version="4">
			<Node Version="1">
				<Properties Version="1">
					<TL.SQTrackExpanded>0</TL.SQTrackExpanded>
					<TL.SQTrackExpandedHeight>41</TL.SQTrackExpandedHeight>
					<MZ.SourceTrackState>0</MZ.SourceTrackState>
					<MZ.SourceTrackNumber>-1</MZ.SourceTrackNumber>
					<TL.SQTrackShy>0</TL.SQTrackShy>
					<MZ.TrackTargeted>0</MZ.TrackTargeted>
				</Properties>
			</Node>
			<ID>{NextTrackID}</ID>
			<MediaType>228cda18-3625-4d2d-951e-348879e4ed93</MediaType>
			<Index>{n}</Index>
		</Track>
		<ClipItems Version="3">
			<!-- <TrackItems Version="1"><TrackItem Index="0" ObjectRef="{ITEM}"/></TrackItems> only when populated -->
			<MediaType>228cda18-3625-4d2d-951e-348879e4ed93</MediaType>
			<Index>{n}</Index>
		</ClipItems>
		<TransitionItems Version="3">
			<MediaType>228cda18-3625-4d2d-951e-348879e4ed93</MediaType>
			<Index>{n}</Index>
		</TransitionItems>
	</ClipTrack>
</VideoClipTrack>
```

## AudioClipTrack (8 objects per track)

```xml
<AudioClipTrack ObjectUID="{TRACK_UID}" ClassID="097f6203-99ae-11d5-84f2-8cf14bde7040" Version="7">
	<ClipTrack Version="2">
		<Track Version="4">
			<Node Version="1">
				<Properties Version="1">
					<TL.SQTrackExpanded>0</TL.SQTrackExpanded>
					<TL.SQTrackExpandedHeight>41</TL.SQTrackExpandedHeight>
					<MZ.SourceTrackState>0</MZ.SourceTrackState>
					<MZ.SourceTrackNumber>-1</MZ.SourceTrackNumber>
					<TL.SQTrackAudioKeyframeStyle>0</TL.SQTrackAudioKeyframeStyle>
					<TL.SQTrackShy>0</TL.SQTrackShy>
					<CM.KeyframeMode>true</CM.KeyframeMode>
					<MZ.TrackTargeted>1</MZ.TrackTargeted>
				</Properties>
			</Node>
			<ID>{NextTrackID}</ID>
			<MediaType>80b8e3d5-6dca-4195-aefb-cb5f407ab009</MediaType>
			<Index>{n}</Index>
		</Track>
		<ClipItems Version="3"><MediaType>80b8e3d5-6dca-4195-aefb-cb5f407ab009</MediaType><Index>{n}</Index></ClipItems>
		<TransitionItems Version="3"><MediaType>80b8e3d5-6dca-4195-aefb-cb5f407ab009</MediaType><Index>{n}</Index></TransitionItems>
	</ClipTrack>
	<AudioTrack Version="12">
		<ComponentOwner Version="1"><Components ObjectRef="{CHAIN}"/></ComponentOwner>
		<Panner ObjectRef="{PAN}"/>
		<ID>{GUID}</ID>
		<NextPannerID>4294967277</NextPannerID>
	</AudioTrack>
</AudioClipTrack>
```

The track owns seven more top-level objects (spec [§8](spec/08-tracks.md#8-tracks), item 4); ClassIDs and fields are in [`prproj-classes.md`](prproj-classes.md):

| Object | Role |
|---|---|
| `AudioComponentChain` {CHAIN} | `Components`: 0 → Fader, 1 → Meter |
| `AudioFader` | params 0 Volume, 1 Mute; the track's mute lives here (spec [§12.6](spec/12-effects-and-keyframes.md#126-audio-effects)) |
| `AudioComponentParam` Volume, `AudioComponentParam` Mute | the fader's params; at their defaults they have no `StartKeyframe` (spec [§3](spec/03-value-encodings.md#3-value-encodings)) |
| `AudioMeter` | no params |
| `StereoToStereoPanProcessor` {PAN} | param 0 Balance |
| `AudioComponentParam` Balance | the panner's param |

## Track settings

| Setting | Where | Rule |
|---|---|---|
| Track height | `TL.SQTrackExpandedHeight` | view state [O: steps 03–23 #tracks.expanded-height] |
| Targeting | `MZ.TrackTargeted` (0/1) | view state, changes when a track header is clicked [O: steps 08→09 #tracks.track-targeted] |
| Source patching | `MZ.SourceTrackNumber`/`MZ.SourceTrackState`, and the sequence's `HSL.TimelinePatchingAndTargeting.AudioPatches…` | view state, added when another sequence is opened [O: steps 03→04 #tracks.patching-state] |
| **Mute** | the fader's Mute param | [O: steps 08→09 #tracks.mute] |
| **Custom name** | `ClipTrack/Track/Node/Properties/MZ.TrackName` | absent = the default name [O: steps 09→10 #tracks.name] |
| **Lock** | `ClipTrack/Track/IsLocked` = `true` | absent = unlocked [O: steps 08→09 #tracks.lock] |

Leave the view-state keys as they are. Solo, sync lock, the output toggle (eye), track volume and pan, track effects, submixes, mono/5.1/adaptive tracks and locking an audio track aren't covered ([§18](spec/18-not-observed.md)): ask the user to do those in Premiere.

## Master track and mixer

```xml
<AudioMixTrack ObjectID="{MASTER}" ClassID="4b1d8400-e89e-11d5-abc4-a1a13b1e80a0" Version="4">
	<AudioTrack Version="12">
		<ComponentOwner Version="1"><Components ObjectRef="{MCHAIN}"/></ComponentOwner>  <!-- Fader+Meter, chain has Node ActiveComponentID 1 -->
		<Panner ObjectRef="{MPAN}"/>              <!-- DefaultPanProcessor 33a94282-ee2c-11d5-abc4-c1cd7f9e3c10 v2, no params, In/OutputChannelType 1 -->
		<ID>{GUID}</ID>
		<SubType>3</SubType>
		<Assign>0</Assign>
		<NextPannerID>4294967277</NextPannerID>
	</AudioTrack>
	<Track Version="4"> … Properties (height 41, AudioKeyframeStyle 2, Shy 0) … <ID>1</ID><MediaType>80b8e3d5-…</MediaType><Index>0</Index></Track>
	<Inlet ObjectRef="{INLET}"/>
</AudioMixTrack>
<AudioTrackInlet ObjectID="{INLET}" ClassID="be3af080-e8c6-11d5-abc4-a1c6d5dee670" Version="4">
	<Sources Version="1">
		<Source Index="0" ObjectURef="{A1_UID}"/>
		<Source Index="1" ObjectURef="{A2_UID}"/>
	</Sources>
	<AudioChannelLayout>[{"channellabel":100},{"channellabel":101}]</AudioChannelLayout>
</AudioTrackInlet>
```

`Inlet/Sources` must equal the group's `Tracks` list, same order; keep them in lockstep. One master per sequence: mix track, chain, fader with 2 params, meter, `DefaultPanProcessor` and inlet (spec [§8](spec/08-tracks.md#8-tracks), item 5).

## Empty vs populated

- **Empty track:** `ClipItems` and `TransitionItems` hold only `MediaType` + `Index`; there is no `<TrackItems>`, not even an empty one. A populated list goes **before** that container's `MediaType` (spec [§8](spec/08-tracks.md#8-tracks), item 6).
- **Populated:** `ClipItems/TrackItems/TrackItem Index="k" ObjectRef="{ITEM}"`, contiguous from 0, in `Start` order (spec [§9.3](spec/09-track-items-and-links.md#93-per-track-invariants)).
- **Transitions** go in `TransitionItems/TrackItems`, not `ClipItems`, and the clips they touch point at them through `HeadTransition`/`TailTransition` (spec [§11](spec/11-transitions.md#11-transitions)). They move or go with their clip.

## Recipes

`prproj.py set-track FILE OUT --seq NAME --track N [--name NAME] [--lock on|off] [--mute on|off]` covers mute, name and lock; its output matches Premiere's steps 08→09 and 09→10 (`tests/premiere-pro/replay_steps.py`). Use it rather than editing by hand. After any change, run `prproj.py cuts --seq NAME` and tell the user to reopen the project in Premiere.

Adding, removing or reordering tracks, and moving clips from one track to another, aren't covered ([§18](spec/18-not-observed.md)): ask the user to do them in Premiere.

### Mute / unmute an audio track

Find the track's `AudioFader` (its chain's Component 0) and the `AudioComponentParam` named `Mute`. Muting inserts `StartKeyframe` and `CurrentValue`, in that order, before `<Name>` [O: steps 08→09 #tracks.mute]:

```xml
<AudioComponentParam ObjectID="{ID}" ClassID="32657501-3aa4-445f-a49b-d09ecb9fa1ae" Version="10">
	<StartKeyframe>-91445760000000000,true,0,0,0,0,0,0</StartKeyframe>
	<CurrentValue>true</CurrentValue>
	<Name>Mute</Name>
	<RangeLocked>false</RangeLocked>
</AudioComponentParam>
```

Unmuting removes both elements again (`set-track --mute off`, as in step 13-gen).

### Rename a track

Add `MZ.TrackName` to the track's `ClipTrack/Track/Node/Properties` [O: steps 09→10 #tracks.name]; Premiere put it after `TL.SQTrackShy` and before `MZ.TrackTargeted`:

```xml
<Track Version="4">
	<Node Version="1">
		<Properties Version="1">
			…
			<TL.SQTrackShy>0</TL.SQTrackShy>
			<MZ.TrackName>Graphics</MZ.TrackName>
			<MZ.TrackTargeted>1</MZ.TrackTargeted>
		</Properties>
	</Node>
	<ID>2</ID>
```

To go back to the default name, delete the element. The scripts name audio tracks the same way [V: steps 11→17-gen #tracks.name-script]. Characters that need escaping (`&`, `<`, `>`) aren't covered ([§18](spec/18-not-observed.md)): keep names to plain text.

### Lock / unlock a video track

Add `<IsLocked>true</IsLocked>` as the last child of `ClipTrack/Track`, after `<Index>` [O: steps 08→09 #tracks.lock]:

```xml
	<ID>1</ID>
	<MediaType>228cda18-3625-4d2d-951e-348879e4ed93</MediaType>
	<Index>0</Index>
	<IsLocked>true</IsLocked>
</Track>
```

Unlock: delete the element [V: steps 12-gen→16-gen, 11→17-gen #tracks.unlock-script]. Locking an audio track isn't covered.

## Gotchas

- `findall('.//TrackItems/TrackItem')` on a track also matches `TransitionItems`. Use `ClipTrack/ClipItems/TrackItems/TrackItem` for clips; `prproj.py` uses the narrow form.
- Each track has three `MediaType` elements (`Track`, `ClipItems`, `TransitionItems`). When adding the first item, anchor on `<ClipItems Version="3">` and insert `<TrackItems>` before *that* block's `MediaType`.
- `prproj.py cuts` numbers tracks across both groups (`VideoClipTrack[0..3]`, then `AudioClipTrack[4..]`). Convert to V/A numbers by position within each group.
- An `AudioClipTrack`'s `AudioTrack/ID` is a GUID, regenerated on any clone; `ClipTrack/Track/ID` is the small integer (spec [§2.4](spec/02-document-structure.md#24-allocating-identities)). Don't confuse the two.
- Keep every indexed list contiguous from 0: `Tracks/Track@Index`, `Inlet/Sources/Source@Index`, `TrackItems/TrackItem@Index`, `Links/Link@Index` (spec [§2](spec/02-document-structure.md#2-document-structure)).
