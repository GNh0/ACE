"""ACE comply: measure whether agents actually follow the ACE rules (idea from ECC skill-comply, MIT).

  python -B comply/run_comply.py [scenario ...] [--host claude|codex|both] [--levels supportive,neutral,competing]
                                 [--model M] [--timeout S] [--out DIR] [--dry-run] [--grade-only DIR]

Each scenario (comply/scenarios/<id>/scenario.json + fixture files) is a real user-style task built from a
lesson. It runs headless in a throwaway copy of the fixtures, once per host and prompt level:
  supportive  "follow the ACE rules" + task
  neutral     the task as the user writes it
  competing   task + pressure to skip reading ("be quick, don't read long docs")
The output files are graded deterministically (check_sql items, regexes, functions below) and the tool trace
is searched for evidence (e.g. the skill was loaded). The report lists compliance per host and level, and the
rules that fail under neutral/competing prompts: candidates to move into check_sql or a hook.

Safety: DB MCP servers are turned off (Claude --strict-mcp-config with none, Codex -c mcp_servers={}), work
happens in a temp copy, Codex runs with -s workspace-write. Nothing touches a database or the repo.
"""
import argparse
import datetime
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'skills', 'sql', 'scripts'))


def example_profile():
    """Scenario fixtures use the made-up example profile, so grade with it, not with the user's local profile."""
    d = tempfile.mkdtemp(prefix='ace_example_profile_')
    for name in ('profile', 'designer'):
        shutil.copy(os.path.join(ROOT, 'skills', 'erp', 'data', name + '.example.json'), os.path.join(d, name + '.json'))
    os.environ['ACE_PROFILE_DIR'] = d


example_profile()
import check_sql  # noqa: E402

LEVELS = {
    'supportive': 'ACE 스킬(work·sql·erp 중 맞는 것)을 읽고 그 규칙대로 작업해. {task}',
    'neutral': '{task}',
    'competing': '{task} 급하니까 문서 길게 읽지 말고 바로 고쳐줘.',
}


# ---------------------------------------------------------------- hosts

def find_claude():
    if os.environ.get('ACE_CLAUDE'):
        return os.environ['ACE_CLAUDE']
    exe = shutil.which('claude')
    if exe:
        return exe
    hits = sorted(glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\Claude-Data\*\claude-code\*\*\claude.exe')),
                  key=os.path.getmtime)
    return hits[-1] if hits else None


def find_codex():
    """Prefer the CLI bundled with the Codex app: the standalone one can lag behind the app's config.toml."""
    if os.environ.get('ACE_CODEX'):
        return os.environ['ACE_CODEX']
    hits = sorted(glob.glob(r'C:\Program Files\WindowsApps\OpenAI.Codex_*\app\resources\codex.exe'),
                  key=os.path.getmtime)
    return hits[-1] if hits else shutil.which('codex')


def run_claude(exe, work, prompt, model, timeout):
    cmd = [exe, '-p', '--output-format', 'stream-json', '--verbose',
           '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}',
           '--permission-mode', 'acceptEdits',
           '--allowedTools', 'Read,Write,Edit,Glob,Grep,Bash,Skill,PowerShell',
           '--add-dir', work]
    if model:
        cmd += ['--model', model]
    return _run(cmd, work, prompt, timeout)


def run_codex(exe, work, prompt, model, timeout):
    cmd = [exe, 'exec', '--json', '--skip-git-repo-check', '-s', 'workspace-write', '-C', work,
           '-c', 'mcp_servers={}']
    if model:
        cmd += ['-m', model]
    return _run(cmd + ['-'], work, prompt, timeout)


def _run(cmd, cwd, prompt, timeout):
    try:
        p = subprocess.run(cmd, input=prompt, capture_output=True, encoding='utf-8', errors='replace',
                           timeout=timeout, cwd=cwd)
        return p.stdout, p.returncode, False
    except subprocess.TimeoutExpired as e:
        out = e.stdout or b''
        return (out.decode('utf-8', 'replace') if isinstance(out, bytes) else out), -1, True


# ---------------------------------------------------------------- trace

def trace_events(stdout):
    """[(kind, text)] from Claude stream-json or Codex exec --json."""
    ev = []
    for line in stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get('type') == 'assistant':  # Claude
            for c in d.get('message', {}).get('content') or []:
                if c.get('type') == 'tool_use':
                    ev.append(('tool:' + c.get('name', ''), json.dumps(c.get('input'), ensure_ascii=False)))
                elif c.get('type') == 'text':
                    ev.append(('text', c.get('text', '')))
        elif d.get('type') == 'item.completed':  # Codex
            it = d.get('item') or {}
            t = it.get('type', '')
            if t == 'agent_message':
                ev.append(('text', it.get('text', '')))
            elif t in ('command_execution', 'file_change', 'mcp_tool_call', 'web_search'):
                ev.append(('tool:' + t, json.dumps({k: v for k, v in it.items()
                                                     if k not in ('aggregated_output',)}, ensure_ascii=False)))
    return ev


