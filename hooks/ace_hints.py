"""ACE context hints for Claude Code and Codex (ideas from ECC continuous-learning and mcp-health-check, MIT).

  python -B ace_hints.py UserPromptSubmit|PostToolUse [--host claude|codex]

UserPromptSubmit: when the user's message reads as a correction ("장난치니", "왜 이렇게 했어", "말했잖아", "넣지마" …),
  adds one line reminding the agent to fix it and record the lesson (work skill, Compound).
  Also, while an API-credit key is registered (skills/credit) and not marked exhausted, one line routing real work
  to the credit or dispatch; silent without a key, so the plugin is safe for anyone.
PostToolUse: when an MSSQL MCP tool fails with "No active database connection", adds one line: connect first.
Prints nothing otherwise; never blocks; ACE_HOOK=off turns it off.
"""
import json
import os
import re
import sys

CORRECTION = re.compile(
    r'장난|왜\s*(이렇게|저렇게|그렇게|이걸|저걸|그걸|자꾸|또|안\s*하|했|넣|뺐|바꿨|썼)|말했잖|말했는데|말했지|몇\s*번|아니라니까|아니라고|'
    r'아니잖|틀렸|잘못\s*(했|됐|된|짰)|이상하게\s*(짜|했|되)|개같이|그게\s*아니|하지\s*말라|하지\s*마라|넣지\s*마|넣지마|쓰지\s*마|'
    r'빼라고|빼야지|안\s*그렇냐|팔아먹|가져다\s*팔|선호하는?\s*편이\s*아니|별로\s*안\s*좋아|싫어하|왜\s*.+\?\?')
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


def prompt_hint(data):
    t = text_of(data)
    if not t.strip() or t.lstrip().startswith('<'):
        return None
    hints = [h for h in (LESSON if CORRECTION.search(t) else None, credit_hint()) if h]
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
