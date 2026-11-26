"""Antigravity adapter for ace_stop_check.py, ace_ag_pretool.py and ace_ag_context.py. The host starts hooks with
cwd = plugin root: PostToolUse events are kept per conversation in %TEMP%/ace-hook/, and Stop (fullyIdle, normal end
"NO_TOOL_CALL") judges them once per request and writes the work-state file that SessionStart restores.
"""
import hashlib
import json
import os
import re
import tempfile

from ace_hosts import MAX_WRITES, Turn, finish_originals, skills_in, strings

AG_WRITES = {'write_to_file', 'replace_file_content', 'multi_replace_file_content', 'write_file', 'edit_file'}


def _ag_state_path(conversation):
    folder = os.path.join(tempfile.gettempdir(), 'ace-hook')
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, 'antigravity-%s.json' % hashlib.sha256(conversation.encode('utf-8')).hexdigest()[:24])


def ag_pre(event):
    """Antigravity PreToolUse event -> (tool name, argument text, latest user message, conversation state)."""
    call = event.get('toolCall') if isinstance(event.get('toolCall'), dict) else {}
    args = call.get('args') if isinstance(call.get('args'), dict) else {}
    state = {}
    conversation = event.get('conversationId')
    if isinstance(conversation, str) and conversation:
        try:
            with open(_ag_state_path(conversation), encoding='utf-8') as f:
                state = json.load(f)
        except (OSError, ValueError):
            state = {}
        token = hashlib.sha256(str(event.get('lastUserInput') or '').encode('utf-8')).hexdigest()
        if state.get('turn') != token:
            state = {'turn': token, 'db': []}
    return str(call.get('name') or ''), '\n'.join(strings(args)), str(event.get('lastUserInput') or ''), state


def ag_answer(reason):
    """PreToolUse output: deny with the reason, else "ask" = the host's normal permission flow. An empty object is a
    deny in Antigravity, and "allow" would skip the user's approval (both checked with agy -p, 2026-11-26)."""
    return json.dumps({'decision': 'deny', 'reason': reason}) if reason else json.dumps({'decision': 'ask'})


