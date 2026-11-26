"""Antigravity context hints (the Claude/Codex ace_hints.py and ace_state.py SessionStart, as Antigravity events).

  python -B hooks/ace_ag_context.py PreInvocation|SessionStart

PreInvocation (before each model call): once per user request, when lastUserInput reads as a correction, injects the
  lesson reminder; when a SQL tool failed with "No active database connection" (recorded by ace_stop_check's
  PostToolUse), injects "connect first" once.
SessionStart: when ~/.claude/ace/state/<folder key>.md exists for this workspace and is younger than 3 days (written
  by Claude/Codex PreCompact or Antigravity Stop), injects it.
Output: {"injectSteps": [{"systemMessage": {"systemMessage": ...}}]} or {}. ASCII JSON (the host reads UTF-8).
Never blocks; ACE_HOOK=off turns it off.
"""
import datetime
import io
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ace_antigravity  # noqa: E402
import ace_hints  # noqa: E402
import ace_state  # noqa: E402


def load(conversation):
    try:
        with open(ace_antigravity._ag_state_path(conversation), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(conversation, state):
    with open(ace_antigravity._ag_state_path(conversation), 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)


def pre_invocation(event):
    conversation = event.get('conversationId')
    if not isinstance(conversation, str) or not conversation:
        return []
    import hashlib
    last = str(event.get('lastUserInput') or '')
    token = hashlib.sha256(last.encode('utf-8')).hexdigest()
    state = load(conversation)
    msgs, changed = [], False
    if state.get('hinted') != token:
        state['hinted'], changed = token, True
        hint = ace_hints.prompt_hint({'prompt': last})
        if hint:
            msgs.append(hint)
    if state.get('need_connect'):
        tool = str(state.pop('need_connect'))
        changed = True
        server = tool.split('.')[0] if '.' in tool else 'mssql'
        msgs.append('[ACE] DB 연결이 없다. `%s`의 mssql_connect_database를 먼저 부르고 같은 쿼리를 다시 실행해라.' % server)
    if changed:
        save(conversation, state)
    return msgs


def session_start(event):
    folder = ace_antigravity.work_folder(event)
    if not folder:
        return []
    path = os.path.join(ace_state.STATE_DIR, ace_state.key_of(folder) + '.md')
    if not os.path.isfile(path):
        return []
    if datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(path)) > ace_state.MAX_AGE:
        return []
    text = io.open(path, encoding='utf-8').read()[:4000]
    return ['[ACE] 이전 작업 상태 파일(%s). 이어서 하는 작업이면 이 내용을 기준으로 삼아라:\n%s' % (path, text)]


def main(argv):
    name = next((a for a in argv if a in ('PreInvocation', 'SessionStart')), '')
    msgs = []
    try:
        event = json.loads(sys.stdin.buffer.read().decode('utf-8-sig', 'replace') or '{}')
        if isinstance(event, dict) and os.environ.get('ACE_HOOK', '').strip().lower() != 'off':
            msgs = pre_invocation(event) if name == 'PreInvocation' else session_start(event) if name else []
    except Exception:
        msgs = []
    out = {'injectSteps': [{'systemMessage': {'systemMessage': m}} for m in msgs]} if msgs else {}
    sys.stdout.write(json.dumps(out))


if __name__ == '__main__':
    main(sys.argv[1:])
