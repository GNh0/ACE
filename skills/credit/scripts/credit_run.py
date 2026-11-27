"""Run a Claude Code task on the organization's API credit first, then on the subscription.

  python -B credit_run.py status                 key registered? valid? credit marked exhausted?
  python -B credit_run.py setup [--open]         steps to issue and register a key (opens the Console keys page)
  python -B credit_run.py run --brief <file> [--cwd <dir>] [--model <m>] [--plan] [--no-fallback]
  python -B credit_run.py ledger [--days 30]     spend per mode

Nothing here is personal: the key is read from an environment variable (default ANTHROPIC_CREDIT_KEY, or
"anthropic_key_var" in the local ~/.claude/ace/credit.json; process env, then the Windows user environment) and is
never printed or written anywhere by this script. Without a key every run goes to the subscription and the ACE hint
stays silent, so the plugin is safe to install for anyone. ACE_CREDIT=off turns the credit off.
State and ledger: ~/.claude/ace/credit/ (`ledger` also reads an older ~/.claude/credit-first/ledger.jsonl). `run` starts `claude -p` with that key in a
clean environment (no desktop-app proxy/session variables), so skills, hooks, plugins, CLAUDE.md and memory all
load as usual and the cost is billed to the key's organization. A "credit balance is too low" answer marks the
credit exhausted (retried once a day) and the same task re-runs on the subscription unless --no-fallback.
"""
import argparse
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

HOME = os.path.expanduser('~')
CONFIG = os.path.join(HOME, '.claude', 'ace', 'credit.json')
DATA = os.path.join(HOME, '.claude', 'ace', 'credit')
OLD_DATA = os.path.join(HOME, '.claude', 'credit-first')
LEDGER = os.path.join(DATA, 'ledger.jsonl')
STATE = os.path.join(DATA, 'state.json')


def config():
    """The user's local credit settings (never in the repository); {} when absent or malformed."""
    try:
        with io.open(CONFIG, encoding='utf-8') as f:
            c = json.load(f)
        return c if isinstance(c, dict) else {}
    except (OSError, ValueError):
        return {}


KEY_VAR = str(config().get('anthropic_key_var') or 'ANTHROPIC_CREDIT_KEY')
KEY_VARS = {KEY_VAR, 'ANTHROPIC_CREDIT_KEY'}  # never passed on to a child, whatever its billing
SECRET_RE = re.compile(r'sk-(?:proj-|ant-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}')
CONSOLE_KEYS = 'https://console.anthropic.com/settings/keys'
RETRY_AFTER = 24 * 3600
CREDIT_LOW = re.compile(r'credit balance (is )?too low|insufficient (credit|balance)', re.I)
AUTH_BAD = re.compile(r'invalid (x-)?api[ -]?key|authentication_error|invalid bearer', re.I)
# desktop-app / parent-session variables that would route the child through the app instead of the API key
DROP = re.compile(r'^(CLAUDECODE|CLAUDE_CODE_.*|CLAUDE_AGENT_SDK.*|CLAUDE_PID|CLAUDE_EFFORT|CLAUDE_PREVIEW_.*'
                  r'|ANTHROPIC_BASE_URL|ANTHROPIC_AUTH_TOKEN|ANTHROPIC_API_KEY|USE_LOCAL_OAUTH|USE_STAGING_OAUTH)$', re.I)


def out(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=1) + '\n')


def get_key():
    if os.environ.get('ACE_CREDIT', '').strip().lower() == 'off':
        return None
    k = os.environ.get(KEY_VAR)
    if not k and os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as h:
                k = winreg.QueryValueEx(h, KEY_VAR)[0]
        except OSError:
            k = None
    return (k.strip() or None) if isinstance(k, str) else None


def load_state():
    try:
        with io.open(STATE, encoding='utf-8') as f:
            st = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(st, dict) or not isinstance(st.get('exhausted_at', 0), (int, float)):
        return {}
    return st


