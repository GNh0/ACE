"""Antigravity adapter for ace_stop_check.py. The host starts hooks with cwd = plugin root and sends no transcript:
PostToolUse events are kept per conversation in %TEMP%/ace-hook/, and Stop (fullyIdle) judges them once per request.
"""
import hashlib
import json
import os
import re
import tempfile

from ace_hosts import MAX_WRITES, Turn, finish_originals, skills_in, strings

AG_WRITES = {'write_to_file', 'replace_file_content', 'multi_replace_file_content'}


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
    token = hashlib.sha256(str(event.get('lastUserInput') or '').encode('utf-8')).hexdigest()
    skills = set(state.get('skills', []))
    if state.get('turn') != token:
        state = {'turn': token, 'writes': [], 'db': []}
    out = {}
    call = event.get('toolCall') if isinstance(event.get('toolCall'), dict) else {}
    args = call.get('args') if isinstance(call.get('args'), dict) else {}
    tool = str(call.get('name') or '')
    text = '\n'.join(strings(args))
    if name == 'PostToolUse' and not event.get('error'):
        skills |= skills_in(text)
        target = args.get('TargetFile')
        if tool in AG_WRITES and isinstance(target, str) and len(state['writes']) < MAX_WRITES:
            chunks = [args] if tool == 'replace_file_content' else args.get('ReplacementChunks') or []
            hunks = [tuple(str(c.get(k, '')).replace('\r\n', '\n').split('\n')
                           for k in ('TargetContent', 'ReplacementContent')) for c in chunks if isinstance(c, dict)]
            body = args.get('CodeContent') if tool == 'write_to_file' else '\n'.join('\n'.join(h[1]) for h in hunks)
            state['writes'].append({'path': target, 'body': str(body or ''), 'hunks': hunks,
                                    'added': tool == 'write_to_file'})
        elif 'sql' in tool.lower() or re.search(r'sqlcmd|Invoke-Sqlcmd', text, re.I):
            state['db'].append(text[:20000])
    elif name == 'Stop' and event.get('fullyIdle') is True and event.get('terminationReason') in (None, 'model_stop') \
            and not state.get('blocked'):
        turn = Turn()
        turn.skills = skills
        for w in state['writes']:
            turn.add_write(w['path'], w['body'], added=w['added'], hunks=[tuple(h) for h in w['hunks']])
        turn.db = list(state['db'])
        turn.finals = [str(event.get(k) or '') for k in ('lastModelResponse', 'response', 'finalResponse')]
        reasons = analyze(finish_originals(turn))
        if reasons:
            state['blocked'] = True
            out = {'decision': 'continue', 'reason': '[ACE] ' + '\n\n'.join(reasons)}
    state['skills'] = sorted(skills)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)
    return out
