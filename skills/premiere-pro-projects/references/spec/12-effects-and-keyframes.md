# 12. Effects and keyframes

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

Templates and recipes: [`effects.md`](../effects.md).

## 12.1 Chains

- Each track item owns one `VideoComponentChain` or `AudioComponentChain`; so do the video track group, each audio track, the master track and each MasterClip with audio (an audio chain) [O: steps 03–23 #effects.chain-owners].
- **Intrinsic effects are implicit.** A video item's chain carries `DefaultMotion`/`DefaultOpacity` = `true` and `DefaultMotionComponentID` 1 / `DefaultOpacityComponentID` 2; an audio item's or MasterClip's, `DefaultVol` = `true`, `DefaultVolumeComponentID` 1, `DefaultChannelVolumeComponentID` 2; track chains carry none [O: steps 03–23 #effects.implicit-defaults].
- `ComponentChain/Components/Component[Index]` lists the chain's components, and is absent when there are none [O: steps 03–23 #effects.components-absent-when-empty].
- `Component/ID` is unique in the chain; while Motion and Opacity are implicit, 1 and 2 stay reserved and the first added effect takes 3 = max(IDs ∪ {1,2}) + 1 [O: step 15 #effects.component-ids].
- `MZ.ComponentChain.ActiveComponentID` and `…ActiveComponentParamIndex` in `ComponentChain/Node/Properties` are view state: they appear on a clip's chain once it has been selected [O: steps 06→07 #effects.active-component-view-state].

## 12.2 Components and params

- A `VideoFilterComponent` holds `Component/Params/Param[Index]`, `Component/ID`, `Component/DisplayName`, `VideoFilterType` 2 and `MatchName` (`AE.ADBE Geometry2` for Transform) [O: step 15 #effects.filter-component]. Other effects are not covered; see [§18](18-not-observed.md).
- Param classes follow the value type, not the tag [O: step 15 #effects.param-classes]:

| Tag | ClassID | Holds |
|---|---|---|
| `PointComponentParam` | `ca81d347-309b-44d2-acc7-1c572efb973c` | point |
| `VideoComponentParam` | `fe47129e-6c94-4fc0-95d5-c056a517aaf3` | float |
| `VideoComponentParam` | `cc12343e-f113-4d3b-ae05-b287db77d461` | bool |
| `VideoComponentParam` | `6e02e8bb-2569-46b2-8ab1-4ab11c43e9c8` | enum |
| `AudioComponentParam` | `a714635e-a628-4b27-9d59-77eba47dbc1a` | float (Volume, Balance) |
| `AudioComponentParam` | `32657501-3aa4-445f-a49b-d09ecb9fa1ae` | bool (Mute) |

- A param's `ParameterID` is fixed per effect: Premiere kept the script-written Transform's IDs on re-save [O: steps 12-gen→15 #effects.parameter-ids-stable]. Video param child order: [`prproj-classes.md`](../prproj-classes.md).

## 12.3 Static value

`StartKeyframe` = time `,` value `,` six or more fields; the time is `-91445760000000000` [O: steps 03–23 #keys.static-form]:

```
point  : T,x:y,0,0,0,0,0,0,5,4,0,0,0,0
scalar : T,value,0,0,0,0,0,0          (float, bool true/false, or enum integer)
```

On an animated param `StartKeyframe` keeps its own value; Premiere doesn't set it to the first key [O: step 15 #keys.start-keyframe-kept].

## 12.4 Animation

An animated **video** param has `IsTimeVarying` = `true` (after `Name`, or first without one) and `Keyframes` right after `StartKeyframe` [O: step 15 #keys.animated-video-param]. Animated audio params and scalar keys are not covered; see [§18](18-not-observed.md).

```
Keyframes   = key { ";" key } ";"
point key   = t "," x ":" y "," interp ",0," speedIn "," inflIn "," speedOut "," inflOut ",5,4," tanInX "," tanInY "," tanOutX "," tanOutY
```

| Field | Meaning [O: step 15 #keys.point-key-format] |
|---|---|
| `t` | **source time** of the clip, in ticks (not clip-relative): `t = InPoint + (timeline − Start) · PlaybackSpeed` (the step 15 Transform's first key is its clip's `InPoint`, not 0) |
| `interp` | `5` Bezier key, `0` linear key |
| `0`, `5`, `4` | constant in every key seen |

| Field | Rule [O: step 15 #keys.reproduce-position] |
|---|---|
| speeds | 0 on Bezier (eased) keys. On linear keys, the adjacent segment's unsigned path speed `hypot(Δx,Δy)` per second of source time; 0 on a side with no segment |
| influences | Eased: 1/3 on a side whose segment changes value (Premiere's Ease In/Out), 1/6 on a hold or open side. Linear: 1/6 both sides |
| tangents | relative to the key: per segment A→B with Δ = B − A, A's out-tangent = +Δ/6 and B's in-tangent = −Δ/6 |

These rules reproduce every field of the step 15 Position animation.

## 12.5 Transform (`AE.ADBE Geometry2`)

One `VideoFilterComponent` plus 12 params in a fixed order, ParameterIDs in brackets: Anchor Point [1], Position [2], Uniform Scale [11], Scale Height [3], Scale Width [4], Skew [5], Skew Axis [6], Rotation [7], Opacity [8], Use Composition's Shutter Angle [9], Shutter Angle [10] (240 in the steps), Sampling [12] (an enum). [9] and [11] have no `Name` element [O: step 15 #effects.transform-params]. The scripts write the same layout, and `false` in [9] turns motion blur on [V: step 12-gen #effects.transform-written]. Types, names and the verbatim object set: [`effects.md`](../effects.md).

## 12.6 Audio effects

Track chains hold an `AudioFader` (Volume, Mute params) and an `AudioMeter`; track mute is the fader's Mute param ([§8](08-tracks.md#8-tracks)) [O: steps 08→09 #effects.track-fader]. Clip volume (the intrinsic Volume and Channel Volume components) is not covered; see [§18](18-not-observed.md).