def save_state(st):
    os.makedirs(DATA, exist_ok=True)
    with io.open(STATE, 'w', encoding='utf-8') as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def check_key(key):
    """GET /v1/models: valid key without spending credit. Credit itself is only known from a real call."""
    req = urllib.request.Request('https://api.anthropic.com/v1/models?limit=1',
                                 headers={'x-api-key': key, 'anthropic-version': '2023-06-01'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return 'valid' if r.status == 200 else 'http %d' % r.status
    except urllib.error.HTTPError as e:
        return 'invalid' if e.code in (401, 403) else 'http %d' % e.code
    except (urllib.error.URLError, OSError) as e:
        return 'network error: %s' % getattr(e, 'reason', e)


def status():
    key = get_key()
    st = load_state()
    s = {'key': 'missing' if not key else check_key(key), 'key_var': KEY_VAR}
    models = config().get('models')
    if isinstance(models, dict):
        s['models'] = models  # the user's model choice per kind of work (local config)
    if st.get('exhausted_at'):
        s['credit'] = 'exhausted since ' + time.strftime('%Y-%m-%d %H:%M', time.localtime(st['exhausted_at']))
        s['retry_credit_after'] = time.strftime('%Y-%m-%d %H:%M', time.localtime(st['exhausted_at'] + RETRY_AFTER))
    else:
        s['credit'] = 'unknown until a run (no balance API); assumed available'
    s['route'] = route(key, st, s['key'])
    if os.environ.get('CREDIT_FIRST_CHILD'):
        s['route'] = 'here (this is a credit-first child run: do the work directly, never call run)'
    return s


def route(key, st, key_state):
    if not key or key_state == 'invalid':
        return 'subscription (no usable key: run setup)'
    if st.get('exhausted_at') and time.time() - st['exhausted_at'] < RETRY_AFTER:
        return 'subscription (credit exhausted)'
    return 'credit'


def find_claude():
    if os.environ.get('CREDIT_CLAUDE'):
        return os.environ['CREDIT_CLAUDE']
    exe = shutil.which('claude')
    if exe:
        return exe
    pats = [r'%LOCALAPPDATA%\Claude-Data\*\claude-code\*\*\claude.exe', r'%APPDATA%\Claude\claude-code\*\*\claude.exe',
            r'%LOCALAPPDATA%\npm-cache\_npx\*\node_modules\@anthropic-ai\claude-code-win32-x64\claude.exe']
    hits = sorted((h for p in pats for h in glob.glob(os.path.expandvars(p))), key=os.path.getmtime)
    return hits[-1] if hits else None


def clean_env(key=None):
    env = {k: v for k, v in os.environ.items() if not DROP.match(k) and k not in KEY_VARS}
    if key:
        env['ANTHROPIC_API_KEY'] = key
    env['CREDIT_FIRST_CHILD'] = '1'  # the child must do the work itself, never re-dispatch
    env['ACE_DISPATCH_CHILD'] = '1'
    return env


def run_claude(prompt, cwd, model, plan, key, add_dirs=()):
    cmd = [find_claude(), '-p', '--output-format', 'json', '--permission-mode', 'plan' if plan else 'acceptEdits']
    for d in add_dirs or ():
        cmd += ['--add-dir', d]
    if model:
        cmd += ['--model', model]
    t0 = time.time()
    p = subprocess.run(cmd, input=prompt, cwd=cwd, env=clean_env(key), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    raw = (p.stdout or '').strip()
    try:
        data = json.loads(raw.splitlines()[-1]) if raw else {}
    except ValueError:
        data = {}
    text = data.get('result') if isinstance(data.get('result'), str) else ''
    err_text = ' '.join(x for x in (text if data.get('is_error') else '', p.stderr or '',
                                     '' if data else raw) if x)
    return {'mode': 'credit' if key else 'subscription', 'exit': p.returncode, 'is_error': bool(data.get('is_error'))
            or (p.returncode != 0 and not data), 'result': redact(text, key), 'error': redact(err_text[-1500:], key),
            'turns': data.get('num_turns'),
            'cost_usd': data.get('total_cost_usd'), 'usage': data.get('usage'), 'session_id': data.get('session_id'),
            'seconds': round(time.time() - t0, 1)}


def redact(text, key=None):
    """Never hand a key back to the orchestrator: the known key and anything shaped like one become [REDACTED]."""
    if not text:
        return text
    for k in (key, get_key()):
        if k:
            text = text.replace(k, '[REDACTED]')
    return SECRET_RE.sub('[REDACTED]', text)


def ledger_add(r, cwd):
    os.makedirs(DATA, exist_ok=True)
    u = r.get('usage') or {}
    row = {'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'mode': r['mode'], 'ok': not r['is_error'],
           'cost_usd': r.get('cost_usd'), 'input_tokens': u.get('input_tokens'), 'output_tokens': u.get('output_tokens'),
           'cache_read': u.get('cache_read_input_tokens'), 'session_id': r.get('session_id'), 'cwd': cwd,
           'seconds': r.get('seconds')}
    with io.open(LEDGER, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def run(a):
    if os.environ.get('CREDIT_FIRST_CHILD'):
        return out({'error': 'inside a credit-first child run: do the work directly'}) or 2
    prompt = io.open(a.brief, encoding='utf-8-sig').read()
    cwd = os.path.abspath(a.cwd or os.getcwd())
    if not find_claude():
        return out({'error': 'claude CLI not found (set CREDIT_CLAUDE)'}) or 2
    key, st = get_key(), load_state()
    tried = []
    if route(key, st, 'unchecked') == 'credit':
        r = run_claude(prompt, cwd, a.model, a.plan, key, a.add_dir)
        ledger_add(r, cwd)
        tried.append(r)
        blob = r['error'] + ' ' + (r['result'] if r['is_error'] else '')
        if not r['is_error']:
            if st.pop('exhausted_at', None):
                save_state(st)
            return out({'route': 'credit', 'result': r}) or 0
        early = (r.get('turns') or 0) <= 1  # an API refusal comes on the first call, before any tool ran
        if CREDIT_LOW.search(blob) and early:
            st['exhausted_at'] = time.time()
            save_state(st)
            reason = 'credit exhausted'
        elif AUTH_BAD.search(blob) and early:
            reason = 'key rejected (run setup)'
        else:
            return out({'route': 'credit', 'failed': True, 'result': r,
                        'note': 'failed for another reason; not re-run on the subscription'}) or 1
        if a.no_fallback:
            return out({'route': 'credit', 'failed': True, 'reason': reason, 'result': r}) or 3
    else:
        reason = route(key, st, 'unchecked')
    r = run_claude(prompt, cwd, a.model, a.plan, None, a.add_dir)
    ledger_add(r, cwd)
    out({'route': 'subscription', 'reason': reason, 'credit_attempt': tried[0] if tried else None, 'result': r})
    return 0 if not r['is_error'] else 1


def setup(a):
    steps = [
        '1. 사용자가 Claude Console(%s)에서 크레딧이 들어온 조직을 고르고 API 키를 직접 만든다. '
        'Claude는 키를 만들거나 보거나 입력하지 않는다.' % CONSOLE_KEYS,
        '2. 사용자가 자기 터미널에서 register_key.ps1을 실행해 키를 붙여 넣는다(입력은 가려지고, Windows 사용자 '
        '환경 변수 %s에 저장된다). Windows가 아니면 셸 프로필에 같은 이름의 환경 변수를 직접 둔다.' % KEY_VAR,
        '3. python -B credit_run.py status 로 key=valid 를 확인한다.',
    ]
    if a.open and os.name == 'nt':
        os.startfile(CONSOLE_KEYS)
    out({'steps': steps, 'register': os.path.join(os.path.dirname(os.path.abspath(__file__)), 'register_key.ps1'),
         'status_now': status()})
    return 0


def ledger(a):
    rows, since = [], time.time() - a.days * 86400
    for path in (os.path.join(OLD_DATA, 'ledger.jsonl'), LEDGER):
        try:
            for line in io.open(path, encoding='utf-8'):
                try:
                    r = json.loads(line)
                    if time.mktime(time.strptime(r['time'], '%Y-%m-%d %H:%M:%S')) >= since:
                        rows.append(r)
                except (ValueError, KeyError, TypeError):
                    continue
        except OSError:
            pass
    agg = {}
    for r in rows:
        m = agg.setdefault(r['mode'], {'runs': 0, 'ok': 0, 'cost_usd': 0.0})
        m['runs'] += 1
        m['ok'] += 1 if r.get('ok') else 0
        m['cost_usd'] = round(m['cost_usd'] + (r.get('cost_usd') or 0), 4)
    out({'days': a.days, 'by_mode': agg, 'note': 'subscription cost_usd is the API-equivalent estimate, not a charge'})
    return 0


def main(argv):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    sp.add_parser('status')
    s = sp.add_parser('setup')
    s.add_argument('--open', action='store_true')
    r = sp.add_parser('run')
    r.add_argument('--brief', required=True)
    r.add_argument('--cwd')
    r.add_argument('--model')
    r.add_argument('--plan', action='store_true')
    r.add_argument('--no-fallback', action='store_true')
    r.add_argument('--add-dir', action='append', default=[], help='extra folder the child may read/write (repeatable)')
    lg = sp.add_parser('ledger')
    lg.add_argument('--days', type=int, default=30)
    a = ap.parse_args(argv)
    if a.cmd == 'status':
        out(status())
        return 0
    return {'setup': setup, 'run': run, 'ledger': ledger}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
