# 11. Transitions

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

Transitions live in the track's `ClipTrack/TransitionItems/TrackItems` (time order) and are referenced, after `SubClip`, Head first, as `ClipTrackItem/HeadTransition` on the clip after the cut and `ClipTrackItem/TailTransition` on the clip before it [O: step 15 #transitions.placement]. Video transitions are not covered; see [§18](18-not-observed.md).

An `AudioTransitionTrackItem` (ClassID `23f687b6-9c5a-42f4-bea1-e7b3e28e7082`, Version 4) holds `TransitionTrackItem/TrackItem/Start`/`End`, `HasOutgoingClip`, `HasIncomingClip`, `DisplayName`, `MatchName`, `Alignment`, then `AudioChannelLayout` [O: step 15 #transitions.class]:

| Kind | Outgoing / Incoming | Name | `Alignment` | `FadeShapeValue` | Referenced as |
|---|---|---|---|---|---|
| Fade-in at a clip's head | false / true | `Custom Fade` | 0 | 0 | that clip's `HeadTransition` [V: step 13-gen #transitions.fade-in] |
| Fade-out at a clip's tail | true / false | `Custom Fade` | the fade's duration | 0 | that clip's `TailTransition` [V: step 14-gen #transitions.fade-out-script] [O: step 15 #transitions.fade-out] |
| Crossfade at a cut | true / true | `Constant Power` | d/2 when centred | absent | left clip's `TailTransition` and right clip's `HeadTransition` [O: step 15 #transitions.crossfade] |

- **`Alignment` = cut − `Start`** in ticks [O: step 15 #transitions.alignment].
- A crossfade spans cut − d/2 … cut + d/2 while both items keep their edges at the cut; Premiere plays the clips' **handles** (media beyond their in/out points) under it, so each side needs d/2 of handle [O: step 15 #transitions.crossfade-handles].
- Fades don't touch the clip's Volume/Level params ([§12.6](12-effects-and-keyframes.md#126-audio-effects)): the faded clips' chains keep `DefaultVol` true and no components [O: step 15 #transitions.no-volume-keys]. `prproj.py fade-in`, `fade-out` and `crossfade` write them; `tests/premiere-pro/replay_steps.py` checks the latter two against step 15.
