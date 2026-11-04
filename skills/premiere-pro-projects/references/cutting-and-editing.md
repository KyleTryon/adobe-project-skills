# Cutting and editing track items

Status of every rule here: [the spec](spec/README.md) (§0 for the tags); the formats are spec [§9](spec/09-track-items-and-links.md#9-track-items-and-clips) (track items), [§10](spec/09-track-items-and-links.md#10-links) (links), [§11](spec/11-transitions.md#11-transitions) (transitions) and [§13](spec/13-markers.md#13-markers) (markers). `prproj.py diff OLD NEW` between two steps shows what an edit wrote. Object internals for effects and keyframes are in [effects.md](effects.md), ID rules and cloning in [object-surgery.md](object-surgery.md).

## 1. Track item anatomy

Chain: `Track` (`ClipTrack/ClipItems/TrackItems/TrackItem Index= ObjectRef=`) → `VideoClipTrackItem`/`AudioClipTrackItem` → `SubClip` → `VideoClip`/`AudioClip` → `Source` (a `*MediaSource`) → `Media` (spec [§9.1](spec/09-track-items-and-links.md#91-anatomy)). ClassIDs and versions, from [`prproj-classes.md`](prproj-classes.md):

| Object | ClassID | Ver |
|---|---|---|
| VideoClipTrackItem | `368b0406-29e3-4923-9fcd-094fbf9a1089` | 8 |
| AudioClipTrackItem | `064ec682-9ba6-11d5-af2d-9ca32c7d6164` | 11 |
| SubClip | `e0c58dc9-dbdd-4166-aef7-5db7e3f22e84` | 6 |
| VideoClip | `9308dbef-2440-4acb-9ab2-953b9a4e82ec` | 11 |
| AudioClip | `b8830d03-de02-41ee-84ec-fe566dc70cd9` | 8 |
| SecondaryContent | `f9d004b5-cb04-4e2f-af6f-64fadc2c4be9` | 1 |
| VideoComponentChain / AudioComponentChain | `0970e08a-f58f-4108-b29a-1a717b8e12e2` / `3cb131d1-d3c0-47ae-a19a-bdf75ea11674` | 3 / 4 |
| Link | `149d4ea5-a7d4-4b34-9bb7-16d783904bf2` | 1 |
| AudioTransitionTrackItem | `23f687b6-9c5a-42f4-bea1-e7b3e28e7082` | 4 |
| Markers | `bee50706-b524-416c-9f03-b596ce5f6866` | 4 |
| Marker | `a45508e0-3ff7-4d04-90a7-2e0dfff4c910` | 3 |

**Nothing is shared per item:** each track item has its own chain, SubClip and clip, each AudioClip its own SecondaryContent objects, and every component and param object one referrer (spec [§2.2](spec/02-document-structure.md#22-references)). Only the MasterClip, the Source, the Media and the media's Markers object are shared. Split pieces are no exception (spec [§9.4](spec/09-track-items-and-links.md#94-premieres-edits)).

Video item, as Premiere writes it (clip-b on V1 in step 06; IDs replaced):

```xml
<VideoClipTrackItem ObjectID="T" ClassID="368b0406-29e3-4923-9fcd-094fbf9a1089" Version="8">
  <ClipTrackItem Version="8">
    <ComponentOwner Version="1"><Components ObjectRef="CHAIN"/></ComponentOwner>
    <TrackItem Version="4">
      <Start>2330808480000</Start>     <!-- omitted when 0 -->
      <End>2627456832000</End>
    </TrackItem>
    <SubClip ObjectRef="SC"/>
  </ClipTrackItem>
  <ToneMapSettings>{"peak":-1,"version":3}</ToneMapSettings>
  <FrameRect>0,0,1920,1080</FrameRect>  <!-- the sequence's frame size -->
  <PixelAspectRatio>1,1</PixelAspectRatio>
</VideoClipTrackItem>
<SubClip ObjectID="SC" ClassID="e0c58dc9-dbdd-4166-aef7-5db7e3f22e84" Version="6">
  <Clip ObjectRef="C"/>
  <MasterClip ObjectURef="MASTERCLIP-UID"/>
  <Name>clip-b.mp4</Name>              <!-- the name shown on the timeline -->
  <OrigChGrp>0</OrigChGrp>
</SubClip>
<VideoClip ObjectID="C" ClassID="9308dbef-2440-4acb-9ab2-953b9a4e82ec" Version="11">
  <Clip Version="18">
    <Node Version="1"><Properties Version="1">
      <asl.clip.label.color>6769408</asl.clip.label.color>
      <asl.clip.label.name>BE.Prefs.LabelColors.1</asl.clip.label.name>
    </Properties></Node>
    <MarkerOwner Version="1"><Markers ObjectRef="M"/></MarkerOwner>  <!-- media clips only -->
    <Source ObjectRef="SRC"/>
    <ClipID>GUID</ClipID>
    <InPoint>7225506288000</InPoint>   <!-- written even when 0 -->
    <OutPoint>7522154640000</OutPoint>
  </Clip>
</VideoClip>
```

The audio half differs as follows:

```xml
<AudioClipTrackItem ObjectID="T2" ClassID="064ec682-9ba6-11d5-af2d-9ca32c7d6164" Version="11">
  <ClipTrackItem Version="8">
    <ComponentOwner Version="1"><Components ObjectRef="ACHAIN"/></ComponentOwner>
    <TrackItem Version="4">
      <Node Version="1"><Properties Version="1"> …ESP.* / MZ.AudioCategorization… (Essential Sound; copy as-is)</Properties></Node>
      <Start>…</Start><End>…</End>
    </TrackItem>
    <SubClip ObjectRef="SC2"/>
    <HeadTransition ObjectRef="TR"/>   <!-- only with a head fade, see §6 -->
  </ClipTrackItem>
  <ID>GUID</ID>
  <PreRenderComponentChainHashVersion>1</PreRenderComponentChainHashVersion>
</AudioClipTrackItem>
<AudioClip ObjectID="C2" ClassID="b8830d03-de02-41ee-84ec-fe566dc70cd9" Version="8">
  <Clip Version="18"> …Node, Source, ClipID, InPoint, OutPoint as above… </Clip>
  <SecondaryContents Version="1">
    <SecondaryContentItem Index="0" ObjectRef="S0"/>
    <SecondaryContentItem Index="1" ObjectRef="S1"/>
  </SecondaryContents>
  <AudioChannelLayout>[{"channellabel":100},{"channellabel":101}]</AudioChannelLayout>
</AudioClip>
<SecondaryContent ObjectID="S0" ClassID="f9d004b5-cb04-4e2f-af6f-64fadc2c4be9" Version="1">
  <Content ObjectRef="SRC2"/><ChannelIndex>0</ChannelIndex>
</SecondaryContent>
```

Field notes (spec [§9](spec/09-track-items-and-links.md#9-track-items-and-clips)):

- **SecondaryContent:** one per channel (2 for the demo clips' stereo audio), each pointing at the clip's own `Source`.
- **Labels:** `Clip/Node/Properties/asl.clip.label.name`, per clip and per A/V half. New timeline clips of an `.mp4` get Iris (`BE.Prefs.LabelColors.1`), and split pieces copy their original's label (spec [§9.4](spec/09-track-items-and-links.md#94-premieres-edits)). Writing a label isn't covered yet (`set-label` refuses without `--unproven`); ask the user to label clips in Premiere.
- **ClipID:** unique per clip and stable across saves while every ObjectID changes (spec [§9.3](spec/09-track-items-and-links.md#93-per-track-invariants)). Use it to re-find an item after Premiere renumbers.
- Speed, reverse, frame blending, time remapping, disabling a clip, audio gain and Essential Graphics items aren't covered (spec [§18](spec/18-not-observed.md)). Track lock, mute and name are on tracks ([tracks.md](tracks.md)).

## 2. Timeline arithmetic

Every clip the spec covers plays at speed 1 (spec [§9.2](spec/09-track-items-and-links.md#92-timing)):

```
End − Start = Out − In
timeline t  ↔ source s:  s = In + (t − Start),   t = Start + (s − In)
```

- **Frame grid:** `Start` and `End` lie on the sequence's frame grid; ticks per frame = the sequence's `VideoTrackGroup/TrackGroup/FrameRate` (`10594584000` = 23.976 in the steps). At 23.976 fps a frame is exactly 2 002 samples of 48 kHz audio, so every frame boundary is a sample boundary (spec [§3](spec/03-value-encodings.md#3-value-encodings)).
- Don't extend an `Out` past the media's `OriginalDuration`.
- Check script: for each item, `(End−Start) == (Out−In)`, and Start and End are both multiples of the frame ticks.

## 3. Links

Spec [§10](spec/09-track-items-and-links.md#10-links):

- They live in the Sequence's `PersistentGroupContainer/LinkContainer/Links/Link Index=n ObjectRef=`. A `Link` holds `TrackItemGroup/TrackItems/TrackItem Index="0|1" ObjectRef=`: the video item, then the audio item.
- Every link has 2 members, a video item and an audio item, with identical Start/End/In/Out except in a split edit (J/L cut), which keeps the link with different audio edges. `Links` is in time order. An item is in at most one link.
- A video-only placement has no Link. Deleting one member of a link, and links of more than two items, aren't covered.

## 4. Rough cuts of a nested sequence

Not covered: no step nests a sequence (spec [§7.5](spec/07-sequences.md#75-nesting), [§18](spec/18-not-observed.md)). Cut a sequence's own clips instead, or ask the user to nest in Premiere.

## 5. Recipes

**Use the script:** `prproj.py split`, `trim` and `delete [--ripple]` make these edits, and `tests/premiere-pro/replay_steps.py` checks their output against Premiere's own saves of the same edits. They refuse clips with transitions, locked tracks, overlaps, and a ripple that would knock other tracks out of sync. The recipes say what the commands write, so you can check their work.

Notation: Δ is in timeline ticks and always a whole number of frames. "Partner" = the other member of the item's Link; do the same to the partner. Keep a backup sequence, and run `validate --orig` at the end.

| Operation | Command | Proof (spec [§9.4](spec/09-track-items-and-links.md#94-premieres-edits)) |
|---|---|---|
| Split at T | `split` | Premiere's razor, steps 05→06; script-written, step 17-gen |
| Place a clip | `place` | Premiere, steps 04→05; script-written, steps 12-gen, 18-gen |
| Trim the tail | `trim --end` | Premiere, steps 06→07; script-written, steps 16-gen, 17-gen |
| Trim the head | `trim --start` | script-written, steps 16-gen, 17-gen |
| Ripple delete | `delete --ripple` | Premiere, steps 07→08 |
| Back up a sequence | `backup-seq` | script-written, step 17-gen ([object-surgery.md](object-surgery.md)) |
| Add a sequence marker | `add-marker` | Premiere, steps 10→11; script-written, steps 17-gen, 20-gen (§7) |
| Audio fade-in, fade-out, crossfade | `fade-in`, `fade-out`, `crossfade` | spec [§11](spec/11-transitions.md#11-transitions) (§6) |

Not covered (spec [§18](spec/18-not-observed.md)); do these in Premiere: nesting, importing media by hand, ripple trim, lift, moving or slipping a clip, closing gaps, insert edits, speed changes, deleting a marker, disabling a clip, clip markers, video transitions, and moving or removing a transition.

**Trim head by Δ** (Δ > 0 shortens; script-written, steps 16-gen and 17-gen; Premiere's own head trim isn't recorded): `Start += Δ` and `In += Δ`, on the item and its partner. Write `<Start>` before `<End>` if it was absent; if Start becomes 0, delete the element, because Premiere never writes `<Start>0`.

**Trim tail by Δ** (Premiere, steps 06→07: a linked trim of 46 frames): `End −= Δ` and `Out −= Δ`, on the item and its partner; Premiere changed exactly these four values and added or removed nothing. `Monitor.ProgramZoomOut` follows the sequence length; leave `MZ.WorkOutPoint` and the sources' `OriginalDuration` alone (spec [§7.4](spec/07-sequences.md#74-length)).

**Split at T** (Start < T < End, T on the grid; Premiere's razor in steps 05→06):
- Piece A keeps its objects: `End = T`, `Out = In + (T − Start)`. Piece B is new: `Start = T`, `In` = A's new Out, and the original End/Out.
- Piece B is 11 new objects per A/V pair, including its own chains with every component and param object cloned ([object-surgery.md](object-surgery.md)), a new ClipID per clip and a new audio `ID`.
- **Index:** insert B's `TrackItem` right after A's and renumber that track's later `Index` values; every track stays time-sorted.
- Add a new 2-member Link for the new pair and insert its `Links` entry at the pair's time position, renumbering the later ones. Video-only items need no Link.

**Ripple delete** of one linked pair (Premiere, steps 07→08):
1. Delete the pair's 11 objects (per side the track item, its chain, the SubClip, the clip and the audio clip's SecondaryContents, plus the Link) and their entries in `TrackItems` and `Links`, and renumber both lists.
2. Every later item moves left by the deleted duration on `Start` and `End` only; In/Out stay.
3. `Monitor.ProgramZoomOut` = the new length. The sources' `OriginalDuration` and `MZ.WorkOutPoint` stay (spec [§7.4](spec/07-sequences.md#74-length)); `MZ.EditLine` is the playhead, view state Premiere moves during edits (spec [§7.3](spec/07-sequences.md#73-settings)).

## 6. Transitions

Format, the three kinds (fade-in, fade-out, crossfade) and their proof: spec [§11](spec/11-transitions.md#11-transitions). Use `prproj.py fade-in`, `fade-out` and `crossfade`. An empty track has no `TrackItems` in its `ClipTrack/TransitionItems`; the first transition adds them (spec [§8](spec/08-tracks.md#8-tracks)). The fade-in the script writes (step 13-gen, opened in Premiere):

```xml
<AudioTransitionTrackItem ObjectID="TR" ClassID="23f687b6-9c5a-42f4-bea1-e7b3e28e7082" Version="4">
  <TransitionTrackItem Version="3">
    <TrackItem Version="4"><Start>35629585992000</Start><End>36095747688000</End></TrackItem>
    <HasOutgoingClip>false</HasOutgoingClip>
    <HasIncomingClip>true</HasIncomingClip>
    <DisplayName>Custom Fade</DisplayName><MatchName>Custom Fade</MatchName>
    <Alignment>0</Alignment>
  </TransitionTrackItem>
  <AudioChannelLayout>[{"channellabel":100},{"channellabel":101}]</AudioChannelLayout>
  <FadeShapeValue>0</FadeShapeValue>
</AudioTransitionTrackItem>
```

Start = the clip's Start, incoming clip only, on the frame grid. `split`, `trim` and `delete` refuse a clip with a transition; moving, trimming or removing a transition isn't covered, so ask the user to do it in Premiere.

## 7. Markers

The format is spec [§13](spec/13-markers.md#13-markers): sequence markers with the orange and pink colours are covered; clip markers with entries, marker durations, other types and other colours aren't.

**Read.** For a sequence, follow `Sequence/MarkerOwner/Markers`; a media file's clips all share one `Clip/MarkerOwner/Markers` object. Each entry in the Markers object's inner `Markers` list points (`Second`) at a `Marker` object; parse its `DVAMarker` text as JSON. `mStartTime.ticks` is in sequence time. Sort by it, because the list isn't in time order. Colour is in `mCuePointList` (spec [§13.3](spec/13-markers.md#133-marker-object)).

`prproj.py markers` reads them (`--chapters` for YouTube chapter lines) and `prproj.py add-marker` writes this recipe; its output matches Premiere's step 11 apart from new GUIDs (`tests/premiere-pro/replay_steps.py`).

**Add a sequence marker** (Premiere, steps 10→11; script-written, steps 17-gen and 20-gen):

1. If the Sequence has no `MarkerOwner`, insert `<MarkerOwner Version="1">`, `<Markers ObjectRef="{MK}"/>`, `</MarkerOwner>` (three lines, tab-indented) between its `Node` and `PersistentGroupContainer`, and add a top-level `Markers` object {MK} as in spec [§13.2](spec/13-markers.md#132-markers-object), with zero state GUIDs.
2. If the Markers object has no inner `<Markers Version="1">` list, add one as its first child.
3. Write a `Marker` object {ID} (ClassID `a45508e0-3ff7-4d04-90a7-2e0dfff4c910`, Version 3) whose `DVAMarker` is the JSON of spec [§13.3](spec/13-markers.md#133-marker-object): a new `mMarkerID` GUID, `mName`, `mComment`, `mStartTime.ticks` on the frame grid, `mType` `Comment` or `Chapter`, and one cue point with key `keywordExtDVAv1_{new GUID}` and value `{\"color\":N}` (orange or pink). Keys in alphabetical order, no whitespace, no duration key.
4. Append `<Marker Version="1" Index="n">` with `<First>{mMarkerID}</First>` and `<Second ObjectRef="{ID}"/>` to the list, n = the current count.
5. Insert the new top-level objects after the Sequence's other objects and run `validate --orig`.

**Clip markers:** media clips share one Markers object per master clip, so a clip marker would belong to the source, not the timeline instance; clips whose source is a sequence have no MarkerOwner at all (spec [§13.1](spec/13-markers.md#131-owners)). Writing clip markers isn't covered: to flag edit points, add a sequence marker.

## 8. Invariants after any edit

Check spec [§16](spec/16-checklist.md#16-conformance-checklist) (conformance checklist) and spec [§9.3](spec/09-track-items-and-links.md#93-per-track-invariants) after any edit. Also:

- `MZ.WorkOutPoint` is the user's work area and `*SequenceSource/OriginalDuration` only grows (spec [§7.4](spec/07-sequences.md#74-length)): neither is a length check.
- No new unreferenced top-level objects (`validate --orig`). Then re-run `cuts` and compare it with the intended edit list.
