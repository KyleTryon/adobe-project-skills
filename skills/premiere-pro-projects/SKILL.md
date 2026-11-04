---
name: premiere-pro-projects
description: "Use this skill for any work inside an Adobe Premiere Pro project file (.prproj): reading its media, bins, sequences, tracks, markers, effects and cut list; pulling the embedded Speech-to-Text transcript, fixing speaker names or exporting captions/SRT; or changing the project (backup sequences, placing clips, splits, trims and ripple deletes, audio fades and crossfades, markers and chapters, renaming, locking or muting tracks, Transform moves with keyframes). Use it whenever the user asks about or wants changes to their Premiere edit, timeline, sequence or captions, even if they never say \".prproj\" or only describe the edit (\"slide that graphic in\", \"what's left in my cut\"). Not for editing rendered video files directly (ffmpeg), other editors' projects (Final Cut, DaVinci Resolve, After Effects), exporting/rendering, or how-to questions about Premiere's own UI."
license: MIT
compatibility: Requires Python 3.8+ (standard library only). Format evidence is from Premiere Pro 26.x (2026) projects; run scripts/selftest.py on projects from other versions.
metadata:
  version: "3.0"
---

# Premiere Pro project files (.prproj)

A `.prproj` is gzip-compressed XML: a flat list of objects that reference each other by ID. `scripts/prproj.py` (Python 3, stdlib only) reads it, makes the common edits safely and validates the result. Everything here is proven against files Premiere itself saved; anything else is listed in [spec §18](references/spec/18-not-observed.md) as not covered, so do that part in Premiere instead. Run `python3 -I scripts/prproj.py --help` for the full interface. Use the script wherever it covers the job, and follow the editing workflow below for every change.

## Commands

| Need | Command |
|---|---|
| Overview: media, bins, sequences, tracks | `summary FILE` |
| Cut list of a sequence (`#N timeline src name [label]`, track indices) | `cuts FILE --seq NAME [--json]` |
| Effect stack of each clip, keyframes at timeline times | `effects FILE --seq NAME [--track N] [--item N] [--json]` |
| Words that survive in a sequence | `cut-transcript FILE --seq NAME [--json \| --srt]` |
| Whole transcript of a media file | `transcript FILE [--index N]` (`--index -1` lists them) |
| Captions from corrected words | `srt-from-words WORDS.json` |
| Who speaks when; rename speakers or give a turn to another speaker | `speakers FILE`, `rename-speaker FILE OUT --from A --to B`, `set-speaker FILE OUT --at SECONDS --speaker NAME` |
| Compare the transcript with another one (official, Whisper); optionally mark each difference on a sequence | `compare-transcript FILE --ref REF.srt [--ignore-fillers] [--seq NAME --markers OUT]` |
| Back up a sequence inside the project before changing it | `backup-seq FILE OUT --seq NAME [--name COPY]` |
| Put a media clip from the bins onto free space in a sequence (linked video + audio) | `place FILE OUT --seq NAME --clip NAME --at TIME [--track N] [--audio-track N] [--in TIME] [--out TIME \| --duration TIME] [--video-only]` |
| Fade audio in or out, or crossfade at a cut (needs handles) | `fade-in`/`fade-out FILE OUT --seq NAME --track N --item N --duration TIME`, `crossfade … --item N [--duration TIME]` (the clip before the cut; default 2 s) |
| Razor clips at a time (all unlocked tracks, or one track and its linked partners) | `split FILE OUT --seq NAME --at TIME [--track N]` |
| Move a clip's start or end (linked partners follow; neighbours don't move) | `trim FILE OUT --seq NAME --track N --item N [--start TIME] [--end TIME]` |
| Remove a clip and its linked partners, optionally closing the gap | `delete FILE OUT --seq NAME --track N --item N [--ripple]` |
| List markers; YouTube chapters from Chapter markers | `markers FILE --seq NAME [--json \| --chapters]` |
| Add a sequence marker | `add-marker FILE OUT --seq NAME --at TIME --name NAME [--type Comment\|Chapter] [--comment TEXT] [--colour orange\|pink]` |
| Rename, lock or mute a track | `set-track FILE OUT --seq NAME --track N [--name NAME] [--lock on\|off] [--mute on\|off]` |
| Add a Transform, with or without keyframes | `add-transform FILE OUT --seq NAME --track N --item N [--set k=v] [--motion-blur on] [--keys PARAM SPEC]` |
| Check an edited file | `validate FILE --orig ORIGINAL` |
| What changed between two saves (e.g. what one action in Premiere wrote) | `diff OLD NEW [--json] [--all]` |
| Raw XML in/out | `unpack FILE OUT.xml`, `pack IN.xml OUT.prproj` |
| Check the script's assumptions against a project from a new Premiere version | `python3 -I scripts/selftest.py FILE` (read-only) |
| Infer the structure of a project (e.g. from another Premiere version) to compare with `prproj-schema.json` | `python3 -I scripts/schema_dump.py FILE [--class NAME] [--json]` (read-only) |

