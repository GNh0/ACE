"""ACE dbhub: one local MSSQL MCP hub shared by Claude Code, Codex and Antigravity.

  python -B dbhub.py status                       설치·실행·클라이언트 설정 상태와 다음 할 일
  python -B dbhub.py install [--from FILE] [--no-autostart] [--port N]
                                                  허브 구축: 기존 클라이언트 설정(npx mssql-mcp)의 연결을 옮기고 세 클라이언트를 허브로 바꾼다
  python -B dbhub.py add NAME --server S --database D --user U (--password-prompt | --password-stdin | --password-env VAR | --password P)
                     [--port 1433] [--no-encrypt] [--no-trust-cert] [--legacy-tls] [--force]
  python -B dbhub.py set NAME [--server S] [--port P] [--database D] [--user U] [--password-prompt|--password-stdin]
                     [--encrypt on|off] [--trust-cert on|off] [--legacy-tls on|off]     일부 항목만 수정
  python -B dbhub.py rename OLD NEW               이름 변경(운영 보호 목록도 같이)
  python -B dbhub.py enable|disable NAME ...      클라이언트 목록에 넣기/빼기(설정은 남김)
  python -B dbhub.py protect|unprotect NAME ...   ACE 운영 DB 보호(~/.claude/ace/config.json protected_db)
  python -B dbhub.py diagnose NAME ... [--fix]    실패 원인 진단: 주소(DNS)·포트(TCP)·로그인 오류 번호·DB 이름/권한·암호화/TLS
                                                  (--fix: 암호화/TLS/인증서 문제면 되는 설정으로 고친다)
  python -B dbhub.py remove NAME
  python -B dbhub.py list                         연결 목록(비밀번호 제외): 켬/끔, 운영 보호 표시
  python -B dbhub.py check [NAME ...] [--fix]     허브를 거쳐 SELECT DB_NAME() 실행 (--fix: 실패한 연결에 encrypt 끔·구형 TLS를 차례로 시도)
  python -B dbhub.py sync [--dry]                 connections.json → 세 클라이언트 설정
  python -B dbhub.py start | stop | restart
  python -B dbhub.py ensure [--quiet] [--host claude|codex|antigravity]   (SessionStart 훅) 설치돼 있고 꺼져 있으면 띄운다

Runtime (never in the repository): $ACE_DBHUB_DIR or ~/.claude/ace/dbhub — connections.json (passwords; owner-only),
node_modules, vendor/, hub.log, backup/. Client server names are mssql_<NAME>; the tools keep mssql-mcp 3.0.0's names.
Managed client entries: names starting with mssql_ and legacy entries that run mssql-mcp. Other MCP servers are untouched.
"""
import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), 'hub')
HOME = os.path.expanduser('~')
RT = os.environ.get('ACE_DBHUB_DIR') or os.path.join(HOME, '.claude', 'ace', 'dbhub')
CONF = os.path.join(RT, 'connections.json')
LOG = os.path.join(RT, 'hub.log')
TASK = 'ace-dbhub'
WIN = os.name == 'nt'
PREFIX = 'mssql_'
CLAUDE = os.path.join(HOME, '.claude.json')
CODEX = os.path.join(os.environ.get('CODEX_HOME') or os.path.join(HOME, '.codex'), 'config.toml')
AGY = os.path.join(HOME, '.gemini', 'config', 'mcp_config.json')
MSSQL_MCP = '3.0.0'


def out(msg=''):
    try:
        sys.stdout.buffer.write((msg + '\n').encode('utf-8'))
        sys.stdout.flush()
    except (OSError, ValueError):
        pass  # 출력 파이프가 닫혀도 작업은 끝까지 한다


# ---------- files ----------

def read_json(path, default=None):
    try:
        with io.open(path, encoding='utf-8-sig') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_text(path, text):
    tmp = path + '.tmp-dbhub'
    with io.open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    os.replace(tmp, path)


def backup(path, label):
    if not os.path.isfile(path):
        return
    d = os.path.join(RT, 'backup')
    os.makedirs(d, exist_ok=True)
    shutil.copy2(path, os.path.join(d, '%s.%s.%s' % (os.path.basename(path), label, time.strftime('%Y%m%d_%H%M%S'))))


def owner_only(path):
    try:
        if WIN:
            user = os.environ.get('USERNAME', '')
            subprocess.run(['icacls', path, '/inheritance:r', '/grant:r', '%s:F' % user], capture_output=True)
        else:
            os.chmod(path, 0o600)
    except OSError:
        pass


def load_conf():
    return read_json(CONF, None)


def save_conf(conf):
    os.makedirs(RT, exist_ok=True)
    new = not os.path.exists(CONF)
    write_text(CONF, json.dumps(conf, ensure_ascii=False, indent=2) + '\n')
    if new:
        owner_only(CONF)


def port_of(conf=None):
    conf = conf or load_conf() or {}
    return int(conf.get('port') or 8765)


def active(conf):
    """Connections shown to the clients (a disabled one stays in connections.json but is left out)."""
    return [n for n, c in conf['connections'].items() if c.get('enabled', True)]


ACE_CFG = os.path.join(HOME, '.claude', 'ace', 'config.json')