def run_error(stdout, events):
    """A run that never reached the model (login, API error): not graded."""
    if 'Not logged in' in stdout or 'authentication_failed' in stdout:
        return 'not logged in (run the host CLI once and sign in)'
    if not events:
        for line in reversed(stdout.splitlines()):
            if '"is_error":true' in line or '"type":"error"' in line or '"type":"turn.failed"' in line:
                return 'host error: ' + line[:160]
        return 'no output'
    return ''


# ---------------------------------------------------------------- checks

def first_write_pos(up):
    m = re.search(r'\b(INSERT\s+INTO\s+(?!@)\w|UPDATE\s+(?!@)\w|DELETE\s+(?!@)\w|DELETE\s+FROM\s+(?!@)\w)', up)
    return m.start() if m else None


def validations_first(sql):
    """Every IF EXISTS … RAISERROR inside the NEW/EDIT part appears before the first real-table write."""
    up = check_sql.mask(sql).upper()
    w = first_write_pos(up)
    checks = [m.start() for m in re.finditer(r'\bIF\s+(NOT\s+)?EXISTS\b', up)
              if re.search(r'RAISERROR|THROW', up[m.start():m.start() + 3000])]
    if not checks:
        return False, 'no IF EXISTS validation left'
    late = [c for c in checks if w is not None and c > w]
    return (not late), ('%d check(s) after the first write' % len(late) if late else '')


def precheck_uses_staging(sql):
    """The over-quantity check before the write reads the staging table (this save's rows)."""
    up = check_sql.mask(sql).upper()
    w = first_write_pos(up)
    head = up[:w] if w is not None else up
    for m in re.finditer(r'\bIF\s+(NOT\s+)?EXISTS\b', head):
        block = head[m.start():m.start() + 4000]
        if re.search(r'@TMP\w*', block) and re.search(r'\bSUM\s*\(', block) and re.search(r'RAISERROR|THROW', block):
            return True, ''
    return False, 'no pre-write SUM check over @TMP rows'


FUNCS = {'validations_first': validations_first, 'precheck_uses_staging': precheck_uses_staging}


def grade(scn, sdir, work, events):
    res = []
    for c in scn['checks']:
        ok, note = False, ''
        path = os.path.join(work, c['file']) if c.get('file') else None
        text = check_sql.read_sql(path) if path and os.path.isfile(path) else None
        if c['type'] == 'trace':
            ok = any(re.search(c['pattern'], t, re.I) for _, t in events)
        elif text is None:
            note = 'file missing'
        elif c['type'] == 'file_changed':
            ok = text.strip() != check_sql.read_sql(os.path.join(sdir, c['file'])).strip()
        elif c['type'] == 'regex_absent':
            m = re.search(c['pattern'], check_sql.mask(text).upper(), re.I)
            ok, note = (m is None), (m.group(0)[:60] if m else '')
        elif c['type'] == 'regex_present':
            ok = re.search(c['pattern'], check_sql.mask(text).upper(), re.I) is not None
        elif c['type'] == 'func':
            ok, note = FUNCS[c['name']](text)
        elif c['type'] == 'sql_check':
            results, _ = check_sql.run_checks(text, scn.get('caller', 'unknown'))
            fails = [(item, ls) for st, item, ls, _n in results if st == check_sql.FAIL
                     and (c['item'] == '*' or c['item'] in item)]
            ok = not fails
            note = '; '.join('%s %s' % (i, check_sql.fmt_lines(ls, 5)) for i, ls in fails)[:200]
        res.append({'id': c['id'], 'rule': c['rule'], 'ok': ok, 'note': note})
    return res


# ---------------------------------------------------------------- main

def load(ids):
    out = []
    for p in sorted(glob.glob(os.path.join(HERE, 'scenarios', '*', 'scenario.json'))):
        s = json.load(io.open(p, encoding='utf-8'))
        if not ids or s['id'] in ids:
            out.append((s, os.path.dirname(p)))
    return out


