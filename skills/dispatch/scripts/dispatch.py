"""Hand pieces of a development task to Claude Code, Codex and Antigravity through their subscription CLIs.

  python -B dispatch.py usage [--json]                      remaining usage per host (see usage.py)
  python -B dispatch.py run plan.json [--out DIR] [--dry-run] run the pieces of a plan in parallel
  python -B dispatch.py ledger [--last N]                   past pieces: host, model, effort, tokens, result
  python -B dispatch.py whoami                              which host is running this (the orchestrator)
  python -B dispatch.py review OUT ID "통과"                 record a piece's check result (rewrites the log)
  python -B dispatch.py collect OUT ID [--final-file F]     finish an Orca piece after its worker_done (diff, result)

plan.json:
  {"task": "short name", "decisions": "what the user and the orchestrator decided (goes into every brief)",
   "cwd": "the orchestrator's working folder (default: this process's cwd)",
   "pieces": [{"id": "a", "host": "codex|claude|agy", "model": "...", "effort": "low|medium|high|xhigh",
               "dir": "C:/work/folder", "files": ["src/A.cs", "sql/*.sql"], "read_only": false,
               "needs_db": false, "timeout": 1800, "prompt": "..." | "prompt_file": "piece-a.md",
               "resume": "<worker session id of an earlier run of this piece: follow-up in that session>",
               "billing": "auto|credit|sub", "via": "cli|orca"}]}

Billing (Claude pieces): "auto" (default) runs on the organization's API credit when the credit-first key is registered
and the credit is not marked exhausted, else on the subscription; "credit" refuses the plan when the credit is not
usable; "sub" always uses the subscription. Key, exhaustion state and the clean environment come from the credit-first
skill (~/.claude/skills/credit-first/scripts/credit_run.py, or ACE_CREDIT_RUN). A Claude piece on the credit is a
different account, so a Claude orchestrator may dispatch it without "allow_self". "credit balance is too low" marks
the credit exhausted and an "auto" piece re-runs on the subscription.
Billing (Codex pieces): "credit" = the OpenAI API key of the Codex APIs launcher, decrypted per run (Windows DPAPI, the
launcher's own scheme) and passed only as CODEX_API_KEY to that `codex exec`; never printed or written. The vault path
is in ~/.claude/ace/dispatch/openai.json ({"vault": ".../agents-credentials.dpapi"}) or ACE_OPENAI_VAULT. "auto" =
API first, except when the subscription's weekly window resets within BALANCE_HOURS with more than BALANCE_LEFT % left
(that headroom would be lost): then the subscription. insufficient_quota marks the API exhausted for 24 h
(openai-state.json) and an "auto" piece that changed nothing re-runs on the subscription. Antigravity: subscription only.
Via (where a piece runs): "cli" (default) runs headless here. "orca" (Codex or subscription Claude editing pieces, only
inside Orca) is not run: `run` writes its brief and a before-snapshot and prints the `orca orchestration worker-start`
command; the orchestrator starts it, ends its turn, and after worker_done runs `collect` for the diff and the result.

Base instructions: Codex runs with -c model_instructions_file=<ACE>/skills/dispatch/base/codex.md (replaces Codex's
default instructions; tools and sandbox stay Codex's). Claude keeps its default system prompt plus
--append-system-prompt base/claude-append.md (never --system-prompt). Antigravity's cannot be replaced from the CLI
(rules files and ACP only append), so it gets read-only pieces only.
Context block (every new brief): the plan's decisions, the orchestrator's memory paths (Claude
~/.claude/projects/<key>/memory/MEMORY.md, Codex ~/.codex/memories/ and AGENTS.md), the ACE state file
~/.claude/ace/state/<key>.md inlined (max 3000 chars), the orchestrator's transcript path, and this ACE folder.

Every piece runs headless in its `dir`:
  codex  : codex exec --json --skip-git-repo-check -s workspace-write|read-only -C dir -m model
           -c model_reasoning_effort=... [-c mcp_servers={}] -      (prompt on stdin; the CLI bundled with the
           Codex app first, since the standalone one fails on the app's config.toml; config.toml is never written)
  claude : claude -p --output-format stream-json --verbose --permission-mode acceptEdits|plan --model --effort
           [--strict-mcp-config --mcp-config {"mcpServers":{}}]      (prompt on stdin)
  agy    : agy -p <prompt> --output-format json --mode accept-edits|plan --model --effort --print-timeout
           (personal account: Vertex/Cloud variables are dropped for the run)
Each worker runs in a job object: its whole process tree (MCP servers too) is killed when it ends
or times out. DB MCP servers are off unless the piece says needs_db; Antigravity's live-DB guard is checked only on run_command, so a needs_db piece
is refused there. Codex and Claude keep ACE hooks/ace_db_guard.py when the plugin and its hooks are installed.

Checks before running: the hosts exist, no two pieces share a file (same dir, overlapping globs), the
orchestrator's own host is only used when the plan asks for it. After each piece: the trace (raw.jsonl), the final
message (final.md), changed files and a unified diff (diff.patch) from a before/after snapshot of `dir`, files
changed outside the piece's scope, token usage, duration and timeout. result.json per piece, summary.md for the
run, log.md (request, final answer, changed files, check, worker session id and how to reopen it) copied to
~/.claude/ace/dispatch/<yyyymmdd-hhmm>-<task>.md, and one line per piece in ~/.claude/ace/dispatch/ledger.jsonl.
Exec/print runs are not listed in the hosts' app chat lists, so the log is the record. For project work set
`dir` to the project folder itself (Codex -C), never a temp copy. Nothing here reads credentials.
"""
import argparse
import difflib
import fnmatch
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import usage as U  # noqa: E402

LEDGER = os.path.join(os.path.expanduser('~'), '.claude', 'ace', 'dispatch', 'ledger.jsonl')
SKIP_DIRS = {'.git', '.svn', '.vs', 'bin', 'obj', 'node_modules', '__pycache__', 'packages'}
TEXT_LIMIT = 2 * 1024 * 1024
HOSTS = ('claude', 'codex', 'agy')
CREDIT_DIR = os.environ.get('ACE_CREDIT_RUN') or os.path.join(os.path.expanduser('~'), '.claude', 'skills',
                                                                'credit-first', 'scripts')
_CREDIT = []


def credit():
    """The credit-first module (key lookup, exhaustion state, clean env), or None when it is not installed."""
    if not _CREDIT:
        mod = None
        if os.path.isfile(os.path.join(CREDIT_DIR, 'credit_run.py')):
            if CREDIT_DIR not in sys.path:
                sys.path.insert(0, CREDIT_DIR)
            try:
                import credit_run as mod  # noqa: E402
            except Exception:  # a broken credit-first install must not break dispatch
                mod = None
        _CREDIT.append(mod)
    return _CREDIT[0]


