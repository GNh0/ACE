"""Remaining subscription usage of Claude Code, Codex and Antigravity. Read-only, standard library only.

  python -B usage.py [--json] [--host claude,codex,agy]

- Claude Code: `claude -p "/usage"` (a local slash command: no model turn, no tokens) → 5-hour and weekly percent.
- Codex: the last `rate_limits` event in the newest ~/.codex/sessions/<y>/<m>/<d>/*.jsonl that has one, plus
  model / model_reasoning_effort from ~/.codex/config.toml (read only, never written).
- Antigravity: `agy -p "/usage" --output-format json` (also a local command) → remaining fraction per model group.

Never opens auth.json, credential stores or tokens. A host that cannot be read reports status "unknown" with
the reason. Every figure is normalised to `used_percent` (0-100) per window so hosts can be compared.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True

# agy.exe is ~240 MB; an antivirus scan can hold each start for minutes. Extra seconds for every agy call.
AGY_START = int(os.environ.get('ACE_AGY_START', '240'))
GCP_VARS = ('GOOGLE_CLOUD_PROJECT', 'GOOGLE_CLOUD_PROJECT_ID', 'GOOGLE_CLOUD_LOCATION',
            'GOOGLE_GENAI_USE_VERTEXAI', 'AGY_ADC_AUTH')


# ---------------------------------------------------------------- executables

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
    """Prefer the CLI bundled with the Codex app: the standalone one can fail on the app's config.toml."""
    if os.environ.get('ACE_CODEX'):
        return os.environ['ACE_CODEX']
    hits = sorted(glob.glob(r'C:\Program Files\WindowsApps\OpenAI.Codex_*\app\resources\codex.exe'),
                  key=os.path.getmtime)
    return hits[-1] if hits else shutil.which('codex')


def find_agy():
    if os.environ.get('ACE_AGY'):
        return os.environ['ACE_AGY']
    p = os.path.expandvars(r'%LOCALAPPDATA%\agy\bin\agy.exe')
    return p if os.path.isfile(p) else shutil.which('agy')


def agy_env():
    """The personal (subscription) account: drop Vertex/Cloud project variables for this run only."""
    return {k: v for k, v in os.environ.items() if k not in GCP_VARS}


def claude_env():
    """A child `claude` must not attach to the parent app session (messaging socket, child-session notes)."""
    drop = ('CLAUDECODE', 'CLAUDE_CODE_MESSAGING_SOCKET', 'CLAUDE_CODE_MESSAGING_TOKEN', 'CLAUDE_CODE_CHILD_SESSION',
            'CLAUDE_CODE_CHILD_NOTES_DIR', 'CLAUDE_CODE_SESSION_ID', 'CLAUDE_CODE_HOST_SESSION_ID', 'CLAUDE_PID',
            'CLAUDE_CODE_SESSION_ATTENDED')
    return {k: v for k, v in os.environ.items() if k not in drop}


def _quiet_dir():
    """An empty folder to run the CLIs in: the home folder makes them scan or ask to trust it."""
    import tempfile
    d = os.path.join(tempfile.gettempdir(), 'ace-dispatch', 'usage')
    os.makedirs(d, exist_ok=True)
    return d