def report(rows, out):
    lines = ['# ACE comply report', '', datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), '',
             '| scenario | host | level | passed | failed rules |', '|---|---|---|---|---|']
    weak = {}
    for r in rows:
        if r.get('error'):
            lines.append('| %s | %s | %s | not run | %s |' % (r['scenario'], r['host'], r['level'], r['error']))
            continue
        bad = [g for g in r['grades'] if not g['ok']]
        n = len(r['grades'])
        lines.append('| %s | %s | %s | %d/%d%s | %s |' % (
            r['scenario'], r['host'], r['level'], n - len(bad), n, ' (timeout)' if r['timeout'] else '',
            '<br>'.join('%s%s' % (g['id'], (': ' + g['note']) if g['note'] else '') for g in bad) or '-'))
        if r['level'] != 'supportive':
            for g in bad:
                weak.setdefault((r['scenario'], g['id'], g['rule']), []).append('%s/%s' % (r['host'], r['level']))
    total = sum(len(r['grades']) for r in rows)
    passed = sum(g['ok'] for r in rows for g in r['grades'])
    lines += ['', 'Overall: %d/%d (%.0f%%)' % (passed, total, 100.0 * passed / total if total else 0), '']
    if weak:
        lines += ['## Rules that fail without a reminder', '',
                  'Candidates for check_sql, a hook, or a shorter SKILL.md line:', '']
        lines += ['- %s / %s: %s (%s)' % (s, i, rule, ', '.join(w)) for (s, i, rule), w in sorted(weak.items())]
    path = os.path.join(out, 'report.md')
    io.open(path, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    return path, passed, total


def main(argv):
    ap = argparse.ArgumentParser(description='ACE comply')
    ap.add_argument('scenarios', nargs='*')
    ap.add_argument('--host', default='both', choices=['claude', 'codex', 'both'])
    ap.add_argument('--levels', default='supportive,neutral,competing')
    ap.add_argument('--model')
    ap.add_argument('--timeout', type=int, default=900)
    ap.add_argument('--out')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--grade-only', help='re-grade an earlier --out folder without running agents')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    scns = load(a.scenarios)
    hosts = ['claude', 'codex'] if a.host == 'both' else [a.host]
    levels = [x.strip() for x in a.levels.split(',') if x.strip()]
    out = a.grade_only or a.out or os.path.join(tempfile.gettempdir(), 'ace-comply',
                                                datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
    exes = {'claude': find_claude(), 'codex': find_codex()}
    print('scenarios: %s\nhosts: %s\nlevels: %s\nout: %s' % (
        ', '.join(s['id'] for s, _ in scns), ', '.join('%s=%s' % (h, exes[h]) for h in hosts), ', '.join(levels), out))
    if a.dry_run:
        for s, _ in scns:
            for lv in levels:
                print('\n[%s/%s] %s' % (s['id'], lv, LEVELS[lv].format(task=s['task'])))
        return 0
    rows = []
    for s, sdir in scns:
        for h in hosts:
            for lv in levels:
                run_dir = os.path.join(out, s['id'], '%s-%s' % (h, lv))
                work = os.path.join(run_dir, 'work')
                if a.grade_only:
                    trace = io.open(os.path.join(run_dir, 'trace.jsonl'), encoding='utf-8').read()
                    to = os.path.isfile(os.path.join(run_dir, 'TIMEOUT'))
                else:
                    if not exes[h]:
                        print('skip %s: %s not found' % (s['id'], h))
                        continue
                    shutil.rmtree(run_dir, ignore_errors=True)
                    shutil.copytree(sdir, work, ignore=shutil.ignore_patterns('scenario.json'))
                    prompt = LEVELS[lv].format(task=s['task'])
                    print('run %s %s %s ...' % (s['id'], h, lv), flush=True)
                    fn = run_claude if h == 'claude' else run_codex
                    trace, rc, to = fn(exes[h], work, prompt, a.model, a.timeout)
                    io.open(os.path.join(run_dir, 'trace.jsonl'), 'w', encoding='utf-8').write(trace)
                    if to:
                        io.open(os.path.join(run_dir, 'TIMEOUT'), 'w').write('')
                events = trace_events(trace)
                err = run_error(trace, events)
                if err:
                    rows.append({'scenario': s['id'], 'host': h, 'level': lv, 'grades': [], 'timeout': to, 'error': err})
                    print('  %s %s %s: ERROR %s' % (s['id'], h, lv, err), flush=True)
                    continue
                g = grade(s, sdir, work, events)
                rows.append({'scenario': s['id'], 'host': h, 'level': lv, 'grades': g, 'timeout': to})
                print('  %s %s %s: %d/%d' % (s['id'], h, lv, sum(x['ok'] for x in g), len(g)), flush=True)
    path, passed, total = report(rows, out)
    print('\nreport: %s\nOverall: %d/%d' % (path, passed, total))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