def antigravity(name, event, analyze):
    """One Antigravity hook event (cwd = plugin root). PostToolUse records; Stop judges once per user request."""
    if name == 'PreToolUse':
        return {'decision': 'allow'}
    conversation = event.get('conversationId')
    if not isinstance(conversation, str) or not conversation:
        return {}
    path = _ag_state_path(conversation)
    try:
        with open(path, encoding='utf-8') as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    last = str(event.get('lastUserInput') or '')
    token = hashlib.sha256(last.encode('utf-8')).hexdigest()
    skills = set(state.get('skills', []))
    hist = state.get('hist') if isinstance(state.get('hist'), dict) else {'users': [], 'files': [], 'procs': []}
    if state.get('turn') != token:
        state = {'turn': token, 'writes': [], 'db': [], 'need_connect': state.get('need_connect')}
        if last.strip():
            hist['users'] = (hist.get('users') or [])[-15:] + [last]
    state['hist'] = hist
    out = {}
    call = event.get('toolCall') if isinstance(event.get('toolCall'), dict) else {}
    args = call.get('args') if isinstance(call.get('args'), dict) else {}
    tool = str(call.get('name') or '')
    text = '\n'.join(strings(args))
    if name == 'PostToolUse' and event.get('error'):
        if 'sql' in tool.lower() and re.search(r'No active database connection|connect_database first', str(event['error'])):
            state['need_connect'] = tool  # ace_ag_context.py adds the hint before the next model call
    elif name == 'PostToolUse':
        skills |= skills_in(text)
        # 도구 이름: 예전 write_to_file/replace_file_content(TargetFile), 현재 write_file(Path, Content)·
        # edit_file(Path, Target, Replacement) (agy 2026-11-26 확인)
        target = args.get('TargetFile') or args.get('Path')
        if tool in AG_WRITES and isinstance(target, str) and len(state['writes']) < MAX_WRITES:
            whole = tool in ('write_to_file', 'write_file')
            if tool == 'edit_file':
                chunks, keys = [args], ('Target', 'Replacement')
            else:
                chunks = [args] if tool == 'replace_file_content' else args.get('ReplacementChunks') or []
                keys = ('TargetContent', 'ReplacementContent')
            hunks = [] if whole else [tuple(str(c.get(k, '')).replace('\r\n', '\n').split('\n') for k in keys)
                                      for c in chunks if isinstance(c, dict)]
            if whole:
                body = args.get('CodeContent') if tool == 'write_to_file' else args.get('Content')
            else:
                body = '\n'.join('\n'.join(h[1]) for h in hunks)
            state['writes'].append({'path': target, 'body': str(body or ''), 'hunks': hunks, 'added': whole})
            hist['files'] = [f for f in hist.get('files') or [] if f != target][-40:] + [target]
        elif 'sql' in tool.lower() or re.search(r'sqlcmd|Invoke-Sqlcmd', text, re.I):
            state['db'].append(text[:20000])
            import ace_apply_gate
            for p in sorted(ace_apply_gate.targets(text)):
                hist['procs'] = [x for x in hist.get('procs') or [] if x != p][-20:] + [p]
    elif name == 'Stop':
        save_work_state(event, hist)
        # 정상 종료는 NO_TOOL_CALL(호스트 문서). Stop 훅이 이어가게 한 작업 중(continuationActive)에는 다시 막지 않는다
        normal = event.get('terminationReason') in (None, '', 'NO_TOOL_CALL', 'model_stop')
        if event.get('fullyIdle') is True and normal and not event.get('continuationActive') and not state.get('blocked'):
            turn = Turn()
            turn.skills = skills
            for w in state['writes']:
                turn.add_write(w['path'], w['body'], added=w['added'], hunks=[tuple(h) for h in w['hunks']])
            turn.db = list(state['db'])
            turn.finals = [str(event.get(k) or '') for k in ('finalModelOutput', 'lastModelResponse', 'response')]
            reasons = analyze(finish_originals(turn))
            if reasons:
                state['blocked'] = True
                out = {'decision': 'continue', 'reason': '[ACE] ' + '\n\n'.join(reasons)}
    state['skills'] = sorted(skills)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)
    return out


def work_folder(event):
    paths = event.get('workspacePaths') if isinstance(event.get('workspacePaths'), list) else []
    return str(paths[0] if paths else event.get('cwd') or '')


def save_work_state(event, hist):
    """Same file as ace_state.py PreCompact (~/.claude/ace/state/<folder key>.md). Antigravity has no compaction
    event, so it is written at every Stop from what PostToolUse saw (user requests, files, SPs)."""
    import datetime
    import ace_state
    folder = work_folder(event)
    if not folder:
        return
    uniq = lambda xs: list(dict.fromkeys(reversed(xs)))
    lines = ['# ACE 작업 상태 (%s, Antigravity)' % datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), '',
             '폴더: %s' % folder, '', '## 최근 사용자 요청 (원문, 최신이 아래)', '']
    lines += ['- ' + ' '.join(u.split())[:300] for u in (hist.get('users') or [])[-8:]] or ['- 없음']
    lines += ['', '## 쓰거나 고친 파일 (최신 순)', ''] + (['- ' + f for f in uniq(hist.get('files') or [])[:25]] or ['- 없음'])
    lines += ['', '## DB에 만들거나 바꾼 SP', ''] + (['- ' + p for p in uniq(hist.get('procs') or [])[:15]] or ['- 없음'])
    lines += ['', '적용 전에는 해시를 다시 확인한다(다른 도구에서 바뀌었을 수 있다).']
    os.makedirs(ace_state.STATE_DIR, exist_ok=True)
    with open(os.path.join(ace_state.STATE_DIR, ace_state.key_of(folder) + '.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
