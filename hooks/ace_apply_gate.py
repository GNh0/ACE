"""ACE PreToolUse gate for Claude Code and Codex (idea from ECC gateguard, MIT). Prints nothing when fine.

  python -B ace_apply_gate.py [--host claude|codex|auto]

Stops the first attempt in a turn to CREATE/ALTER a real stored procedure (not a #temp proc) unless the
current DB definition was checked first: an earlier query in this turn read its hash or definition
(HASHBYTES / OBJECT_DEFINITION / sp_helptext / sql_modules naming the SP), or the apply batch itself is
guarded (HASHBYTES compared in an IF that RETURNs, RAISERRORs or THROWs). The user edits the same SPs from
other tools, so an unchecked ALTER can overwrite their work. A second attempt for the same SP in the same
turn passes, so the gate never deadlocks. Blocks with exit code 2 + stderr (understood by both hosts).
ACE_HOOK=off turns it off; never blocks on its own errors.
"""
import hashlib
import json
import os
import re
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ace_hosts  # noqa: E402

APPLY = re.compile(r'\b(?:CREATE|ALTER)\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\s+(?!#)([\w\[\]\.]+)', re.I)
DYNAMIC = re.compile(r"N?'ALTER'", re.I)
OBJ = re.compile(r"OBJECT_ID\s*\(\s*N?'([^']+)'", re.I)
READ_DEF = re.compile(r'HASHBYTES|OBJECT_DEFINITION|sp_helptext|sql_modules', re.I)
GUARD = re.compile(r'\bIF\b[^;]*?<>[\s\S]{0,400}?\b(RETURN|RAISERROR|THROW)\b', re.I)


def short(name):
    return name.replace('[', '').replace(']', '').split('.')[-1].lower()


def targets(q):
    """SP names this batch creates or alters (empty when it does not apply a real SP)."""
    names = {short(m.group(1)) for m in APPLY.finditer(q)}
    if not names and DYNAMIC.search(q) and re.search(r'\bEXEC(UTE)?\s*\(', q, re.I):
        names = {short(n) for n in OBJ.findall(q)}
    return {n for n in names if n and not n.startswith('#')}


def checked_before(name, queries):
    return any(READ_DEF.search(q) and re.search(re.escape(name), q, re.I) for q in queries)


def guarded(q):
    return bool(re.search(r'HASHBYTES', q, re.I) and GUARD.search(q))


def marker(transcript, name, turn_key):
    key = hashlib.sha1(('%s|%s|%s' % (transcript, name, turn_key)).encode('utf-8')).hexdigest()[:16]
    return os.path.join(tempfile.gettempdir(), 'ace-apply-gate', key)


def decide(data, host):
    name = str(data.get('tool_name') or '')
    inp = data.get('tool_input')
    q = ' '.join(ace_hosts.strings(inp)) if not isinstance(inp, str) else inp
    if not ('mssql' in name.lower() or re.search(r'sqlcmd|Invoke-Sqlcmd', q, re.I)):
        return None
    names = targets(q)
    if not names or guarded(q):
        return None
    path = os.path.expanduser(str(data.get('transcript_path') or ''))
    records = ace_hosts.read_jsonl(path) if path and os.path.isfile(path) else []
    if host == 'auto':
        host = ace_hosts.detect_host(records) if records else 'claude'
    turn = (ace_hosts.codex_turn if host == 'codex' else ace_hosts.claude_turn)(records, data) if records else None
    queries = turn.db if turn else []
    todo = [n for n in sorted(names) if not checked_before(n, queries)]
    if not todo:
        return None
    turn_key = data.get('turn_id') or len(records)
    first = []
    for n in todo:
        m = marker(path, n, turn_key if host == 'codex' else _claude_turn_start(records))
        if not os.path.exists(m):
            os.makedirs(os.path.dirname(m), exist_ok=True)
            open(m, 'w').close()
            first.append(n)
    if not first:
        return None
    return ('[ACE] SP 적용 전 확인: %s. 적용 직전에 DB 정의 해시(HASHBYTES(\'SHA2_256\', OBJECT_DEFINITION(...)))를 '
            '읽어 파일·마지막으로 본 상태와 같은지 보여라. 다른 곳(Codex 등)에서 바뀌었으면 다시 읽고 그 변경을 '
            '반영한 뒤 적용한다. 확인했으면 같은 적용을 다시 실행하면 통과한다. 적용 배치 안에 해시 가드'
            '(IF @H <> \'<해시>\' … RETURN)를 넣어도 된다.' % ', '.join(first))


def _claude_turn_start(records):
    """Index of the last real user message: one gate per SP per user turn."""
    idx = 0
    for i, d in enumerate(records):
        if d.get('type') == 'user' and isinstance(d.get('message'), dict) and ace_hosts._claude_real_user(d):
            idx = i
    return idx


def main(argv):
    host = argv[argv.index('--host') + 1] if '--host' in argv[:-1] else 'auto'
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8-sig', 'replace') or '{}')
        if not isinstance(data, dict) or os.environ.get('ACE_HOOK', '').strip().lower() == 'off':
            return 0
        reason = decide(data, host)
    except Exception:
        return 0
    if reason:
        sys.stderr.buffer.write(reason.encode('utf-8'))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
