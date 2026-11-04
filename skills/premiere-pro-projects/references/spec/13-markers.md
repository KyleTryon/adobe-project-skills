# 13. Markers

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

Sequence markers are observed: Premiere added two zero-length markers, a Comment and a Chapter [O: steps 10→11 #markers.sequence-markers]. Script-written ones in both colours open correctly [V: steps 17-gen, 20-gen #markers.script-written], and a backup sequence needs its own marker GUIDs [V: step 17-gen #markers.backup-own-guids]. Recipe: [`cutting-and-editing.md`](../cutting-and-editing.md) §7.

## 13.1 Owners

- **Media:** every clip of a media MasterClip, and every timeline clip of that media, has `Clip/MarkerOwner/Markers` → one shared `Markers` object, created empty at import [O: steps 00→01 #markers.media-owner]. Clips whose source is a sequence have none [O: steps 03–23 #markers.sequence-clips-have-none].
- **Sequences:** the first marker adds `<MarkerOwner Version="1"><Markers ObjectRef="{ID}"/></MarkerOwner>` (on three lines) between the Sequence's `Node` and `PersistentGroupContainer`, and a top-level `Markers` object whose only referrer is the Sequence [O: steps 10→11 #markers.sequence-owner].

## 13.2 Markers object

ClassID `bee50706-b524-416c-9f03-b596ce5f6866`, Version 4 [O: steps 01–23 #markers.markers-class]:

```xml
<Markers ObjectID="{ID}" ClassID="bee50706-b524-416c-9f03-b596ce5f6866" Version="4">
	<Markers Version="1">
		<Marker Version="1" Index="0">
			<First>{MARKER_GUID}</First>
			<Second ObjectRef="{MARKER_ID}"/>
		</Marker>
	</Markers>
	<ByGUID>byGUID</ByGUID>
	<LastMetadataState>00000000-0000-0000-0000-000000000000</LastMetadataState>
	<LastContentState>00000000-0000-0000-0000-000000000000</LastContentState>
</Markers>
```

- The inner `Markers` list has one entry per marker: `First` = its GUID, `Second` → its `Marker`. With no markers the list is absent, as on every media clip's Markers object [O: steps 01–23 #markers.list-entries]. `ByGUID` is the literal text `byGUID` [O: steps 01–23 #markers.byguid].
- `LastMetadataState` and `LastContentState` are zeros on a sequence's [O: steps 11–17, 20–23 #markers.sequence-states-zero]; on a media clip's, `LastContentState` = the Media's `ContentAndMetadataState` [O: steps 01–23 #markers.media-content-state].
- **The list is not in time order** (the 0:08 chapter is Index 0, the 0:02 comment Index 1) [O: step 11 #markers.not-time-ordered]. Read markers by `mStartTime`.

## 13.3 Marker object

ClassID `a45508e0-3ff7-4d04-90a7-2e0dfff4c910`, Version 3. Its only child is `DVAMarker`, a JSON string ([§3](03-value-encodings.md#3-value-encodings)) [O: steps 11–17, 20–23 #markers.marker-class]:

```xml
<Marker ObjectID="{MARKER_ID}" ClassID="a45508e0-3ff7-4d04-90a7-2e0dfff4c910" Version="3">
	<DVAMarker>{"DVAMarker":{"mComment":"this is a comment","mCuePointList":[{"mKey":"keywordExtDVAv1_32982d91-7093-44c1-9a97-f3877046ab4c","mValue":"{\"color\":4280578025}"}],"mMarkerID":"23cf893a-c327-4a53-a4b3-2bf3ca2b2f14","mName":"Marker_Test","mStartTime":{"ticks":508540032000},"mType":"Comment"}}</DVAMarker>
</Marker>
```

| Key | Meaning [O: step 11 #markers.dvamarker-keys] |
|---|---|
| `mMarkerID` | the marker's GUID; equals `First` in its list entry |
| `mName` | name (`Marker_Test`, `Chapter 01`) |
| `mComment` | comment text |
| `mStartTime.ticks` | start in **sequence time**, in ticks ([§3](03-value-encodings.md#3-value-encodings)): `508540032000` = 48 frames = 00:00:02:00 and `2193078888000` = 207 frames = 00:00:08:15 at 23.976 |
| `mType` | `Comment` or `Chapter` |
| `mCuePointList` | one entry: `mKey` = `keywordExtDVAv1_` + a GUID that differs per marker, `mValue` = the JSON text `{"color":N}` |

- Keys are alphabetical, with no whitespace; `mValue` is JSON inside a JSON string, its quotes escaped (`{\"color\":…}`) [O: steps 11–17, 20–23 #markers.json-form].
- **Colour** `N` is a 32-bit integer `0xAABBGGRR`: `N = 0xFF000000 | B<<16 | G<<8 | R` [O: step 11 #markers.colour-bgr]. `4280578025` = `0xFF246FE9` = `#E96F24` (orange); `4289825711` = `0xFFB18BAF` = `#AF8BB1` (pink).
- A zero-length marker has exactly these six keys, no duration [O: steps 11–17, 20–23 #markers.zero-length-no-duration]. Don't write a duration: how one is stored isn't covered ([§18](18-not-observed.md)).
- Script-written markers use new random GUIDs for `mMarkerID` and the cue-point key, and open correctly [V: steps 17-gen, 20-gen #markers.script-written].