OPENAI_CFG = os.path.join(os.path.expanduser('~'), '.claude', 'ace', 'dispatch', 'openai.json')
OPENAI_STATE = os.path.join(os.path.expanduser('~'), '.claude', 'ace', 'dispatch', 'openai-state.json')
OPENAI_LOW = re.compile(r'insufficient_quota|exceeded your current quota|billing_hard_limit', re.I)
OPENAI_BAD = re.compile(r'invalid_api_key|incorrect api key', re.I)
BALANCE_HOURS, BALANCE_LEFT = 48, 40
# The Codex APIs launcher's DPAPI call (same entropy): base64 in on stdin, base64 out.
_DPAPI = ("Add-Type -AssemblyName System.Security; $b=[Convert]::FromBase64String([Console]::In.ReadToEnd()); "
          "$e=[Text.Encoding]::UTF8.GetBytes('Codex-Agents-API-v1'); "
          "$r=[Security.Cryptography.ProtectedData]::Unprotect($b,$e,"
          "[Security.Cryptography.DataProtectionScope]::CurrentUser); [Console]::Out.Write([Convert]::ToBase64String($r))")
_OPENAI = []


def openai_vault():
    path = os.environ.get('ACE_OPENAI_VAULT')
    if not path:
        try:
            with open(OPENAI_CFG, encoding='utf-8') as f:
                cfg = json.load(f)
            path = cfg.get('vault') if isinstance(cfg, dict) else None
        except (OSError, ValueError):
            path = None
    return path if isinstance(path, str) and os.path.isfile(path) else None


def openai_key():
    """The launcher's OpenAI API key, decrypted once per dispatch process; None when unavailable. Never printed."""
    if not _OPENAI:
        key = None
        vault = openai_vault()
        if vault and os.name == 'nt':
            try:
                import base64
                with open(vault, 'rb') as f:
                    blob = base64.b64encode(f.read()).decode('ascii')
                ps = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'System32', 'WindowsPowerShell',
                                  'v1.0', 'powershell.exe')
                r = subprocess.run([ps, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', _DPAPI], input=blob,
                                   capture_output=True, text=True, timeout=30)
                if r.returncode == 0 and r.stdout.strip():
                    key = (json.loads(base64.b64decode(r.stdout.strip())).get('apiKey') or '').strip() or None
            except Exception:
                key = None
        _OPENAI.append(key)
    return _OPENAI[0]


def openai_state():
    try:
        with open(OPENAI_STATE, encoding='utf-8') as f:
            st = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(st, dict) or not isinstance(st.get('exhausted_at', 0), (int, float)):
        return {}
    return st


def openai_save(st):
    try:
        os.makedirs(os.path.dirname(OPENAI_STATE), exist_ok=True)
        with open(OPENAI_STATE, 'w', encoding='utf-8') as f:
            json.dump(st, f)
    except OSError:
        pass


def codex_balance_prefers_sub():
    """True when the Codex subscription's weekly headroom would expire unused soon."""
    try:
        u = U.codex_usage()
        if u.get('status') != 'ok' or u.get('reached'):
            return False
        as_of = time.mktime(time.strptime(u['as_of'], '%Y-%m-%d %H:%M')) if u.get('as_of') else 0
        if time.time() - as_of > 6 * 3600:  # stale sample: the current headroom is unknown
            return False
        if any(w.get('window') != 'weekly' and w.get('used_percent', 0) >= 90 for w in u.get('windows') or []):
            return False  # the short window is nearly used up: the subscription cannot take the piece now
        for w in u.get('windows') or []:
            if w.get('window') != 'weekly' or not w.get('resets'):
                continue
            left_h = (time.mktime(time.strptime(w['resets'], '%Y-%m-%d %H:%M')) - time.time()) / 3600
            if 0 < left_h <= BALANCE_HOURS and 100 - w['used_percent'] > BALANCE_LEFT and not u.get('reached'):
                return True
    except Exception:
        pass
    return False


def billing_of(piece):
    """'credit', 'sub' or 'credit-unavailable' for a piece. Only Claude pieces can use the API credit."""
    want = str(piece.get('billing') or 'auto').lower()
    if want == 'sub' or piece.get('host') == 'agy':
        return 'credit-unavailable' if want == 'credit' else 'sub'
    if want == 'auto' and str(piece.get('via') or 'cli').lower() == 'orca':
        return 'sub'  # Orca workers run on the signed-in account
    if piece.get('host') == 'codex':
        st = openai_state()
        ok = bool(openai_key()) and not (st.get('exhausted_at') and time.time() - st['exhausted_at'] < 24 * 3600)
        if want == 'credit':
            return 'credit' if ok else 'credit-unavailable'
        return 'credit' if ok and not codex_balance_prefers_sub() else 'sub'
    if piece.get('host') != 'claude':
        return 'sub'
    c = credit()
    key = c.get_key() if c else None
    ok = bool(key) and c.route(key, c.load_state(), 'unchecked') == 'credit'
    if ok:
        return 'credit'
    return 'credit-unavailable' if want == 'credit' else 'sub'


SECRET_RE = re.compile(r'sk-(?:proj-|ant-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}')
CHILD_DROP = ('CODEX_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY',  # API routing of a credit run is set per piece
              'ANTHROPIC_CREDIT_KEY')


def redact(text):
    """Remove the known keys and anything shaped like an API key before it is written anywhere."""
    if not text:
        return text
    known = [k for k in (_OPENAI[0] if _OPENAI else None,) if k]
    c = _CREDIT[0] if _CREDIT else None
    try:
        if c and c.get_key():
            known.append(c.get_key())
    except Exception:
        pass
    for k in known:
        text = text.replace(k, '[REDACTED]')
    return SECRET_RE.sub('[REDACTED]', text)


def child_env(host, base=None):
    """A worker's environment: no inherited keys or API routing, marked with its host (whoami) and as a dispatch
    child, so a worker never re-dispatches or mistakes itself for the orchestrator."""
    env = dict(base if base is not None else os.environ)
    for k in CHILD_DROP:
        env.pop(k, None)
    env['ACE_DISPATCH_SELF'] = host
    env['ACE_DISPATCH_CHILD'] = '1'
    return env


def billing_text(r):
    if r.get('billing') == 'credit' and r.get('host') == 'codex':
        return 'OpenAI API'
    if r.get('billing') == 'credit':
        cost = r.get('cost_usd')
        return '크레딧 $%.2f' % cost if isinstance(cost, (int, float)) else '크레딧'
    spent = r.get('credit_attempt_usd')
    note = r.get('fallback') or ''
    if r.get('host') == 'codex' and r.get('fallback'):
        note += ', API 시도 1회'  # Codex returns no cost figure
    elif isinstance(spent, (int, float)) and spent:
        note += '%s크레딧 시도 $%.2f' % (', ' if note else '', spent)
    return '구독' + (' (%s)' % note if note else '')


# ---------------------------------------------------------------- orchestrator

def whoami():
    """The host whose agent runs this script."""
    if os.environ.get('ACE_DISPATCH_SELF'):
        return os.environ['ACE_DISPATCH_SELF']
    if os.environ.get('CLAUDECODE') or os.environ.get('CLAUDE_CODE_ENTRYPOINT'):
        return 'claude'
    if any(k.startswith('CODEX_') for k in os.environ):
        return 'codex'
    if any(k.startswith(('ANTIGRAVITY_', 'AGY_')) and k != 'AGY_ADC_AUTH' for k in os.environ):
        return 'agy'
    return 'unknown'


# ---------------------------------------------------------------- snapshot / diff

EXCLUDE = []  # run folders (--out) inside a piece's dir: dispatch's own files, never a worker's change


def snapshot(root):
    snap = {}
    skip = [os.path.normcase(os.path.abspath(x)) for x in EXCLUDE]
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS
                  and os.path.normcase(os.path.abspath(os.path.join(dp, d))) not in skip]
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root).replace('\\', '/')
            try:
                st = os.stat(p)
                with open(p, 'rb') as f:
                    data = f.read() if st.st_size <= TEXT_LIMIT else b''
            except OSError:
                continue
            snap[rel] = (hashlib.sha1(data).hexdigest() if data or st.st_size == 0
                         else 'big:%d:%d' % (st.st_size, st.st_mtime_ns),
                         data if b'\0' not in data[:4096] else None)
    return snap


