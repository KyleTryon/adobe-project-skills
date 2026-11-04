# Contributing

Adobe doesn't publish its project file formats, so everything the skills know comes from watching what the apps write. This guide covers how that's done here: how evidence is recorded, how a finding becomes a rule, how a rule is proven, and what else has to change with it. The examples are Premiere Pro (`skills/premiere-pro-projects/`); other skills follow the same layout.

## Set up once

```bash
git config core.hooksPath .githooks
```

The pre-commit hook blocks a commit that contains personal data (your user name, home folder, volume names, git name or email, and anything you list in a git-ignored `.private-words` file, one word per line), an unscrubbed project, a file that must never be committed, or a broken link or rule check. The pre-push hook runs the whole test suite. CI runs the same checks, but only after you've pushed, so keep the hooks on.

## How evidence works

**One small public project, saved after every action.** [`fixtures/premiere-pro/`](fixtures/premiere-pro/) holds a demo project built from licence-free media. [`steps/`](fixtures/premiere-pro/steps/) has a save of it after each single action: `05-add_clip_b.prproj`, `06-cut.prproj`, …. Diffing two neighbouring saves shows exactly what that action writes. The [steps table](fixtures/premiere-pro/README.md#steps) says what each one is.

**Two kinds of proof, and nothing else.** Every rule in [the spec](skills/premiere-pro-projects/references/spec/README.md) carries a tag naming its evidence and the check that proves it:

| Tag | Means | Example |
|---|---|---|
| `[O: … #id]` observed | Premiere wrote it | `[O: steps 05→06 #edits.split]` |
| `[V: … #id]` verified | the scripts wrote it, and the result opened correctly in Premiere | `[V: step 13-gen #transitions.fade-in]` |

`tests/premiere-pro/test_rules.py` runs each rule's check on exactly the steps its tag cites. A claim without a passing check doesn't go in the spec, the guides or `SKILL.md`; neither does hedged wording ("derived", "assumed", "expected to"). Ideas that aren't proven yet go in the backlog, [`fixtures/premiere-pro/generated/BACKLOG.md`](fixtures/premiere-pro/generated/BACKLOG.md), each with the step that would prove it.

**No private projects.** Real projects hold media paths, user names, fonts, library IDs and often whole transcripts. Don't commit them, cite them or describe them. To learn from your own project, contribute its structure (below) or reproduce the feature in the demo project.

## Recording a step in Premiere

1. Turn **Auto Save** off (Settings › Auto Save).
2. Open the latest step (or a copy) from `fixtures/premiere-pro/steps/`, or start the project fresh as the fixtures README describes, with the media from `fixtures/premiere-pro/media/`.
3. Make **one** action: one razor cut, one trim, one marker, one setting.
4. **File › Save a Copy** into `steps/` as `NN-short_name.prproj`, the next free number. Save a Copy keeps you in the working project; Save As would change the project's own name and paths. If you slip, undo and save the copy again under the same number.
5. Scrub it: `python3 -I tools/premiere-pro/scrub_steps.py`. It rewrites your user name and the repo's location on your disk to neutral paths (`/Users/editor/adobe-project-skills/…`).
6. Add its row to the steps table: what you did, anything not obvious (a setting picked, a dialog seen).

## Generating a step instead

Many backlog items can be proven without recording anything by hand: the scripts write the file, and Premiere is the referee.

1. Pick an item from `BACKLOG.md`. Each says which step to generate.
2. Add its commands to [`fixtures/premiere-pro/generated/build.sh`](fixtures/premiere-pro/generated/build.sh) (only `prproj.py` commands, starting from a step) and what to look for in Premiere to [`CHECKLIST.md`](fixtures/premiere-pro/generated/CHECKLIST.md).
3. Run `./build.sh --local` (rewrites paths to your home folder so Premiere finds the media), open the result in Premiere, and go through the checklist.
4. If it checks out, move it to `steps/` as `NN-gen-short_name.prproj` (scrubbed), and add its row. If something's wrong, **Save a Copy** as `NN-…-premiere.prproj`: the diff against the generated file shows what Premiere corrected, which is often the most useful evidence of all.

## Working out what changed

```bash
P="python3 -I skills/premiere-pro-projects/scripts/prproj.py"
$P diff steps/05-add_clip_b.prproj steps/06-cut.prproj      # objects added, removed, moved, and fields changed
$P diff OLD NEW --all                                        # including view state (selection, zoom, panel layout)
$P unpack steps/06-cut.prproj /tmp/06.xml                   # the raw XML
$P validate FILE                                             # structural checks, plus any structure the steps never showed
python3 -I skills/premiere-pro-projects/scripts/schema_dump.py --class Marker steps/11-markers.prproj
```

- `diff` matches objects by their place in the graph, because Premiere renumbers ObjectIDs on every save. View state is hidden unless you pass `--all`; decide deliberately whether a change is view state before ignoring it.
- `validate` warns about classes, ClassIDs, Versions or paths that `prproj-schema.json` hasn't seen: that's the quickest way to find what's new in a step or a newer Premiere.
- Look for the smallest claim the diff supports. "Premiere wrote X in this step" is a rule; "Premiere always writes X" needs more steps.

## Turning a finding into a rule

1. Write the sentence in the right file under `skills/premiere-pro-projects/references/spec/` (the [spec contents](skills/premiere-pro-projects/references/spec/README.md) say which part covers what), ending with its tag: `[O: steps 05→06 #edits.split]`. Citations are single steps (`step 11`), ranges (`steps 01–23`), pairs (`steps 05→06`) or a list of those. One tag per claim.
2. Write its check in `tests/premiere-pro/rules/<area>.py`:

   ```python
   @rule('edits.split')
   def _(ev):                       # ev.steps: cited steps; ev.pairs: cited before→after pairs
       for a, b in ev.pairs:
           ...
           expect(cond, 'what went wrong')
   ```

   Test what the sentence says, on the cited steps, and fail if a cited step lacks the subject. If the check fails, the sentence is wrong or too broad: narrow it or cite the steps that really show it. Never weaken the check.
3. If new classes or paths appeared, regenerate the catalogue: `python3 -I skills/premiere-pro-projects/scripts/schema_dump.py --write fixtures/premiere-pro/steps/*.prproj`.
4. If the rule proves a backlog item, delete it from `BACKLOG.md`; if it covers something listed in [§18 Not covered](skills/premiere-pro-projects/references/spec/18-not-observed.md), remove it there.

## Adding or changing a command

- Write commands live in `skills/premiere-pro-projects/scripts/prproj.py` (standard library only). They validate before writing, refuse unsafe edits with a message saying what to fix, and support `--dry-run`.
- **Proof:** a write command needs a case in `tests/premiere-pro/replay_steps.py` that runs it on a step and compares the result with Premiere's own save of the same edit, or with a verified `-gen-` step. A read command needs a check in `tests/premiere-pro/test_commands.py` comparing its output with what Premiere did in a step. Until then, list it in `UNPROVEN` in `prproj.py`: it refuses to run without `--unproven`, and `SKILL.md` doesn't offer it.
- Then update `SKILL.md` (commands table, any gotcha an agent would otherwise hit, `metadata.version`), the matching task guide in `references/`, and the skill's entry in `.claude-plugin/marketplace.json` if the description changed.

## Evals, roadmap and README

- **Evals:** if users would ask for the feature, add a case to `skills/<skill>/evals/evals.json`, build its input from a step in `tools/premiere-pro/build_eval_files.py`, add script checks to `evals/graders.py` and a known-good build to `tests/premiere-pro/test_eval_graders.py`, and add phrasings to `trigger-queries.json`. Results are recorded by `tools/run_evals.py`, never by hand; see `evals/RESULTS.md`.
- **Roadmap:** update the feature's mark in [`skills/README.md`](skills/README.md) and run `python3 tools/update_roadmap.py`.
- **README:** update it when what the skill can do, the layout or the commands change.

## Contributing from your own projects, without sharing them

`schema_dump.py` reports only structure: classes, ClassIDs, Versions, element paths and value *kinds*, never names, paths, transcript text or other content. If your project uses a feature the demo project doesn't (nested sequences, speed changes, Essential Graphics, other effects, another Premiere version), open an issue with:

- your Premiere version and OS;
- `python3 -I skills/premiere-pro-projects/scripts/schema_dump.py --json YOUR.prproj` (or `--class NAME` for the part involved), and `prproj.py validate YOUR.prproj` output;
- what you did in Premiere.

That tells us what to reproduce in the demo project, where it can become a step and a rule.

## Privacy and scrubbing

Premiere writes personal data into projects: absolute paths with your user name, network volume names, recent files, fonts, library and Stock IDs, account and organisation strings, some of it inside base64 or UTF-16 blobs.

- Scrub every new step (`tools/premiere-pro/scrub_steps.py`); the pre-commit hook and CI fail on a home-folder path in any committed project.
- `python3 -I tools/check_private.py FILE…` (run by the hook) looks for your own identifiers in projects, their decoded blobs, media metadata and text files. Add client or project names you never want published to `.private-words`.
- Before committing a `.prproj`, also search its decompressed XML and decoded blobs (UTF-8 and UTF-16LE) for names, emails, organisations, volumes and URNs.
- Projects may only point at `fixtures/premiere-pro/media/`.
- Never commit `.prin` files, `Adobe Premiere Pro Auto-Save/` folders, `*-workspace/` eval runs or caches (`.gitignore` covers them; check `git status` anyway).
- Keep the media credits and the interview clip's terms in the fixtures README.

## Before you open a pull request

```bash
python3 -I tests/run_all.py
```

It runs the link check, the replay tests against Premiere's saves, every rule check, the command proofs, the schema freshness check and the eval input and grader tests. CI runs it too, plus the home-path scan, the Agent Skills validator and the plugin manifest check. Make sure:

- every new step has its row in the steps table, and is scrubbed;
- no tag lacks a check, and no hedged wording slipped in;
- `SKILL.md`, the guide, the roadmap and the README match what's now proven.