def protected():
    return list((read_json(ACE_CFG, {}) or {}).get('protected_db') or [])


def set_protected(names):
    cfg = read_json(ACE_CFG, {}) or {}
    cfg['protected_db'] = names
    os.makedirs(os.path.dirname(ACE_CFG), exist_ok=True)
    backup(ACE_CFG, 'ace-config')
    write_text(ACE_CFG, json.dumps(cfg, ensure_ascii=False, indent=2) + '\n')


def url(name, port):
    return 'http://127.0.0.1:%d/mcp/%s' % (port, urllib.request.quote(name))


# ---------- legacy discovery ----------

def legacy_env(v):
    if not isinstance(v, dict):
        return None
    cmd = ' '.join([str(v.get('command') or '')] + [str(a) for a in (v.get('args') or [])])
    env = v.get('env') or {}
    if 'mssql-mcp' in cmd or env.get('DB_SERVER'):
        return env if env.get('DB_SERVER') else None
    return None


def codex_envs(text):
    res = {}
    for m in re.finditer(r'^\[mcp_servers\.([^\].]+)\.env\]\s*\n(.*?)(?=^\[|\Z)', text, re.M | re.S):
        env = {}
        for line in m.group(2).split('\n'):
            r = re.match(r'''^\s*([A-Za-z_]\w*)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|'([^']*)')\s*$''', line)
            if r:
                env[r.group(1)] = r.group(2) if r.group(2) is not None else r.group(3)
        if env.get('DB_SERVER'):
            res[m.group(1)] = env
    return res


def to_conn(env):
    c = {
        'server': env['DB_SERVER'],
        'port': int(env.get('DB_PORT') or 1433),
        'database': env.get('DB_DATABASE') or '',
        'user': env.get('DB_USER') or '',
        'password': env.get('DB_PASSWORD') or '',
        'encrypt': str(env.get('DB_ENCRYPT', 'true')).lower() != 'false',
        'trustServerCertificate': str(env.get('DB_TRUST_SERVER_CERTIFICATE', 'false')).lower() == 'true',
    }
    if 'tls-min-v1.0' in str(env.get('NODE_OPTIONS') or ''):
        c['tls'] = {'minVersion': 'TLSv1', 'ciphers': 'DEFAULT@SECLEVEL=0'}
    return c


def discover():
    """Legacy (per-client npx mssql-mcp) connections in the three clients: [(client, server_name, conn)]."""
    found = []
    cj = read_json(CLAUDE, {}) or {}
    for k, v in (cj.get('mcpServers') or {}).items():
        e = legacy_env(v)
        if e:
            found.append(('claude', k, to_conn(e)))
    try:
        with io.open(CODEX, encoding='utf-8') as f:
            for k, e in codex_envs(f.read()).items():
                found.append(('codex', k, to_conn(e)))
    except OSError:
        pass
    ag = read_json(AGY, {}) or {}
    for k, v in (ag.get('mcpServers') or {}).items():
        e = legacy_env(v)
        if e:
            found.append(('antigravity', k, to_conn(e)))
    return found


def ident(c):
    return '|'.join(str(c.get(x, '')).lower() for x in ('server', 'port', 'database', 'user'))


def merge(conns, found):
    """Add discovered connections not already present. Claude/Codex names (mssql_X → X) win over Antigravity ones."""
    seen = {ident(c): n for n, c in conns.items()}
    order = {'claude': 0, 'codex': 1, 'antigravity': 2}
    added = []
    for client, name, c in sorted(found, key=lambda x: order[x[0]]):
        if ident(c) in seen:
            continue
        n = name[len(PREFIX):] if name.startswith(PREFIX) else name
        n = re.sub(r'[^A-Za-z0-9_]', '_', n)
        base, i = n, 2
        while n in conns:
            n, i = '%s_%d' % (base, i), i + 1
        conns[n] = c
        seen[ident(c)] = n
        added.append((n, client, name))
    return added


# ---------- hub process ----------

def running(port=None):
    port = port or port_of()
    try:
        with urllib.request.urlopen('http://127.0.0.1:%d/status' % port, timeout=1.5) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception:
        return None


def port_open(port):
    s = socket.socket()
    s.settimeout(0.3)
    try:
        return s.connect_ex(('127.0.0.1', port)) == 0
    finally:
        s.close()


def node_bin():
    return shutil.which('node')


def task_exists():
    if not WIN:
        return False
    r = subprocess.run(['schtasks', '/query', '/tn', TASK], capture_output=True)
    return r.returncode == 0


def spawn():
    """Start the hub detached from this process (it must outlive the hook or session that started it)."""
    # 로그인 작업은 기본 런타임 폴더의 허브를 띄운다. 다른 폴더(ACE_DBHUB_DIR)면 직접 띄운다
    if WIN and not os.environ.get('ACE_DBHUB_DIR') and task_exists():
        subprocess.run(['schtasks', '/run', '/tn', TASK], capture_output=True)
        return
    node = node_bin()
    if not node:
        raise RuntimeError('node not found')
    log = open(LOG, 'ab')
    kw = dict(cwd=RT, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True)
    if WIN:
        flags = 0x08000000 | 0x00000200  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
        try:
            subprocess.Popen([node, 'hub.mjs'], creationflags=flags | 0x01000000, **kw)  # + CREATE_BREAKAWAY_FROM_JOB
        except OSError:
            subprocess.Popen([node, 'hub.mjs'], creationflags=flags, **kw)
    else:
        subprocess.Popen([node, 'hub.mjs'], start_new_session=True, **kw)