`--track`/`--item` are the indices `cuts` prints. TIME is seconds (`4.5`), frames (`119f`) or timecode (`00:00:04:23`) on the sequence timeline, snapped to a frame. `split`, `trim` and `delete` refuse clips with transitions, locked tracks, overlaps, and a ripple that would knock other tracks out of sync. Write commands refuse to save a file that fails validation, accept `--dry-run` to check an edit without writing, and allow OUT to be the same path as FILE. `add-transform` refuses an item that already has a Transform. A few writes no Premiere-checked step proves yet (changing an existing Transform, clip labels, audio-only placement, other marker colours) refuse to run; do those in Premiere, and don't pass `--unproven` unless the user explicitly accepts an unchecked file. Errors go to stderr with what to fix; exit 0 = ok, 1 = error, 2 = bad arguments. Prefer `--json` output when you'll process the result.

Key times in `--keys` are seconds or frames (`12f`) from the clip's first frame; negative counts back from its last frame (`-1f`). Points are `x:y` frame fractions (0.5:0.5 = centre). For example, slide a graphic up from below over 12 frames and back out over its last 11, with motion blur:

```bash
python3 -I scripts/prproj.py add-transform P.prproj P.prproj --seq Edit --track 2 --item 4 --motion-blur on --dry-run \
  --keys position "0f=0.5:1.6@linear, 12f=0.5:0.5, -12f=0.5:0.5, -1f=0.5:1.55@linear"
```

## Editing workflow

Copy this checklist and tick it off for every change to a project:

- [ ] 1. **Read fresh.** Run `summary` and `cuts --seq NAME` (plus `effects` for effect work) on the file as it is now, and note its mtime.
- [ ] 2. **Keep a way back.** `backup-seq FILE FILE --seq NAME` (add `--name "NAME (backup YYYY-MM-DD HHMM)"` with the user's local time when the machine's clock may be UTC) duplicates the sequence you'll change inside the project (named `NAME (backup YYYY-MM-DD HHMM)`, same bin), unless the user prefers a file copy or says not to bother. Don't leave `.bak` or scratch files next to the user's project; put scratch work in a temporary folder.
- [ ] 3. **Make the change.** Use a script command when one covers it, with `--dry-run` first. Otherwise read the spec part for the job (below); if it covers the change, list every object you'll touch and make targeted text edits. If it's in [§18](references/spec/18-not-observed.md), don't: ask the user to do that part in Premiere.
- [ ] 4. **Validate.** `validate FILE --orig ORIGINAL`. If it fails, fix the cause and validate again; don't hand over a file that fails.
- [ ] 5. **Check the result.** Re-run `cuts`/`effects` and compare with what the user asked for (times, tracks, keys).
- [ ] 6. **Write and hand back.** Confirm the mtime hasn't changed since step 1 (if it has, start over), write, then tell the user to close the project in Premiere *without saving* and reopen it, and add: if they had unsaved changes open in Premiere, they should keep it open and tell you, and you'll redo the edit after they've saved and closed. Save anything else you produce (an SRT, a chapter list) **next to the project file** unless the user names another place, and give its path.

