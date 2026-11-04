#!/usr/bin/env python3
"""Run a skill's evals (skills/<name>/evals/evals.json) in clean, isolated Claude Code
sessions, grade them, and record the results.

Each case runs in two arms on the same prompt, input and tools: `with_skill` (the repo's
skill loaded with --plugin-dir) and `without_skill` (nothing loaded). Every run gets:

  * an empty project folder holding only the case's input, copied in as demo.<ext>
  * an empty HOME, no settings sources (so no account or user skills, plugins or settings),
    no CLAUDE.md, no auto memory, no MCP servers
  * the same tool list: Bash, Read, Write, Edit, Glob, Grep, Skill

Assertions are graded by script where the skill provides checks (skills/<name>/evals/graders.py,
see grade_scripted) and by a judge model otherwise. The judge has no tools, sees
the prompt, the reply, the folder listing and the script findings, never expected_output.

  python3 tools/run_evals.py --dry-run                  show what would run
  python3 tools/run_evals.py                            all cases, 1 run per arm
  python3 tools/run_evals.py --cases 6,7 --runs 3 -j 4  some cases, 3 runs each, 4 at a time
  python3 tools/run_evals.py --regrade 1                regrade iteration 1 (after a grader fix)
  python3 tools/run_evals.py --triggers                 trigger-rate eval for the description

  python3 tools/run_evals.py --skill NAME ...           another skill (default: the only one)

Results: skills/<name>-workspace/iteration-N/ (ignored by git: transcripts, outputs,
grading.json, timing.json), a summary row in skills/<name>/evals/RESULTS.md, and the round's
figures (no transcripts or files) in skills/<name>/evals/results/iteration-N.json.

Needs the `claude` CLI, logged in. On macOS the login lives in the keychain, which an empty
HOME can hide: if runs fail to authenticate, pass --keep-home (the other isolation still holds).
"""
import argparse, concurrent.futures as cf, datetime, hashlib, json, os, re, shutil, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = SKILL = EVALS = WORKSPACE = RESULTS = G = None     # set by configure()
TOOLS = 'Bash,Read,Write,Edit,Glob,Grep,Skill'


class _NoGraders:
    """Stand-in when a skill has no evals/graders.py: everything goes to the judge."""
    JUDGE = None

    class Run:
        def __init__(self, case, input_path, project_dir, reply):
            self.case, self.input, self.dir, self.reply = case, input_path, project_dir, reply or ''

        def files(self):
            return sorted(os.path.relpath(os.path.join(d, f), self.dir) for d, _, fs in os.walk(self.dir) for f in fs)

    @staticmethod
    def grade_scripted(case, run):
        return {**{i: None for i in range(len(case['assertions']))},
                **{f'c{i}': None for i in range(len(json.load(open(os.path.join(EVALS, 'evals.json'))).get('common_assertions', [])))}}


def configure(name):
    """Point the runner at skills/<name>/ and load its graders, if it has any."""
    global NAME, SKILL, EVALS, WORKSPACE, RESULTS, G
    NAME = name
    SKILL = os.path.join(ROOT, 'skills', name)
    EVALS = os.path.join(SKILL, 'evals')
    WORKSPACE = os.path.join(ROOT, 'skills', f'{name}-workspace')
    RESULTS = os.path.join(EVALS, 'RESULTS.md')
    gp = os.path.join(EVALS, 'graders.py')
    if os.path.exists(gp):
        import importlib.util
        spec = importlib.util.spec_from_file_location(f'{name.replace("-", "_")}_graders', gp)
        G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
    else:
        G = _NoGraders


def skills_with_evals():
    d = os.path.join(ROOT, 'skills')
    return sorted(x for x in os.listdir(d) if os.path.exists(os.path.join(d, x, 'evals', 'evals.json')))


# ---------- isolation ----------

def build_plugin(it_dir):
    """Copy the skill without its evals into a temporary folder outside the repo: a bare skill
    folder loads as a plugin of the same name (NAME:NAME), and runs can't see the expected
    outputs or graders, or find the repo by looking around."""
    root = tempfile.mkdtemp(prefix='eval-plugin-')
    p = os.path.join(root, NAME)
    shutil.copytree(SKILL, p, ignore=shutil.ignore_patterns('evals', '__pycache__', '*.pyc'))
    return p