def start(wait=8.0):
    if running():
        return True
    spawn()
    end = time.time() + wait
    while time.time() < end:
        if running():
            return True
        time.sleep(0.3)
    return False


def stop():
    st = running()
    if not st:
        return False
    pid = int(st.get('pid') or 0)
    if pid:
        if WIN:
            subprocess.run(['taskkill', '/pid', str(pid), '/f'], capture_output=True)
        else:
            try:
                os.kill(pid, 15)
            except OSError:
                pass
    for _ in range(20):
        if not running():
            return True
        time.sleep(0.2)
    return not running()


def autostart(port):
    if not WIN:
        return 'skip (Windows only; SessionStart hooks start the hub elsewhere)'
    node = node_bin()
    vbs = os.path.join(RT, 'start-hub.vbs')
    write_text(vbs, 'Set sh = CreateObject("WScript.Shell")\r\nsh.CurrentDirectory = "%s"\r\n'
                    'sh.Run "cmd /c """"%s"" hub.mjs >> hub.log 2>&1""", 0, False\r\n' % (RT, node))
    ps = ("$a=New-ScheduledTaskAction -Execute 'wscript.exe' -Argument '//B \"%s\"';"
          "$t=New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME;"
          "$s=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0;"
          "Register-ScheduledTask -TaskName '%s' -Action $a -Trigger $t -Settings $s "
          "-Description 'ACE dbhub: shared MSSQL MCP hub' -Force | Out-Null") % (vbs, TASK)
    r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], capture_output=True)
    return 'task %s registered' % TASK if r.returncode == 0 else 'task registration failed: %s' % \
        r.stderr.decode('utf-8', 'replace').strip()[:200]


# ---------- install ----------

