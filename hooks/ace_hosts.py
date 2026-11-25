"""Claude Code and Codex adapters for ace_stop_check.py (Antigravity: ace_antigravity.py): one Turn per stop.

Turn = skills used in the session, files written in the current turn (path, written text, original if it can be
rebuilt), DB tool inputs of the turn, and the final assistant messages. Standard library only.
"""
import json
import os
import re

DOC_PATH = re.compile(r'[\\/]skills[\\/]+(work|sql|csharp|pb|erp|review|style|comply|dispatch)[\\/]+references[\\/]'
                      r'|[\\/]ace[\\/]+lessons[\\/]+(work|sql|csharp|pb|erp)\.md', re.I)


def docs_in(text):
    return {(m.group(1) or m.group(2)).lower() for m in DOC_PATH.finditer(text or '')}


SKILL_PATH = re.compile(r'[\\/]ace[\\/](?:[^\s\'"`<>|]*?[\\/])?skills[\\/](work|sql|csharp|pb|erp)(?=[\\/\'"`\s]|$)', re.I)
HOST_BLOCK = ('<', '# AGENTS.md instructions')
JS_CONST = re.compile(r'\b(?:const|let|var)\s+(\w+)\s*=\s*(["\'`])((?:\\.|(?!\2).)*?)\2', re.S)
PATCH = re.compile(r'\*\*\* Begin Patch(.*?)\*\*\* End Patch', re.S)
MAX_WRITES = 64


class Turn:
    def __init__(self):
        self.skills, self.writes, self.db, self.finals = set(), [], [], []
        self.docs = set()  # ACE skills whose references/lessons were opened in the session

    def add_write(self, path, body='', original=None, added=False, hunks=()):
        """path None = written but the path is not known (a JS template the adapter cannot resolve)."""
        if len(self.writes) < MAX_WRITES:
            self.writes.append({'path': path, 'body': body, 'original': original, 'added': added,
                                'hunks': list(hunks)})


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def skills_in(text):
    return {m.group(1).lower() for m in SKILL_PATH.finditer(text or '')}


def read_jsonl(path):
    if path.endswith('.zst'):
        from compression import zstd  # Python 3.14+
        f = zstd.open(path, 'rt', encoding='utf-8')
    else:
        f = open(path, encoding='utf-8')
    out = []
    with f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if isinstance(d, dict):
                out.append(d)
    return out


def detect_host(records):
    for d in records[:20]:
        if d.get('type') in ('session_meta', 'turn_context', 'response_item', 'event_msg'):
            return 'codex'
    return 'claude'


# ---------------------------------------------------------------- apply_patch (Codex)

def _unescape_js(s):
    return re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t', 'r': ''}.get(m.group(1), m.group(1)), s, flags=re.S)


def _js_consts(text):
    consts = {}
    for name, _, value in JS_CONST.findall(text):
        consts.setdefault(name, _unescape_js(value))
    return consts


def _subst(text, consts):
    for _ in range(3):
        text = re.sub(r'\$\{(\w+)\}', lambda v: consts.get(v.group(1), v.group(0)), text)
    return text


def patches_in(text):
    """Every file block of every `*** Begin Patch` in a tool input (raw patch, JSON arguments or exec JS code)."""
    if not text or '*** Begin Patch' not in text:
        return []
    consts, out = _js_consts(text), []
    for m in PATCH.finditer(text):
        body = m.group(1)
        if body.count('\\n') > body.count('\n'):
            body = _unescape_js(body)
        out += _parse_patch(_subst(body, consts))
    return out


QUOTED = re.compile(r'[\'"`]([^\'"`\n$]{1,260})[\'"`]')


def mentioned_files(text, cwd):
    """Existing .sql/.cs files named by quoted literals in a tool input (shell writes such as WriteAllText):
    a path, or a bare file name joined with a quoted directory of the same input."""
    lits = [x.strip() for x in QUOTED.findall(_subst(text, _js_consts(text)))]
    base = cwd or os.getcwd()
    full = [os.path.normpath(x if os.path.isabs(x) else os.path.join(base, x)) for x in lits if 2 < len(x)]
    dirs = [p for p in full if os.path.isdir(p)][:20]
    out = set()
    for lit, p in zip([x for x in lits if 2 < len(x)], full):
        if not lit.lower().endswith(('.sql', '.cs')):
            continue
        tries = [p] if re.search(r'[\\/]', lit) else [p] + [os.path.join(d, lit) for d in dirs]
        out.update(t for t in tries if os.path.isfile(t))
    return out


def changed_since(path, since, text):
    """Replaceable (tests): did this turn change the file?"""
    return since is not None and os.path.getmtime(path) >= since - 1


