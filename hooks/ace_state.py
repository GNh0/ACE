"""ACE work-state save/restore for Claude Code and Codex (ideas from ECC pre:compact / session:start, MIT).

  python -B ace_state.py PreCompact|SessionStart [--host claude|codex]

PreCompact: before the conversation is summarized, writes ~/.claude/ace/state/<folder key>.md with what a summary
  tends to lose: the user's recent requests (verbatim, shortened), files written or edited (newest first), SPs
  created/altered and SQL files touched, and DB definition hashes read in the session.
SessionStart: when that file exists for the same folder and is younger than 3 days, adds it as context (after a
  compaction and in a new session), so the work continues from the user's words, not from the summary alone.
Prints nothing otherwise; never blocks; ACE_HOOK=off turns it off.
"""
import datetime
import hashlib
import io
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ace_apply_gate  # noqa: E402
import ace_hosts  # noqa: E402

STATE_DIR = os.path.join(os.path.expanduser('~'), '.claude', 'ace', 'state')
MAX_AGE = datetime.timedelta(days=3)
HASH = re.compile(r'\\*"H\\*"\s*:\s*\\*"([0-9A-F]{16})')
PROC = re.compile(r'\b(?:CREATE|ALTER)\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\s+(?!#)([\w\[\]\.]+)', re.I)


def key_of(cwd):
    return hashlib.sha1(os.path.normcase(os.path.abspath(cwd or '.')).encode('utf-8')).hexdigest()[:12]


def user_texts(records):
    out = []
    for d in records:
        if d.get('type') == 'user' and isinstance(d.get('message'), dict) and ace_hosts._claude_real_user(d):
            c = d['message'].get('content')
            out.append(c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c if isinstance(x, dict)))
        elif d.get('type') == 'response_item' and isinstance(d.get('payload'), dict):
            p = d['payload']
            if p.get('type') == 'message' and p.get('role') == 'user' and ace_hosts._codex_user(p):
                out.append(' '.join(x.get('text', '') for x in p.get('content') or [] if isinstance(x, dict)))
    return [t.strip() for t in out if t.strip()]


def tool_uses(records):
    for d in records:
        if d.get('type') == 'assistant' and isinstance(d.get('message'), dict):
            for x in d['message'].get('content') or []:
                if isinstance(x, dict) and x.get('type') == 'tool_use' and isinstance(x.get('input'), dict):
                    yield x.get('name') or '', x['input'], x.get('id')
        elif d.get('type') == 'response_item' and isinstance(d.get('payload'), dict):
            call = ace_hosts._codex_call(d['payload'])
            if call:
                yield call[0], {'text': call[1]}, None


def results_by_id(records):
    res = {}
    for d in records:
        c = d.get('message', {}).get('content') if d.get('type') == 'user' and isinstance(d.get('message'), dict) else None
        for x in c if isinstance(c, list) else []:
            if isinstance(x, dict) and x.get('type') == 'tool_result':
                res[x.get('tool_use_id')] = json.dumps(x.get('content'), ensure_ascii=False)
    return res


def build(records, cwd):
    users = user_texts(records)
    files, procs, hashes = [], [], []
    res = results_by_id(records)
    for name, inp, tid in tool_uses(records):
        p = inp.get('file_path') or ''
        if name in ('Write', 'Edit', 'MultiEdit') and p:
            files.append(p)
        for f in ace_hosts.patches_in(inp.get('text', '')) if 'text' in inp else []:
            if f.get('path'):
                files.append(f['path'])
        if 'mssql' in name.lower() or re.search(r'sqlcmd|Invoke-Sqlcmd', json.dumps(inp), re.I):
            q = ' '.join(ace_hosts.strings(inp))
            procs += sorted(ace_apply_gate.targets(q))
            if re.search(r'HASHBYTES', q, re.I):
                objs = re.findall(r"OBJECT_ID\s*\(\s*N?'([^']+)'", q, re.I)
                hs = HASH.findall(res.get(tid, ''))
                if objs and hs:
                    hashes.append('%s = %s' % (objs[0], hs[-1]))
    uniq = lambda xs: list(dict.fromkeys(reversed(xs)))  # newest first, no repeats
    lines = ['# ACE 작업 상태 (%s)' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), '', '폴더: %s' % cwd, '',
             '## 최근 사용자 요청 (원문, 최신이 아래)', '']
    lines += ['- ' + ' '.join(u.split())[:300] for u in users[-8:]] or ['- 없음']
    lines += ['', '## 쓰거나 고친 파일 (최신 순)', ''] + (['- ' + f for f in uniq(files)[:25]] or ['- 없음'])
    lines += ['', '## DB에 만들거나 바꾼 SP', ''] + (['- ' + p for p in uniq(procs)[:15]] or ['- 없음'])
    latest = {}
    for h in reversed(hashes):  # 같은 SP는 마지막으로 본 해시 하나만
        latest.setdefault(h.split(' = ')[0].lower(), h)
    lines += ['', '## 마지막으로 확인한 SP 정의 해시', ''] + (['- ' + h for h in list(latest.values())[:15]] or ['- 없음'])
    lines += ['', '적용 전에는 해시를 다시 확인한다(다른 도구에서 바뀌었을 수 있다).']
    return '\n'.join(lines) + '\n'


def main(argv):
    event = next((a for a in argv if a in ('PreCompact', 'SessionStart')), '')
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8-sig', 'replace') or '{}')
        if not isinstance(data, dict) or os.environ.get('ACE_HOOK', '').strip().lower() == 'off':
            return 0
        event = event or str(data.get('hook_event_name') or '')
        cwd = data.get('cwd') or os.getcwd()
        path = os.path.join(STATE_DIR, key_of(cwd) + '.md')
        if event == 'PreCompact':
            tp = os.path.expanduser(str(data.get('transcript_path') or ''))
            if tp and os.path.isfile(tp):
                os.makedirs(STATE_DIR, exist_ok=True)
                io.open(path, 'w', encoding='utf-8').write(build(ace_hosts.read_jsonl(tp), cwd))
        elif event == 'SessionStart' and os.path.isfile(path):
            age = datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(path))
            if age <= MAX_AGE:
                text = io.open(path, encoding='utf-8').read()[:4000]
                ctx = '[ACE] 이전 작업 상태 파일(%s). 이어서 하는 작업이면 이 내용을 기준으로 삼아라:\n%s' % (path, text)
                out = {'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': ctx}}
                sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False).encode('utf-8'))
    except Exception:
        return 0
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