class _Job:
    """Windows job object that kills the whole process tree when closed. The CLIs start MCP servers
    (node + cmd per server); agy leaves them running after it exits or is killed, so every run is
    wrapped in a job and the job is closed afterwards. No-op off Windows."""

    def __init__(self):
        self.h = None
        if os.name != 'nt':
            return
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL('kernel32', use_last_error=True)
        k.CreateJobObjectW.restype = wintypes.HANDLE
        k.OpenProcess.restype = wintypes.HANDLE
        self.k = k
        h = k.CreateJobObjectW(None, None)
        if not h:
            return

        class BASIC(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                        ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                        ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                        ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD),
                        ('SchedulingClass', wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ('r', 'w', 'o', 'rb', 'wb', 'ob')]

        class EXT(ctypes.Structure):
            _fields_ = [('Basic', BASIC), ('Io', IO), ('ProcessMemoryLimit', ctypes.c_size_t),
                        ('JobMemoryLimit', ctypes.c_size_t), ('PeakProcessMemoryUsed', ctypes.c_size_t),
                        ('PeakJobMemoryUsed', ctypes.c_size_t)]

        info = EXT()
        info.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if k.SetInformationJobObject(wintypes.HANDLE(h), 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.h = h
        else:
            k.CloseHandle(wintypes.HANDLE(h))

    def add(self, pid):
        if not self.h:
            return
        from ctypes import wintypes
        ph = self.k.OpenProcess(0x0101, False, pid)  # PROCESS_TERMINATE | PROCESS_SET_QUOTA
        if ph:
            self.k.AssignProcessToJobObject(wintypes.HANDLE(self.h), wintypes.HANDLE(ph))
            self.k.CloseHandle(wintypes.HANDLE(ph))

    def close(self):
        if self.h:
            from ctypes import wintypes
            self.k.CloseHandle(wintypes.HANDLE(self.h))  # kills every process still in the job
            self.h = None


def run_tree(cmd, input_text=None, timeout=90, cwd=None, env=None):
    """subprocess.run with the child's whole process tree killed afterwards (also on timeout).
    Returns (stdout, stderr, returncode, timed_out)."""
    job = _Job()
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', errors='replace',
                         cwd=cwd, env=env)
    job.add(p.pid)
    try:
        out, err = p.communicate(input_text, timeout=timeout)
        return out, err, p.returncode, False
    except subprocess.TimeoutExpired:
        job.close()
        p.kill()
        out, err = p.communicate()
        return out, err, None, True
    finally:
        job.close()


class _Result:
    def __init__(self, stdout, stderr, returncode):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def _run(cmd, env=None, timeout=90):
    out, err, rc, timed_out = run_tree(cmd, timeout=timeout, cwd=_quiet_dir(), env=env)
    if timed_out:
        raise subprocess.TimeoutExpired(cmd, timeout)
    return _Result(out, err, rc)


# ---------------------------------------------------------------- readers

def claude_usage():
    exe = find_claude()
    if not exe:
        return {'host': 'claude', 'status': 'unknown', 'reason': 'claude CLI not found'}
    try:
        p = _run([exe, '-p', '/usage', '--output-format', 'json', '--strict-mcp-config',
                  '--mcp-config', '{"mcpServers":{}}'], env=claude_env())
        text = json.loads(p.stdout).get('result', '')
    except Exception as e:  # noqa: BLE001
        return {'host': 'claude', 'status': 'unknown', 'reason': 'claude -p /usage failed: %s' % e}
    windows = []
    for label, key in (('Current session', '5h'), ('Current week (all models)', 'weekly')):
        m = re.search(re.escape(label) + r':\s*(\d+(?:\.\d+)?)% used\W*resets ([^\n]+)', text)
        if m:
            windows.append({'window': key, 'used_percent': float(m.group(1)), 'resets': m.group(2).strip()})
    for m in re.finditer(r'Current week \(([^)]+)\):\s*(\d+(?:\.\d+)?)% used\W*resets ([^\n]+)', text):
        if m.group(1) != 'all models':
            windows.append({'window': 'weekly:' + m.group(1), 'used_percent': float(m.group(2)),
                            'resets': m.group(3).strip()})
    if not windows:
        return {'host': 'claude', 'status': 'unknown', 'reason': 'no usage lines in /usage output'}
    return {'host': 'claude', 'status': 'ok', 'plan': 'subscription', 'windows': windows}


def _toml_value(text, key):
    m = re.search(r'^\s*' + re.escape(key) + r'\s*=\s*"([^"]*)"', text.split('\n[', 1)[0], re.M)
    return m.group(1) if m else None


def codex_usage(max_files=40):
    home = os.path.join(os.path.expanduser('~'), '.codex')
    out = {'host': 'codex', 'status': 'unknown'}
    try:
        with open(os.path.join(home, 'config.toml'), encoding='utf-8', errors='replace') as f:
            cfg = f.read()
        out['model'] = _toml_value(cfg, 'model')
        out['effort'] = _toml_value(cfg, 'model_reasoning_effort')
    except OSError:
        pass
    files = sorted(glob.glob(os.path.join(home, 'sessions', '*', '*', '*', '*.jsonl')),
                   key=os.path.getmtime, reverse=True)[:max_files]
    for path in files:
        last = None
        try:
            with open(path, encoding='utf-8', errors='replace') as f:
                for line in f:
                    if '"rate_limits"' not in line:
                        continue
                    try:
                        rl = (json.loads(line).get('payload') or {}).get('rate_limits')
                    except ValueError:
                        continue
                    if rl:
                        last = rl
        except OSError:
            continue
        if not last:
            continue
        windows = []
        for name in ('primary', 'secondary'):
            w = last.get(name)
            if w:
                mins = w.get('window_minutes') or 0
                windows.append({'window': 'weekly' if mins >= 10080 else '%dh' % (mins // 60) if mins else name,
                                'used_percent': float(w.get('used_percent') or 0),
                                'resets': time.strftime('%Y-%m-%d %H:%M', time.localtime(w['resets_at']))
                                if w.get('resets_at') else None})
        out.update(status='ok', plan=last.get('plan_type'), windows=windows,
                   reached=last.get('rate_limit_reached_type'),
                   as_of=time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(path))))
        return out
    out['reason'] = 'no rate_limits event in the newest Codex session files'
    return out