def _parse_patch(body):
    files, cur, hunk = [], None, None
    for line in body.replace('\r\n', '\n').split('\n'):
        head = re.match(r'\*\*\* (Add|Update|Delete) File: (.+)$', line)
        if head:
            cur = None
            if head.group(1) != 'Delete':
                cur = {'path': head.group(2).strip(), 'added': head.group(1) == 'Add', 'lines': [], 'hunks': []}
                files.append(cur)
            hunk = None
        elif cur is None or line.startswith('*** End of File'):
            continue
        elif line.startswith('*** Move to: '):
            cur['path'] = line[13:].strip()
        elif cur['added']:
            if line.startswith('+'):
                cur['lines'].append(line[1:])
        elif line.startswith('@@'):
            hunk = ([], [])
            cur['hunks'].append(hunk)
        elif line[:1] in (' ', '-', '+', ''):
            if hunk is None:
                hunk = ([], [])
                cur['hunks'].append(hunk)
            if line[:1] != '+':
                hunk[0].append(line[1:])
            if line[:1] != '-':
                hunk[1].append(line[1:])
    for f in files:
        f['body'] = '\n'.join(f['lines']) if f['added'] else '\n'.join('\n'.join(h[1]) for h in f['hunks'])
        if '${' in f['path']:
            f['path'] = None
    return files


def reverse_hunks(text, hunks):
    """Undo hunks (in application order) on text; None if any hunk is not found."""
    for old, new in reversed(hunks):
        new_block, old_block = '\n'.join(new), '\n'.join(old)
        if not new_block.strip() or new_block not in text:
            return None
        text = text.replace(new_block, old_block, 1)
    return text


def read_file(path):
    try:
        with open(path, 'rb') as f:
            data = f.read()
        for enc in ('utf-8-sig', 'cp949'):
            try:
                return data.decode(enc).replace('\r\n', '\n')
            except UnicodeError:
                continue
    except OSError:
        pass
    return None


def finish_originals(turn, read=read_file):
    """Group a turn's patch writes per file and rebuild each file's text before the turn."""
    merged = {}
    for w in turn.writes:
        if not w['path']:
            continue
        key = os.path.normcase(os.path.abspath(w['path']))
        m = merged.setdefault(key, {'path': w['path'], 'body': '', 'added': False, 'hunks': [], 'original': None})
        m['body'] += '\n' + w['body']
        m['added'] = m['added'] or w['added']
        m['hunks'] += w['hunks']
        m['original'] = m['original'] or w['original']
    for m in merged.values():
        if not m['added'] and m['hunks'] and m['original'] is None:
            current = read(m['path'])
            m['original'] = reverse_hunks(current, m['hunks']) if current is not None else None
    turn.writes = [w for w in turn.writes if not w['path']] + list(merged.values())
    return turn


# ---------------------------------------------------------------- Claude Code

def _claude_real_user(d):
    if d.get('type') != 'user' or d.get('isMeta'):
        return False
    c = d['message'].get('content')
    if isinstance(c, str):
        return bool(c.strip()) and not c.lstrip().startswith('<')
    if isinstance(c, list):
        if any(isinstance(x, dict) and x.get('type') == 'tool_result' for x in c):
            return False
        return any(isinstance(x, dict) and x.get('type') == 'text' and x.get('text', '').strip()
                   and not x['text'].lstrip().startswith('<') for x in c)
    return False


def _claude_uses(entries):
    for d in entries:
        c = d['message'].get('content') if d.get('type') == 'assistant' else None
        for x in c if isinstance(c, list) else []:
            if isinstance(x, dict) and x.get('type') == 'tool_use' and isinstance(x.get('input'), dict):
                yield x.get('name') or '', x['input']


def claude_turn(records, event):
    entries = [d for d in records if d.get('type') in ('user', 'assistant') and isinstance(d.get('message'), dict)]
    turn = Turn()
    for name, inp in _claude_uses(entries):
        skill = str(inp.get('skill', '')).lower() if name == 'Skill' else ''
        if skill.startswith(('ace:', 'ace/')):
            turn.skills.add(skill[4:])
        turn.skills |= skills_in(' '.join(strings(inp)))
        turn.docs |= docs_in(' '.join(strings(inp)))
    start = max([i for i, d in enumerate(entries) if _claude_real_user(d)] or [0])
    window = entries[start:]
    # rule documents opened before this turn's first .sql/.cs write (reading them only afterwards does not count)
    before, first_write = set(), False
    for i, d in enumerate(entries):
        for name, inp in _claude_uses([d]):
            p = str(inp.get('file_path', '')).lower()
            if i >= start and name in ('Write', 'Edit', 'MultiEdit') and p.endswith(('.sql', '.cs')):
                first_write = True
                break
            before |= docs_in(' '.join(strings(inp)))
        if first_write:
            break
    turn.docs_before_write = before
    originals = {}
    for d in window:
        r = d.get('toolUseResult')
        if isinstance(r, dict) and r.get('filePath') and 'originalFile' in r:
            originals.setdefault(os.path.normcase(os.path.abspath(r['filePath'])), r.get('originalFile'))
    seen = set()
    for name, inp in _claude_uses(window):
        p = str(inp.get('file_path', ''))
        if name in ('Write', 'Edit', 'MultiEdit') and p:
            key = os.path.normcase(os.path.abspath(p))
            orig = originals.get(key)
            body = ' '.join(strings({k: v for k, v in inp.items() if k != 'file_path'}))
            if key in seen:
                for w in turn.writes:
                    if w['path'] and os.path.normcase(os.path.abspath(w['path'])) == key:
                        w['body'] += '\n' + body
                continue
            seen.add(key)
            turn.add_write(p, body, orig.replace('\r\n', '\n') if isinstance(orig, str) else None)
        elif 'mssql' in name.lower() or (name in ('Bash', 'PowerShell') and re.search(
                r'sqlcmd|Invoke-Sqlcmd', str(inp.get('command', '')), re.I)):
            turn.db.append(' '.join(strings(inp)))
    turn.finals.append(str(event.get('last_assistant_message') or ''))
    for d in reversed(window):
        if d.get('type') == 'assistant':
            c = d['message'].get('content')
            t = ' '.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text') \
                if isinstance(c, list) else str(c or '')
            if t.strip():
                turn.finals.append(t)
                break
    turn.finals += [str(inp.get('message', '')) for name, inp in _claude_uses(window) if name == 'SubagentHandback'][-1:]
    return turn


