# Effects, component chains and keyframes

Status of every rule here: [the spec](spec/README.md) (§0 for the tags); formats are in spec [§12](spec/12-effects-and-keyframes.md#12-effects-and-keyframes). Covered: reading any chain, and adding a Transform, static or with Position keys, with or without motion blur. Not covered (spec [§18](spec/18-not-observed.md)): other effects, explicit Motion or Opacity, clip volume and audio Level keys, keyed scalar params. Do those in Premiere.

Use the script:

```
prproj.py effects FILE --seq NAME [--track N] [--item N]          # read the stack, keys at timeline times
prproj.py add-transform FILE OUT --seq NAME --track N --item N [--set k=v] [--motion-blur on] [--keys position SPEC]
```

`--track`/`--item` are the indices `cuts --seq NAME` prints (items start at 1). `add-transform` refuses an item that already has a Transform unless `--force`; all write commands take `--dry-run`. Changing an existing Transform (`set-transform`) isn't proven yet and refuses to run. The rest of this file is what the script writes, so you can check its work.

## Component chains

Every track item's `ClipTrackItem/ComponentOwner/Components` points at its own chain object, never shared (spec [§12.1](spec/12-effects-and-keyframes.md#121-chains); ClassIDs in [`prproj-classes.md`](prproj-classes.md)):

| Item | Chain |
|---|---|
| `VideoClipTrackItem` | `VideoComponentChain` (Version 3) |
| `AudioClipTrackItem` | `AudioComponentChain` (Version 4) |

### Intrinsic effects are implicit

Motion and Opacity (video) and Volume / Channel Volume (audio) aren't written while they hold their defaults; the chain carries flags instead (spec [§12.1](spec/12-effects-and-keyframes.md#121-chains)):

```xml
<VideoComponentChain ObjectID="{CHAIN}" ClassID="0970e08a-f58f-4108-b29a-1a717b8e12e2" Version="3">
	<DefaultMotion>true</DefaultMotion>
	<DefaultOpacity>true</DefaultOpacity>
	<DefaultMotionComponentID>1</DefaultMotionComponentID>
	<DefaultOpacityComponentID>2</DefaultOpacityComponentID>
	<ComponentChain Version="3">
		<Components Version="1">            <!-- absent when there are no effects -->
			<Component Index="0" ObjectRef="{FILTER}"/>
		</Components>
	</ComponentChain>
</VideoComponentChain>
```

`ComponentChain/Node/Properties` (`MZ.ComponentChain.ActiveComponentID`, `…ActiveComponentParamIndex`) is view state Premiere adds once a clip has been selected. To move, scale or fade a picture, add a **Transform**; don't write an explicit Motion or Opacity component.

### Component IDs

`Component/ID` is unique within a chain. 1 and 2 stay reserved for Motion and Opacity while they're implicit, so the first added effect is 3: new ID = max(IDs in the chain ∪ {1,2}) + 1 (spec [§12.1](spec/12-effects-and-keyframes.md#121-chains)). `effects` lists any other component by its `MatchName`; don't edit or create those.

## Transform (`AE.ADBE Geometry2`) — complete object set

A Transform is one `VideoFilterComponent` plus 12 param objects, all top-level. This is the object set `add-transform` writes (spec [§12.5](spec/12-effects-and-keyframes.md#125-transform-aeadbe-geometry2): verified in step 12-gen, and Premiere kept it on re-save in step 15). Copy it exactly, replacing the `{…}` placeholders with fresh ObjectIDs ([object-surgery.md](object-surgery.md)). A Transform applied in Premiere itself isn't in any step, so its defaults there may differ.

```xml
<VideoFilterComponent ObjectID="{F}" ClassID="d10da199-beea-4dd1-b941-ed3a78766d50" Version="9">
	<Component Version="7">
		<Params Version="1">
			<Param Index="0" ObjectRef="{P0}"/>
			<Param Index="1" ObjectRef="{P1}"/>
			…Index 2-10…
			<Param Index="11" ObjectRef="{P11}"/>
		</Params>
		<ID>{COMPONENT_ID}</ID>
		<DisplayName>Transform</DisplayName>
	</Component>
	<VideoFilterType>2</VideoFilterType>
	<MatchName>AE.ADBE Geometry2</MatchName>
</VideoFilterComponent>
<PointComponentParam ObjectID="{P0}" ClassID="ca81d347-309b-44d2-acc7-1c572efb973c" Version="4">
	<Name>Anchor Point</Name>
	<ParameterID>1</ParameterID>
	<StartKeyframe>-91445760000000000,0.5:0.5,0,0,0,0,0,0,5,4,0,0,0,0</StartKeyframe>
</PointComponentParam>
<PointComponentParam ObjectID="{P1}" ClassID="ca81d347-309b-44d2-acc7-1c572efb973c" Version="4">
	<Name>Position</Name>
	<ParameterID>2</ParameterID>
	<StartKeyframe>-91445760000000000,0.5:0.5,0,0,0,0,0,0,5,4,0,0,0,0</StartKeyframe>
</PointComponentParam>
<VideoComponentParam ObjectID="{P2}" ClassID="cc12343e-f113-4d3b-ae05-b287db77d461" Version="10">
	<ParameterID>11</ParameterID>
	<StartKeyframe>-91445760000000000,true,0,0,0,0,0,0</StartKeyframe>
</VideoComponentParam>
<VideoComponentParam ObjectID="{P3}" ClassID="fe47129e-6c94-4fc0-95d5-c056a517aaf3" Version="10">
	<Name>Scale Height</Name>
	<LowerUIBound>-200</LowerUIBound>
	<ParameterID>3</ParameterID>
	<UpperUIBound>200</UpperUIBound>
	<StartKeyframe>-91445760000000000,100.,0,0,0,0,0,0</StartKeyframe>
	<LowerBound>-30000</LowerBound>
	<UpperBound>30000</UpperBound>
</VideoComponentParam>
<VideoComponentParam ObjectID="{P4}" ClassID="fe47129e-6c94-4fc0-95d5-c056a517aaf3" Version="10">
	<Name>Scale Width</Name>
	<LowerUIBound>-200</LowerUIBound>
	<ParameterID>4</ParameterID>
	<UpperUIBound>200</UpperUIBound>
	<StartKeyframe>-91445760000000000,100.,0,0,0,0,0,0</StartKeyframe>
	<LowerBound>-30000</LowerBound>
	<UpperBound>30000</UpperBound>
</VideoComponentParam>
<VideoComponentParam ObjectID="{P5}" ClassID="fe47129e-6c94-4fc0-95d5-c056a517aaf3" Version="10">
	<Name>Skew</Name>
	<ParameterID>5</ParameterID>
	<StartKeyframe>-91445760000000000,0.,0,0,0,0,0,0</StartKeyframe>
	<LowerBound>-70</LowerBound>
	<UpperBound>70</UpperBound>
</VideoComponentParam>
<VideoComponentParam ObjectID="{P6}" ClassID="fe47129e-6c94-4fc0-95d5-c056a517aaf3" Version="10">
	<Name>Skew Axis</Name>
	<ParameterControlType>3</ParameterControlType>
	<ParameterID>6</ParameterID>
	<StartKeyframe>-91445760000000000,0.,0,0,0,0,0,0</StartKeyframe>
	<LowerBound>-32768</LowerBound>
	<UpperBound>32767</UpperBound>
</VideoComponentParam>
<VideoComponentParam ObjectID="{P7}" ClassID="fe47129e-6c94-4fc0-95d5-c056a517aaf3" Version="10">
	<Name>Rotation</Name>
	<ParameterControlType>3</ParameterControlType>
	<ParameterID>7</ParameterID>
	<StartKeyframe>-91445760000000000,0.,0,0,0,0,0,0</StartKeyframe>
	<LowerBound>-32768</LowerBound>
	<UpperBound>32767</UpperBound>
</VideoComponentParam>
<VideoComponentParam ObjectID="{P8}" ClassID="fe47129e-6c94-4fc0-95d5-c056a517aaf3" Version="10">
	<Name>Opacity</Name>
	<ParameterID>8</ParameterID>
	<StartKeyframe>-91445760000000000,100.,0,0,0,0,0,0</StartKeyframe>
	<LowerBound>0</LowerBound>
	<UpperBound>100</UpperBound>
</VideoComponentParam>
<VideoComponentParam ObjectID="{P9}" ClassID="cc12343e-f113-4d3b-ae05-b287db77d461" Version="10">
	<ParameterID>9</ParameterID>
	<StartKeyframe>-91445760000000000,true,0,0,0,0,0,0</StartKeyframe>
</VideoComponentParam>
<VideoComponentParam ObjectID="{P10}" ClassID="fe47129e-6c94-4fc0-95d5-c056a517aaf3" Version="10">
	<Name>Shutter Angle</Name>
	<ParameterID>10</ParameterID>
	<StartKeyframe>-91445760000000000,240.,0,0,0,0,0,0</StartKeyframe>
	<CurrentValue>240</CurrentValue>
	<LowerBound>0</LowerBound>
	<UpperBound>360</UpperBound>
</VideoComponentParam>
<VideoComponentParam ObjectID="{P11}" ClassID="6e02e8bb-2569-46b2-8ab1-4ab11c43e9c8" Version="10">
	<Name>Sampling</Name>
	<DiscontinuousInterpolate>true</DiscontinuousInterpolate>
	<ParameterID>12</ParameterID>
	<StartKeyframe>-91445760000000000,0,0,0,0,0,0,0</StartKeyframe>
	<LowerBound>0</LowerBound>
	<UpperBound>1</UpperBound>
</VideoComponentParam>
```

Then add `<Component Index="n" ObjectRef="{F}"/>` to the chain's `Components` (create the `<Components Version="1">` block, indented as above, before `</ComponentChain>` if missing). Insert the new objects right after the chain so the diff stays local.

| Index | Param | ParameterID | Value format | Notes |
|---|---|---|---|---|
| 0 | Anchor Point | 1 | point `x:y` | |
| 1 | Position | 2 | point `x:y` | |
| 2 | Uniform Scale | 11 | `true`/`false` | no `<Name>` element |
| 3 | Scale Height | 3 | float, % | the scale when uniform (`--set scale=40` in step 12-gen) |
| 4 | Scale Width | 4 | float, % | used only when Uniform Scale is false |
| 5 | Skew | 5 | float | |
| 6 | Skew Axis | 6 | float, degrees | |
| 7 | Rotation | 7 | float, degrees | |
| 8 | Opacity | 8 | float, % | the Transform's own opacity |
| 9 | Use Composition's Shutter Angle | 9 | `true`/`false` | no `<Name>`. **`false` = motion blur on** |
| 10 | Shutter Angle | 10 | float | 240 in the steps |
| 11 | Sampling | 12 | enum | 0 in the steps |

### Positions

Points are `x:y` fractions of the frame, as `--keys` and `--set` take them (0.5:0.5 = centre). How far off-screen a clip must start depends on its scale and anchor; in step 12-gen a picture-in-picture at 40% slides in from `1.3:0.75` to `0.78:0.75`. Check any other start point in Premiere.

### Motion blur

`--motion-blur on` sets param 9 to `false` and keeps Shutter Angle at 240, which turns motion blur on for the move (spec [§12.5](spec/12-effects-and-keyframes.md#125-transform-aeadbe-geometry2), verified in step 12-gen). Say in your report that you did.

## Static values and keyframes

Formats: spec [§12.3](spec/12-effects-and-keyframes.md#123-static-value) (`StartKeyframe`) and [§12.4](spec/12-effects-and-keyframes.md#124-animation) (`IsTimeVarying`, `Keyframes`, the point-key fields). Only Position keys are covered; removing animation and keying Scale, Rotation or Opacity aren't (spec [§18](spec/18-not-observed.md)).

### Keyframe times are source time, not clip-relative

A key's time is in the clip's **source** timebase, like its `InPoint`/`OutPoint` (spec [§12.4](spec/12-effects-and-keyframes.md#124-animation): step 15's first key sits at its clip's `InPoint`, 5.005 s, while the clip starts at 12.012 s on the timeline). For the speed-1 clips the spec covers:

```
key_ticks      = InPoint + (timeline_ticks - TrackItem.Start)
timeline_ticks = TrackItem.Start + (key_ticks - InPoint)
```

Snap `timeline_ticks − Start` to the sequence frame grid (ticks per frame = the sequence's `VideoTrackGroup` `FrameRate`) before converting. `effects` shows keys at timeline times and `--keys` takes clip-relative seconds or frames, converting for you. Clips with speed changes aren't covered; the script refuses reversed clips without `--force`.

### Key strings

The script's key writer follows spec [§12.4](spec/12-effects-and-keyframes.md#124-animation), which reproduces every field of the step 15 Position animation; it recomputes speeds and tangents from the key values rather than copying them from an existing key. `scripts/selftest.py PROJECT.prproj` re-runs that comparison (plus the Transform layout and timeline checks) on any project; run it on a project saved by a newer Premiere before trusting the write commands there.

### Slide in and out

Step 12-gen's picture-in-picture, opened in Premiere: an off-screen key `@linear` → an on-screen key (eased by default) arrives at full speed and settles; two equal on-screen keys hold; an on-screen key → an off-screen key `@linear` leaves.

```
prproj.py add-transform P.prproj P.prproj --seq clip-a --track 1 --item 1 --motion-blur on --set scale=40 \
  --keys position "0f=1.3:0.75@linear, 12f=0.78:0.75, -12f=0.78:0.75, -1f=1.3:0.75@linear"
```

## Audio

Track volume and mute live on the track's `AudioFader` (spec [§12.6](spec/12-effects-and-keyframes.md#126-audio-effects); `set-track --mute`, [tracks.md](tracks.md)). Audio fades and crossfades are transitions, not volume keys ([cutting-and-editing.md](cutting-and-editing.md) §6). Clip volume, clip gain and Level keyframes aren't covered (spec [§18](spec/18-not-observed.md)): ask the user to set them in Premiere.

## Checks after an effects edit

1. `prproj.py validate OUT --orig ORIGINAL` (refs resolve, no duplicate IDs, nothing new left unreferenced).
2. `prproj.py effects OUT --seq NAME --track N --item N` and confirm keys land where intended on the timeline.
3. Tell the user to reopen the project in Premiere (without saving the old open copy) and scrub the move; that's the only full validation.
