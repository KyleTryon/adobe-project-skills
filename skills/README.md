# Skills

| Skill | App | Status |
|---|---|---|
| [`premiere-pro-projects`](premiere-pro-projects/SKILL.md) | Premiere Pro | v3.1, usable; roadmap below |

Each skill folder is self-contained: `SKILL.md`, `scripts/`, `references/` and `evals/`. Copy the folder into your agent's skills directory to install it (see the [repo README](../README.md)). `<skill>-workspace/` folders next to them hold local eval runs and are git-ignored.

## Premiere Pro roadmap

What `premiere-pro-projects` can read, change or automate in a `.prproj`, grouped by area. Premiere Pro 26.x (2026) on macOS; run `scripts/selftest.py` on projects from other versions.

| Mark | Meaning | Counts as |
|---|---|---|
| ✅ | **Supported:** a command does it, proven against Premiere: its output matches Premiere's own save of the same edit ([`replay_steps.py`](../tests/premiere-pro/replay_steps.py)), a script-written step was opened in Premiere, or (for reading) it reports what Premiere did in a step ([`test_commands.py`](../tests/premiere-pro/test_commands.py)) | 1 |
| 🟡 | **Partial:** the format is proven in the spec from a Premiere save, but there's no proven command to write it yet | ½ |
| ⬜ | **Not yet:** no step shows it, so the skill asks you to do it in Premiere; the [backlog](../fixtures/premiere-pro/generated/BACKLOG.md) says what would prove it | 0 |

Eval results (the skill against no skill on 15 editing tasks): [`evals/RESULTS.md`](premiere-pro-projects/evals/RESULTS.md).

A group's percentage is the average of its rows (`python3 -I tools/update_roadmap.py` recomputes them). Overall: **46%** of the 63 features listed.

**Proof:** 217 claims in the spec and guides, each checked against the steps it cites (177 checks); 26 of 28 commands proven against Premiere, 2 refused until a step proves them (`set-label`, `set-transform`).

