"""ACE Stop/SubagentStop 훅. 문제없으면 아무것도 출력하지 않는다.
ACE sql 스킬로 SP를 쓰거나 적용했는데 실행 검증 흔적도, 미실행 사유도 없거나,
쓴 SP 파일이 check_sql.py 검사에 실패하면 한 번만 막는다(stop_hook_active면 통과).
ACE_HOOK=off 이면 아무것도 하지 않는다. 어떤 오류도 작업을 막지 않는다.
"""
import json
import os
import re
import sys

sys.dont_write_bytecode = True

PROC = re.compile(r'\b(CREATE|ALTER)\s+(OR\s+ALTER\s+)?PROC(EDURE)?\b', re.I)
SKIP_REASON = re.compile(r'실행\s*검증\s*:\s*하지\s*않음\s*[-–—:]\s*\S')
# 비교용 원본 사본은 결과물이 아니므로 보지 않는다
COPY_NAME = re.compile(r'orig|backup|bak|before|원본', re.I)
MAX_LINES = 15


def load_entries(path):
    """transcript JSONL에서 user/assistant 기록만 읽는다."""
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if isinstance(d, dict) and d.get('type') in ('user', 'assistant') and isinstance(d.get('message'), dict):
                out.append(d)
    return out


def is_real_user(d):
    if d.get('type') != 'user' or d.get('isMeta'):
        return False
    c = d['message'].get('content')
    if isinstance(c, str):
        return bool(c.strip()) and not c.lstrip().startswith('<')
    if isinstance(c, list):
        if any(isinstance(x, dict) and x.get('type') == 'tool_result' for x in c):
            return False
        texts = [x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text']
        return any(t.strip() and not t.lstrip().startswith('<') for t in texts)
    return False


def tool_uses(entries):
    for d in entries:
        if d.get('type') != 'assistant':
            continue
        c = d['message'].get('content')
        for x in c if isinstance(c, list) else []:
            if isinstance(x, dict) and x.get('type') == 'tool_use' and isinstance(x.get('input'), dict):
                yield x.get('name') or '', x['input']


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def checker():
    """skills/sql/scripts/check_sql.py 모듈."""
    root = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scripts = os.path.join(root, 'skills', 'sql', 'scripts')
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import check_sql
    return check_sql


def read_text(path):
    try:
        return checker().read_sql(path)
    except Exception:
        return ''


def analyze(entries, last_message):
    """막을 이유 목록. 없으면 빈 목록."""
    start = 0
    for i, d in enumerate(entries):
        if is_real_user(d):
            start = i
    window = entries[start:]
    uses = list(tool_uses(window))

    used_skill = False
    for name, inp in uses:
        if name == 'Skill' and str(inp.get('skill', '')).lower() in ('ace:sql', 'ace/sql'):
            used_skill = True
        p = str(inp.get('file_path', '')).replace('\\', '/').lower()
        if name == 'Read' and 'ace' in p and p.endswith('skills/sql/skill.md'):
            used_skill = True
    if not used_skill:
        return []

    sp_files, applied, evidence = [], False, False
    for name, inp in uses:
        if name in ('Write', 'Edit', 'MultiEdit'):
            p = str(inp.get('file_path', ''))
            if p.lower().endswith('.sql') and not COPY_NAME.search(os.path.basename(p)):
                body = ' '.join(strings({k: v for k, v in inp.items() if k != 'file_path'}))
                if PROC.search(body) or (os.path.isfile(p) and PROC.search(read_text(p))):
                    if p not in sp_files:
                        sp_files.append(p)
        elif 'mssql' in name.lower():
            q = ' '.join(strings(inp))
            if PROC.search(q):
                applied = True
            elif (re.search(r'\bROLLBACK\b', q, re.I) and re.search(r'\bEXEC(UTE)?\b', q, re.I)) \
                    or re.search(r'\bEXCEPT\b', q, re.I):
                evidence = True
    if not sp_files and not applied:
        return []

    reasons = []
    finals = [last_message or '']
    for d in reversed(window):
        if d.get('type') == 'assistant':
            c = d['message'].get('content')
            t = ' '.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text') \
                if isinstance(c, list) else str(c or '')
            if t.strip():
                finals.append(t)
                break
    finals += [str(inp.get('message', '')) for name, inp in uses if name == 'SubagentHandback'][-1:]
    if not evidence and not any(SKIP_REASON.search(t) for t in finals):
        reasons.append('SP를 고쳤는데 실행 검증을 하지 않았다. references/verify.md대로 실행해서 시나리오 표에 '
                       '숫자를 적거나, 실행할 수 없으면 답변에 `실행 검증: 하지 않음 - <이유>`를 적어라.')

    fails = []
    try:
        ck = checker()
        for p in sp_files:
            if not os.path.isfile(p):
                continue
            results, _ = ck.run_checks(ck.read_sql(p), 'unknown')
            for st, item, ls, note in results:
                if st == ck.FAIL:
                    fails.append('- %s: %s: %s' % (os.path.basename(p), item,
                                                  ' / '.join(x for x in (ck.fmt_lines(ls, 8), note) if x)))
    except Exception:
        fails = []
    if fails:
        more = len(fails) - MAX_LINES
        reasons.append('check_sql.py 실패 항목. 이번에 쓰거나 고친 부분이면 고친 뒤 다시 돌려라. '
                       '요청 범위 밖의 기존 코드면 고치지 말고 답변에 그렇게 적어라:\n' + '\n'.join(fails[:MAX_LINES])
                       + ('\n- 외 %d개' % more if more > 0 else ''))
    return reasons


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace') or '{}')
        if not isinstance(data, dict) or data.get('stop_hook_active'):
            return
        if os.environ.get('ACE_HOOK', '').strip().lower() == 'off':
            return
        path = data.get('agent_transcript_path') or data.get('transcript_path')
        if not path or not os.path.isfile(os.path.expanduser(path)):
            return
        reasons = analyze(load_entries(os.path.expanduser(path)), data.get('last_assistant_message'))
        if reasons:
            sys.stdout.write(json.dumps({'decision': 'block', 'reason': '[ACE] ' + '\n\n'.join(reasons)}))
    except Exception:
        pass


if __name__ == '__main__':
    main()
    sys.exit(0)
