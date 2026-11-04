# Working in this repo

Adobe Project Skills: unofficial Agent Skills that edit Adobe project files directly, without the app's UI or Computer Use. Today that is one skill, `skills/premiere-pro-projects/`, which reads and edits Premiere Pro `.prproj` files, backed by a reverse-engineered format spec and a public demo project that every rule is checked against. The repo is public: anything committed can be read by anyone.

Follow the Agent Skills format and authoring guidance:

- Specification: https://agentskills.io/specification
- Best practices: https://agentskills.io/skill-creation/best-practices

What the specification requires of every skill here:

- **`name`:** 1–64 characters, lowercase `a-z`, `0-9` and single hyphens, no leading or trailing hyphen, and the same as the skill's folder name.
- **`description`:** 1–1024 characters, saying what the skill does and when to use it, with the words a user would actually say. Tune it with `trigger-queries.json` (`run_evals.py --triggers`), not by guesswork.
- **Optional fields:** `license`, `compatibility` (≤ 500 characters, only for real environment needs), `metadata` (string keys to string values; we keep `version` there), `allowed-tools` (experimental).
- **Body:** under 500 lines and about 5,000 tokens, since it is loaded whole when the skill activates. Move detail into `references/`, keep each reference file focused, and link every one directly from `SKILL.md` (one level deep, relative paths from the skill root).
- **Folders:** `scripts/` (self-contained, clear errors), `references/` (read on demand), `assets/` (templates, data). Nothing a skill needs at run time may live outside its folder.
- **Validate** with the reference library before committing a SKILL.md change: `pip install skills-ref`, then `agentskills validate skills/<name>` (https://github.com/agentskills/agentskills/tree/main/skills-ref). CI runs it too.

## Layout

| Path | What it is |
|---|---|
| `skills/premiere-pro-projects/SKILL.md` | what the agent reads first: commands, gotchas, workflow, which reference to load |
| `skills/premiere-pro-projects/scripts/prproj.py` | the CLI (stdlib only); `selftest.py` checks it against a user's projects; `schema_dump.py` builds `prproj-classes.md` |
| `skills/premiere-pro-projects/references/spec/` | the format spec, one file per part; `README.md` holds the status tags |
| `skills/premiere-pro-projects/references/*.md` | task guides (recipes) and `prproj-classes.md` (generated) |
| `skills/premiere-pro-projects/evals/` | `evals.json`, `trigger-queries.json`, input projects in `files/`, script checks in `graders.py`, `RESULTS.md` |
| `skills/README.md` | per-skill feature roadmap with completeness percentages |
| `fixtures/premiere-pro/` | the public demo project: `media/`, one save per action in `steps/`, the steps table in its `README.md`, `generated/` for projects waiting to be checked |
| `tests/` | `run_all.py` (runs everything), `check_links.py`; per skill in `tests/premiere-pro/`: `replay_steps.py`, `test_eval_files.py`, `test_eval_graders.py` |
| `tools/` | `run_evals.py` (any skill, `--skill NAME`), `update_roadmap.py`; per skill in `tools/premiere-pro/`: `scrub_steps.py`, `build_eval_files.py`, `make_media.sh`, `extract_interview.sh` |
| `.claude-plugin/marketplace.json` | makes the repo a Claude Code plugin marketplace; one entry per skill |
| `.github/workflows/checks.yml` | CI: `tests/run_all.py`, the scrub check, `agentskills validate`, `claude plugin validate` |

Shared tools live at the top of `tests/` and `tools/`; anything for one skill goes in a subfolder named like its fixtures (`premiere-pro/`). A new skill gets `skills/<name>/`, `fixtures/<short>/`, `tests/<short>/`, `tools/<short>/` as needed, a `marketplace.json` entry and a section in `skills/README.md`.

## Evidence rules

The process for evidence, rules, commands, evals and scrubbing is in [`CONTRIBUTING.md`](CONTRIBUTING.md); follow it for every change. What matters most for you:

- **Only proven claims.** Every rule in the spec, the guides and `SKILL.md` has an `[O: … #id]` or `[V: … #id]` tag whose check passes on the cited steps (`tests/premiere-pro/test_rules.py`). No `[D]`/`[N]` tags and no hedged wording ("derived", "assumed", "expected to"): the test fails on them. Unproven ideas go in `fixtures/premiere-pro/generated/BACKLOG.md` with the step that would prove them.
- **Never weaken a check to make it pass.** If the evidence doesn't support a sentence, narrow the sentence or cite the steps that do.
- **Every command is proven or refused.** Write commands need a replay case, read commands a check in `tests/premiere-pro/test_commands.py`; anything else goes in `UNPROVEN` in `prproj.py` and isn't offered in `SKILL.md`.
- **Only public evidence.** Never cite, name or describe a private project, a client's or the maintainer's own work, even as an example. If something was learned from a private file, turn it into a generated step (`generated/build.sh` + `CHECKLIST.md`), have a person open it in Premiere, and commit that step instead.
- **Out of scope for now:** Lumetri and Adobe Stock / CC Library files.
- **Premiere is the referee.** Don't claim more than the tests show.

## Adding or changing a feature

Follow "Adding or changing a command", "Turning a finding into a rule" and "Evals, roadmap and README" in [`CONTRIBUTING.md`](CONTRIBUTING.md), in the same change. Also keep `SKILL.md` under 500 lines and bump its `metadata.version`, and keep the skill's `description`/`version` in `.claude-plugin/marketplace.json` matching `SKILL.md`. There is no separate findings or notes file: the spec, the steps table, the backlog and the tests are the record.

## Scrubbing data

See "Privacy and scrubbing" in [`CONTRIBUTING.md`](CONTRIBUTING.md). In addition:

- Run `python3 -I tools/check_private.py --all` before saying anything is ready to commit, and search every new `.prproj` yourself as well; `scrub_steps.py` only fixes home-folder paths. The repo's hooks (`.githooks/`, enabled with `git config core.hooksPath .githooks`) run these on commit and push; never bypass them with `--no-verify`.
- Don't put the maintainer's name or other personal details in working files (checklists, notes, eval history); use neutral wording.

## Running the checks

```bash
python3 -I tests/run_all.py              # everything; CI runs this on every push
python3 -I tests/run_all.py premiere     # only paths containing "premiere"
```

What it runs: `check_links.py` (every relative Markdown link and `#heading` resolves), then each skill's folder: `replay_steps.py` (every step pair against Premiere's saves, plus the home-path check), `test_rules.py` (every spec claim proven on its cited steps), `test_commands.py` (every command proven or refused), `test_schema.py` (the class catalogue is current), `test_eval_files.py` (eval inputs match their recipes), `test_eval_graders.py` (graders pass a correct output and fail an untouched one). Add new test files to `tests/<skill>/` and `run_all.py` picks them up.

