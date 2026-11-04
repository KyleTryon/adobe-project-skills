# 3. Value encodings

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

| # | Kind | Encoding | Example |
|---|---|---|---|
| 3.1 | Time | integer **ticks**, 254 016 000 000 per second; absolute, never relative unless stated | `2330808480000` = 9.176 s |
| 3.2 | Frame/sample rate | ticks per frame (video) or per sample (audio) | see table below |
| 3.3 | "Beginning of time" | `-91445760000000000` (−100 h), the time of every static value | first field of `StartKeyframe` |
| 3.3b | Unset in/out | `-101606400000000000` (−111.11 h) in export settings | `ExportSettings` JSON |
| 3.4 | Boolean | `true` / `false` | |
| 3.5 | Float | C-style; integral values end in `.` in keyframe strings; up to 17 significant digits | `100.`, `0.83333333333333326` |
| 3.6 | Point | `x:y`, fractions of the frame (0,0 top-left; 0.5:0.5 centre) | `0.5:1.5995` (below the frame) |
| 3.7 | Rect, pixel aspect | `left,top,right,bottom`; `num,den` | `0,0,1920,1080`; `1,1` |
| 3.8 | FourCC | big-endian bytes as a decimal integer | `1635148593` = `avc1`, `1634743400` = `ap4h`, `1634755443` = `apcs` |
| 3.9 | Colour param | packed 64-bit integer | `18374686479671623936` |
| 3.10 | Binary | base64 text in an element with `Encoding="base64"` and `BinaryHash` | see below |
| 3.11 | JSON | JSON text in an element | `AudioChannelLayout` `[{"channellabel":100},{"channellabel":101}]` |
| 3.12 | Label | `asl.clip.label.name` = `BE.Prefs.LabelColors.N` (slot 0–15) | `BE.Prefs.LabelColors.7` |

Rates in ticks: 23.976 = `10594584000`, 25 = `10160640000`, 29.97 = `8475667200` (the media and sequences in the steps), 48 kHz = `5292000` per sample; at 23.976 fps a frame is exactly 2 002 samples [O: step 01 #values.rates]. Other rates are not covered; see [§18](18-not-observed.md).

**Defaults are omitted** [O: steps 03–23 #values.defaults-omitted]: `TrackItem/Start` 0, an unchanged Motion effect, an empty `Node/Properties`, a track's default lock, name and mute (and the fader `Volume`/`Mute` params' `StartKeyframe`), a zero-length marker's duration. Absent means default; a writer SHOULD NOT add zero-valued fields Premiere would omit. Always written: an effect param's `StartKeyframe` and a timeline clip's `Clip/InPoint`, even when 0 [O: steps 03–23 #values.always-written].

**Binary blobs (3.10).** `<Tag Encoding="base64" BinaryHash="xxxxxxxx-xxxx-xxxx-xxxx-xxxxLLLLLLLL">DATA` + newline + tabs + `</Tag>`, used by `ModificationState` and `TranscriptData` [O: step 19 #values.blob-form].
- The last 8 hex digits of `BinaryHash` = decoded length + 12; the rest is a content hash of unknown algorithm (not MD5, SHA-1 or SHA-256 of the data or its base64) [O: steps 01–22 #values.binaryhash-length]. Premiere doesn't check the content part: a transcript blob whose content part was computed with MD5 and whose length part was right opened [V: step 23-gen #values.binaryhash-content-unchecked]. Still, edit blobs only through a command that rebuilds and re-reads them (`rename-speaker`, `set-speaker`).
- Deduplicated (self-closing) blobs and base64 in other elements (`PremiereFilterPrivateData`, `StartKeyframeValue`, `ImporterPrefs`) are not covered: no step has one; see [§18](18-not-observed.md).