def other_copies(plugin):
    """Other copies of the skill on this machine that a run could find and read."""
    out = []
    for base in ['/mnt', '/tmp', '/home', '/root', os.path.expanduser('~'), '/Users']:
        if not os.path.isdir(base):
            continue
        for d, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in ('.git', 'node_modules', '__pycache__', 'proc')]
            if os.path.basename(d) == NAME and 'SKILL.md' in files:
                rp = os.path.realpath(d)
                if rp not in (os.path.realpath(SKILL), os.path.realpath(plugin)):
                    out.append(d)
            if d.count(os.sep) > 9:
                dirs[:] = []
    return sorted(set(out))

def skill_hash(plugin):
    h = hashlib.sha256()
    base = plugin
    for d, _, fs in sorted(os.walk(base)):
        for f in sorted(fs):
            h.update(os.path.relpath(os.path.join(d, f), base).encode()); h.update(open(os.path.join(d, f), 'rb').read())
    return h.hexdigest()[:12]


def claude_cmd(prompt, plugin, args, tools=TOOLS, max_turns=None):
    cmd = [args.claude, '-p', prompt, '--setting-sources', '', '--strict-mcp-config',
           '--mcp-config', '{"mcpServers":{}}', '--disallowedTools', 'mcp__claude-in-chrome__*',
           '--tools', tools, '--permission-mode', 'dontAsk', '--allowedTools', tools,
           '--output-format', 'stream-json', '--verbose', '--no-session-persistence']
    if plugin:
        cmd += ['--plugin-dir', plugin]
    if args.model:
        cmd += ['--model', args.model]
    if max_turns:
        cmd += ['--max-turns', str(max_turns)]
    return cmd


def clean_env(home, keep_home):
    env = {k: v for k, v in os.environ.items() if k != 'CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD'}
    env.update(CLAUDE_CODE_DISABLE_CLAUDE_MDS='1', CLAUDE_CODE_DISABLE_AUTO_MEMORY='1')
    if not keep_home:
        os.makedirs(home, exist_ok=True); env['HOME'] = home
    return env


def read_stream(path):
    ev = []
    for line in open(path, encoding='utf-8', errors='replace'):
        try:
            ev.append(json.loads(line))
        except ValueError:
            pass
    return ev


