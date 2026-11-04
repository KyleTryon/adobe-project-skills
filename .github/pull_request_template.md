## What this changes

<!-- The feature, rule or fix, and the step(s) that prove it. -->

## Checklist ([CONTRIBUTING.md](../CONTRIBUTING.md))

- [ ] `python3 -I tests/run_all.py` passes
- [ ] New steps are scrubbed (`tools/premiere-pro/scrub_steps.py`), searched for personal data, and have a row in the steps table
- [ ] Every new claim has an `[O: … #id]` / `[V: … #id]` tag whose check passes; nothing unproven or hedged (it goes in `BACKLOG.md`)
- [ ] New or changed commands have a replay case or read check, or are listed in `UNPROVEN`
- [ ] `SKILL.md`, the guide, `skills/README.md` (`tools/update_roadmap.py`) and the README match what's now proven
- [ ] No real projects, `.prin` files, auto-saves or eval workspaces