def file_hash(p):
    try:
        with open(p, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return ''


def deploy_code():
    """Copy hub code into the runtime and (re)apply the patches. Returns True when something changed."""
    os.makedirs(RT, exist_ok=True)
    changed = False
    for f in ('hub.mjs', 'diag.mjs', 'package.json'):
        if file_hash(os.path.join(SRC, f)) != file_hash(os.path.join(RT, f)):
            shutil.copy2(os.path.join(SRC, f), os.path.join(RT, f))
            changed = True
    vend = os.path.join(RT, 'vendor', 'mssql-mcp')
    pkg = os.path.join(RT, 'node_modules', 'mssql-mcp')
    if not os.path.isdir(vend) and os.path.isdir(pkg):
        shutil.copytree(pkg, vend)
        changed = True
    for f, rel in (('connection.js', ('dist', 'src', 'db', 'connection.js')), ('config.js', ('dist', 'src', 'config.js'))):
        dst = os.path.join(vend, *rel)
        if os.path.isdir(vend) and file_hash(os.path.join(SRC, 'patch', f)) != file_hash(dst):
            shutil.copy2(os.path.join(SRC, 'patch', f), dst)
            changed = True
    return changed


def npm_install():
    npm = shutil.which('npm') or shutil.which('npm.cmd')
    if not npm:
        raise RuntimeError('npm not found')
    r = subprocess.run([npm, 'install', '--omit=dev', '--no-audit', '--no-fund'], cwd=RT, capture_output=True,
                       shell=WIN)
    if r.returncode != 0:
        raise RuntimeError('npm install failed: ' + r.stderr.decode('utf-8', 'replace')[-400:])
    ver = (read_json(os.path.join(RT, 'node_modules', 'mssql-mcp', 'package.json'), {}) or {}).get('version')
    if ver != MSSQL_MCP:
        raise RuntimeError('mssql-mcp %s installed, %s expected' % (ver, MSSQL_MCP))


def cmd_install(args):
    node = node_bin()
    if not node:
        out('실패: node가 없다. Node.js 20 이상을 설치한 뒤 다시 실행.')
        return 1
    v = subprocess.run([node, '-v'], capture_output=True, text=True).stdout.strip()
    if int(re.sub(r'\D', ' ', v).split()[0] or 0) < 20:
        out('실패: Node.js %s — 20 이상이 필요하다.' % v)
        return 1
    conf = load_conf() or {'port': 8765, 'connections': {}}
    if '--port' in args:
        conf['port'] = int(args[args.index('--port') + 1])
    if '--from' in args:
        src = read_json(args[args.index('--from') + 1], {}) or {}
        for n, c in (src.get('connections') or {}).items():
            conf['connections'].setdefault(n, c)
    added = merge(conf['connections'], discover())
    os.makedirs(RT, exist_ok=True)
    deploy_code()
    if not os.path.isdir(os.path.join(RT, 'node_modules', 'mssql-mcp')):
        out('npm install (mssql-mcp %s) ...' % MSSQL_MCP)
        npm_install()
    deploy_code()
    save_conf(conf)
    out('연결 %d개 (이번에 옮긴 것 %d개)' % (len(conf['connections']), len(added)))
    for n, client, old in added:
        out('  + %s  ← %s:%s' % (n, client, old))
    if not conf['connections']:
        out('연결이 없다. `add`로 등록한 뒤 `sync`.')
    if not start():
        out('실패: 허브가 뜨지 않았다. %s 확인.' % LOG)
        return 1
    out('허브 실행 중: http://127.0.0.1:%d' % port_of(conf))
    cmd_check(['--fix'])
    cmd_sync([])
    if '--no-autostart' not in args:
        out('자동 실행: ' + autostart(port_of(conf)))
    out('끝. 열려 있는 Claude·Codex·Antigravity 세션은 다시 시작해야 새 설정을 읽는다.')
    return 0


# ---------- sync ----------

def managed(k, v):
    return k.startswith(PREFIX) or legacy_env(v) is not None or (
        isinstance(v, dict) and 'mssql-mcp' in ' '.join([str(v.get('command') or '')] + [str(a) for a in v.get('args') or []]))


def sync_json(path, label, entry, dry):
    j = read_json(path, None)
    if j is None:
        return '%s: 없음(건너뜀)' % label
    conf = load_conf()
    port = port_of(conf)
    old = j.get('mcpServers') or {}
    nxt = {k: v for k, v in old.items() if not managed(k, v)}
    for n in active(conf):
        nxt[PREFIX + n] = entry(url(n, port))
    gone = sorted(k for k in old if managed(k, old[k]) and k not in nxt)
    if nxt == old:
        return '%s: 변경 없음' % label
    if not dry:
        backup(path, label)
        j['mcpServers'] = nxt
        write_text(path, json.dumps(j, ensure_ascii=False, indent=2) + '\n')
    return '%s: %d개로 맞춤%s' % (label, len(active(conf)), (' (제거: %s)' % ', '.join(gone)) if gone else '')


def sync_codex(dry):
    if not os.path.isfile(CODEX):
        return 'codex: 없음(건너뜀)'
    with io.open(CODEX, encoding='utf-8') as f:
        text = f.read()
    conf = load_conf()
    port = port_of(conf)
    names = [PREFIX + n for n in active(conf)]
    parts = re.split(r'^(?=\[)', text, flags=re.M)
    enabled, tools, keep = {}, [], []
    insert_at, removed = -1, []
    for p in parts:
        h = re.match(r'^\[mcp_servers\.([^\].]+)((?:\.[^\]]+)?)\]', p)
        srv = h.group(1) if h else None
        is_legacy_env = bool(h and h.group(2) == '.env' and re.search(r'^\s*DB_SERVER\s*=', p, re.M))
        is_legacy = bool(h and not h.group(2) and re.search(r'mssql-mcp', p))
        if not h or not (srv.startswith(PREFIX) or is_legacy or is_legacy_env or
                         (h.group(2) == '.env' and srv in removed)):
            keep.append(re.sub(r'^# ACE dbhub:.*\n', '', p, flags=re.M))
            continue
        sub = h.group(2)
        if not sub:
            e = re.search(r'^\s*enabled\s*=\s*(true|false)', p, re.M)
            if e:
                enabled[srv] = e.group(1) == 'true'
            removed.append(srv)
            if insert_at < 0:
                insert_at = len(keep)
        elif sub.startswith('.tools.') and srv in names:
            tools.append(p)
    blocks = ''.join('[mcp_servers.%s]\nurl = "%s"\nenabled = %s\n\n' % (
        PREFIX + n, url(n, port), 'true' if enabled.get(PREFIX + n, True) else 'false') for n in active(conf))
    gen = '# ACE dbhub: mssql_* entries below are generated by `dbhub.py sync`; edit connections.json instead.\n' + \
        blocks + ''.join(tools)
    if insert_at < 0:
        keep.append('\n' + gen)
    else:
        keep.insert(insert_at, gen)
    new = ''.join(keep)
    if new == text:
        return 'codex: 변경 없음'
    if not dry:
        backup(CODEX, 'codex')
        write_text(CODEX, new)
    return 'codex: %d개로 맞춤 (도구별 설정 %d개 유지)' % (len(names), len(tools))


def cmd_sync(args):
    if not load_conf():
        out('허브가 설치돼 있지 않다: install 먼저.')
        return 1
    dry = '--dry' in args
    out(sync_json(CLAUDE, 'claude', lambda u: {'type': 'http', 'url': u}, dry))
    out(sync_codex(dry))
    out(sync_json(AGY, 'antigravity', lambda u: {'serverUrl': u}, dry))
    if dry:
        out('(dry: 바꾸지 않음)')
    return 0


# ---------- add / remove / list / check ----------

def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args[:-1] else default


def read_password(args, name):
    """--password-prompt (hidden prompt; never enters the conversation) | --password-stdin | --password-env VAR |
    --password P. None when none is given."""
    if '--password-prompt' in args:
        import getpass
        return getpass.getpass('%s 비밀번호(화면에 안 보임): ' % name)
    if '--password-stdin' in args:
        return sys.stdin.readline().rstrip('\r\n')
    if '--password-env' in args:
        return os.environ.get(opt(args, '--password-env'), '')
    return opt(args, '--password')


def tcp_probe(host, port):
    """'ok' | 'dns' (name not found) | 'timeout' | 'refused' | other error text."""
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return 'dns'
    last = 'timeout'
    for fam, typ, proto, _, addr in infos[:3]:
        s = socket.socket(fam, typ, proto)
        s.settimeout(5)
        try:
            s.connect(addr)
            return 'ok'
        except socket.timeout:
            last = 'timeout'
        except ConnectionRefusedError:
            last = 'refused'
        except OSError as e:
            last = str(e)
        finally:
            s.close()
    return last


def run_diag(name):
    node = node_bin()
    if not node or not os.path.isfile(os.path.join(RT, 'diag.mjs')):
        return None
    r = subprocess.run([node, 'diag.mjs', name], cwd=RT, capture_output=True, timeout=120)
    try:
        return json.loads(r.stdout.decode('utf-8', 'replace').strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


LOGIN_NUMBERS = {
    18456: '계정 또는 비밀번호가 틀렸다',
    18452: '서버가 SQL 계정 로그인을 받지 않는다(Windows 인증만 허용). 서버에서 "SQL Server 및 Windows 인증 모드"를 켜야 한다',
    18470: '계정이 비활성화(disabled)돼 있다. DBA가 계정을 활성화해야 한다',
    18486: '로그인 실패가 반복돼 계정이 잠겼다. DBA가 잠금을 풀어야 한다',
    18487: '비밀번호가 만료됐다. 새 비밀번호로 바꾼 뒤 `set NAME --password-prompt`',
    18488: '비밀번호를 바꿔야 하는 계정이다(첫 로그인 변경 필요). SSMS 등으로 한 번 바꾼 뒤 `set NAME --password-prompt`',
}


def diagnose(name, apply_fix=False):
    """Find why a connection fails and say how to fix it. Returns True when a fix was applied and works."""
    conf = load_conf()
    c = conf['connections'][name]
    host, port = c['server'], int(c.get('port') or 1433)
    out('[진단] %s  (%s:%d / %s / %s)' % (PREFIX + name, host, port, c.get('database'), c.get('user')))
    net = tcp_probe(host, port)
    if net == 'dns':
        out('  원인: 서버 주소 "%s"를 찾을 수 없다.' % host)
        out('  확인: 주소 오타, 사내 DNS, VPN 연결. 고치기: set %s --server <주소>' % name)
        return False
    if net == 'timeout':
        out('  원인: %s:%d 에 5초 안에 닿지 않는다(네트워크 단계에서 막힘 — 계정·DB 문제 아님).' % (host, port))
        out('  확인: VPN 연결, 방화벽(서버·사내), 서버 전원, 포트 번호. 포트가 다르면: set %s --port <포트>' % name)
        return False
    if net == 'refused':
        out('  원인: 서버는 응답하지만 %d 포트에서 SQL Server가 연결을 받지 않는다.' % port)
        out('  확인: 포트 번호(명명된 인스턴스면 고정 포트·SQL Browser), SQL Server 구성 관리자의 TCP/IP 사용, 서비스 실행 여부.')
        return False
    if net != 'ok':
        out('  원인: 네트워크 오류 — %s' % net)
        return False
    out('  네트워크: %s:%d 접속 가능' % (host, port))
    d = run_diag(name)
    if not d or d.get('error'):
        out('  진단 실행 실패: %s' % ((d or {}).get('error') or 'node diag.mjs'))
        return False
    res = {r['label']: r for r in d['results']}
    first, master = res.get('as-is'), res.get('master')
    if first and first['ok']:
        out('  지금은 정상 접속된다(일시적 문제였을 수 있다). check %s 로 다시 확인.' % name)
        return True
    num, msg = first.get('number'), first.get('message') or ''
    out('  서버 응답: %s%s' % (('[%s] ' % num) if num else '', msg[:200]))
    fixed = next((r for r in d['results'] if r['label'] not in ('as-is', 'master') and r['ok']), None)
    if master and master['ok'] and not fixed:
        dbs = [r['name'] for r in (master.get('rows') or [])]
        out('  원인: 로그인은 되는데 DB "%s"를 열 수 없다 — DB 이름이 틀렸거나 이 계정에 그 DB 권한이 없다.' % c.get('database'))
        import difflib
        near = difflib.get_close_matches(c.get('database') or '', dbs, n=3, cutoff=0.5)
        if near:
            out('  비슷한 DB: %s → 고치기: set %s --database %s' % (', '.join(near), name, near[0]))
        if dbs:
            out('  이 계정으로 열 수 있는 DB(%d개): %s%s' % (len(dbs), ', '.join(dbs[:20]), ' …' if len(dbs) > 20 else ''))
        else:
            out('  이 계정으로 열 수 있는 사용자 DB가 없다. DBA에게 권한(사용자 매핑)을 요청.')
        return False
    if fixed:
        labels = {'encrypt-off': ('암호화를 끄면 접속된다(서버가 TLS 암호화를 지원하지 않거나 맞지 않음)', ['--encrypt', 'off']),
                  'legacy-tls': ('구형 TLS(1.0/약한 암호)를 허용하면 접속된다(오래된 SQL Server)', ['--legacy-tls', 'on']),
                  'encrypt-off+legacy-tls': ('암호화 끔 + 구형 TLS 로 접속된다', ['--encrypt', 'off', '--legacy-tls', 'on']),
                  'trust-cert': ('서버 인증서를 신뢰하도록 하면 접속된다(자체 서명 인증서)', ['--trust-cert', 'on'])}
        why, flags = labels[fixed['label']]
        out('  원인: %s.' % why)
        if apply_fix:
            cmd_set_quiet(name, flags)
            out('  고침: set %s %s 적용' % (name, ' '.join(flags)))
            return True
        out('  고치기: set %s %s' % (name, ' '.join(flags)))
        return False
    if num in LOGIN_NUMBERS or 'Login failed' in msg or '로그인하지 못했습니다' in msg:
        out('  원인: %s.' % LOGIN_NUMBERS.get(num, LOGIN_NUMBERS[18456]))
        if num in (None, 18456):
            out('  확인: 계정 "%s" 철자, 비밀번호(대소문자·특수문자), 다른 클라이언트(SSMS)에서 같은 계정으로 되는지. '
                '비밀번호를 다시 넣으려면: set %s --password-prompt' % (c.get('user'), name))
        return False
    low = msg.lower()
    if 'certificate' in low or 'self signed' in low or 'self-signed' in low:
        out('  원인: 서버 인증서 검증 실패. 고치기: set %s --trust-cert on' % name)
    elif 'timeout' in low or first.get('code') == 'ETIMEOUT':
        out('  원인: 포트는 열려 있지만 로그인 응답이 늦다(서버 과부하·느린 회선·중간 장비). 잠시 후 check %s, 계속되면 서버 상태 확인.' % name)
    elif 'hang up' in low or 'econnreset' in low or first.get('code') == 'ESOCKET':
        out('  원인: 접속 직후 서버가 끊는다 — 암호화·TLS 설정 불일치로 보이나 모든 조합이 실패했다. 서버의 TLS 설정·포트(다른 서비스가 아닌지) 확인.')
    else:
        out('  원인을 특정하지 못했다. 위 서버 응답을 그대로 사용자에게 보여 준다.')
    return False


def cmd_set_quiet(name, flags):
    conf = load_conf()
    c = conf['connections'][name]
    pairs = dict(zip(flags[::2], flags[1::2]))
    if '--encrypt' in pairs:
        c['encrypt'] = onoff(pairs['--encrypt'])
    if '--trust-cert' in pairs:
        c['trustServerCertificate'] = onoff(pairs['--trust-cert'])
    if '--legacy-tls' in pairs:
        if onoff(pairs['--legacy-tls']):
            c['tls'] = {'minVersion': 'TLSv1', 'ciphers': 'DEFAULT@SECLEVEL=0'}
        else:
            c.pop('tls', None)
    backup(CONF, 'conf')
    save_conf(conf)


def cmd_diagnose(args):
    conf = load_conf()
    names = [a for a in args if not a.startswith('-')]
    if not conf or not names or any(n not in conf['connections'] for n in names):
        out('사용법: diagnose NAME [NAME ...] [--fix]')
        return 1
    bad = 0
    for n in names:
        if not diagnose(n, '--fix' in args):
            bad += 1
    if '--fix' in args and bad < len(names):
        time.sleep(0.8)
        cmd_sync([])
    return 1 if bad else 0


def test_and_report(name, conf, fix=True):
    start()
    time.sleep(0.8)  # 허브가 connections.json 변경을 읽을 시간
    ok, line = check_one(name, port_of(conf))
    out(line)
    if ok:
        return True
    if diagnose(name, apply_fix=fix):
        time.sleep(0.8)
        ok, line = check_one(name, port_of(conf))
        out(line)
        if ok:
            return True
    out('설정은 저장됐다 — 고치려면 set %s ..., 지우려면 remove %s.' % (name, name))
    return False


def cmd_add(args):
    conf = load_conf()
    if not conf:
        out('허브가 설치돼 있지 않다: install 먼저.')
        return 1
    if not args or args[0].startswith('-'):
        out('사용법: add NAME --server S --database D --user U --password-stdin')
        return 1
    name = args[0]
    if not re.match(r'^[A-Za-z0-9_]+$', name):
        out('이름은 영문·숫자·_ 만.')
        return 1
    if name in conf['connections'] and '--force' not in args:
        out('%s 는 이미 있다. 바꾸려면 --force.' % name)
        return 1
    pw = read_password(args, name) or ''
    for req in ('--server', '--database', '--user'):
        if not opt(args, req):
            out('%s 가 필요하다.' % req)
            return 1
    c = {'server': opt(args, '--server'), 'port': int(opt(args, '--port', 1433)), 'database': opt(args, '--database'),
         'user': opt(args, '--user'), 'password': pw, 'encrypt': '--no-encrypt' not in args,
         'trustServerCertificate': '--no-trust-cert' not in args}
    if '--legacy-tls' in args:
        c['tls'] = {'minVersion': 'TLSv1', 'ciphers': 'DEFAULT@SECLEVEL=0'}
    conf['connections'][name] = c
    save_conf(conf)
    out('등록: %s → %s:%d/%s' % (name, c['server'], c['port'], c['database']))
    test_and_report(name, conf)
    return cmd_sync([])


def onoff(v):
    return str(v).lower() in ('on', 'true', '1', 'yes', 'y')


def cmd_set(args):
    """Change some fields of one connection; the rest stay."""
    conf = load_conf()
    if not conf or not args or args[0] not in conf['connections']:
        out('사용법: set NAME [--server S] [--port P] [--database D] [--user U] [--password-prompt|--password-stdin] '
            '[--encrypt on|off] [--trust-cert on|off] [--legacy-tls on|off]')
        return 1
    name = args[0]
    c = dict(conf['connections'][name])
    changed = []
    for flag, key, conv in (('--server', 'server', str), ('--port', 'port', int), ('--database', 'database', str),
                            ('--user', 'user', str), ('--encrypt', 'encrypt', onoff),
                            ('--trust-cert', 'trustServerCertificate', onoff)):
        v = opt(args, flag)
        if v is not None:
            c[key] = conv(v)
            changed.append(key)
    v = opt(args, '--legacy-tls')
    if v is not None:
        if onoff(v):
            c['tls'] = {'minVersion': 'TLSv1', 'ciphers': 'DEFAULT@SECLEVEL=0'}
        else:
            c.pop('tls', None)
        changed.append('legacy-tls')
    pw = read_password(args, name)
    if pw is not None:
        c['password'] = pw
        changed.append('password')
    if not changed:
        out('바꿀 항목이 없다.')
        return 1
    backup(CONF, 'conf')
    conf['connections'][name] = c
    save_conf(conf)
    out('수정: %s (%s)' % (name, ', '.join(changed)))
    test_and_report(name, conf, fix=False)
    return cmd_sync([])


def cmd_rename(args):
    conf = load_conf()
    if not conf or len(args) < 2 or args[0] not in conf['connections']:
        out('사용법: rename OLD NEW')
        return 1
    old, new = args[0], args[1]
    if not re.match(r'^[A-Za-z0-9_]+$', new) or new in conf['connections']:
        out('새 이름이 잘못됐거나 이미 있다.')
        return 1
    backup(CONF, 'conf')
    conf['connections'] = {(new if k == old else k): v for k, v in conf['connections'].items()}
    save_conf(conf)
    out('이름 변경: mssql_%s → mssql_%s' % (old, new))
    prot = protected()
    if old in prot:
        set_protected([new if x == old else x for x in prot])
        out('운영 보호 목록도 바꿈: %s → %s' % (old, new))
    return cmd_sync([])


def cmd_enable(args, on):
    conf = load_conf()
    if not conf or not args or any(a not in conf['connections'] for a in args):
        out('사용법: %s NAME [NAME ...]' % ('enable' if on else 'disable'))
        return 1
    for n in args:
        if on:
            conf['connections'][n].pop('enabled', None)
        else:
            conf['connections'][n]['enabled'] = False
    save_conf(conf)
    out('%s: %s (설정은 connections.json에 남는다)' % ('켬' if on else '끔(클라이언트 목록에서 뺌)', ', '.join(args)))
    return cmd_sync([])


def cmd_protect(args, on):
    conf = load_conf() or {'connections': {}}
    if not args:
        out('사용법: %s NAME [NAME ...]' % ('protect' if on else 'unprotect'))
        return 1
    unknown = [a for a in args if a not in conf['connections']]
    if unknown and on:
        out('없는 연결: %s' % ', '.join(unknown))
        return 1
    prot = protected()
    nxt = sorted(set(prot) | set(args)) if on else [x for x in prot if x not in args]
    if nxt == prot:
        out('변경 없음. 운영 보호: %s' % (', '.join(prot) or '(없음)'))
        return 0
    set_protected(nxt)
    out('운영 보호 %s: %s → 지금 목록: %s' % ('추가' if on else '해제', ', '.join(args), ', '.join(nxt) or '(없음)'))
    if on:
        out('(ACE DB 보호 훅이 이 연결의 쓰기 문장을 막는다. 사용자가 그 DB 이름과 수정 지시를 직접 적으면 통과)')
    return 0


def cmd_remove(args):
    conf = load_conf()
    if not conf or not args:
        out('사용법: remove NAME')
        return 1
    if args[0] not in conf['connections']:
        out('%s 없음.' % args[0])
        return 1
    backup(CONF, 'conf')
    del conf['connections'][args[0]]
    save_conf(conf)
    out('삭제: %s' % args[0])
    return cmd_sync([])


def cmd_list(args):
    conf = load_conf()
    if not conf:
        out('허브가 설치돼 있지 않다.')
        return 1
    prot = set(protected())
    for n, c in conf['connections'].items():
        flags = [f for f, on in (('no-encrypt', not c.get('encrypt', True)), ('legacy-tls', 'tls' in c)) if on]
        out('%-26s %s %s  %s:%s/%s  %s %s' % (
            PREFIX + n, '켬' if c.get('enabled', True) else '끔', '운영' if n in prot else '    ', c.get('server'),
            c.get('port'), c.get('database'), c.get('user'), ' '.join(flags)))
    out('%d개 (켬 %d) · 허브 %s' % (len(conf['connections']), len(active(conf)), '실행 중' if running() else '꺼짐'))
    return 0


def mcp_call(name, port, body, timeout=40):
    req = urllib.request.Request(url(name, port), data=json.dumps(body).encode('utf-8'), method='POST', headers={
        'content-type': 'application/json', 'accept': 'application/json, text/event-stream',
        'mcp-protocol-version': '2025-06-18'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def check_one(name, port):
    t0 = time.time()
    try:
        r = mcp_call(name, port, {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
            'name': 'mssql_run_sql_query', 'arguments': {'query': 'SELECT DB_NAME() AS db, @@SERVERNAME AS srv'}}})
        res = r.get('result') or {}
        row = ((res.get('structuredContent') or {}).get('recordset') or [None])[0]
        ms = int((time.time() - t0) * 1000)
        if res.get('isError') or not row:
            txt = ((res.get('content') or [{}])[0].get('text') or json.dumps(r))[:160]
            return False, 'FAIL %-22s %5dms %s' % (name, ms, txt)
        return True, 'OK   %-22s %5dms %s @ %s' % (name, ms, row.get('db'), row.get('srv'))
    except Exception as e:
        return False, 'FAIL %-22s %s' % (name, str(e)[:160])


def cmd_check(args):
    conf = load_conf()
    if not conf:
        out('허브가 설치돼 있지 않다.')
        return 1
    if not running() and not start():
        out('허브가 꺼져 있고 띄우지 못했다. %s 확인.' % LOG)
        return 1
    names = [a for a in args if not a.startswith('-')] or active(conf)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(lambda n: check_one(n, port_of(conf)), names))
    for _, line in res:
        out(line)
    if any(not ok for ok, _ in res):
        again = []
        for n, (ok, line) in zip(names, res):
            if not ok and diagnose(n, apply_fix='--fix' in args):
                time.sleep(1.0)  # 허브가 바뀐 설정을 읽을 시간
                ok, line = check_one(n, port_of(conf))
                out(line)
            again.append((ok, line))
        res = again
    bad = sum(1 for ok, _ in res if not ok)
    out('%d/%d OK' % (len(res) - bad, len(res)))
    return 1 if bad else 0


# ---------- status / ensure ----------

def cmd_status(args):
    conf = load_conf()
    legacy = discover()
    st = running(port_of(conf)) if conf else None
    out('설치: %s' % ('예 (%s)' % RT if conf else '아니오'))
    if conf:
        out('연결: %d개 · 허브: %s' % (len(conf['connections']), 'pid %s, %sMB, 열린 연결 %d개' % (
            st['pid'], st['memory_mb'], len(st.get('open_pools') or {})) if st else '꺼짐'))
        out('자동 실행 작업(%s): %s' % (TASK, '있음' if task_exists() else '없음') if WIN else '자동 실행: SessionStart 훅')
    out('예전 방식(클라이언트마다 npx mssql-mcp) 항목: %d개%s' % (
        len(legacy), (' — ' + ', '.join(sorted({'%s:%s' % (c, n) for c, n, _ in legacy})[:8])) if legacy else ''))
    if not conf:
        out('다음: install (예전 방식 항목의 연결을 옮겨 허브를 만든다)' if legacy else '다음: install 후 add')
    elif legacy:
        out('다음: install 다시 실행 (남은 예전 방식 항목을 허브로 옮긴다)')
    elif not st:
        out('다음: start')
    return 0


def cmd_ensure(args):
    host = opt(args, '--host', 'claude')
    msg = None
    try:
        if os.environ.get('ACE_HOOK', '').strip().lower() != 'off':
            conf = load_conf()
            if conf:
                deploy_code() and stop()  # 플러그인 업데이트로 허브 코드가 바뀌었으면 새 코드로 다시 띄운다
                if not port_open(port_of(conf)):
                    spawn()
            elif host != 'antigravity' and len(discover()) >= 3:
                msg = '[ACE] DB MCP가 클라이언트마다 따로 뜬다(npx mssql-mcp). 사용자가 DB MCP 등록·정리·속도를 말하면 ' \
                      'dbhub 스킬로 공용 허브를 구축할 수 있다고 한 번 알려라.'
    except Exception:
        msg = None
    if host == 'antigravity':
        sys.stdout.write('{}')
    elif msg and '--quiet' not in args:
        out(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': msg}},
                       ensure_ascii=False))
    return 0


def main(argv):
    if not argv:
        out(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    fn = {'status': cmd_status, 'install': cmd_install, 'add': cmd_add, 'remove': cmd_remove, 'list': cmd_list,
          'set': cmd_set, 'rename': cmd_rename, 'diagnose': cmd_diagnose, 'enable': lambda a: cmd_enable(a, True),
          'disable': lambda a: cmd_enable(a, False), 'protect': lambda a: cmd_protect(a, True),
          'unprotect': lambda a: cmd_protect(a, False),
          'check': cmd_check, 'sync': cmd_sync, 'ensure': cmd_ensure,
          'start': lambda a: out('허브 실행 중' if start() else '실패: %s 확인' % LOG) or 0,
          'stop': lambda a: out('중지' if stop() else '떠 있지 않음') or 0,
          'restart': lambda a: (stop(), out('허브 실행 중' if start() else '실패: %s 확인' % LOG))[0] and 0}.get(cmd)
    if not fn:
        out(__doc__)
        return 1
    return fn(args) or 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