def _lines(b):
    if b is None:
        return []
    for enc in ('utf-8-sig', 'cp949', 'latin-1'):
        try:
            return b.decode(enc).splitlines(keepends=True)
        except UnicodeDecodeError:
            continue
    return []


def compare(before, after):
    changed, patch = [], []
    for rel in sorted(set(before) | set(after)):
        b, a = before.get(rel), after.get(rel)
        if b and a and b[0] == a[0]:
            continue
        kind = 'added' if not b else 'deleted' if not a else 'modified'
        changed.append({'file': rel, 'change': kind,
                        'patch': ''.join(difflib.unified_diff(_lines(b[1] if b else b''), _lines(a[1] if a else b''),
                                                              'a/' + rel, 'b/' + rel))})
    return changed


def in_scope(rel, globs):
    rel = rel.replace('\\', '/')
    return any(fnmatch.fnmatch(rel, g.replace('\\', '/').lstrip('./')) for g in globs)


# ---------------------------------------------------------------- hosts

ACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # the plugin folder this script runs from
BASE_CODEX = os.path.join(os.path.dirname(HERE), 'base', 'codex.md')
BASE_CLAUDE_APPEND = os.path.join(os.path.dirname(HERE), 'base', 'claude-append.md')


def build(piece, prompt):
    """(cmd, stdin_text, env) for a piece. `resume` = the worker's own earlier session id (follow-up)."""
    host, model, effort = piece['host'], piece.get('model'), piece.get('effort')
    ro, db, d, again = piece.get('read_only'), piece.get('needs_db'), piece['dir'], piece.get('resume')
    if host == 'codex':
        # Codex's default instructions are replaced by the ACE worker file; tools and sandbox stay Codex's.
        base = ['-c', "model_instructions_file='%s'" % BASE_CODEX.replace('\\', '/')]
        sandbox = 'read-only' if ro else 'workspace-write'
        if again:  # `exec resume` has no -s/-C: sandbox by config, folder by the process cwd
            cmd = [U.find_codex(), 'exec', 'resume', '--json', '--skip-git-repo-check',
                   '-c', 'sandbox_mode="%s"' % sandbox] + base
        else:
            cmd = [U.find_codex(), 'exec', '--json', '--skip-git-repo-check', '-s', sandbox, '-C', d] + base
        if model:
            cmd += ['-m', model]
        if effort:
            cmd += ['-c', 'model_reasoning_effort="%s"' % effort]
        if not db:
            cmd += ['-c', 'mcp_servers={}']
        env = child_env('codex')
        if piece.get('_billing') == 'credit':
            env['CODEX_API_KEY'] = openai_key()  # this run only; the ChatGPT login stays untouched
        return cmd + ([again] if again else []) + ['-'], prompt, env
    if host == 'claude':
        # Claude keeps its default system prompt; only the rules a worker would otherwise miss are appended.
        with open(BASE_CLAUDE_APPEND, encoding='utf-8') as f:
            append = f.read().strip()
        cmd = [U.find_claude(), '-p', '--output-format', 'stream-json', '--verbose',
               '--permission-mode', 'plan' if ro else 'acceptEdits', '--add-dir', d, '--add-dir', ACE_ROOT,
               '--append-system-prompt', append]
        for extra in sorted(set((piece.get('_ctx') or {}).get('dirs') or [])):
            cmd += ['--add-dir', extra]  # read the orchestrator's memory and transcript
        if again:
            cmd += ['--resume', again]
        cmd += ['--allowedTools', 'Read,Glob,Grep' if ro else 'Read,Write,Edit,Glob,Grep,Bash,PowerShell,Skill']
        if model:
            cmd += ['--model', model]
        if effort:
            cmd += ['--effort', effort]
        if not db:
            cmd += ['--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}']
        if piece.get('_billing') == 'credit':
            c = credit()
            env = child_env('claude', c.clean_env(None))
            env['ANTHROPIC_API_KEY'] = c.get_key()  # billed to the key; CREDIT_FIRST_CHILD keeps it local
            return cmd, prompt, env
        return cmd, prompt, child_env('claude', U.claude_env())  # the signed-in subscription, no inherited key
    if host == 'agy':
        cmd = [U.find_agy(), '-p', prompt, '--output-format', 'json', '--mode', 'plan' if ro else 'accept-edits',
               '--print-timeout', '%ds' % int(piece.get('timeout') or 1800)]
        if again:
            cmd += ['--conversation', again]
        if model:
            cmd += ['--model', model]
        if effort:
            cmd += ['--effort', effort]
        return cmd, None, child_env('agy', U.agy_env())
    raise ValueError('unknown host ' + host)


def session_id(host, stdout):
    """The worker's own session id: Codex thread.started, Claude system/init, Antigravity conversation_id."""
    key = {'codex': 'thread_id', 'claude': 'session_id', 'agy': 'conversation_id'}[host]
    for line in stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get(key) and (host != 'codex' or d.get('type') == 'thread.started'):
            return d[key]
    return None


def resume_cmd(host, sid, d):
    """How to reopen the worker's session. Exec/print runs are not listed in the hosts' app chat lists."""
    if not sid:
        return ''
    if host == 'codex':
        return 'codex resume %s -C "%s"' % (sid, d)
    return 'cd "%s" && %s %s' % (d, 'claude --resume' if host == 'claude' else 'agy --conversation', sid)