## Running evals

Evals measure the skill against a no-skill baseline on the cases in `evals/evals.json` (format: https://agentskills.io/skill-creation/evaluating-skills).

```bash
python3 tools/run_evals.py --dry-run           # what would run, and the exact command
python3 tools/run_evals.py                     # all cases, with and without the skill, 1 run each
python3 tools/run_evals.py --cases 6,7 --runs 3 -j 4
python3 tools/run_evals.py --regrade N         # grade iteration N again after changing a grader
python3 tools/run_evals.py --triggers          # trigger rate of the SKILL.md description
```

- **Always use `run_evals.py`, never helper agents in your own session.** Your session may have other skills loaded, including a private skill with the same name, which would contaminate the result. The script starts each run as a fresh `claude -p` with an empty HOME, no setting sources (so no account or user skills), no CLAUDE.md, no memory, no MCP servers, the same tool list in both arms, and only the input copied in as `demo.prproj`. It marks a run unclean if anything else was loaded or read.
- **Ask before running a round.** A full round is about 46 runs (the multi-step cases get 3 per arm) plus a judge call each, on the user's plan.
- On macOS, if runs can't authenticate with an empty HOME, add `--keep-home`.
- Grading: script checks in the skill's `evals/graders.py` (using its own `prproj.py`; a skill without one is judged entirely) wherever the project can be checked; a judge model with no tools for the rest, which never sees `expected_output`. Prefer adding a script check over relying on the judge.
- Results: raw runs in `skills/premiere-pro-projects-workspace/iteration-N/` (git-ignored); the script adds the summary row to `evals/RESULTS.md` and the round's figures to `evals/results/iteration-N.json` (both committed). Update the README's "How well it works" table after a full round. Don't edit result numbers by hand; regrade instead. Add a short note to the row explaining any failure worth knowing about.
