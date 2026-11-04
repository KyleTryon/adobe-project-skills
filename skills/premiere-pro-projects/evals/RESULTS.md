# Eval results

Results of running [`evals.json`](evals.json) against this skill. Each run compares the skill against a baseline with no skill loaded, on the same prompts and input files. Trigger-rate results for [`trigger-queries.json`](trigger-queries.json) go in their own table below.

Raw outputs (transcripts, output files, `grading.json`, `timing.json`) stay in `skills/premiere-pro-projects-workspace/iteration-N/`, which git ignores. This file keeps the summary, and [`results/`](results/) the full figures for each round (`iteration-N.json`: per-case and per-arm scores, timing, cost, model, Claude Code version and a hash of the skill files tested). Rounds before the repo's first commit show `uncommitted`; the skill hash identifies what was tested.

## What counts as a clean run

A run only goes in the log if every case was:

- **Isolated:** a fresh session with no memory, no CLAUDE.md, no user or account skills, no MCP servers and no other plugins. Another skill with the same name, such as a private copy, must not be loadable.
- **Given only the case:** the prompt, plus the input file copied into an empty project folder (a temporary folder outside the repo) as `demo.prproj`. The skill under test is a copy without its `evals/` folder, also outside the repo.
- **Run in both arms:** with the skill (`with_skill`) and without it (`without_skill`), same model, same tools.
- **Graded against the case's assertions** plus the `common_assertions`. Script-checkable assertions are graded by script (`prproj.py validate`, `cuts`, `markers`, `speakers`, `cut-transcript`); the rest by a judge model that sees the reply and the output files, never the expected output. Multi-step edits are graded on the end state (the cut list, sync, gaps and flash frames, words kept whole or removed, transitions), so any correct order of operations passes.

**Two scores.** Each assertion is an **edit** check (the project and deliverables end up right) or a **habit** check (a backup sequence, a tidy project folder, what the reply suggests). The edit score is the headline. A run that loaded or read something it shouldn't (a foreign skill or MCP tool, a file outside its folder) is **unclean**: it's re-run once, and left out of the totals if it's still unclean.

## Running

From the repo root, with the `claude` CLI logged in:

```bash
python3 tools/run_evals.py --dry-run          # what would run, and the exact command
python3 tools/run_evals.py                    # all cases, 1 run per arm; adds a row below
python3 tools/run_evals.py --cases 6,7 --runs 3
python3 tools/run_evals.py --regrade N        # grade iteration N again after a grader change
python3 tools/run_evals.py --triggers         # trigger queries, 3 runs each
```

The script checks live in [`graders.py`](graders.py); `tests/premiere-pro/test_eval_graders.py` proves they pass a correct output, fail an untouched one and catch plausible wrong edits. A case's `runs` in `evals.json` sets how many runs it gets per arm (the multi-step cases get 3). Each run's `run.json` lists anything that made it unclean.

## Run log

| Iteration | Date | Skill version (commit) | Model | Edits, with skill | Edits, without | Δ edits | Habits, with / without | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-04 | 3.0 (uncommitted, a6733c50dd63) | claude-sonnet-5-5 | 88% (38/43) | 78% (29/37) | +10 pts | 100% (20/20) / 83% (15/18) | runs: 9 with, 9 without; 26.1 s vs 74.4 s mean; $2.90; **1 unclean run(s) left out** |
| 3 | 2026-11-04 | 3.0 (uncommitted, c6e50538d011) | claude-sonnet-5-5 | 100% (37/37) | 73% (27/37) | +27 pts | 100% (14/14) / 79% (11/14) | runs: 7 with, 7 without; 31.2 s vs 83.9 s mean; $2.36; cases 5,10,13; after adding the filler-token guidance to SKILL.md and making case 13's prompt say "on the timeline" |
| 2 | 2026-11-04 | 3.0 (uncommitted, 1ffb4f444df6) | claude-sonnet-5-5 | 95% (107/113) | 77% (87/113) | +18 pts | 100% (50/50) / 72% (36/50) | runs: 23 with, 23 without; 25.9 s vs 90.4 s mean; $10.08; with-skill misses: case 13's prompt was ambiguous (all 3 runs cut 0:08–0:10 of clip-b's own media, not the timeline), case 5 didn't recognise Speech-to-Text's empty filler tokens, case 10 left fillers in 2 of 3 runs |
<!-- runlog:end -->