def parse(host, stdout):
    """(final_message, usage dict, model actually used, error)."""
    final, usage, model, err = '', {}, None, ''
    if host == 'agy':
        try:
            d = json.loads(stdout.strip().splitlines()[-1] if stdout.strip() else '{}')
        except ValueError:
            return '', {}, None, 'no JSON result'
        u = d.get('usage') or {}
        usage = {'input': u.get('input_tokens', 0), 'output': u.get('output_tokens', 0),
                 'thinking': u.get('thinking_tokens', 0), 'cache_read': u.get('cache_read_tokens', 0),
                 'total': u.get('total_tokens', 0)}
        if not d:
            err = 'no JSON result (agy did not answer)'
        elif d.get('status') != 'SUCCESS':
            err = 'status %s' % d.get('status')
        return d.get('response', ''), usage, d.get('model'), err
    tot = {'input': 0, 'output': 0, 'cache_read': 0, 'cache_write': 0}
    for line in stdout.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        t = d.get('type')
        if host == 'codex':
            if t == 'item.completed' and (d.get('item') or {}).get('type') == 'agent_message':
                final = d['item'].get('text', '')
            elif t == 'turn.completed':
                u = d.get('usage') or {}  # Codex input_tokens already includes the cached part
                tot['input'] += u.get('input_tokens', 0) - u.get('cached_input_tokens', 0)
                tot['cache_read'] += u.get('cached_input_tokens', 0)
                tot['output'] += u.get('output_tokens', 0) + u.get('reasoning_output_tokens', 0)
            elif t in ('turn.failed', 'error'):
                err = json.dumps(d.get('error') or d, ensure_ascii=False)[:300]
        else:
            if t == 'system' and d.get('subtype') == 'init':
                model = d.get('model')
            elif t == 'result':
                final = d.get('result', '') or final
                u = d.get('usage') or {}
                tot = {'input': u.get('input_tokens', 0), 'output': u.get('output_tokens', 0),
                       'cache_read': u.get('cache_read_input_tokens', 0),
                       'cache_write': u.get('cache_creation_input_tokens', 0)}
                if d.get('modelUsage'):
                    tot['by_model'] = {k: {kk: v.get(kk) for kk in ('inputTokens', 'outputTokens',
                                                                   'cacheReadInputTokens', 'costUSD')}
                                       for k, v in d['modelUsage'].items()}
                if d.get('total_cost_usd') is not None:
                    tot['api_equiv_usd'] = d['total_cost_usd']
                if d.get('is_error'):
                    err = (d.get('result') or d.get('subtype') or 'error')[:300]
    tot['total'] = tot['input'] + tot['output'] + tot['cache_read'] + tot.get('cache_write', 0)
    if not final and not err:
        err = 'no final message'
    return final, tot, model, err


def run_piece(piece, out_dir):
    pdir = os.path.join(out_dir, piece['id'])
    os.makedirs(pdir, exist_ok=True)
    prompt = piece.get('prompt') or open(piece['prompt_file'], encoding='utf-8').read()
    prompt = framing(piece) + prompt
    if piece.get('via') == 'orca':
        return prepare_orca(piece, pdir, prompt)
    with open(os.path.join(pdir, 'prompt.md'), 'w', encoding='utf-8') as f:
        f.write(prompt)
    if piece.get('_billing') == 'credit' and str(piece.get('billing') or 'auto').lower() == 'auto' \
            and billing_of(piece) != 'credit':
        reason = 'API 소진 표시됨' if piece['host'] == 'codex' else '크레딧 소진 표시됨'
        if piece.get('_self') and not piece.get('_allow_self'):
            return finish(piece, pdir, prompt, [], '', '', '', {}, None,
                          '%s: 구독 실행은 오케스트레이터 자신이라 하지 않음 — 여기서 처리하거나 "allow_self"' % reason,
                          1, False, 0, None)
        piece['_billing'], piece['_fallback'] = 'sub', reason
    cmd, stdin_text, env = build(piece, prompt)
    before = snapshot(piece['dir'])
    timeout = int(piece.get('timeout') or 1800)
    t0 = time.time()
    # The worker's whole process tree (its MCP servers too) is killed when the piece ends or times out.
    stdout, stderr, rc, timed_out = U.run_tree(
        cmd, stdin_text, timeout=timeout + 60 + (U.AGY_START if piece['host'] == 'agy' else 0),
        cwd=piece['dir'], env=env)
    stdout, stderr = stdout or '', stderr or ''
    dur = round(time.time() - t0, 1)
    after = snapshot(piece['dir'])
    final, tokens, model_used, err = parse(piece['host'], stdout)
    sid = session_id(piece['host'], stdout)
    if piece.get('_billing') == 'credit':
        fallback = credit_outcome(piece, err or ('exit %s' % rc if rc else ''), stderr, '', tokens, sid, dur, t0)
        others = piece.get('_others') or []
        own = lambda snap: {k: v for k, v in snap.items() if not in_scope(k, others)}  # noqa: E731
        if fallback and own(before) == own(after):  # this worker changed nothing: re-run on the subscription
            piece['_credit_spent'] = (piece.get('_credit_spent') or 0) + (tokens.get('api_equiv_usd') or 0)
            if piece.get('_self') and not piece.get('_allow_self'):
                err = '%s: 구독 재실행은 오케스트레이터 자신이라 하지 않음 — 여기서 처리하거나 "allow_self"' % fallback
                piece['_fallback'] = fallback
            else:
                piece['_billing'], piece['_fallback'] = 'sub', fallback
                return run_piece(piece, out_dir)
    return finish(piece, pdir, prompt, compare(before, after), stdout, stderr, final, tokens, model_used, err, rc,
                  timed_out, dur, sid)


def credit_outcome(piece, err, stderr, final, tokens, sid, dur, t0):
    """Book a credit run in the credit-first ledger and state. Returns the fallback reason for an "auto" piece
    whose credit run failed on the credit itself (exhausted, key rejected), else None."""
    blob = ' '.join((err or '', stderr or '', final or ''))
    auto = str(piece.get('billing') or 'auto').lower() == 'auto'
    if piece['host'] == 'codex':
        st = openai_state()
        if not err:
            if st.get('exhausted_at') and st['exhausted_at'] < t0:
                st.pop('exhausted_at')
                openai_save(st)
            return None
        if OPENAI_LOW.search(blob):
            st['exhausted_at'] = time.time()
            openai_save(st)
            return 'API 잔액 부족' if auto else None
        return 'API 키 거부' if OPENAI_BAD.search(blob) and auto else None
    c = credit()
    try:
        c.ledger_add({'mode': 'credit', 'is_error': bool(err), 'cost_usd': tokens.get('api_equiv_usd'),
                      'usage': {'input_tokens': tokens.get('input'), 'output_tokens': tokens.get('output'),
                                'cache_read_input_tokens': tokens.get('cache_read')},
                      'session_id': sid, 'seconds': dur}, piece['dir'])
    except Exception:
        pass
    try:
        st = c.load_state()
        if not err:
            # a run that started before another piece marked the credit exhausted does not clear that mark
            if st.get('exhausted_at') and st['exhausted_at'] < t0:
                st.pop('exhausted_at')
                c.save_state(st)
            return None
        if c.CREDIT_LOW.search(blob):
            st['exhausted_at'] = time.time()
            c.save_state(st)
    except Exception:
        pass
    reason = None
    if c.CREDIT_LOW.search(blob):
        reason = '크레딧 소진'
    elif c.AUTH_BAD.search(blob):
        reason = '키 거부'
    return reason if reason and (piece.get('billing') or 'auto').lower() == 'auto' else None