def agy_usage():
    exe = find_agy()
    if not exe:
        return {'host': 'agy', 'status': 'unknown', 'reason': 'agy CLI not found'}
    try:
        p = _run([exe, '-p', '/usage', '--output-format', 'json'], env=agy_env(), timeout=AGY_START + 60)
        data = json.loads(p.stdout)
        groups = ((data.get('command') or {}).get('data') or {}).get('groups') or []
    except Exception as e:  # noqa: BLE001
        return {'host': 'agy', 'status': 'unknown', 'reason': 'agy -p /usage failed: %s' % e}
    windows = []
    for g in groups:
        for b in g.get('buckets') or []:
            frac = b.get('remaining_fraction')
            if frac is None:
                continue
            windows.append({'window': '%s:%s' % (b.get('window'), g.get('name')),
                            'used_percent': round((1 - float(frac)) * 100, 1), 'resets': b.get('reset_time')})
    if not windows:
        return {'host': 'agy', 'status': 'unknown', 'reason': 'no quota groups in /usage output'}
    return {'host': 'agy', 'status': 'ok', 'plan': 'subscription', 'windows': windows}


CACHE = os.path.join(os.path.expanduser('~'), '.claude', 'ace', 'dispatch', 'usage-%s.json')


def cached(reader, host):
    """Live read; on success keep a copy, on failure fall back to the last good read marked `cached`."""
    def run():
        u = reader()
        path = CACHE % host
        if u.get('status') == 'ok':
            u.setdefault('as_of', time.strftime('%Y-%m-%d %H:%M'))
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(u, f, ensure_ascii=False)
            except OSError:
                pass
            return u
        try:
            with open(path, encoding='utf-8') as f:
                old = json.load(f)
            old.update(status='ok', cached=True, reason=u.get('reason'))
            return old
        except (OSError, ValueError):
            return u
    return run


READERS = {'claude': cached(claude_usage, 'claude'), 'codex': codex_usage, 'agy': cached(agy_usage, 'agy')}


def headroom(u, group=None):
    """Smallest remaining percent over the host's windows (optionally only windows naming `group`)."""
    if u.get('status') != 'ok':
        return None
    ws = [w for w in u['windows'] if not group or group.lower() in w['window'].lower()] or u['windows']
    return round(100 - max(w['used_percent'] for w in ws), 1)


def read_all(hosts=('claude', 'codex', 'agy')):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(len(hosts)) as ex:
        return list(ex.map(lambda h: READERS[h](), hosts))


def table(rows):
    lines = ['| 호스트 | 상태 | 창 | 사용 % | 리셋 |', '| --- | --- | --- | --- | --- |']
    for u in rows:
        if u.get('status') != 'ok':
            lines.append('| %s | unknown | - | - | %s |' % (u['host'], u.get('reason', '')))
            continue
        for w in u['windows']:
            lines.append('| %s | %s | %s | %s | %s |' % (u['host'], 'cached %s' % u.get('as_of') if u.get('cached')
                                                         else 'ok', w['window'], w['used_percent'], w.get('resets')))
        if u['host'] == 'codex':
            lines.append('| codex | 설정 | model=%s effort=%s | | as_of %s |'
                         % (u.get('model'), u.get('effort'), u.get('as_of')))
    return '\n'.join(lines)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--host', default='claude,codex,agy')
    a = ap.parse_args(argv)
    rows = read_all(tuple(h.strip() for h in a.host.split(',') if h.strip()))
    print(json.dumps(rows, ensure_ascii=False, indent=1) if a.json else table(rows))
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main(sys.argv[1:]))
