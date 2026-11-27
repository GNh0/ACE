"""ACE context hints for Claude Code and Codex (ideas from ECC continuous-learning and mcp-health-check, MIT).

  python -B ace_hints.py UserPromptSubmit|PostToolUse [--host claude|codex]

UserPromptSubmit: when the user's message reads as a correction ("장난치니", "왜 이렇게 했어", "말했잖아", "넣지마" …),
  adds one line reminding the agent to fix it and record the lesson (work skill, Compound). Phrases that also open an
  ordinary request ("그게 아니라 ~되게", "~하지 마") count only when the agent changed files in the previous turn.
  Also, while an API-credit key is registered (skills/credit) and not marked exhausted, one line routing real work
  to the credit or dispatch; silent without a key, so the plugin is safe for anyone.
PostToolUse: when an MSSQL MCP tool fails with "No active database connection", adds one line: connect first.
Prints nothing otherwise; never blocks; ACE_HOOK=off turns it off.
"""
import json
import os
import re
import sys

# Unambiguous corrections, and phrases that also open an ordinary request ("그게 아니라 조회 버튼 누를 때 조회되게",
# "몇 번 실행돼?", 2026-11-27): the second kind counts only right after the agent's own edit.
STRONG = re.compile(
    r'장난|왜\s*(이렇게|저렇게|그렇게|이걸|저걸|그걸|자꾸|또|안\s*하|했|넣|뺐|바꿨|썼)|말했잖|말했는데|말했지|아니라니까|아니라고|'
    r'아니잖|틀렸|잘못\s*(했|됐|된|짰)|이상하게\s*(짜|했|되)|개같이|안\s*그렇냐|팔아먹|가져다\s*팔|선호하는?\s*편이\s*아니|'
    r'별로\s*안\s*좋아|싫어하')
WEAK = re.compile(r'그게\s*아니|하지\s*말라|하지\s*마|넣지\s*마|넣지마|쓰지\s*마|빼라고|빼야지|몇\s*번|왜\s*[^?\n]*\?\?')
CORRECTION = re.compile(STRONG.pattern + '|' + WEAK.pattern)
WRITE_TOOLS = ('Write', 'Edit', 'MultiEdit', 'NotebookEdit')
TAIL_BYTES = 3 * 1024 * 1024  # the previous turn is at the end; never parse a whole long transcript in a 10 s hook
LESSON = ('[ACE] 사용자 교정으로 보인다. 고친 뒤 work 스킬 Compound대로 `~/.claude/ace/lessons/<skill>.md`에 '
          '기록하고 답변에 `교정 기록에 추가: <제목>`을 적어라. 같은 실수가 다른 파일에도 있는지 확인한다.')


def text_of(data):
    p = data.get('prompt') or data.get('user_prompt') or data.get('message') or ''
    if isinstance(p, list):
        p = ' '.join(x.get('text', '') for x in p if isinstance(x, dict))
    return str(p)


CREDIT = ('[ACE credit] API 크레딧을 쓸 수 있다. 파일을 고치거나 만드는 작업, 여러 파일을 읽는 분석이면 직접 하지 말고 보낸다. '
          '서로 다른 파일로 나눌 수 있거나 Codex·Antigravity가 더 맞는 조각이 있으면 ace:dispatch(billing auto: Claude 조각은 '
          'Anthropic 크레딧, Codex 조각은 OpenAI API 우선·균형, Orca 안이면 지켜볼 편집 조각은 via orca), 나눌 것 없는 단일 작업은 '
          'ace:credit 절차대로 `python -B "%s" run --brief <파일> --cwd <프로젝트> --model <모델>`. 이 대화 맥락이 꼭 필요한 일, '
          '운영 DB 변경, 질문·짧은 답만 여기서 한다. 보낸 결과는 직접 확인하고 답변 끝에 `처리: 크레딧 $<비용>` 또는 '
          '`처리: 구독(<이유>)`을 적어라.')


def credit_hint():
    """The credit reminder, only while a key is registered and the credit is not marked exhausted. Silent for
    anyone without a key, inside a credit or dispatch worker, and with ACE_CREDIT=off. No network call."""
    if os.environ.get('CREDIT_FIRST_CHILD') or os.environ.get('ACE_DISPATCH_CHILD'):
        return None
    here = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'skills', 'credit', 'scripts')
    try:
        sys.dont_write_bytecode = True
        if here not in sys.path:
            sys.path.insert(0, here)
        import credit_run as c
        key = c.get_key()
        if not key or c.route(key, c.load_state(), 'unchecked') != 'credit':
            return None
        return CREDIT % os.path.join(here, 'credit_run.py')
    except Exception:
        return None


def tail_records(path):
    """The JSON records in the last TAIL_BYTES of a transcript (the first, partial line is dropped)."""
    with open(path, 'rb') as f:
        f.seek(0, 2)
        size = f.tell()
        start = max(0, size - TAIL_BYTES)
        prev = b'\n'
        if start:
            f.seek(start - 1)
            prev = f.read(1)
        f.seek(start)
        data = f.read(min(size, TAIL_BYTES))
    lines = data.split(b'\n')
    if prev != b'\n':  # the cut fell inside a record
        lines = lines[1:]
    out = []
    for line in lines:
        try:
            d = json.loads(line.decode('utf-8', 'replace'))
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


