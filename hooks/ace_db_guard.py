"""ACE PreToolUse guard for live databases (Claude Code and Codex). Prints nothing when fine.

  python -B ace_db_guard.py [--host claude|codex|auto]

The user lists live (read-only) DB connections in ~/.claude/ace/config.json:
  {"protected_db": ["PROD_ERP"]}
An entry matches the MCP server part of a tool name (`mcp__mssql_PROD_ERP__mssql_run_sql_query` →
`mssql_PROD_ERP`, equal or ending with `_<entry>`) or a sqlcmd/Invoke-Sqlcmd command naming it.
Any statement that changes data or objects is refused there: INSERT/UPDATE/DELETE/MERGE/TRUNCATE/DROP/ALTER/
CREATE/GRANT/EXEC of a procedure (writes to @table variables and #temp objects are allowed), unless the user's
latest message itself asks for it: it names that DB (or 운영/live) and a change verb (수정, 적용, 반영, 실행,
바꿔, 넣어, 삭제, ALTER …). Only the user's words count, never the agent's. ACE_HOOK=off turns it off; never blocks on its
own errors. Ideas from ECC hookify/config-protection (MIT).
"""
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ace_hosts  # noqa: E402

CONFIG = os.path.join(os.path.expanduser('~'), '.claude', 'ace', 'config.json')
WRITE = re.compile(
    r'\b(?:INSERT\s+(?:INTO\s+)?(?!INTO\b)(?![@#])[\w\[\]\.]+'
    r'|UPDATE\s+(?![@#])[\w\[\]\.]+\s+SET\b|UPDATE\s+\w+\s*$'
    r'|DELETE\s+(?:FROM\s+)?(?!FROM\b)(?![@#])[\w\[\]\.]+'
    r'|MERGE\s+(?:INTO\s+)?(?!INTO\b)(?![@#])[\w\[\]\.]+'
    r'|TRUNCATE\s+TABLE\s+(?!#)'
    r'|DROP\s+(?:TABLE|PROC|PROCEDURE|VIEW|FUNCTION|INDEX|TRIGGER|DATABASE)\s+(?!#)(?!IF\s+EXISTS\s+#)'
    r'|ALTER\s+(?:TABLE|PROC|PROCEDURE|VIEW|FUNCTION|INDEX|TRIGGER|DATABASE)\b'
    r'|CREATE\s+(?:OR\s+ALTER\s+)?(?:TABLE|PROC|PROCEDURE|VIEW|FUNCTION|INDEX|TRIGGER)\s+(?!#)'
    r'|GRANT\b|REVOKE\b|DENY\b'
    r'|EXEC(?:UTE)?\s+(?!SP_XML_PREPAREDOCUMENT|SP_XML_REMOVEDOCUMENT|SP_EXECUTESQL\b|\(|@\w+\s*=?\s*N?\')(?!#)[\w\[\]\.]+'
    r'|EXEC(?:UTE)?\s*\()', re.I | re.M)


def protected():
    try:
        with open(CONFIG, encoding='utf-8-sig') as f:
            return [str(x) for x in json.load(f).get('protected_db', []) if str(x).strip()]
    except (OSError, ValueError):
        return []


def strip_comments(q):
    q = re.sub(r'/\*.*?\*/', ' ', q, flags=re.S)
    q = re.sub(r'--[^\n]*', ' ', q)
    return re.sub(r"'(?:''|[^'])*'", "''", q)  # 문자열 안의 'UPDATE …'는 보지 않는다


def target(name, text, keys):
    server = name.split('__')[1] if name.startswith('mcp__') and name.count('__') >= 2 else ''
    for k in keys:
        if server and (server.lower() == k.lower() or server.lower().endswith('_' + k.lower())):
            return k
        if re.search(r'sqlcmd|Invoke-Sqlcmd', text, re.I) and re.search(r'(?<![\w])' + re.escape(k) + r'(?![\w])', text, re.I):
            return k
    return None


ALLOW_VERB = re.compile(r'수정|적용|반영|실행|바꿔|바꾸|고쳐|넣어|추가해|삭제|지워|업데이트|ALTER|UPDATE|INSERT|DELETE|EXEC', re.I)


def user_allows(data, key):
    """The latest real user message names this DB (or 운영/live) together with a change verb."""
    path = os.path.expanduser(str(data.get('transcript_path') or ''))
    if not path or not os.path.isfile(path):
        return False
    last = ''
    for d in ace_hosts.read_jsonl(path):
        if d.get('type') == 'user' and isinstance(d.get('message'), dict) and ace_hosts._claude_real_user(d):
            c = d['message'].get('content')
            last = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c if isinstance(x, dict))
        elif d.get('type') == 'response_item' and isinstance(d.get('payload'), dict):
            p = d['payload']
            if p.get('type') == 'message' and p.get('role') == 'user' and ace_hosts._codex_user(p):
                last = ' '.join(x.get('text', '') for x in p.get('content') or [] if isinstance(x, dict))
    # 연결 이름 그대로(PROD_ERP / PROD ERP) 또는 '운영'·live. 접두어를 뺀 DB 이름만으로는 개발 사본과 구분되지 않아 열지 않는다
    names = [key, key.replace('_', ' ', 1), '운영', 'live']
    return bool(ALLOW_VERB.search(last)) and any(n and n.lower() in last.lower() for n in names)


def decide(data):
    keys = protected()
    if not keys:
        return None
    name = str(data.get('tool_name') or '')
    inp = data.get('tool_input')
    text = inp if isinstance(inp, str) else ' '.join(ace_hosts.strings(inp))
    k = target(name, text, keys)
    if not k:
        return None
    m = WRITE.search(strip_comments(text))
    if not m or user_allows(data, k):
        return None
    return ('[ACE] 운영 DB 보호: %s 는 읽기 전용으로 지정돼 있다(~/.claude/ace/config.json). 변경 문장이 있어 막았다: "%s". '
            '조회(SELECT)만 해라. 바꿔야 하면 사용자에게 묻는다: 사용자가 그 DB 이름(또는 운영)과 수정·적용 지시를 직접 적으면 다음 시도는 통과한다.'
            % (k, ' '.join(m.group(0).split())[:60]))


def main(argv):
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8-sig', 'replace') or '{}')
        if not isinstance(data, dict) or os.environ.get('ACE_HOOK', '').strip().lower() == 'off':
            return 0
        reason = decide(data)
    except Exception:
        return 0
    if reason:
        sys.stderr.buffer.write(reason.encode('utf-8'))
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
