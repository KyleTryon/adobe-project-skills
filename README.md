<p align="center">
  <img src="assets/icon.png" alt="Adobe Project Skills" width="128" height="128">
</p>

<h1 align="center">Adobe Project Skills</h1>

<p align="center">
  Unofficial Agent Skills that let AI agents read and edit Adobe Premiere Pro project files directly: no app UI, no Computer Use.
</p>

<p align="center">
  <a href="#how-well-it-works">Results</a> ·
  <a href="#install">Install</a> ·
  <a href="#using-the-script-directly">Use the CLI</a> ·
  <a href="#compatibility">Compatibility</a> ·
  <a href="#contributing">Contribute</a>
</p>

> **Unofficial, reverse-engineered formats.** Adobe doesn't publish these file formats. Edits are designed to be safe, not guaranteed. Keep a copy of anything you can't afford to lose.

These [Agent Skills](https://agentskills.io) let an AI agent work directly with project files, without using the app's UI.

| Skill | What it does |
|---|---|
| [`premiere-pro-projects`](skills/premiere-pro-projects/SKILL.md) | Read and edit Premiere Pro `.prproj` files: cut lists, embedded transcripts, speakers and SRT captions, backup sequences, placing, splitting, trimming and ripple-deleting clips, audio fades and crossfades, markers and chapters, track names, locks and mutes, and Transform moves with keyframes. Every rule is proven against files Premiere saved. |

Feature coverage and roadmap: [`skills/README.md`](skills/README.md).

## What you can do

Ask about your project in plain language. The agent reads the `.prproj`, makes the requested change with the bundled script, and reports what changed:

- "What's left in my Edit sequence? Give me the cut list with timecodes."
- "Export captions for the final cut as an SRT."
- "Back up the Edit sequence, then slide the graphic on V2 at 1:04 in from the bottom over 12 frames, with motion blur."
- "Scale the facecam down to 40% and park it in the bottom-right corner."
- "Cut out the bit where I say 'sorry, let me start again' around 1:14, using the transcript."
- "Rename Speaker 1 to the interviewer and give me captions for the final cut."
- "What frame rate and resolution are my sequences?"

## How well it works

The skill is evaluated against the same model with no skill loaded, on 15 editing tasks run on the demo project, in clean, isolated sessions ([`RESULTS.md`](skills/premiere-pro-projects/evals/RESULTS.md)). Edits are graded by script on the end state of the project (cut points to the frame, A/V sync, gaps, words kept whole or removed, transitions, markers); habits are the backup sequence and a tidy project folder.

| Round | Model | Edit checks passed, with skill | Without skill | Habits, with / without |
|---|---|---|---|---|
| 2: all 15 tasks, 46 runs | Sonnet 5.5 | **95%** (107/113) | 77% (87/113) | 100% / 72% |
| 3: the three tasks round 2 missed, after fixes | Sonnet 5.5 | **100%** (37/37) | 73% (27/37) | 100% / 79% |

With the skill, runs also took under a third of the time (26 s against 90 s on average) and under a third of the usage. Without it, agents most often skipped the backup, cut off the frame grid, clipped words in transcript cuts, or hand-edited parts of the format nothing proves Premiere accepts.

These are small numbers: one model, one demo project, one run per simple task and three per multi-step task, graded by script against the proven format rather than checked by a person in Premiere. Per-round figures are in [`evals/results/`](skills/premiere-pro-projects/evals/results/); `tools/run_evals.py` reproduces them.

## Install

The skills follow the open [Agent Skills specification](https://agentskills.io/specification), so they work with any compatible agent. Each skill is a self-contained folder under `skills/`.

### Claude Code

Add this repository as a plugin marketplace, then install the skill:

```text
/plugin marketplace add KyleTryon/adobe-project-skills
/plugin install premiere-pro-projects@adobe-project-skills
```

Or clone the repository and copy (or symlink) the skill folder into your personal or project skills directory:

```bash
cp -r skills/premiere-pro-projects ~/.claude/skills/             # every project
cp -r skills/premiere-pro-projects your-project/.claude/skills/  # one project
```

### Other agents

Place the skill folder wherever your agent loads skills from, or upload it as a custom skill.

> **Requirements:** Python 3.8+. The scripts use only the standard library; nothing to install.

## Using the script directly

The agent uses `scripts/prproj.py`, but you can run the CLI yourself:

```bash
cd skills/premiere-pro-projects
python3 -I scripts/prproj.py summary  MyProject.prproj               # media, bins, sequences, tracks
python3 -I scripts/prproj.py cuts     MyProject.prproj --seq Edit    # cut list with track/item numbers
python3 -I scripts/prproj.py cut-transcript MyProject.prproj --seq Edit --srt > edit.srt
python3 -I scripts/prproj.py backup-seq MyProject.prproj MyProject.prproj --seq Edit
python3 -I scripts/prproj.py add-transform MyProject.prproj MyProject.prproj --seq Edit \
  --track 2 --item 4 --motion-blur on --dry-run \
  --keys position "0f=0.5:1.6@linear, 12f=0.5:0.5"
python3 -I scripts/prproj.py validate MyProject.prproj --orig MyProject-before.prproj
```

`python3 -I scripts/prproj.py --help` lists every command. Write commands validate their result and refuse to save an invalid file; `--dry-run` checks an edit without writing anything.


## Compatibility

Format evidence comes from projects saved by Premiere Pro 26.x (2026) on macOS. Before trusting write commands with another Premiere version, run the read-only self-test on one of your projects:

```bash
python3 -I skills/premiere-pro-projects/scripts/selftest.py YOUR_PROJECT.prproj
```

It compares the script's assumptions with what Premiere actually wrote in that project and fails loudly if the format has drifted.

## The .prproj format

[`references/spec/`](skills/premiere-pro-projects/references/spec/README.md) is the reverse-engineered specification, one file per part: the container, object model and IDs, value encodings and time units, and every subsystem from bins and sequences to keyframes and the Speech-to-Text transcript, ending with a conformance checklist. Every rule is proven, and says how:

| Tag | Meaning |
|---|---|
| **observed** | Premiere wrote it: a check passes on the demo project's saves that the rule cites |
| **verified** | the scripts wrote it, and the file opened correctly in Premiere |

`tests/premiere-pro/test_rules.py` runs every rule's check on the saves it cites, so a claim the evidence doesn't support fails the build. What isn't proven is listed as [not covered](skills/premiere-pro-projects/references/spec/18-not-observed.md), and waits in the [backlog](fixtures/premiere-pro/generated/BACKLOG.md) for a step that proves it.

[`prproj-schema.json`](skills/premiere-pro-projects/references/prproj-schema.json) is the machine-readable catalogue of every object class seen in the demo project (ClassIDs, Versions, element paths, value kinds), and [`prproj-classes.md`](skills/premiere-pro-projects/references/prproj-classes.md) the same for reading. `scripts/schema_dump.py --write` regenerates both from the steps; run on your own project, it shows what's different without revealing any content, and `prproj.py validate` warns about structure the demo project never showed.



## Evals

Each skill keeps its evals in `skills/<skill>/evals/`:

- `evals.json`: output-quality test cases with assertions ([Evaluating skill output quality](https://agentskills.io/skill-creation/evaluating-skills))
- `trigger-queries.json`: should-trigger and should-not-trigger prompts for the description ([Optimizing skill descriptions](https://agentskills.io/skill-creation/optimizing-descriptions))
- `files/`: the input projects, built from the demo project's steps by `tools/premiere-pro/build_eval_files.py`
- `graders.py`: script checks for the assertions
- `RESULTS.md`: what counts as a clean run, and the results of each one; `results/iteration-N.json` the full figures per round

`tools/run_evals.py` runs every case twice, with the skill and without it, each in a fresh Claude Code session with an empty home folder, no settings, account skills, CLAUDE.md, memory or MCP servers, and only the input copied in as `demo.prproj`. It grades what it can by script (the skill's `evals/graders.py`, reading the result with the skill's own `prproj.py`) and the rest with a judge model that never sees the expected output, flags any run that loaded or read something it shouldn't, and adds a row to `RESULTS.md`. Raw runs go in `skills/<skill>-workspace/`, beside the skill folder, and are git-ignored.

```bash
python3 tools/run_evals.py --dry-run     # what would run, and the exact command (--skill NAME once there are several)
python3 tools/run_evals.py --runs 3 -j 4 # every case, 3 runs per arm
python3 tools/run_evals.py --triggers    # trigger rate of the description
```

## Tests

[`fixtures/premiere-pro/steps/`](fixtures/premiere-pro/steps/) holds the demo project after each single action (import, razor, trim, ripple delete, lock, rename, markers, fades, Speech to Text, speakers, …): most saved by Premiere, some (`NN-gen-*`) written by the scripts and checked in Premiere. The [steps table](fixtures/premiere-pro/README.md#steps) says what each one shows. The replay tests make the same edit with the scripts and compare the result with Premiere's own save:

```bash
python3 -I tests/run_all.py
```

CI runs the same on every push, plus a check that no committed project contains a home folder path, `agentskills validate` (the [specification](https://agentskills.io/specification)'s reference validator) on each skill, and `claude plugin validate` on the marketplace manifest.

## Contributing

[`CONTRIBUTING.md`](CONTRIBUTING.md) explains how the formats are reverse-engineered: recording a step in Premiere (or generating one and checking it there), working out what an action wrote, turning that into a rule with a check, and what else to update.

The most useful contributions are new steps and format reports. To report on a feature the demo project doesn't use, run `schema_dump.py` on your project and open an issue with its output: it carries only structure, never names, paths or transcripts. **Please don't attach real projects**; they contain your media paths, user name and often full transcripts.

## License

[MIT](LICENSE), except the public-domain interview clip in `fixtures/premiere-pro/media/` (see that folder's README for its credit and terms).

Adobe, Premiere Pro and After Effects are trademarks of Adobe Inc. This project is not affiliated with, endorsed by or sponsored by Adobe.
