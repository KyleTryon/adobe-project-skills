# Transcripts and captions

Status of every rule here: [the spec](spec/README.md) (§0 for the tags); the transcript format is spec [§14](spec/14-transcripts-and-captions.md#14-transcripts-speech-to-text), captions [§15](spec/14-transcripts-and-captions.md#15-captions). The evidence is Premiere's Speech to Text on `interview.mp4`: defaults (step 19), speaker labelling (step 21), renamed speakers (step 22), and the script's speaker edit (step 23-gen).

Covered: reading transcripts, mapping them onto a sequence's cut, captions as SRT, speaker names and turns (`rename-speaker`, `set-speaker`). Not covered (spec [§18](spec/18-not-observed.md)): editing words or timings, caption tracks, transcripts of nested sequences.

## 1. Object graph

The chain from the transcribed media to its transcript (spec [§14](spec/14-transcripts-and-captions.md#14-transcripts-speech-to-text)):

```
ClipProjectItem ──MasterClip(URef)──► MasterClip  (Name = the transcribed media, e.g. interview.mp4)
                                       └─ Clips: VideoClip, AudioClip ► *MediaSource ► Media (the real file)
                                       └─ Clips (last): TranscriptClip
TranscriptClip ─ DataClip/Clip/Source ─► DataMediaSource ─ MediaSource/Media(URef) ─► Media "SyntheticTranscript" ─► DataStream
              └─ TranscriptTextSegments ─► ExternallyProvidedTranscriptDocument (TranscriptProvider, TranscriptData)
```

- The transcript belongs to the media's **MasterClip**, not to a sequence, and its times are that media's source time (spec [§14.1](spec/14-transcripts-and-captions.md#141-speech-to-text-on-a-new-project)). Map through the timeline to get sequence times (§5).
- The synthetic Media is titled `SyntheticTranscript` and its `FilePath` is the integer `1398035014` (ASCII `STRF`), not a path; `summary` leaves it out. Skip it when relinking.
- `Project` view state holds local ObjectIDs that collide with global ones such as the TranscriptClip's (spec [§2.3](spec/02-document-structure.md#23-local-scope-inside-project)): resolve references through `index(root)`, never `root.iter()`.
- Field-level detail for each class: [`prproj-classes.md`](prproj-classes.md).

Only `interview.mp4` is transcribed in the steps. `cut-transcript` without `--index` picks whichever transcript maps the most words onto the sequence.

## 2. FlatBuffer schema

`TranscriptData` is a little-endian FlatBuffer with no file identifier: Document → Segments → Words, plus Speakers. Vectors are in chronological order though their tables are stored back to front, and default values are left out of vtables, so read every field by vtable slot (spec [§14](spec/14-transcripts-and-captions.md#14-transcripts-speech-to-text)). `uoffset` is u32 forward; each table starts with an i32 soffset to its vtable (vtable = table − soffset); a vtable is `u16 vtsize, u16 objsize, u16 fieldoff[]`, and a 0 or missing entry means the default.

Every field below round-trips: each step's transcript decodes and rebuilds to the same model (`replay_steps.py`), and Premiere opened a rebuilt one (step 23-gen). Meanings are given where a check proves them; the rest are kept unchanged by the writer but aren't covered.

| Table | Field | Type | Meaning |
|---|---|---|---|
| Root | f0 | → Document | |
| Document | f0 | [Segment] | segments |
| | f1 | string | not covered (`"en-us"` in the steps) |
| | f2 | [Speaker] | speakers |
| | f3 | → Guid | not covered |
| | f4 | string | not covered (empty in the steps) |
| | f5 | [Speaker] | the same vector as f2 |
| Speaker | f0 | string | display name (`Unknown`, `Speaker 1`, a renamed name) |
| | f1 | → Guid | speaker id |
| Guid | f0, f1 | 2 × 8 B | the 16 id bytes, first half then second half |
| Segment | f0 | int64 | start, ticks of media time |
| | f1 | int64 | duration, ticks |
| | f2 | → Guid | the speaker's id (Speaker f1) |
| | f3 | [Word] | tokens |
| | f4 | string | not covered (`"en-us"` in the steps) |
| Word | f0 | int64 | start, ticks of media time |
| | f1 | int64 | duration, ticks |
| | f2 | string | text with its punctuation attached; `""` = not speech |
| | f3 | float32 | not covered |
| | f4 | bool | ends with punctuation (not on abbreviations like `U.S.`); also set on empty tokens |
| | f5 | bool | sentence end; never on empty tokens |
| | f6 | u32 | `3` on pause tokens (empty text) |
| | f7 | u32 | `1` on filler tokens ("uh", "um"; empty text) |

The word flags, speakers and segment turns are spec [§14](spec/14-transcripts-and-captions.md#14-transcripts-speech-to-text) and [§14.1](spec/14-transcripts-and-captions.md#141-speech-to-text-on-a-new-project): with speaker labelling the speaker vector lists `Speaker 1`, `Speaker 2`, … and each segment is one speaker's turn; renaming a speaker keeps its GUID, and reassigning a turn changes that segment's f2.

Readers: `transcripts()` returns segments with each word's text, times, kind (`word`, `pause`, `filler`), sentence and phrase ends, and speaker names; `transcript_model()` keeps every field for rewriting. Skip empty tokens when building text or captions.

## 3. Rewriting the FlatBuffer

`rename-speaker` and `set-speaker` rewrite the transcript through `transcript_model` / `transcript_build`. The builder keeps every field above, shares the f2/f5 speaker vector and identical vtables, aligns every int64 to 8 bytes, writes strings as u32 length + UTF-8 + NUL padded to 4, and checks that the rebuilt buffer reads back identically before writing. The speaker edits it makes decode identically to Premiere's own (steps 21→22), and Premiere opened a transcript it rebuilt (spec [§14](spec/14-transcripts-and-captions.md#14-transcripts-speech-to-text), step 23-gen).

Writing it back: one base64 line followed by a newline and the closing tag's tabs, and a `BinaryHash` whose length part is the new decoded length + 12; Premiere doesn't check the hash's content part (spec [§3](spec/03-value-encodings.md#3-value-encodings)). Editing words or timings isn't covered (spec [§18](spec/18-not-observed.md)): deliver corrected captions as an SRT instead (§5).

### Speech-to-Text accuracy

Premiere's transcript of `fixtures/premiere-pro/media/interview.mp4` against the official DVIDS captions of the same 93 s (`interview.srt`), measured with `prproj.py compare-transcript`; `tests/premiere-pro/replay_steps.py` re-checks every number here.

| Step | Settings | Words (Premiere / official) | WER | WER without "uh"/"um" | Pause / filler tokens |
|---|---|---|---|---|---|
| `19-speech_to_text` | Premiere Pro 26.5.2, English, defaults | 217 / 223 | 4.0% | 0.5% | 22 / 12 |
| `21-speaker_labeling` | same, speaker labelling on | 219 / 223 | 3.1% | | 22 / 14 |

`compare-transcript` treats "gonna"/"going to", "Ok"/"Okay" and "US"/"U.S." as equal, and every filler as "uh". Add a row (and a check) for each engine or setting tried on the same clip (e.g. Whisper: `--ref whisper.json`).

## 4. Captions in these files

There are no caption tracks, caption items or subtitle data in any step. Every sequence has a third `TrackGroup` holding a `DataTrackGroup` with no tracks (spec [§15](spec/14-transcripts-and-captions.md#15-captions)). Don't synthesise caption-track XML: deliver an `.srt`, which the user imports in Premiere and adds to the sequence.

## 5. Recipes

**Sequence-timed transcript.** `cut-transcript FILE --seq NAME [--json|--srt]` maps the transcript through the sequence's cut list:
- it collects the spans where the owner media appears on the sequence's tracks;
- it keeps a token if its **midpoint** falls inside a span, and retimes it to `t − media_in + tl_start`;
- on step 19's `Interview` sequence that's every non-empty token, at its media time (the clip sits at 0 with In 0); on the cut eval input it drops the removed turn and shifts the rest left.

Mapping through a nested sequence isn't covered (spec [§18](spec/18-not-observed.md)).

**SRT cue rules** (`cut-transcript --srt`, `srt-from-words`):
- Drop empty tokens.
- Break at a sentence end (Word f5 / `.?!`), a pause > 0.8 s, > 84 chars, or > 6.5 s.
- Wrap to ≤ 2 balanced lines of ≤ 42 chars.
- Cue end = last word end. Number cues from 1; times `HH:MM:SS,mmm`.

**Correct misheard words without changing what was said:**
1. `cut-transcript --seq NAME --json > words.json`.
2. Fix recognition errors only: brand or product names, homophones, and split or merged compounds (e.g. a product name heard as a common word). Keep fillers, repeats, false starts and grammar exactly as spoken. Keep attached punctuation.
3. Keep `t`/`d` untouched and the token count equal. If one wrong token stands for two real words or vice versa, split or merge it inside its original time range.
4. Diff old against new: only the `w` fields should change, and each change should be justified by the audio or context. Flag uncertain ones instead of guessing.
5. `srt-from-words words.json > NAME.srt`.

**Round trip into Premiere:**
- Deliver the `.srt`; the user imports it onto the same sequence the words were timed to.
- Cue times count from the sequence's start (tick 0). Sequences with a start timecode aren't covered.
- Re-run `cut-transcript` after any re-edit: it maps through the current cut list.
- Covered: decoding, mapping and SRT generation (`tests/premiere-pro/test_commands.py`), and speaker edits (step 23-gen). Not covered: Premiere's import of a generated SRT, and word or timing writes.
