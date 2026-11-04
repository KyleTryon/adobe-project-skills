# 14. Transcripts (Speech to Text)

[Spec contents](README.md) · status tags: [§0](README.md#0-conventions)

FlatBuffer schema, layout and rewrite rules: [`transcripts-and-captions.md`](../transcripts-and-captions.md) §2–3.

- Chain: owner `MasterClip/Clips` → `TranscriptClip` → `DataClip/Clip/Source` → `DataMediaSource` → `Media` titled `SyntheticTranscript` (`ImplementationID` `42008e7a-de6f-4270-96de-7e287abb9b4b`, `FilePath` the integer `1398035014` = `STRF`) → `DataStream`; and `TranscriptClip/TranscriptTextSegments` → `ExternallyProvidedTranscriptDocument` (`TranscriptProvider` `9a139944-f00d-4f74-ac45-751e998bb5dc`, `TranscriptData` base64) [O: step 19 #transcripts.object-chain]. Times are the owner media's source time: they line up with the media's own captions [O: steps 19, 21 #transcripts.media-time].
- `TranscriptData` is a little-endian **FlatBuffer** with no file identifier (Document → Segments → Words, plus Speakers). Vectors are chronological though their tables run back to front; defaults are omitted from vtables, so read fields by vtable slot [O: steps 19, 21 #transcripts.flatbuffer].
- **Word flags:** empty text is not speech: `f6 = 3` marks a pause, `f7 = 1` a filler word ("uh", "um"). `f4` is set on empty tokens and on words ending in punctuation (not on abbreviations like `U.S.`), `f5` on sentence ends [O: steps 19, 21 #transcripts.word-flags]. Skip empty tokens when building text or captions.
- Speaker edits through `rename-speaker`/`set-speaker` (a rebuilt FlatBuffer in the scripts' own layout, with a new content hash) open correctly [V: steps 22→23-gen #transcripts.speaker-edits-written]. Editing words or timings is not covered; treat them as read-only; see [§18](18-not-observed.md).

## 14.1 Speech to Text on a new project

- Transcribing adds a `TranscriptClip` as the media MasterClip's last clip, with its own source chain and document. The transcript belongs to the media's MasterClip, not to a sequence [O: steps 18-gen→19 #transcripts.adds-clip].
- Without speaker labelling, segments are 20–40 s with one speaker, `Unknown` [O: step 19 #transcripts.unlabelled]. With it, speakers are `Speaker 1`, `Speaker 2`, … and each segment is one speaker's turn (a long turn can take two segments), pointing at its speaker's GUID (Segment f2); Document f2 and f5 are the same speaker vector [O: step 21 #transcripts.labelled].
- Renaming a speaker keeps its GUID; reassigning a turn changes that segment's speaker GUID; Premiere rebuilds the FlatBuffer and its BinaryHash [O: steps 21→22 #transcripts.rename-reassign].

# 15. Captions

Every sequence has a `DataTrackGroup` (data media type, frame rate equal to the sequence's; every step's sequences are 23.976) with no tracks [O: steps 03–23 #captions.data-track-group]. Caption tracks and items are not covered: bring captions in as SRT through Premiere's import; see [§18](18-not-observed.md).