Pass rate = assertions passed / assertions checked, over all cases and runs. Record time and tokens per arm in the notes when they differ by more than a few percent.

### Per case (latest iteration)

<!-- percase:start -->
Iteration 2, clean runs only. Failed assertions are listed by key: a number is the case's own assertion (0-based), c0-c1 the common ones.

| # | Case | Edit, with skill | Edit, without | Habits, with | Habits, without | Failed (with skill) |
|---|---|---|---|---|---|---|
| 1 | pip-slide-in | 100% (5/5) | 20% (1/5) | 100% (2/2) | 100% (2/2) |  |
| 2 | trimmed-head-slide | 100% (5/5) | 100% (5/5) | 100% (2/2) | 50% (1/2) |  |
| 3 | split-interview | 100% (5/5) | 100% (5/5) | 100% (2/2) | 50% (1/2) |  |
| 4 | label-while-open | 100% (2/2) | 50% (1/2) | 100% (3/3) | 100% (3/3) |  |
| 5 | filler-markers | 75% (3/4) | 75% (3/4) | 100% (2/2) | 100% (2/2) | 1 |
| 6 | transcript-cut | 100% (6/6) | 83% (5/6) | 100% (2/2) | 50% (1/2) |  |
| 7 | captions-after-cut | 100% (6/6) | 100% (6/6) | 100% (2/2) | 100% (2/2) |  |
| 8 | rename-speakers | 100% (6/6) | 100% (6/6) | 100% (2/2) | 100% (2/2) |  |
| 9 | crossfade-no-handles | 100% (4/4) | 75% (3/4) | 100% (3/3) | 100% (3/3) |  |
| 10 | rough-cut | 89% (16/18) | 67% (12/18) | 100% (6/6) | 50% (3/6) | 1 |
| 11 | assemble | 100% (18/18) | 83% (15/18) | 100% (6/6) | 83% (5/6) |  |
| 12 | speaker-chapters | 100% (15/15) | 100% (15/15) | 100% (6/6) | 50% (3/6) |  |
| 13 | cut-and-crossfade | 80% (12/15) | 53% (8/15) | 100% (6/6) | 67% (4/6) | 1 |
| 14 | trim-blocked-by-fade | 100% (2/2) | 0% (0/2) | 100% (3/3) | 33% (1/3) |  |
| 15 | speed-not-covered | 100% (2/2) | 100% (2/2) | 100% (3/3) | 100% (3/3) |  |
<!-- percase:end -->

## Trigger queries

| Iteration | Date | Description version | Train pass | Validation pass | Notes |
|---|---|---|---|---|---|
| 4 | 2026-11-04 | 3.0 (description 1b8c1ed2) | 16/17 | 11/11 | claude-sonnet-5-5; misses: "convert this SRT file to WebVTT" (3/3, shouldn't trigger) |
| 5 | 2026-11-04 | 3.1 (description 66f69cd8) | 17/17 | 10/11 | claude-sonnet-5-5; misses: "I need a Final Cut Pro XML of this edit decision list" (2/3, shouldn't trigger) |

Each query runs 3 times; it passes when it triggers more than half the time (should trigger) or less than half (shouldn't).

## Earlier runs

Iterations 1–2 ran on an earlier fixture that has since been retired, so their numbers aren't comparable with these cases. What they showed: the skill's value was the in-project backup sequence, the close-without-saving warning, and speed. Cases 1–5 were rebuilt on the public demo project afterwards; cases 6–9 (transcript-driven cut, captions after a cut, speaker rename, crossfade without handles) were added once the Speech-to-Text and crossfade steps were verified in Premiere.