| Area | Complete |
|---|---|
| [Project, media and bins](#project-media-and-bins) | `███░░░░░░░` 29% |
| [Sequences](#sequences) | `█████░░░░░` 50% |
| [Timeline editing](#timeline-editing) | `█████░░░░░` 54% |
| [Tracks](#tracks) | `█████░░░░░` 50% |
| [Effects and keyframes](#effects-and-keyframes) | `████░░░░░░` 36% |
| [Transitions](#transitions) | `██████░░░░` 60% |
| [Markers](#markers) | `████░░░░░░` 40% |
| [Transcripts and captions](#transcripts-and-captions) | `████████░░` 78% |
| [Graphics and text](#graphics-and-text) | `█░░░░░░░░░` 12% |
| [Audio mixing](#audio-mixing) | `█░░░░░░░░░` 12% |

### Project, media and bins

| | Feature | How / evidence |
|---|---|---|
| ✅ | Read media, bins and sequences | `summary` |
| ⬜ | Label clips | `set-label` exists but refuses to run until a step proves it |
| 🟡 | Import media | format observed (steps 00→01); no command yet |
| 🟡 | Create bins, move items between bins | recipe matches Premiere (steps 01→02); no command yet |
| ⬜ | Rename project items | no step yet |
| ⬜ | Relink or replace media | no step yet (how `RelativePath` changes on save is proven) |
| ⬜ | Delete project items |  |

### Sequences

| | Feature | How / evidence |
|---|---|---|
| ✅ | Read settings and length | `summary`, `cuts` |
| ✅ | Back up / duplicate a sequence | `backup-seq`; clone recipe verified |
| 🟡 | New sequence (empty or from a clip) | format matches Premiere (steps 02→04); no command yet |
| ⬜ | Nest clips / use a sequence as a clip | no step yet |
| ⬜ | Change frame size, frame rate or audio settings | no step yet |

### Timeline editing

| | Feature | How / evidence |
|---|---|---|
| ✅ | Cut list with source and timeline times | `cuts` |
| ✅ | Split (razor) on one or all tracks | `split`; replay-tested (steps 05→06) |
| ✅ | Trim a clip's end | `trim --end`; replay-tested (06→07) |
| ✅ | Ripple delete | `delete --ripple`; replay-tested (07→08) |
| ✅ | Trim a clip's start | `trim --start`; checked in Premiere (steps/16-gen) |
| ⬜ | Lift (delete leaving a gap) | `delete` without `--ripple` refuses until a step proves it |
| ✅ | Place a clip on the timeline (linked, or video only) | `place`; replay-tested (steps 04→05), video-only placement opened in Premiere (step 12-gen); audio-only refuses until proven |
| ⬜ | Speed changes | no step yet |
| ⬜ | Move, slip, slide, roll edits |  |
| ⬜ | Reverse clips | not yet seen in a file |
| ⬜ | Enable / disable clips | not yet seen in a file |
| 🟡 | Link / unlink | link format observed (steps 03–23); no command |

### Tracks

| | Feature | How / evidence |
|---|---|---|
| ✅ | Read tracks and their clips | `summary`, `cuts` |
| ✅ | Rename, lock, mute | `set-track`; replay-tested (steps 08→10) |
| 🟡 | Add an audio track | format observed (steps 03→04); no command yet |
| ⬜ | Add a video track, delete or reorder tracks | no step yet |
| ⬜ | Solo, sync lock, hide (eye) | not yet seen in a file |

### Effects and keyframes

| | Feature | How / evidence |
|---|---|---|
| ✅ | Read effect stacks and keyframes | `effects` |
| ✅ | Transform: add, with keyframes and motion blur | `add-transform`; opened in Premiere (step 12-gen) |
| ⬜ | Change an existing Transform | `set-transform` exists but refuses to run until a step proves it |
| 🟡 | Motion and Opacity | read (implicit until changed, proven); no command |
| ⬜ | Clip volume and level keyframes | no step yet |
| ⬜ | Other video effects (crop, blur, …) and adjustment layers |  |
| ⬜ | Audio effects |  |

### Transitions

| | Feature | How / evidence |
|---|---|---|
| ✅ | Audio fade-in at a clip's head | `fade-in`; opened in Premiere |
| ✅ | Audio fade-out at a clip's tail | `fade-out`; opened in Premiere, replay-tested (step 15) |
| ✅ | Audio crossfades (Constant Power) | `crossfade` (default 2 s); replay-tested against Premiere's own (step 15), checked in Premiere (steps/16-gen); needs handles on both clips |
| ⬜ | Video transitions | no step yet |
| ⬜ | Remove a transition | no step yet |

### Markers

| | Feature | How / evidence |
|---|---|---|
| ✅ | Sequence markers: read and add (name, comment, type, colour) | `markers`, `add-marker`; replay-tested (steps 10→11) |
| ✅ | YouTube chapters from Chapter markers | `markers --chapters` |
| ⬜ | Marker durations | not yet seen in a file |
| ⬜ | Clip (source) markers |  |
| ⬜ | Other marker types and colours | Segmentation, Web Link, Flash Cue Point |

### Transcripts and captions

| | Feature | How / evidence |
|---|---|---|
| ✅ | Read the Speech-to-Text transcript | `transcript` |
| ✅ | Transcript of what survives an edit | `cut-transcript` |
| ✅ | SRT captions from the edit or corrected words | `cut-transcript --srt`, `srt-from-words` |
| ✅ | Compare Premiere's transcript with another (official, Whisper) and mark the differences | `compare-transcript [--markers]`; checked on the interview (step 19) |
| ✅ | Tell words, filler words and pauses apart | read from the transcript's word flags (step 19) |
| ✅ | Speaker labels (who said what) from Premiere's speaker labelling | `transcript`, `cut-transcript --json` (step 21) |
| ✅ | Rename speakers or reassign turns | `rename-speaker`, `set-speaker`; decode identically to Premiere's own edit (step 22), opened in Premiere (steps/23-gen) |
| ⬜ | Write or correct the embedded transcript | read-only for now |
| ⬜ | Caption tracks: read, create, edit | no step yet; deliver captions as SRT |

### Graphics and text

| | Feature | How / evidence |
|---|---|---|
| 🟡 | Rendered graphics and stills on the timeline | `place` and Transform moves are proven for video clips; stills not yet |
| ⬜ | Motion Graphics templates (.mogrt) | no step yet |
| ⬜ | Edit template text and parameters |  |
| ⬜ | Essential Graphics text layers | no step yet |

### Audio mixing

| | Feature | How / evidence |
|---|---|---|
| 🟡 | Track volume and pan | fader and panner format observed (steps 03–23); no command |
| ⬜ | Essential Sound tags (dialogue, music, SFX) | seen, not decoded |
| ⬜ | Ducking |  |
| ⬜ | Submixes, mono / 5.1 / adaptive tracks | not yet seen in a file |

### Not planned

- **Rendering and export.** Use Premiere or Adobe Media Encoder; the skill can tell you what's in the timeline, not render it.
- **Team Projects, Productions and cloud-synced projects.** These aren't plain `.prproj` files on disk.
- **Editing a project while Premiere has it open.** Premiere overwrites outside changes on save; the skill always asks you to close the project first.

### How features move up

Each change Premiere makes is recorded as a pair of saves in [`fixtures/premiere-pro/steps/`](../fixtures/premiere-pro/steps/) (listed in the [steps table](../fixtures/premiere-pro/README.md#steps)). The format goes into [the spec](premiere-pro-projects/references/spec/README.md) with a check that proves it (⬜ → 🟡), then a command reproduces the edit and `tests/premiere-pro/replay_steps.py` checks it against Premiere's save, or a script-written step is opened in Premiere (🟡 → ✅). [`CONTRIBUTING.md`](../CONTRIBUTING.md) has the process, and the [backlog](../fixtures/premiere-pro/generated/BACKLOG.md) lists the steps to record next: clip labels, changing a Transform, speed and reverse, nesting, clip volume, video transitions, captions, Essential Graphics, more marker colours.