def finish(piece, pdir, prompt, changed, stdout, stderr, final, tokens, model_used, err, rc, timed_out, dur, sid,
           note=''):
    """Scope check, files, result.json and the ledger line for a finished piece (headless or Orca)."""
    scope = piece.get('files') or []
    # Pieces running at the same time in the same dir: their files are theirs, not this piece's violation.
    others = piece.get('_others') or []
    mine = [c for c in changed if piece.get('read_only') and not in_scope(c['file'], others)
            or not piece.get('read_only') and (in_scope(c['file'], scope) or not in_scope(c['file'], others))]
    patch = note + ''.join(c.pop('patch') for c in mine)  # only this piece's files, not a concurrent piece's
    changed = [{k: v for k, v in c.items() if k != 'patch'} for c in mine]
    outside = [c['file'] for c in changed if piece.get('read_only') or not in_scope(c['file'], scope)]
    stdout, stderr, final, err, prompt = (redact(x) for x in (stdout, stderr, final, err, prompt))
    for name, text in (('raw.jsonl', stdout), ('stderr.txt', stderr), ('final.md', final), ('diff.patch', patch)):
        with open(os.path.join(pdir, name), 'w', encoding='utf-8') as f:
            f.write(text or '')
    status = 'timeout' if timed_out else 'error' if (err or rc) else 'scope-violation' if outside else 'done'
    billing = piece.get('_billing') or 'sub'
    res = {'id': piece['id'], 'task': piece.get('_task'), 'host': piece['host'],
           'model': model_used or piece.get('model') or default_model(piece['host']),
           'effort': piece.get('effort') or default_effort(piece['host'], piece.get('model')), 'dir': piece['dir'], 'files': scope,
           'read_only': bool(piece.get('read_only')), 'status': status, 'returncode': rc, 'timed_out': timed_out,
           'error': err or (stderr.strip()[-300:] if rc else ''), 'duration_s': dur, 'tokens': tokens,
           'billing': billing, 'cost_usd': (tokens or {}).get('api_equiv_usd') if billing == 'credit' else None,
           'fallback': piece.get('_fallback'), 'via': piece.get('via') or 'cli',
           'credit_attempt_usd': piece.get('_credit_spent') if billing != 'credit' else None,
           'changed': changed, 'outside_scope': outside, 'out': pdir, 'review': 'pending',
           'session_id': sid, 'resume': piece.get('_resume') or resume_cmd(piece['host'], sid, piece['dir']),
           'prompt': prompt, 'final': final, 'at': time.strftime('%Y-%m-%d %H:%M:%S')}
    with open(os.path.join(pdir, 'result.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    ledger(res)
    return res


# ---------------------------------------------------------------- Orca transport

def orca_exe():
    return os.environ.get('ORCA_CLI_COMMAND') or 'orca'


def orca_command(piece, spec):
    cmd = [orca_exe(), 'orchestration', 'worker-start', '--environment', 'local', '--worktree', 'current',
           '--agent', piece['host'], '--spec-file', os.path.normpath(spec),
           '--task-title', '%s: %s' % (piece.get('_task') or 'dispatch', piece['id'])]
    if piece.get('model'):
        cmd += ['--model', piece['model']]
        if piece.get('effort'):
            cmd += ['--effort', piece['effort']]
    return shell_line(cmd)


def shell_line(cmd):
    """One line to paste: PowerShell on Windows (call operator, single quotes: no $ expansion), POSIX elsewhere."""
    if os.name == 'nt':
        q = lambda c: "'%s'" % re.sub("(['\u2018\u2019\u201a\u201b])", r'\1\1', c)  # noqa: E731
    else:
        q = lambda c: "'%s'" % c.replace("'", "'\\''")  # noqa: E731
    return ('& ' if os.name == 'nt' else '') + ' '.join(q(c) for c in cmd)


def prepare_orca(piece, pdir, prompt):
    """Brief + before-snapshot for a piece an Orca worker runs. Codex's ACE base instructions cannot be set through
    Orca, so they lead the brief. Hashes of every file and copies of the in-scope files are kept for `collect`."""
    if piece['host'] == 'codex':
        with open(BASE_CODEX, encoding='utf-8') as f:
            prompt = '## Worker rules (ACE)\n\n' + f.read().strip() + '\n\n' + prompt
    prompt += ('\n\nWhen you are done, report with worker_done: what you changed and why, the files, '
               'and how you verified it.\n')
    spec = os.path.join(pdir, 'prompt.md')
    with open(spec, 'w', encoding='utf-8') as f:
        f.write(prompt)
    snap = snapshot(piece['dir'])
    bdir = os.path.join(pdir, 'before')
    for rel, (h, data) in snap.items():
        if data is not None and in_scope(rel, piece.get('files') or []):
            dst = os.path.join(bdir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f:
                f.write(data)
    keep = {k: v for k, v in piece.items() if k != '_ctx'}
    with open(os.path.join(pdir, 'pending.json'), 'w', encoding='utf-8') as f:
        json.dump({'piece': keep, 'hashes': {r: v[0] for r, v in snap.items()}, 'started': time.time()},
                  f, ensure_ascii=False, indent=1)
    command = orca_command(piece, spec)
    res = {'id': piece['id'], 'task': piece.get('_task'), 'host': piece['host'], 'model': piece.get('model'),
           'effort': piece.get('effort'), 'dir': piece['dir'], 'files': piece.get('files') or [],
           'read_only': False, 'status': 'orca-pending', 'returncode': None, 'timed_out': False, 'error': '',
           'duration_s': 0, 'tokens': {}, 'billing': 'sub', 'cost_usd': None, 'fallback': None, 'via': 'orca',
           'changed': [], 'outside_scope': [], 'out': pdir, 'review': 'pending', 'session_id': None,
           'resume': '', 'prompt': prompt, 'final': '', 'orca': command, 'at': time.strftime('%Y-%m-%d %H:%M:%S')}
    with open(os.path.join(pdir, 'result.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return res


class RunLock:
    """One `collect` at a time per run folder: results.json is read and rewritten whole."""

    def __init__(self, out):
        self.path = os.path.join(out, '.collect.lock')

    def __enter__(self):
        for _ in range(600):
            try:
                os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                if time.time() - os.path.getmtime(self.path) > 600:  # a crashed collect
                    os.remove(self.path)
                time.sleep(0.5)
        raise RuntimeError('another collect holds ' + self.path)

    def __exit__(self, *exc):
        try:
            os.remove(self.path)
        except OSError:
            pass


def cmd_collect(a):
    with RunLock(a.out):
        return _collect(a)


def _collect(a):
    """After an Orca worker's worker_done: diff against the before-snapshot, scope check, result, summary, log."""
    pdir = os.path.join(a.out, a.id)
    with open(os.path.join(pdir, 'pending.json'), encoding='utf-8') as f:
        pend = json.load(f)
    with open(os.path.join(pdir, 'result.json'), encoding='utf-8') as f:
        prev = json.load(f)
    if prev.get('status') != 'orca-pending' and not a.again:
        print('%s was already collected (%s); pass --again to collect it once more' % (a.id, prev.get('status')))
        return 2
    piece = pend['piece']
    EXCLUDE.append(a.out)
    if a.dispatch:
        piece['_resume'] = shell_line([orca_exe(), 'orchestration', 'worker-read', '--dispatch', a.dispatch])
    bdir = os.path.join(pdir, 'before')
    before = {}
    for rel, h in pend['hashes'].items():
        src = os.path.join(bdir, rel)
        data = None
        if os.path.isfile(src):
            with open(src, 'rb') as f:
                data = f.read()
        before[rel] = (h, data)
    changed, note = [], ''
    for c in compare(before, snapshot(piece['dir'])):
        b = before.get(c['file'])
        if b and b[1] is None and not in_scope(c['file'], piece.get('files') or []):
            note += '# %s: changed outside the scope (no before copy kept)\n' % c['file']
            c['patch'] = ''
        changed.append(c)
    final = ''
    if a.final_file:
        with open(a.final_file, encoding='utf-8', errors='replace') as f:
            final = f.read()
    with open(os.path.join(pdir, 'prompt.md'), encoding='utf-8') as f:
        prompt = f.read()
    err = 'worker reported failure: %s' % a.failed if a.failed else ''
    res = finish(piece, pdir, prompt, changed, '', '', final, {}, piece.get('model'), err, 1 if err else 0, False,
                 round(time.time() - pend['started'], 1), a.dispatch or None, note)
    path = os.path.join(a.out, 'results.json')
    with open(path, encoding='utf-8') as f:
        results = json.load(f)
    results = [res if r['id'] == a.id else r for r in results]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    task = results[0].get('task') if results else None
    with open(os.path.join(a.out, 'summary.md'), 'w', encoding='utf-8') as f:
        f.write(summary(task, results, whoami()))
    extra = ', outside scope: ' + ', '.join(res['outside_scope']) if res['outside_scope'] else ''
    print('%s: %s, %d files changed%s → %s' % (a.id, res['status'], len(res['changed']), extra,
                                               write_log(a.out, task, results, whoami())))
    return 0 if res['status'] == 'done' else 1


def default_model(host):
    return U.codex_usage().get('model') if host == 'codex' else None


def default_effort(host, model=None):
    if host == 'agy' and model and model.rsplit('-', 1)[-1] in ('low', 'medium', 'high', 'xhigh', 'max'):
        return model.rsplit('-', 1)[-1]  # Antigravity model ids carry the effort (gemini-3.8-flash-low)
    return U.codex_usage().get('effort') if host == 'codex' else None


STATE_MAX = 3000


def project_key(path):
    """Claude Code's folder key under ~/.claude/projects (every non-ASCII-alphanumeric character → '-')."""
    return re.sub(r'[^A-Za-z0-9]', '-', os.path.abspath(path))


def state_key(cwd):
    """hooks/ace_state.py key_of(): the ACE state file of a folder."""
    return hashlib.sha1(os.path.normcase(os.path.abspath(cwd or '.')).encode('utf-8')).hexdigest()[:12]


def orchestrator_context(plan, me):
    """What a worker needs from the orchestrator's conversation: decisions, memory, ACE state, transcript, ACE."""
    home = os.path.expanduser('~')
    cwd = os.path.abspath(plan.get('cwd') or os.getcwd())
    ctx = {'decisions': (plan.get('decisions') or '').strip(), 'memory': [], 'state': '', 'transcript': None,
           'ace': ACE_ROOT, 'cwd': cwd, 'dirs': []}  # dirs: folders a Claude worker must be allowed to read
    if me == 'claude':
        mem = os.path.join(home, '.claude', 'projects', project_key(cwd), 'memory')
        if os.path.isdir(mem):
            ctx['memory'].append(os.path.join(mem, 'MEMORY.md') + ' (index; open the linked files that apply)')
            ctx['dirs'].append(mem)
        sid = os.environ.get('CLAUDE_CODE_SESSION_ID')
        if sid:
            hits = glob.glob(os.path.join(home, '.claude', 'projects', '*', sid + '.jsonl'))
            ctx['transcript'] = hits[0] if hits else None
            if hits:
                ctx['dirs'].append(os.path.dirname(hits[0]))
    elif me == 'codex':
        mem = os.path.join(home, '.codex', 'memories')
        if os.path.isdir(mem):
            ctx['memory'].append(os.path.join(mem, 'memory_summary.md') + ' (start here; MEMORY.md beside it is large: '
                                 'search it, never read it whole)')
            ctx['dirs'].append(mem)
        tid = os.environ.get('CODEX_THREAD_ID') or plan.get('orchestrator_session')
        if tid:
            hits = glob.glob(os.path.join(home, '.codex', 'sessions', '*', '*', '*', '*%s*.jsonl' % tid))
            ctx['transcript'] = hits[0] if hits else None
            if hits:
                ctx['dirs'].append(os.path.dirname(hits[0]))
    agents = os.path.join(home, '.codex', 'AGENTS.md') if me == 'codex' else None
    if agents and os.path.isfile(agents):
        with open(agents, encoding='utf-8', errors='replace') as f:
            ctx['agents_md'] = f.read()[:STATE_MAX]  # inlined: never open ~/.codex itself to a worker
    st = os.path.join(home, '.claude', 'ace', 'state', state_key(cwd) + '.md')
    if os.path.isfile(st):
        with open(st, encoding='utf-8', errors='replace') as f:
            text = f.read()
        ctx['state'] = text if len(text) <= STATE_MAX else text[:STATE_MAX] + '\n…(cut; full file: %s)' % st
    return ctx


def context_block(ctx):
    if not ctx:
        return ''
    out = ['## Context from the orchestrator', '',
           'ACE folder to use (same version as the orchestrator; prefer it over your installed copy): `%s`' % ctx['ace']]
    if ctx['decisions']:
        out += ['', '### Decisions so far (the user and the orchestrator)', '', ctx['decisions']]
    if ctx['memory']:
        out += ['', '### Orchestrator memory: read these before starting', ''] + ['- `%s`' % m for m in ctx['memory']]
    if ctx.get('agents_md'):
        out += ['', '### Orchestrator AGENTS.md', '', ctx['agents_md'].strip()]
    if ctx['state']:
        out += ['', '### ACE work state of `%s`' % ctx['cwd'], '', ctx['state'].strip()]
    if ctx['transcript']:
        out += ['', 'Orchestrator transcript (JSONL; search it only when the brief and the notes above leave a '
                    'question open, never read it whole): `%s`' % ctx['transcript']]
    return '\n'.join(out) + '\n\n'


def framing(piece):
    scope = ', '.join(piece.get('files') or []) or '(none)'
    lines = ['[dispatch piece %s] Work only in this folder: %s' % (piece['id'], piece['dir'])]
    if piece.get('read_only'):
        lines.append('This piece is read-only: change no files; answer in your final message.')
    else:
        lines.append('Change only these files: %s. Other files belong to other workers; leave them alone.' % scope)
    lines.append('Never write to a database (no INSERT/UPDATE/DELETE/ALTER/CREATE/EXEC on a server). '
                 'Do not commit, push or switch branches. End with a short summary of what you changed and why.')
    lines.append('Write your final message in Korean (code, paths and identifiers stay as they are).')
    head = '\n'.join(lines) + '\n\n'
    if piece.get('resume'):  # follow-up in the worker's own session: it already has the context
        return head
    return head + context_block(piece.get('_ctx'))


def ledger(res):
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        row = {k: res[k] for k in ('at', 'task', 'id', 'host', 'model', 'effort', 'status', 'duration_s', 'tokens',
                                   'session_id', 'resume',
                                   'dir', 'files', 'out')}
        row.update({k: res.get(k) for k in ('billing', 'cost_usd', 'fallback', 'via')})
        row['changed'] = len(res['changed'])
        with open(LEDGER, 'a', encoding='utf-8') as f:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    except OSError:
        pass


# ---------------------------------------------------------------- plan

def validate(plan, me):
    problems = []
    pieces = plan.get('pieces') or []
    ids = [p.get('id') for p in pieces]
    if not pieces:
        problems.append('no pieces')
    if len(set(ids)) != len(ids) or None in ids:
        problems.append('every piece needs a unique id')
    for p in pieces:
        h = p.get('host')
        if h not in HOSTS:
            problems.append('%s: host must be one of %s' % (p.get('id'), ', '.join(HOSTS)))
            continue
        bill = p.get('_billing') or billing_of(p)
        if str(p.get('billing') or 'auto').lower() not in ('auto', 'credit', 'sub'):
            problems.append('%s: billing must be auto, credit or sub' % p['id'])
        if bill == 'credit-unavailable':
            problems.append('%s: billing "credit" is not possible here (only Claude pieces, with a registered key '
                            'and credit not marked exhausted: credit_run.py status); use "auto" or "sub"' % p['id'])
        if h == me and not plan.get('allow_self') and bill != 'credit':
            problems.append('%s: %s is the orchestrator itself; do it here, set "allow_self": true, or bill it '
                            'to the API credit' % (p['id'], h))
        via = p.get('via') or 'cli'
        if via not in ('cli', 'orca'):
            problems.append('%s: via must be cli or orca' % p['id'])
        if via == 'orca':
            if h not in ('claude', 'codex'):
                problems.append('%s: via orca takes codex or claude pieces (Antigravity stays headless, read-only)'
                                % p['id'])
            if p.get('read_only'):
                problems.append('%s: Orca cannot enforce read-only; run read-only pieces via cli' % p['id'])
            if bill == 'credit':
                problems.append('%s: Orca workers sign in with an account, not the API key; bill it "sub" or run '
                                'it via cli' % p['id'])
            if p.get('resume'):
                problems.append('%s: follow up an Orca worker with `orca orchestration send`, not resume' % p['id'])
            if not (os.environ.get('ORCA_CLI_COMMAND') or os.environ.get('ORCA_TERMINAL_HANDLE')):
                problems.append('%s: via orca needs a session started by Orca' % p['id'])
            if os.path.normcase(os.path.abspath(p.get('dir', ''))) != os.path.normcase(os.getcwd()):
                problems.append('%s: an Orca worker starts in the current workspace (%s); set dir to it or run '
                                'the piece via cli' % (p['id'], os.getcwd()))
        if not os.path.isdir(p.get('dir', '')):
            problems.append('%s: dir does not exist: %s' % (p['id'], p.get('dir')))
        if not (p.get('prompt') or p.get('prompt_file')):
            problems.append('%s: prompt or prompt_file is required' % p['id'])
        if not p.get('read_only') and not p.get('files'):
            problems.append('%s: an editing piece needs its file scope ("files")' % p['id'])
        if h == 'agy' and p.get('needs_db'):
            problems.append('%s: Antigravity live-DB guard not checked on MCP tools; give DB pieces to codex or claude' % p['id'])
        if h == 'agy' and not p.get('read_only'):
            problems.append('%s: Antigravity takes read-only pieces only (its base instructions cannot be '
                            'replaced); give edits to codex or claude' % p['id'])
        exe = {'claude': U.find_claude, 'codex': U.find_codex, 'agy': U.find_agy}[h]()
        if not exe:
            problems.append('%s: %s CLI not found' % (p['id'], h))
    edits = [p for p in pieces if not p.get('read_only') and p.get('files')]
    for i, a in enumerate(edits):
        for b in edits[i + 1:]:
            if os.path.normcase(os.path.abspath(a['dir'])) != os.path.normcase(os.path.abspath(b['dir'])):
                continue
            for ga in a['files']:
                for gb in b['files']:
                    if ga == gb or fnmatch.fnmatch(ga, gb) or fnmatch.fnmatch(gb, ga):
                        problems.append('%s and %s both edit %s' % (a['id'], b['id'], ga if ga == gb else ga + ' / ' + gb))
    return problems


def tok(t):
    if not t:
        return '-'
    s = '%s (in %s / out %s' % (f"{t.get('total', 0):,}", f"{t.get('input', 0):,}", f"{t.get('output', 0):,}")
    if t.get('thinking'):
        s += ' / think %s' % f"{t['thinking']:,}"
    if t.get('cache_read'):
        s += ' / cache %s' % f"{t['cache_read']:,}"
    return s + ')'


def summary(task, results, me):
    head = ['# dispatch: %s' % (task or ''), '', '오케스트레이터: %s' % me, '',
            '| 조각 | 호스트 | 모델 | 추론 | 결제 | 결과 | 변경 파일 | 범위 밖 | 토큰 | 시간(s) | 검사 | 세션 |',
            '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for r in results:
        head.append('| %s | %s%s | %s | %s | %s | %s | %d | %s | %s | %s | %s | %s |' % (
            r['id'], r['host'], ' (orca)' if r.get('via') == 'orca' else '', r['model'] or '(기본)',
            r['effort'] or '(기본)', billing_text(r), r['status'], len(r['changed']),
            ', '.join(r['outside_scope']) or '-', tok(r['tokens']), r['duration_s'], r['review'],
            r.get('session_id') or '-'))
    for r in results:
        if r['error']:
            head.append('\n- %s 오류: %s' % (r['id'], r['error']))
    pending = [r for r in results if r['status'] == 'orca-pending']
    if pending:
        head.append('\nOrca 워커로 시작할 조각 (한 셸 명령으로 함께 시작 → 턴 종료 → worker_done 후 collect):\n')
        head += ['- %s: `%s`' % (r['id'], r.get('orca')) for r in pending]
    return '\n'.join(head) + '\n'


LOG_DIR = os.path.dirname(LEDGER)


def log_text(out, task, results, me):
    lines = [summary(task, results, me), '실행 폴더: `%s`' % out, '']
    for r in results:
        lines += ['## %s — %s / %s / %s → %s' % (r['id'], r['host'], r['model'] or '(기본)', r['effort'] or '(기본)',
                                                 r['status']), '',
                  '- 폴더: `%s`' % r['dir'],
                  '- 범위: %s' % (', '.join(r['files']) or '(읽기 전용)'),
                  '- 세션: `%s`' % (r.get('session_id') or '-'),
                  '- 다시 열기: `%s`' % (r.get('resume') or '-'),
                  '- 변경 파일: %s' % (', '.join('%s (%s)' % (c['file'], c['change']) for c in r['changed']) or '없음'),
                  '- 범위 밖: %s' % (', '.join(r['outside_scope']) or '없음'),
                  '- 결제: %s' % billing_text(r),
                  '- 토큰: %s, 시간 %ss' % (tok(r['tokens']), r['duration_s']),
                  '- 검사: %s' % r['review'], '']
        if r.get('error'):
            lines += ['- 오류: %s' % r['error'], '']
        lines += ['### 요청', '', '```text', (r.get('prompt') or '').strip(), '```', '',
                  '### 최종 답변', '', (r.get('final') or '(없음)').strip(), '']
    return '\n'.join(lines) + '\n'


def write_log(out, task, results, me):
    """One readable Markdown file per dispatch, in the run folder and in ~/.claude/ace/dispatch/:
    exec/print runs do not show up in the hosts' app chat lists."""
    text = log_text(out, task, results, me)
    with open(os.path.join(out, 'log.md'), 'w', encoding='utf-8') as f:
        f.write(text)
    ref = os.path.join(out, '.log_copy')
    copy = None
    if os.path.isfile(ref):
        with open(ref, encoding='utf-8') as f:
            copy = f.read().strip() or None
    if not copy:
        safe = ''.join(ch if ch.isalnum() or ch in '-_' else '-' for ch in (task or 'task'))[:40].strip('-')
        copy = os.path.join(LOG_DIR, '%s-%s.md' % (time.strftime('%Y%m%d-%H%M'), safe or 'task'))
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(copy, 'w', encoding='utf-8') as f:
            f.write(text)
        with open(ref, 'w', encoding='utf-8') as f:
            f.write(copy)
        return copy
    except OSError:
        return os.path.join(out, 'log.md')


def cmd_review(a):
    """Record the orchestrator's check result for a piece, then rewrite summary.md and the log."""
    path = os.path.join(a.out, 'results.json')
    with open(path, encoding='utf-8') as f:
        results = json.load(f)
    hit = [r for r in results if r['id'] == a.id]
    if not hit:
        print('no piece %s in %s' % (a.id, path))
        return 2
    hit[0]['review'] = a.status
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, a.id, 'result.json'), 'w', encoding='utf-8') as f:
        json.dump(hit[0], f, ensure_ascii=False, indent=1)
    task = results[0].get('task') if results else None
    with open(os.path.join(a.out, 'summary.md'), 'w', encoding='utf-8') as f:
        f.write(summary(task, results, whoami()))
    print('%s: %s → %s' % (a.id, a.status, write_log(a.out, task, results, whoami())))
    return 0


def cmd_run(a):
    with open(a.plan, encoding='utf-8') as f:
        plan = json.load(f)
    base = os.path.dirname(os.path.abspath(a.plan))
    ctx = orchestrator_context(plan, whoami())
    for p in plan.get('pieces') or []:
        p['_task'] = plan.get('task')
        p['_ctx'] = ctx
        if p.get('prompt_file') and not os.path.isabs(p['prompt_file']):
            p['prompt_file'] = os.path.join(base, p['prompt_file'])
        p['dir'] = os.path.abspath(p.get('dir') or base)
        p['via'] = str(p.get('via') or 'cli').lower()
        p['_billing'] = billing_of(p)
        p['_self'] = p.get('host') == whoami()
        p['_allow_self'] = bool(plan.get('allow_self'))
    for p in plan.get('pieces') or []:
        same = [q for q in plan['pieces'] if q is not p and not q.get('read_only')
                and os.path.normcase(q['dir']) == os.path.normcase(p['dir'])]
        p['_others'] = [g for q in same for g in (q.get('files') or [])]
    me = whoami()
    if os.environ.get('CREDIT_FIRST_CHILD') or os.environ.get('ACE_DISPATCH_CHILD'):
        print('PLAN REFUSED:\n- this is a dispatch/credit-first worker: do the work directly, never re-dispatch')
        return 2
    problems = validate(plan, me)
    if problems:
        print('PLAN REFUSED:\n- ' + '\n- '.join(problems))
        return 2
    if a.dry_run:
        for p in plan['pieces']:
            if p.get('via') == 'orca':
                print('%s [구독, orca]: %s' % (p['id'], orca_command(p, os.path.join('<out>', p['id'], 'prompt.md'))))
                continue
            cmd, stdin_text, _ = build(p, framing(p) + (p.get('prompt') or '<prompt_file>'))
            shown = [c if len(c) < 120 else c[:60] + '…' for c in cmd]
            print('%s [%s, %s]: %s%s' % (p['id'], billing_text({'billing': p['_billing'], 'host': p['host']}),
                                         p.get('via') or 'cli',
                                         ' '.join(shown), '  < stdin' if stdin_text else ''))
        print('\n--- context block (new briefs) ---\n' + context_block(ctx))
        return 0
    out = a.out or os.path.join(tempfile.gettempdir(), 'ace-dispatch', time.strftime('%Y%m%d-%H%M%S'))
    os.makedirs(out, exist_ok=True)
    EXCLUDE.append(out)
    print('dispatch: %d pieces → %s' % (len(plan['pieces']), out), flush=True)
    with ThreadPoolExecutor(max(1, min(len(plan['pieces']), a.parallel))) as ex:
        futs = [ex.submit(run_piece, p, out) for p in plan['pieces']]
        results = []
        for fu in futs:
            r = fu.result()
            results.append(r)
            print('  %s %s/%s → %s (%ss, %s)' % (r['id'], r['host'], r['model'], r['status'], r['duration_s'],
                                                tok(r['tokens'])), flush=True)
    text = summary(plan.get('task'), results, me)
    log = write_log(out, plan.get('task'), results, me)
    with open(os.path.join(out, 'summary.md'), 'w', encoding='utf-8') as f:
        f.write(text)
    with open(os.path.join(out, 'results.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    print(text)
    print('log: ' + log)
    return 0 if all(r['status'] in ('done', 'orca-pending') for r in results) else 1


def cmd_ledger(a):
    try:
        with open(LEDGER, encoding='utf-8') as f:
            rows = [json.loads(x) for x in f if x.strip()]
    except OSError:
        print('no ledger yet: ' + LEDGER)
        return 0
    rows = rows[-a.last:]
    print('| 시각 | 작업 | 조각 | 호스트 | 모델 | 추론 | 결제 | 결과 | 변경 | 토큰 | 시간(s) |')
    print('| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |')
    for r in rows:
        print('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            r.get('at'), r.get('task') or '', r.get('id'), r.get('host'), r.get('model') or '(기본)',
            r.get('effort') or '(기본)', billing_text(r), r.get('status'), r.get('changed'), tok(r.get('tokens')), r.get('duration_s')))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('usage')
    s.add_argument('--json', action='store_true')
    s.add_argument('--host', default='claude,codex,agy')
    s = sub.add_parser('run')
    s.add_argument('plan')
    s.add_argument('--out')
    s.add_argument('--parallel', type=int, default=4)
    s.add_argument('--dry-run', action='store_true')
    s = sub.add_parser('ledger')
    s.add_argument('--last', type=int, default=30)
    sub.add_parser('whoami')
    s = sub.add_parser('review')
    s.add_argument('out')
    s.add_argument('id')
    s.add_argument('status')
    s = sub.add_parser('collect')
    s.add_argument('out')
    s.add_argument('id')
    s.add_argument('--final-file', required=True, help="the worker's report (worker_done / worker-read output)")
    s.add_argument('--dispatch', help='the Orca dispatch id, for worker-read later')
    s.add_argument('--failed', metavar='REASON', help='the worker reported failure (worker_done says it failed)')
    s.add_argument('--again', action='store_true', help='collect a piece that was already collected')
    a = ap.parse_args(argv)
    if a.cmd == 'usage':
        return U.main((['--json'] if a.json else []) + ['--host', a.host])
    if a.cmd == 'whoami':
        print(whoami())
        return 0
    if a.cmd == 'review':
        return cmd_review(a)
    if a.cmd == 'collect':
        return cmd_collect(a)
    return cmd_run(a) if a.cmd == 'run' else cmd_ledger(a)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main(sys.argv[1:]))