def contamination(events, arm, plugin_dir, run_dir):
    """Reasons a run isn't clean: foreign skills or MCP tools loaded, or files read outside the run."""
    why = []
    init = next((e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init'), None)
    if not init:
        return ['no init event (the session did not start)']
    skills = init.get('skills') or init.get('slash_commands') or []
    ours = f'{NAME}:{NAME}'
    foreign = [s for s in skills if ':' in s and s != ours]
    if foreign:
        why.append('foreign plugin skills loaded: ' + ', '.join(foreign[:6]))
    if [s for s in skills if s.split(':')[-1] == NAME and s != ours] or (arm == 'without_skill' and ours in skills):
        why.append(f'a {NAME} skill was available that should not be')
    if arm == 'with_skill' and ours not in skills:
        why.append('the skill under test did not load')
    mcp = [t for t in init.get('tools', []) if t.startswith('mcp__')]
    if mcp:
        why.append(f'{len(mcp)} MCP tools available')
    allowed = [os.path.realpath(run_dir)] + ([os.path.realpath(plugin_dir)] if arm == 'with_skill' else [])
    for e in events:
        if e.get('type') != 'assistant':
            continue
        for c in (e.get('message') or {}).get('content') or []:
            if c.get('type') != 'tool_use':
                continue
            blob = json.dumps(c.get('input'))
            for p in re.findall(r'(/[\w.\-]+(?:/[\w.\-]+)+)', blob):
                rp = os.path.realpath(p)
                if not os.path.exists(rp):
                    continue    # a path quoted from the project (e.g. media), not a file read here
                if any(rp.startswith(a) for a in allowed) or rp.startswith(('/tmp', '/usr', '/bin', '/opt', '/dev', '/etc', '/proc')):
                    continue
                if re.search(r'\.claude|skills|adobe-project-skills|adobe-creative-cloud|' + re.escape(NAME), rp, re.I):
                    why.append(f'touched {p}')
    return sorted(set(why))


# ---------- one run ----------

def do_run(case, arm, k, it_dir, plugin, args):
    """One run in an empty temporary folder outside the repo; moved into the workspace after."""
    run_dir = os.path.join(it_dir, f"{case['id']:02d}-{case['name']}", arm, f'run-{k}')
    shutil.rmtree(run_dir, ignore_errors=True)
    tmp = tempfile.mkdtemp(prefix='eval-run-')
    proj = os.path.join(tmp, 'project'); os.makedirs(proj)
    src = os.path.join(SKILL, case['files'][0])
    shutil.copyfile(src, os.path.join(proj, 'demo' + os.path.splitext(src)[1]))   # prompts call it demo.<ext>
    cmd = claude_cmd(case['prompt'], plugin if arm == 'with_skill' else None, args, max_turns=args.max_turns)
    t0 = time.time()
    with open(os.path.join(tmp, 'transcript.jsonl'), 'w') as out:
        try:
            p = subprocess.run(cmd, cwd=proj, env=clean_env(os.path.join(tmp, 'home'), args.keep_home),
                               stdout=out, stderr=subprocess.PIPE, text=True, timeout=args.timeout)
            err = p.stderr[-2000:]
        except subprocess.TimeoutExpired:
            err = f'timed out after {args.timeout}s'
    wall = time.time() - t0
    shutil.rmtree(os.path.join(tmp, 'home'), ignore_errors=True)
    events = read_stream(os.path.join(tmp, 'transcript.jsonl'))
    res = next((e for e in reversed(events) if e.get('type') == 'result'), {})
    open(os.path.join(tmp, 'reply.md'), 'w').write(res.get('result') or '')
    timing = {'wall_seconds': round(wall, 1), 'duration_ms': res.get('duration_ms'), 'num_turns': res.get('num_turns'),
              'total_cost_usd': res.get('total_cost_usd'), 'usage': res.get('usage'), 'is_error': res.get('is_error'),
              'stderr': err if not res else None}
    json.dump(timing, open(os.path.join(tmp, 'timing.json'), 'w'), indent=1)
    json.dump({'arm': arm, 'case': case['name'], 'contamination': contamination(events, arm, plugin, tmp),
               'tmp_dir': tmp, 'command': cmd}, open(os.path.join(tmp, 'run.json'), 'w'), indent=1)
    os.makedirs(os.path.dirname(run_dir), exist_ok=True)
    shutil.move(tmp, run_dir)
    return run_dir

# ---------- grading ----------

def judge(case, run, pending, facts, args):
    if not pending:
        return {}
    files = run.files()
    srt = ''
    for f in files:
        if f.lower().endswith(('.srt', '.vtt')):
            srt += f'\n--- {f} ---\n' + open(os.path.join(run.dir, f), encoding='utf-8', errors='replace').read()[:6000]
    items = '\n'.join(f'{k}: {t}' for k, t in pending)
    prompt = f"""You are grading one run of an AI agent that was asked to work on an Adobe Premiere Pro project file (demo.prproj).
Judge each assertion strictly from the evidence below. Pass only if the evidence clearly shows it. Do not guess.

USER PROMPT:
{case['prompt']}

AGENT'S FINAL REPLY:
{run.reply or '(empty)'}

FILES IN THE PROJECT FOLDER AFTER THE RUN: {', '.join(files) or '(none)'}

FACTS CHECKED BY SCRIPT (reliable):
{facts or '(none)'}
{srt}

ASSERTIONS TO JUDGE:
{items}

Answer with only a JSON array, one object per assertion: [{{"key": "<key>", "passed": true|false, "evidence": "<one sentence quoting or citing the evidence>"}}]"""
    jdir = os.path.join(os.path.dirname(run.dir), 'judge')
    os.makedirs(jdir, exist_ok=True)
    cmd = claude_cmd(prompt, None, argparse.Namespace(claude=args.claude, model=args.judge_model), tools='', max_turns=2)
    cmd[cmd.index('--allowedTools') + 1] = ''
    p = subprocess.run(cmd, cwd=jdir, env=clean_env(os.path.join(jdir, 'home'), args.keep_home),
                       capture_output=True, text=True, timeout=600)
    shutil.rmtree(os.path.join(jdir, 'home'), ignore_errors=True)
    open(os.path.join(jdir, 'judge.jsonl'), 'w').write(p.stdout)
    res = next((e for e in reversed([json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')])
                if e.get('type') == 'result'), {})
    m = re.search(r'\[.*\]', res.get('result') or '', re.S)
    try:
        return {str(x['key']): (bool(x['passed']), 'judge: ' + str(x.get('evidence', ''))) for x in json.loads(m.group(0))}
    except (AttributeError, ValueError, KeyError, TypeError):
        return {k: (False, 'judge gave no usable verdict') for k, _ in pending}


def grade(case, run_dir, common, args):
    run = G.Run(case, os.path.join(SKILL, case['files'][0]), os.path.join(run_dir, 'project'),
                open(os.path.join(run_dir, 'reply.md')).read() if os.path.exists(os.path.join(run_dir, 'reply.md')) else '')
    meta = json.load(open(os.path.join(run_dir, 'run.json')))
    run.moved_from = meta.get('tmp_dir')
    scripted = G.grade_scripted(case, run)
    text = {i: t for i, t in enumerate(case['assertions'])}
    text.update({f'c{i}': t for i, t in enumerate(common)})
    facts = '\n'.join(f'- {text[k]}: {"PASS" if v[0] else "FAIL"} ({v[1]})' for k, v in scripted.items() if v is not G.JUDGE)
    pending = [(str(k), text[k]) for k, v in scripted.items() if v is G.JUDGE]
    verdicts = judge(case, run, pending, facts, args) if not args.no_judge else {}
    results = []
    for k, v in scripted.items():
        if v is G.JUDGE:
            passed, ev = verdicts.get(str(k), (None, 'not judged (--no-judge)' if args.no_judge else 'judge skipped it'))
            by = 'judge'
        else:
            (passed, ev), by = v, 'script'
        kind = G.kind(case, k) if hasattr(G, 'kind') else 'edit'
        results.append({'key': str(k), 'kind': kind, 'text': text[k], 'passed': passed, 'evidence': ev, 'graded_by': by})
    summ = {}
    for kind in ('edit', 'habit'):
        js = [r for r in results if r['kind'] == kind and r['passed'] is not None]
        summ[kind] = {'passed': sum(r['passed'] is True for r in js), 'total': len(js)}
    g = {'case': case['name'], 'arm': meta['arm'], 'clean': not meta['contamination'],
         'contamination': meta['contamination'], 'assertion_results': results, 'summary': summ}
    json.dump(g, open(os.path.join(run_dir, 'grading.json'), 'w'), indent=1)
    return g

# ---------- reporting ----------

def benchmark(it_dir, evals, meta):
    """Totals over clean runs only; unclean runs are counted separately and left out."""
    rows = {}
    for case in evals['evals']:
        for arm in ('with_skill', 'without_skill'):
            d = os.path.join(it_dir, f"{case['id']:02d}-{case['name']}", arm)
            runs = sorted(x for x in os.listdir(d) if x.startswith('run-')) if os.path.isdir(d) else []
            gs = [json.load(open(os.path.join(d, r, 'grading.json'))) for r in runs if os.path.exists(os.path.join(d, r, 'grading.json'))]
            tm = [json.load(open(os.path.join(d, r, 'timing.json'))) for r in runs if os.path.exists(os.path.join(d, r, 'timing.json'))]
            if not gs:
                continue
            clean = [g for g in gs if g['clean']]
            row = {'runs': len(gs), 'clean_runs': len(clean), 'unclean_runs': len(gs) - len(clean),
                   'mean_seconds': round(sum(x['wall_seconds'] for x in tm) / len(tm), 1) if tm else None,
                   'cost_usd': round(sum(x.get('total_cost_usd') or 0 for x in tm), 4)}
            for kind in ('edit', 'habit'):
                p = sum(g['summary'][kind]['passed'] for g in clean); t = sum(g['summary'][kind]['total'] for g in clean)
                row[kind] = {'passed': p, 'total': t, 'pass_rate': round(p / t, 3) if t else None}
            row['failed_keys'] = sorted({r['key'] for g in clean for r in g['assertion_results'] if r['passed'] is False},
                                        key=lambda k: (k.startswith('c'), int(k.lstrip('c'))))
            rows.setdefault(case['name'], {'id': case['id']})[arm] = row
    tot = {}
    for arm in ('with_skill', 'without_skill'):
        xs = [r[arm] for r in rows.values() if arm in r]
        t = {'unclean_runs': sum(x['unclean_runs'] for x in xs), 'runs': sum(x['runs'] for x in xs),
             'mean_seconds': round(sum(x['mean_seconds'] or 0 for x in xs) / len(xs), 1) if xs else None,
             'cost_usd': round(sum(x['cost_usd'] for x in xs), 4)}
        for kind in ('edit', 'habit'):
            p = sum(x[kind]['passed'] for x in xs); n = sum(x[kind]['total'] for x in xs)
            t[kind] = {'passed': p, 'total': n, 'pass_rate': round(p / n, 3) if n else None}
        tot[arm] = t
    b = {**meta, 'cases': rows, 'totals': tot}
    json.dump(b, open(os.path.join(it_dir, 'benchmark.json'), 'w'), indent=1)
    return b

def pct(x):
    return '—' if x is None else f'{x:.0%}'


def update_results(b, evals):
    s = open(RESULTS, encoding='utf-8').read()
    w, wo = b['totals'].get('with_skill', {}), b['totals'].get('without_skill', {})
    fr = lambda x, kind: f"{pct(x[kind]['pass_rate'])} ({x[kind]['passed']}/{x[kind]['total']})" if x.get(kind) else '—'
    we, woe = (w.get('edit') or {}).get('pass_rate'), (wo.get('edit') or {}).get('pass_rate')
    delta = '—' if we is None or woe is None else f'{(we - woe) * 100:+.0f} pts'
    unclean = (w.get('unclean_runs') or 0) + (wo.get('unclean_runs') or 0)
    notes = [f"runs: {w.get('runs')} with, {wo.get('runs')} without", f"{w.get('mean_seconds')} s vs {wo.get('mean_seconds')} s mean",
             f"${(w.get('cost_usd') or 0) + (wo.get('cost_usd') or 0):.2f}"]
    if unclean:
        notes.append(f'**{unclean} unclean run(s) left out**')
    if b.get('cases_run') != 'all':
        notes.append(f"cases {b['cases_run']}")
    row = (f"| {b['iteration']} | {b['date']} | {b['skill_version']} ({b['commit'] or 'uncommitted'}, {b['skill_hash']}) | "
           f"{b['model']} | {fr(w, 'edit')} | {fr(wo, 'edit')} | {delta} | {fr(w, 'habit')} / {fr(wo, 'habit')} | {'; '.join(notes)} |")
    s = re.sub(r'\| — \| — \| — \| — \| — \| — \| — \| — \| No runs on the current cases yet \|\n', '', s)
    s = re.sub(rf"^\| {b['iteration']} \| \d{{4}}-\d\d-\d\d \|.*\n", '', s, flags=re.M)      # a regrade replaces its row
    s = s.replace('<!-- runlog:end -->', row + '\n<!-- runlog:end -->')
    lines = ['| # | Case | Edit, with skill | Edit, without | Habits, with | Habits, without | Failed (with skill) |',
             '|---|---|---|---|---|---|---|']
    for case in evals['evals']:
        r = b['cases'].get(case['name'], {})
        f = lambda a, kind: fr(r[a], kind) if a in r and r[a][kind]['total'] else ''
        lines.append(f"| {case['id']} | {case['name']} | {f('with_skill', 'edit')} | {f('without_skill', 'edit')} | "
                     f"{f('with_skill', 'habit')} | {f('without_skill', 'habit')} | {', '.join(r.get('with_skill', {}).get('failed_keys', []))} |")
    if b.get('cases_run') != 'all':          # a partial round doesn't replace the per-case table
        open(RESULTS, 'w', encoding='utf-8').write(s)
        return
    s = re.sub(r'<!-- percase:start -->.*?<!-- percase:end -->',
               '<!-- percase:start -->\n' + f"Iteration {b['iteration']}, clean runs only. Failed assertions are listed by key: a number is the case's own assertion (0-based), c0-c1 the common ones.\n\n"
               + '\n'.join(lines) + '\n<!-- percase:end -->', s, flags=re.S)
    open(RESULTS, 'w', encoding='utf-8').write(s)

# ---------- triggers ----------

def run_triggers(args, plugin, it_dir):
    tq = json.load(open(os.path.join(EVALS, 'trigger-queries.json')))
    out = {}
    jobs = [(split, q, k) for split in ('train', 'validation') for q in tq[split] for k in range(3)]
    if args.dry_run:
        print(f'{len(jobs)} trigger runs (each query 3x), e.g.:'); print(' '.join(map(repr, claude_cmd(jobs[0][1]['query'], plugin, args, tools='Skill', max_turns=1))))
        return
    def one(j):
        split, q, k = j
        d = os.path.join(it_dir, 'triggers', f"{split}-{hashlib.sha1(q['query'].encode()).hexdigest()[:8]}-{k}"); os.makedirs(d, exist_ok=True)
        p = subprocess.run(claude_cmd(q['query'], plugin, args, tools='Skill', max_turns=1), cwd=d,
                           env=clean_env(os.path.join(d, 'home'), args.keep_home), capture_output=True, text=True, timeout=300)
        shutil.rmtree(os.path.join(d, 'home'), ignore_errors=True)
        hit = any(c.get('type') == 'tool_use' and c.get('name') == 'Skill' and NAME in json.dumps(c.get('input'))
                  for l in p.stdout.splitlines() if l.startswith('{')
                  for c in ((json.loads(l).get('message') or {}).get('content') or []) if isinstance(c, dict))
        return split, q['query'], q['should_trigger'], hit
    with cf.ThreadPoolExecutor(args.jobs) as ex:
        for split, query, want, hit in ex.map(one, jobs):
            o = out.setdefault((split, query), {'should_trigger': want, 'hits': 0})
            o['hits'] += hit
    res = {}
    for (split, query), o in out.items():
        ok = (o['hits'] / 3 > 0.5) == o['should_trigger']
        res.setdefault(split, []).append({'query': query, **o, 'passed': ok})
    json.dump(res, open(os.path.join(it_dir, 'triggers.json'), 'w'), indent=1)
    for split in res:
        print(f"{split}: {sum(r['passed'] for r in res[split])}/{len(res[split])} pass")
    if not args.no_record:
        record_triggers(res, it_dir, args)
    shutil.rmtree(os.path.dirname(plugin), ignore_errors=True)


def record_triggers(res, it_dir, args):
    """Add a row to RESULTS.md's trigger table and keep the round's figures in evals/results/."""
    n = int(os.path.basename(it_dir).split('-')[-1])
    desc = re.search(r'^description:\s*(.+)$', open(os.path.join(SKILL, 'SKILL.md'), encoding='utf-8').read(), re.M).group(1)
    ver = re.search(r'version:\s*"?([\w.]+)', open(os.path.join(SKILL, 'SKILL.md')).read())
    dh = hashlib.sha256(desc.encode()).hexdigest()[:8]
    f = lambda sp: f"{sum(r['passed'] for r in res.get(sp, []))}/{len(res.get(sp, []))}"
    misses = [f"\"{r['query'][:60]}\" ({r['hits']}/3, {'should' if r['should_trigger'] else 'shouldn' + chr(39) + 't'} trigger)"
              for sp in res for r in res[sp] if not r['passed']]
    note = f"{args.model or 'CLI default'}; " + ('misses: ' + '; '.join(misses) if misses else 'no misses')
    row = f"| {n} | {datetime.date.today().isoformat()} | {ver.group(1) if ver else '?'} (description {dh}) | {f('train')} | {f('validation')} | {note} |"
    s = open(RESULTS, encoding='utf-8').read()
    s = s.replace('| — | — | — | — | — | Not run yet |\n', '')
    s = re.sub(rf"^\| {n} \| \d{{4}}-\d\d-\d\d \| [^|]*\(description .*\n", '', s, flags=re.M)
    s = s.replace('\nEach query runs 3 times;', row + '\n\nEach query runs 3 times;', 1) if row not in s else s
    open(RESULTS, 'w', encoding='utf-8').write(s)
    os.makedirs(os.path.join(EVALS, 'results'), exist_ok=True)
    json.dump({'iteration': n, 'model': args.model or 'CLI default', 'description_hash': dh, 'results': res},
              open(os.path.join(EVALS, 'results', f'triggers-iteration-{n}.json'), 'w'), indent=1)
    print('recorded in', os.path.relpath(RESULTS, ROOT), 'and', f'evals/results/triggers-iteration-{n}.json')


# ---------- main ----------

def git(*a):
    try:
        return subprocess.run(['git', '-C', ROOT, *a], capture_output=True, text=True).stdout.strip() or None
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--skill', help='skill folder under skills/ (default: the only one with evals)')
    ap.add_argument('--cases', help='ids or names, comma-separated (default: all)')
    ap.add_argument('--runs', type=int, help="runs per arm per case (default: each case's 'runs', else 1)")
    ap.add_argument('--retries', type=int, default=1, help='re-run an unclean run this many times (default 1)')
    ap.add_argument('--arms', default='with_skill,without_skill')
    ap.add_argument('-j', '--jobs', type=int, default=2, help='runs at once (default 2)')
    ap.add_argument('--model', help='model for the runs (default: the CLI default; recorded either way)')
    ap.add_argument('--judge-model', help='model for the judge (default: the CLI default)')
    ap.add_argument('--max-turns', type=int, default=60)
    ap.add_argument('--timeout', type=int, default=1200, help='seconds per run')
    ap.add_argument('--iteration', type=int, help='iteration number (default: next free)')
    ap.add_argument('--regrade', type=int, metavar='N', help='grade iteration N again without running anything')
    ap.add_argument('--no-judge', action='store_true', help='script checks only')
    ap.add_argument('--no-record', action='store_true', help="don't write a row to RESULTS.md")
    ap.add_argument('--keep-home', action='store_true', help='run with your real HOME (macOS keychain login)')
    ap.add_argument('--triggers', action='store_true', help='run trigger-queries.json instead of the cases')
    ap.add_argument('--claude', default='claude', help='path to the claude CLI')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    have = skills_with_evals()
    if not args.skill:
        if len(have) != 1:
            ap.error(f"pick one with --skill: {', '.join(have) or 'no skill has evals/evals.json'}")
        args.skill = have[0]
    if args.skill not in have:
        ap.error(f"skills/{args.skill}/evals/evals.json not found; skills with evals: {', '.join(have)}")
    configure(args.skill)

    evals = json.load(open(os.path.join(EVALS, 'evals.json')))
    cases = evals['evals']
    if args.cases:
        want = {x.strip() for x in args.cases.split(',')}
        cases = [c for c in cases if str(c['id']) in want or c['name'] in want]
        if not cases:
            ap.error(f'no case matches {args.cases}')
    arms = args.arms.split(',')
    taken = [int(m.group(1)) for d in (os.listdir(WORKSPACE) if os.path.isdir(WORKSPACE) else [])
             for m in [re.match(r'iteration-(\d+)$', d)] if m]
    n = args.regrade or args.iteration or (max(taken, default=0) + 1)
    it_dir = os.path.join(WORKSPACE, f'iteration-{n}')

    if args.regrade:
        if not os.path.isdir(it_dir):
            ap.error(f'no {it_dir}')
        meta = json.load(open(os.path.join(it_dir, 'meta.json')))
    else:
        if args.dry_run:
            plugin = os.path.join(it_dir, '_plugin', NAME)
            total = sum(len(arms) * (args.runs or c.get('runs', 1)) for c in cases)
            print(f'iteration {n}: {len(cases)} cases x {len(arms)} arms = {total} runs'
                  + ('' if args.no_judge else ' (+ one judge call each)'))
            print('workspace:', it_dir)
            if args.triggers:
                return run_triggers(args, plugin, it_dir)
            c = cases[0]
            print(f"\nexample, case {c['id']} with_skill, cwd = <run>/project holding {c['files'][0]} as demo{os.path.splitext(c['files'][0])[1]}:")
            print('  env HOME=<run>/home CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 \\')
            print('  ' + ' '.join(repr(x) if (' ' in x or not x) else x for x in claude_cmd(c['prompt'], plugin, args, max_turns=args.max_turns)))
            print('\nwithout_skill: the same command without --plugin-dir')
            return
        os.makedirs(it_dir, exist_ok=True)
        plugin = build_plugin(it_dir)
        copies = other_copies(plugin)
        if copies:
            print('warning: other copies of the skill on this machine (runs that read them are marked unclean):')
            for c in copies:
                print('  ', c)
        if args.triggers:
            return run_triggers(args, plugin, it_dir)
        ver = re.search(r'version:\s*"?([\w.]+)', open(os.path.join(SKILL, 'SKILL.md')).read())
        meta = {'iteration': n, 'date': datetime.date.today().isoformat(), 'model': args.model or 'CLI default',
                'judge_model': args.judge_model or 'CLI default', 'skill_version': ver.group(1) if ver else '?',
                'commit': git('rev-parse', '--short', 'HEAD'), 'dirty': bool(git('status', '--porcelain', f'skills/{NAME}')),
                'skill_hash': skill_hash(plugin), 'runs_per_arm': args.runs or 'per case',
                'cases_run': 'all' if not args.cases else args.cases, 'claude_version': subprocess.run(
                    [args.claude, '--version'], capture_output=True, text=True).stdout.strip()}
        json.dump(meta, open(os.path.join(it_dir, 'meta.json'), 'w'), indent=1)
        jobs = [(c, a, k) for c in cases for a in arms for k in range(1, (args.runs or c.get('runs', 1)) + 1)]
        print(f'iteration {n}: {len(jobs)} runs, {args.jobs} at a time -> {it_dir}')
        with cf.ThreadPoolExecutor(args.jobs) as ex:
            futs = {ex.submit(do_run, c, a, k, it_dir, plugin, args): (c, a, k) for c, a, k in jobs}
            for f in cf.as_completed(futs):
                c, a, k = futs[f]
                try:
                    f.result(); print(f"  done  {c['id']} {c['name']} {a} run-{k}")
                except Exception as e:
                    print(f"  ERROR {c['id']} {c['name']} {a} run-{k}: {e}")
        for attempt in range(args.retries):        # re-run what came out unclean
            again = [(c, a, k) for c, a, k in jobs
                     if json.load(open(os.path.join(it_dir, f"{c['id']:02d}-{c['name']}", a, f'run-{k}', 'run.json')))['contamination']]
            if not again:
                break
            print(f're-running {len(again)} unclean run(s)')
            with cf.ThreadPoolExecutor(args.jobs) as ex:
                list(ex.map(lambda j: do_run(j[0], j[1], j[2], it_dir, plugin, args), again))
        shutil.rmtree(os.path.dirname(plugin), ignore_errors=True)

    print('grading…')
    for c in cases:
        for a in arms:
            d = os.path.join(it_dir, f"{c['id']:02d}-{c['name']}", a)
            for r in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                if r.startswith('run-'):
                    g = grade(c, os.path.join(d, r), evals['common_assertions'], args)
                    s = g['summary']
                    print(f"  {c['id']} {c['name']:<22} {a:<14} {r}: edit {s['edit']['passed']}/{s['edit']['total']}, habits {s['habit']['passed']}/{s['habit']['total']}"
                          + ('' if g['clean'] else '  UNCLEAN: ' + '; '.join(g['contamination'])))
    b = benchmark(it_dir, evals, meta)
    for a, t in b['totals'].items():
        print(f"{a}: edit {pct(t['edit']['pass_rate'])} ({t['edit']['passed']}/{t['edit']['total']}), "
              f"habits {pct(t['habit']['pass_rate'])}, {t['unclean_runs']} unclean left out, ${t['cost_usd']:.2f}")
    if not args.no_record:
        update_results(b, evals)
        os.makedirs(os.path.join(EVALS, 'results'), exist_ok=True)
        shutil.copyfile(os.path.join(it_dir, 'benchmark.json'), os.path.join(EVALS, 'results', f"iteration-{b['iteration']}.json"))
        print('recorded in', os.path.relpath(RESULTS, ROOT), 'and', f"evals/results/iteration-{b['iteration']}.json")


if __name__ == '__main__':
    main()