# ---------------------------------------------------------------- Codex

def _codex_user(p):
    texts = [x.get('text', '') for x in p.get('content') or [] if isinstance(x, dict)
             and x.get('type') in ('input_text', 'text')]
    return any(t.strip() and not t.lstrip().startswith(HOST_BLOCK) for t in texts)


def _codex_call(p):
    """(name, text) of a tool call payload, or None."""
    kind = p.get('type')
    if kind == 'custom_tool_call':
        return p.get('name') or '', str(p.get('input') or '')
    if kind == 'function_call':
        text = str(p.get('arguments') or '')
        if text.lstrip().startswith('{'):
            try:
                text = '\n'.join(strings(json.loads(text)))
            except ValueError:
                pass
        return p.get('name') or '', text
    if kind == 'local_shell_call':
        return 'shell', ' '.join(strings(p.get('action')))
    return None


def codex_turn(records, event):
    turn, cwd, start, by_id, last_user = Turn(), event.get('cwd'), None, None, 0
    for i, d in enumerate(records):
        t, p = d.get('type'), d.get('payload') if isinstance(d.get('payload'), dict) else {}
        if t == 'session_meta' and not cwd:
            cwd = p.get('cwd')
        elif t == 'turn_context' and p.get('cwd'):
            cwd = p['cwd']
        elif t == 'event_msg' and p.get('type') == 'task_started':
            start = i
            if event.get('turn_id') and p.get('turn_id') == event['turn_id']:
                by_id = i
        elif t == 'response_item' and p.get('type') == 'message' and p.get('role') == 'user' and _codex_user(p):
            last_user = i
        elif t == 'response_item':
            call = _codex_call(p)
            if call:
                turn.skills |= skills_in(call[1])
                turn.docs |= docs_in(call[1])
    start = by_id if by_id is not None else (start if start is not None else last_user)
    p0 = records[start].get('payload') if start < len(records) and isinstance(records[start].get('payload'), dict) else {}
    since = p0.get('started_at') if isinstance(p0.get('started_at'), (int, float)) else None
    final, shell = None, {}
    for d in records[start:]:
        t, p = d.get('type'), d.get('payload') if isinstance(d.get('payload'), dict) else {}
        if t == 'event_msg' and p.get('type') == 'task_complete' and p.get('last_agent_message'):
            final = p['last_agent_message']
        if t == 'response_item' and p.get('type') == 'message' and p.get('role') == 'assistant':
            text = ' '.join(x.get('text', '') for x in p.get('content') or [] if isinstance(x, dict))
            final = text if text.strip() else final
        call = _codex_call(p) if t == 'response_item' else None
        if not call:
            continue
        name, text = call
        for f in patches_in(text):
            path = f['path']
            if path and cwd and not os.path.isabs(path):
                path = os.path.normpath(os.path.join(cwd, path))
            turn.add_write(path, f['body'], added=f['added'], hunks=f['hunks'])
        if 'mssql' in name.lower() or 'mssql' in text.lower() or re.search(r'sqlcmd|Invoke-Sqlcmd', text, re.I):
            turn.db.append(re.sub(r'(?m)^\s*//\s*@exec:.*$', '', text))
        if re.search(r'WriteAllText|Set-Content|Out-File|Add-Content|Copy-Item|Move-Item', text):
            for p in mentioned_files(text, cwd):
                shell.setdefault(os.path.normcase(p), (p, text))
    known = {os.path.normcase(os.path.abspath(w['path'])) for w in turn.writes if w['path']}
    for key, (p, text) in shell.items():
        if key not in known and changed_since(p, since, text):
            turn.add_write(p)
    turn.finals += [str(event.get('last_assistant_message') or ''), final or '']
    return finish_originals(turn)