FAILED = re.compile(r'"?(exit_code|exitCode)"?\s*[:=]\s*[1-9]|verification failed|failed to apply|\berror\b', re.I)
APPLY_PATCH = re.compile(r'^\s*(?:(?:bash|sh|zsh)\s+-l?c\s+)?["\']?apply_patch\b')


def agent_wrote_before(data):
    """Did the agent change files (a successful edit) in the turn before this prompt? None when unknown."""
    path = os.path.expanduser(str(data.get('transcript_path') or ''))
    if not path or not os.path.isfile(path):
        return None
    sys.dont_write_bytecode = True
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import ace_hosts as H
    recs = [d for d in tail_records(path) if not d.get('isSidechain')]
    if H.detect_host(recs) == 'codex':
        def is_user(d):
            p = d.get('payload') if isinstance(d.get('payload'), dict) else {}
            return d.get('type') == 'response_item' and p.get('type') == 'message' and p.get('role') == 'user' \
                and H._codex_user(p)
        users = [i for i, d in enumerate(recs) if is_user(d)]
        def is_agent(d):
            p = d.get('payload') if isinstance(d.get('payload'), dict) else {}
            return d.get('type') == 'response_item' and (
                p.get('type') in ('function_call', 'custom_tool_call', 'local_shell_call')
                or (p.get('type') == 'message' and p.get('role') == 'assistant'))
        acted = [i for i, d in enumerate(recs) if is_agent(d)]
        end = len(recs)
        if users and (not acted or users[-1] > acted[-1]):  # the current prompt is already the last record
            end, users = users[-1], users[:-1]
        begin = users[-1] if users else 0
        outputs = {}
        for d in recs[begin:end]:
            p = d.get('payload') if isinstance(d.get('payload'), dict) else {}
            if p.get('type') in ('function_call_output', 'custom_tool_call_output'):
                outputs[p.get('call_id')] = json.dumps(p.get('output'), ensure_ascii=False)
        for d in recs[begin:end]:
            p = d.get('payload') if isinstance(d.get('payload'), dict) else {}
            call = H._codex_call(p) if d.get('type') == 'response_item' else None
            if not call:
                continue
            out = outputs.get(p.get('call_id'), '')
            if FAILED.search(out):
                continue
            if call[0] == 'apply_patch' or APPLY_PATCH.search(call[1]) or H.SHELL_WRITE.search(call[1]):
                return True
        return False
    entries = [d for d in recs if d.get('type') in ('user', 'assistant') and isinstance(d.get('message'), dict)]
    end = len(entries)
    if entries and H._claude_real_user(entries[-1]):  # the current prompt is already recorded
        end -= 1
    users = [i for i, d in enumerate(entries[:end]) if H._claude_real_user(d)]
    begin = users[-1] if users else 0
    failed = set()
    for d in entries[begin:end]:
        c = d['message'].get('content') if d.get('type') == 'user' else None
        for x in c if isinstance(c, list) else []:
            if isinstance(x, dict) and x.get('type') == 'tool_result' and x.get('is_error'):
                failed.add(x.get('tool_use_id'))
    for d in entries[begin:end]:
        c = d['message'].get('content') if d.get('type') == 'assistant' else None
        for x in c if isinstance(c, list) else []:
            if not (isinstance(x, dict) and x.get('type') == 'tool_use') or x.get('id') in failed:
                continue
            cmd = str((x.get('input') or {}).get('command', ''))
            if x.get('name') in WRITE_TOOLS or (x.get('name') in ('Bash', 'PowerShell') and H.SHELL_WRITE.search(cmd)):
                return True
    return False


def correction(data, t):
    if STRONG.search(t):
        return True
    if not WEAK.search(t):
        return False
    try:
        return agent_wrote_before(data) is True  # unknown transcript: an ambiguous phrase is a plain request
    except Exception:
        return False


def prompt_hint(data):
    t = text_of(data)
    if not t.strip() or t.lstrip().startswith('<'):
        return None
    hints = [h for h in (LESSON if correction(data, t) else None, credit_hint()) if h]
    return '\n'.join(hints) or None


def tool_hint(data):
    name = str(data.get('tool_name') or '')
    if 'mssql' not in name.lower():
        return None
    resp = json.dumps(data.get('tool_response') or data.get('tool_output') or '', ensure_ascii=False)
    if 'No active database connection' not in resp and 'connect_database first' not in resp:
        return None
    server = name.split('__')[1] if name.count('__') >= 2 else 'mssql'
    return '[ACE] DB 연결이 없다. `mcp__%s__mssql_connect_database`를 먼저 부르고 같은 쿼리를 다시 실행해라.' % server


def main(argv):
    event = next((a for a in argv if a in ('UserPromptSubmit', 'PostToolUse')), '')
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8-sig', 'replace') or '{}')
        if not isinstance(data, dict) or os.environ.get('ACE_HOOK', '').strip().lower() == 'off':
            return 0
        event = event or str(data.get('hook_event_name') or '')
        hint = prompt_hint(data) if event == 'UserPromptSubmit' else tool_hint(data) if event == 'PostToolUse' else None
    except Exception:
        return 0
    if hint:
        out = {'hookSpecificOutput': {'hookEventName': event, 'additionalContext': hint}}
        sys.stdout.buffer.write(json.dumps(out, ensure_ascii=False).encode('utf-8'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