**If the user says the project is open in Premiere, don't write to it.** Prepare and `--dry-run` the change, tell them exactly what you'll do, and ask them to save and close the project first; write once they confirm. Premiere keeps the project in memory and writes it back on save (and on auto-save when "Auto Save also saves the current project" is on), silently replacing your edit. **If they haven't said, don't stop to ask:** make the change and hand back as in step 6. If the project was uploaded rather than reached on the user's computer, the upload is read-only: write `<name>-edited.prproj` and send it back.

## Gotchas

- **Keyframe times are source time, not clip-relative:** `key = InPoint + (timeline − Start)` (clips at speed 1; speed changes aren't covered). A trimmed clip breaks the clip-relative assumption. `effects` shows keys at timeline times; `--keys` takes clip-relative seconds or frames and converts.
- **ObjectIDs change on every Premiere save.** Never reuse IDs from an earlier read. Find things by sequence/bin/media name, by track and item position, or by a clip's `ClipID` (stable across saves).
- **Only direct children of `<PremiereData>` are objects.** `Project` contains a view-state list with its own local IDs that collide with global ones; `root.iter()` resolves them to the wrong objects.
- **`<Start>` is omitted when it's 0.** Read a missing Start as 0; never write `<Start>0</Start>`.
- **A sequence's length is the largest clip `End`.** `MZ.WorkOutPoint` is the user's work area and `OriginalDuration` is often stale; keep `Monitor.ProgramZoomOut` equal to the length.
- **Transitions live in `TransitionItems`, not `ClipItems`,** and the faded clip also points at them via `HeadTransition`. Move or delete them with the clip.
- **Motion and Opacity are invisible until changed** (`DefaultMotion` flag, no component). To move a clip, add a Transform; don't create a Motion component.
- **"Use Composition's Shutter Angle" ticked means no motion blur** for Transform moves. `--motion-blur on` unticks it.
- **Nothing per clip is shared.** Each track item owns its chain, every effect and param object, its SubClip and its clip, and every clip has its own `ClipID`. Cloning a clip means cloning all of them with new IDs.
- **Audio fades are transitions, not volume keyframes:** `fade-in`/`fade-out`/`crossfade` leave the clip's volume alone. Keyframing the volume line isn't covered; ask the user to do it in Premiere.
- **Mute is the track fader's Mute param, not a track flag;** lock is `Track/IsLocked`, a custom name is `MZ.TrackName`. Use `set-track`.
- **Marker colours are stored as 0xAABBGGRR** inside each marker's JSON (`mCuePointList`), so the bytes read backwards from #RRGGBB. Use `markers`/`add-marker`.
- **`Media/RelativePath` is relative to where the file was last saved,** and Premiere rewrites it on every save. Moving a .prproj by hand leaves it stale; the absolute path still works.
- **Get transcript words on a sequence's timeline with `cut-transcript`;** don't offset times by hand.
- **Filler words (uh, um) and pauses are tokens with empty text.** `transcript` shows fillers as `(uh)`; in `transcript --json` they're words with `"w": ""` and `"kind": "filler"` (pauses: `"pause"`), each with its own start and duration. `cut-transcript` leaves them out, so use `transcript --json` to find them.
- **Cut between words, never inside one you keep.** Take word times from `cut-transcript --json` (or `transcript --json` for media time) and put each cut on a frame boundary in the gap between the last word you keep and the first you remove (and back again). Where two words touch, use the frame nearest the boundary. Removing a filler works the same way: it's a token like any other, so take out its whole span, cutting at the frame nearest each of its edges even when it touches a word, and don't leave fillers in because they're short. Then re-read `cut-transcript` to check the result.

## Reference files

Load the one that matches the job:

| Read | When |
|---|---|
| `references/spec/` | before any hand edit the scripts don't cover, or to answer how the format works: the reverse-engineered specification, one file per part (table below). Read [`spec/README.md`](references/spec/README.md) once for the tags (observed / verified), then only the file for your task |
| `references/prproj-classes.md` | you need a class's exact ClassID, Version or element order. Its index at the top says what each class is and which spec part explains it; then grep for `### ClassName`. Don't read it all |
| `references/cutting-and-editing.md` | splitting, trimming, ripple deletes, placing clips, links, fades, markers |
| `references/effects.md` | effects, Transform moves, keyframes, Motion/Opacity, audio volume |
| `references/sequences.md` | sequence settings and length, work area, copying a sequence (`backup-seq`) |
| `references/tracks.md` | renaming, locking or muting tracks; track and mixer objects |
| `references/media-and-bins.md` | bins, project items and media: what import writes, creating bins, moving items, moving the .prproj |
| `references/transcripts-and-captions.md` | transcript structure, SRT, captions |
| `references/object-surgery.md` | adding, cloning or splitting any object: ID/GUID rules and verified recipes |
| `references/workflow-conventions.md` | the user asks you to set up or follow a structured project layout (bins, a Src → Cut → Edit chain, backup naming) |

### The spec, by task

| Read `references/spec/…` | When you need to |
|---|---|
| [`01-container.md`](references/spec/01-container.md) | unzip or write the file; header, tabs, escaping; the `.prin` index |
| [`02-document-structure.md`](references/spec/02-document-structure.md) | resolve a reference (ObjectID vs ObjectUID, referrers); allocate IDs, UIDs, Node IDs; know which IDs to regenerate when cloning; place new objects |
| [`03-value-encodings.md`](references/spec/03-value-encodings.md) | ticks and frame rates, floats, points, absent fields; base64 blobs and `BinaryHash` |
| [`04-object-graph-and-project.md`](references/spec/04-object-graph-and-project.md) | find anything from `Project`; project properties |
| [`06-project-panel.md`](references/spec/06-project-panel.md) | bins, import, non-media files; relink media; move the .prproj |
| [`07-sequences.md`](references/spec/07-sequences.md) | sequence settings and preview format; length and work area; make a new sequence from an existing one |
| [`08-tracks.md`](references/spec/08-tracks.md) | track order and IDs; rename, lock or mute a track |
| [`09-track-items-and-links.md`](references/spec/09-track-items-and-links.md) | clip timing; what place, split, trim and ripple delete write; linked A/V and J/L cuts |
| [`11-transitions.md`](references/spec/11-transitions.md) | audio fades and crossfades |
| [`12-effects-and-keyframes.md`](references/spec/12-effects-and-keyframes.md) | effect chains, implicit Motion/Opacity, param ClassIDs, static values and keyframe strings, Transform and motion blur |
| [`13-markers.md`](references/spec/13-markers.md) | sequence markers and their colours |
| [`14-transcripts-and-captions.md`](references/spec/14-transcripts-and-captions.md) | transcript word flags, speakers; why captions come in as SRT |
| [`16-checklist.md`](references/spec/16-checklist.md) | check a file before handing it back |
| [`17-load-and-save.md`](references/spec/17-load-and-save.md) | what Premiere rewrites on load and save; why an external edit was lost |
| [`18-not-observed.md`](references/spec/18-not-observed.md) | whether a feature is described at all |

Every rule in the spec is proven: **observed** ones are what Premiere itself wrote, **verified** ones were written by the scripts and opened in Premiere, and the repo's tests check each one against the steps it cites. Anything in [§18](references/spec/18-not-observed.md) (caption tracks, video transitions, nesting, speed changes, other effects, clip volume and more) has no proven format: ask the user to do that part in Premiere instead of inventing XML.

## Other notes

- **On the user's computer:** if you can run commands where the project lives (media paths in the file show where, often an external volume), copy the `scripts/` folder there and work in place rather than copying media. Report times as `m:ss.mmm`, timeline and source side by side.
- **Don't reorganise** a user's bins, sequence names or workflow unless asked. `references/workflow-conventions.md` has an example layout to offer when they want one.
- **Transcript words and timings are read-only;** speaker names and turns can change (`rename-speaker`, `set-speaker`). Deliver corrected captions as an SRT (`srt-from-words`) for the user to import.
