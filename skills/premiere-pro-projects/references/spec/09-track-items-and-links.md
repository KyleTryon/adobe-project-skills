# 9. Track items and clips

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

Recipes: [`cutting-and-editing.md`](../cutting-and-editing.md).

## 9.1 Anatomy

- The timeline classes (the 11 objects in §9.4) keep their child elements in one fixed order (path order in [`prproj-classes.md`](../prproj-classes.md); the keyed settings under `Node/Properties` excepted); a writer SHOULD insert elements where Premiere puts them [O: steps 03–23 #items.child-order]. Field detail: [`cutting-and-editing.md`](../cutting-and-editing.md) §1.
- A track item (`VideoClipTrackItem` / `AudioClipTrackItem`) → its chain (`ComponentOwner/Components`), `TrackItem` (`Start`, `End`), `SubClip`, and on audio optional `HeadTransition`/`TailTransition` ([§11](11-transitions.md#11-transitions)). `SubClip` → its own timeline `Clip`, the shared `MasterClip` (ObjectURef), and holds the timeline `Name` [O: steps 03–23 #items.track-item-parts].
- A timeline `VideoClip`/`AudioClip` holds `Source`, `ClipID`, `InPoint`, `OutPoint`, a label (`Node/Properties`) and, for media, the shared `MarkerOwner/Markers` [O: steps 03–23 #items.clip-parts]. `AudioClip` adds a `SecondaryContent` per channel (each → the same source, with a `ChannelIndex`) and `AudioChannelLayout` [O: steps 03–23 #items.audio-clip-channels].

## 9.2 Timing

Every clip in the steps plays at speed 1, and [O: steps 03–23 #items.timing]:

```
End − Start = OutPoint − InPoint
source   = InPoint + (timeline − Start)
timeline = Start + (source − InPoint)
```

- `Start` and `End` MUST lie on the sequence frame grid (`VideoTrackGroup` FrameRate) [O: steps 03–23 #items.frame-grid].
- Speed changes (`PlaybackSpeed` ≠ 1), speed ramps, reverse, frame blending, time remapping and enable/disable are not covered; see [§18](18-not-observed.md).

## 9.3 Per-track invariants

Clip items are listed in `Start` order with contiguous `Index`; none overlap (`End ≤ next Start`); `Start` is absent when 0, never written `0`; `InPoint` is always written; every `ClipID` and audio item `ID` is unique (split pieces don't share them) [O: steps 03–23 #items.track-invariants]. `ClipID` survives saves and identifies a clip across renumbering [O: steps 04→05, 05→06, 06→07, 07→08 #items.clipid-stable].

## 9.4 Premiere's edits

What each edit writes to a linked A/V pair; recipes in [`cutting-and-editing.md`](../cutting-and-editing.md) §5. "The 11 objects" are a `Link` and per side a `*ClipTrackItem`, `SubClip`, `*Clip` and chain, plus a `SecondaryContent` per audio channel (2 here).

- **Place** [O: steps 04→05 #edits.place] [V: steps 04→18-gen #edits.place-script]: the 11 objects; the items join V1's and A1's `TrackItems`, the link `Links`, in time order. New timeline clips of an `.mp4` get the Iris label (`BE.Prefs.LabelColors.1`) [O: steps 02→03 #edits.default-label]; the MasterClip takes a Node ID on first use ([§2.4](02-document-structure.md#24-allocating-identities)).
- **Split (razor) at T** [O: steps 05→06 #edits.split] [V: steps 11→17-gen #edits.split-script]: the left piece keeps its objects, ClipIDs and audio `ID`, and only `TrackItem/End` (→ T) and `Clip/OutPoint` (→ the matching source time) change. The right piece is 11 new objects (new ClipIDs and audio `ID`): `Start` = T, `InPoint` = the left piece's new `OutPoint`, the original `End`/`OutPoint`, copies of the label, Essential Sound properties and shared `MarkerOwner`; its entries go in at its time position. The length doesn't change.
- **Trim an end** [O: steps 06→07 #edits.trim-end] [V: steps 12-gen→16-gen, 11→17-gen #edits.trim-end-script]: `TrackItem/End` and `Clip/OutPoint` on both items, nothing else; `Monitor.ProgramZoomOut` follows ([§7.4](07-sequences.md#74-length)).
- **Trim a start** [V: steps 12-gen→16-gen, 11→17-gen #edits.trim-start-script]: `TrackItem/Start` and `Clip/InPoint` move by the same amount, on both items. Premiere's own head trim isn't recorded.
- **Ripple delete** [O: steps 07→08 #edits.ripple-delete]: the 11 objects and their `TrackItems`/`Links` entries go, and the lists are re-indexed; later items move left by the deleted duration on `Start` and `End` only.
- **Place only the video** [V: steps 11→12-gen #edits.place-video-only]: the video item, SubClip, clip and chain; no `Link`.
- Premiere bumps `MasterClipChangeVersion` on every clip edit (place, split, trim, ripple delete) ([§7.4](07-sequences.md#74-length)) [O: steps 04→05, 05→06, 06→07, 07→08 #edits.change-version-premiere]; script edits don't, and open correctly [V: steps 11→12-gen, 12-gen→13-gen, 13-gen→14-gen, 12-gen→16-gen, 11→17-gen, 04→18-gen, 19→20-gen, 22→23-gen #edits.change-version-script].

# 10. Links

`Sequence/PersistentGroupContainer/LinkContainer/Links/Link[Index]` → `Link` → `TrackItemGroup/TrackItems/TrackItem[Index]` (ObjectRef, video member first); every link seen has 2 members, a video and an audio item [O: steps 03–23 #links.structure]. Linked items usually have identical Start/End/In/Out; a split edit (J/L cut) keeps the link with different audio edges [O: steps 05, 15 #links.same-edges]. `Links` is in time order; a new link goes in at its pair's position [O: steps 04→05, 05→06 #links.order]. With no links, `LinkContainer` has no `Links` element [O: steps 03→04 #links.empty]. An item MUST NOT appear in two links [O: steps 03–23 #links.one-link-per-item]. Deleting a pair deletes its Link [O: steps 07→08 #links.delete-pair]. Deleting one member of a link, and links of more than two items, are not covered; see [§18](18-not-observed.md).
