"""ACE Stop/SubagentStop hook for Claude Code, Codex and Google Antigravity. Prints nothing when fine.

  python -B ace_stop_check.py [--host claude|codex|antigravity|auto] [<Antigravity event>]

sql (or erp) skill used in the session: blocks once if this turn wrote or applied an SP with neither execution
evidence (rollback test, EXCEPT comparison) nor `실행 검증: 하지 않음 - <이유>`, or if a written SP fails check_sql.py.
csharp (or erp) skill used: blocks once if a written .cs fails check_designer.py (against the turn's original
when it can be rebuilt). No ACE skill used: blocks once to load it (csharp and erp together for a framework screen),
except for a small code-behind change (SMALL_LINES changed lines per file, SMALL_FILES files at most, no Designer file, no .sql, no caption/text
assignment): then only check_designer.py runs and blocks on a failure. Never blocks twice for one stop (stop_hook_active), never on its own errors;
ACE_HOOK=off turns it off. Host adapters: ace_hosts.py (Claude Code, Codex), ace_antigravity.py.
"""
import difflib
import json
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ace_antigravity  # noqa: E402
import ace_hosts  # noqa: E402

PROC = re.compile(r'\b(CREATE|ALTER)\s+(OR\s+ALTER\s+)?PROC(EDURE)?\b', re.I)
REAL_PROC = re.compile(r'\b(CREATE|ALTER)\s+(OR\s+ALTER\s+)?PROC(EDURE)?\s+(?!#)[\w\[]', re.I)
SKIP_REASON = re.compile(r'실행\s*검증\s*:\s*하지\s*않음\s*[-–—:]\s*\S')
COPY_NAME = re.compile(r'orig|backup|bak|before|원본', re.I)  # comparison copies are not deliverables
FIXTURE_DIR = re.compile(r'[\\/]comply(?:_\w+)?[\\/]', re.I)  # comply scenario fixtures and graded runs
MAX_LINES = 15
SMALL_LINES = 15  # changed lines per file
SMALL_FILES = 3   # files per turn
# A changed line that touches what the user sees or the designer: never a "small" change. Any string literal counts
# (a caption split over lines, a message text), and so do resources and the designer method.
CAPTION = re.compile(r'\.(Text|Caption|ToolTip|NullText|Hint)\s*\+?=(?!=)|Properties\.Items\.Add|ApplyResources'
                     r'|\bResources\b|\bInitializeComponent\b|["\']|[\uac00-\ud7a3]')
DESIGNER_IN_FILE = re.compile(r'\bvoid\s+InitializeComponent\s*\(')
MULTILINE_STRING = re.compile(r'"""|@"[^"\n]*\n|\$@"[^"\n]*\n|@\$"[^"\n]*\n')


def checker(skill='sql', module='check_sql'):
    """skills/<skill>/scripts/<module>.py next to this hook."""
    scripts = os.path.join(ROOT, 'skills', skill, 'scripts')
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    return __import__(module)


def used(turn, skill):
    """erp sits on top of sql and csharp, so a erp task gets both checks (split by file extension)."""
    return skill in turn.skills or 'erp' in turn.skills


def fail_block(fails, script):
    more = len(fails) - MAX_LINES
    return (script + ' 실패 항목. 이번에 쓰거나 고친 부분이면 고친 뒤 다시 돌려라. '
            '요청 범위 밖의 기존 코드면 고치지 말고 답변에 그렇게 적어라:\n' + '\n'.join(fails[:MAX_LINES])
            + ('\n- 외 %d개' % more if more > 0 else ''))


def deliverables(turn, ext):
    return [w for w in turn.writes if (w['path'] or '').lower().endswith(ext)
            and not COPY_NAME.search(os.path.basename(w['path'])) and not FIXTURE_DIR.search(w['path'])]


def failures(ck, path, results):
    return ['- %s: %s: %s' % (os.path.basename(path), item, ' / '.join(x for x in (ck.fmt_lines(ls, 8), note) if x))
            for st, item, ls, note in results if st == ck.FAIL]


def sql_reasons(turn):
    if not used(turn, 'sql'):
        return []
    sp_files = []
    for w in deliverables(turn, '.sql'):
        if not os.path.isfile(w['path']):  # a path only named in a command or a test string
            continue
        if PROC.search(w['body']) or PROC.search(ace_hosts.read_file(w['path']) or ''):
            sp_files.append(w['path'])
    unnamed_sp = any(not w['path'] and PROC.search(w['body']) for w in turn.writes)
    applied = evidence = False
    for q in turn.db:
        # 실제 SP 생성·변경(임시 #프로시저와 문자열 안의 'CREATE PROCEDURE'는 제외), 또는 동적 ALTER 적용
        real = REAL_PROC.search(q)
        if real or (re.search(r"N?'ALTER'", q) and re.search(r'\bEXEC(UTE)?\s*\(', q, re.I)):
            applied = True
        # 롤백 테스트·EXCEPT 비교. 임시 프로시저로 새 버전을 만들어 돌리는 비교 배치도 검증이다
        if not real and ((re.search(r'\bROLLBACK\b', q, re.I) and re.search(r'\bEXEC(UTE)?\s+[\w\[#@]', q, re.I))
                         or re.search(r'\bEXCEPT\b', q, re.I)):
            evidence = True
    if not (sp_files or applied or unnamed_sp):
        return []
    reasons = []
    if not evidence and not any(SKIP_REASON.search(t or '') for t in turn.finals):
        reasons.append('SP를 고쳤는데 실행 검증을 하지 않았다. references/verify-save.md대로 실행해서 시나리오 표에 '
                       '숫자를 적거나, 실행할 수 없으면 답변에 `실행 검증: 하지 않음 - <이유>`를 적어라.')
    fails = []
    try:
        ck = checker()
    except Exception:
        ck = None
    for p in sp_files if ck else []:
        try:
            fails += failures(ck, p, ck.run_checks(ck.read_sql(p), 'unknown')[0])
        except Exception:  # one unreadable file never hides another file's failures
            continue
    if fails:
        reasons.append(fail_block(fails, 'check_sql.py'))
    return reasons


def changed_lines(w):
    """Changed (added + removed) lines of one write against the turn's original; None when unknown."""
    if w.get('added') or not w.get('path') or not os.path.isfile(w['path']):
        return None
    if w.get('original') is None:  # newer Claude Code: hunks only (ace_hosts patch_lines), else unknown
        return w.get('patch_lines')
    cur = ace_hosts.read_file(w['path'])
    if cur is None:
        return None
    cur = cur.replace('\r\n', '\n')
    diff = list(difflib.unified_diff(w['original'].splitlines(), cur.splitlines(), lineterm='', n=0))[2:]
    return [l[1:] for l in diff if l[:1] in '+-']


def small_change(files, turn=None):
    """A small code-behind edit (an event hookup, a condition): the rule documents add nothing there, the checker
    still runs. Designer code, SPs, captions/strings (the 2026-11-25 label case) and new files are never small.
    Claude Code only: its tool results carry the exact original; Codex/Antigravity originals are rebuilt from patches
    and can miss shell edits, so those hosts keep the full check. A turn at the write cap is never small."""
    if turn is not None and (getattr(turn, 'host', None) != 'claude' or len(turn.writes) >= ace_hosts.MAX_WRITES
                             or getattr(turn, 'shell_writes', False)):
        return False  # a file changed through the shell is not in the turn's writes: its size is unknown
    if not files or len(files) > SMALL_FILES:  # the same small fix on a few screens; more is a real change
        return False
    for w in files:
        path = (w.get('path') or '').lower()
        if not path.endswith('.cs') or path.endswith('.designer.cs'):
            return False
        text = ace_hosts.read_file(w['path']) or ''
        if DESIGNER_IN_FILE.search(text) or MULTILINE_STRING.search(text):
            return False
        lines = changed_lines(w)
        if lines is None or len(lines) > SMALL_LINES or any(CAPTION.search(l) for l in lines):
            return False
    return True


def csharp_reasons(turn, force=False):
    if not (force or used(turn, 'csharp')):
        return []
    fails, broken = [], []
    try:
        ck = checker('csharp', 'check_designer')
    except Exception:
        ck = None
    for w in deliverables(turn, '.cs'):
        if not os.path.isfile(w['path']):
            continue
        try:
            fails += failures(ck, w['path'], ck.run(w['path'], orig_text=w['original'])[0])
        except Exception:  # one file the checker cannot read never hides another file's failures
            broken.append(os.path.basename(w['path']))
    reasons = [fail_block(fails, 'check_designer.py')] if fails else []
    if force and broken:  # the skill check was skipped for this small change, so the checker must have run
        reasons.append('작은 수정이라 스킬 확인을 건너뛰었지만 check_designer.py를 돌리지 못했다(%s). csharp 스킬을 불러 '
                       '고친 내용을 규칙과 다시 맞춰 본 뒤 답변을 마쳐라.' % ', '.join(broken[:4]))
    return reasons


def framework_pattern():
    """Framework screens by the local profile (<profile>/profile.json base_forms, framework_markers,
    project_path_regex). No profile → no framework check: real names never ship in the repo."""
    d = os.environ.get('ACE_PROFILE_DIR') or os.path.join(os.path.expanduser('~'), '.claude', 'ace', 'profile')
    try:
        with open(os.path.join(d, 'profile.json'), encoding='utf-8') as f:
            prof = json.load(f)
    except (OSError, ValueError):
        return None
    parts = [r':\s*' + re.escape(b) + r'\b' for b in prof.get('base_forms') or []]
    parts += [re.escape(m) for m in prof.get('framework_markers') or []]
    if prof.get('project_path_regex'):
        parts.append(prof['project_path_regex'])
    try:
        return re.compile('|'.join(parts), re.I) if parts else None
    except re.error:
        return None


FRAMEWORK = framework_pattern()
LANG = {'.sql': 'sql', '.cs': 'csharp'}


def doc_files(turn):
    """.sql/.cs deliverables that exist (a path only mentioned in a command or a test string is not an edit)."""
    return [w for ext in LANG for w in deliverables(turn, ext) if w['path'] and os.path.isfile(w['path'])]


def is_framework(files):
    """A framework screen or SP: the profile's path pattern for any file, base forms/markers in .cs content."""
    return bool(FRAMEWORK) and any(
        FRAMEWORK.search(w['path']) or (w['path'].lower().endswith('.cs')
                                        and FRAMEWORK.search((ace_hosts.read_file(w['path']) or '')[:20000]))
        for w in files)


def doc_reasons(turn, small=False):
    """An ACE skill was loaded but none of its rule documents were opened before files were written, or a framework
    screen was changed without the erp skill (a label change where only the csharp SKILL.md was read, 2026-11-25).
    Nothing for a small code-behind change (small_change): its checker runs instead."""
    files = doc_files(turn)
    if not files or small:
        return []
    fw = is_framework(files)
    langs = {LANG[os.path.splitext(w['path'])[1].lower()] for w in files}
    missing = (langs | ({'erp'} if fw else set())) - turn.skills
    if 'erp' in turn.skills:
        missing -= {'sql', 'csharp'}  # erp carries both language checks
    reasons = []
    if missing:  # every missing skill in one block, never one per stop
        reasons.append('SQL·C# 파일을 고쳤는데 필요한 ACE 스킬을 쓰지 않았다(%s). %s 스킬을 함께 불러 lessons.md와 작업 표의 '
                       '문서를 읽고, 고친 내용을 그 규칙과 다시 맞춰 본 뒤 답변을 마쳐라.'
                       % (', '.join(os.path.basename(w['path']) for w in files[:4]), '·'.join(sorted(missing))))
    read = getattr(turn, 'docs_before_write', None)
    read = turn.docs if read is None else read
    unread = sorted(s for s in (langs | ({'erp'} & turn.skills)) if s in turn.skills and s not in read)
    if unread:
        reasons.append('ACE 스킬(%s)을 불렀지만 규칙 문서를 하나도 열지 않고 파일을 고쳤다. 각 스킬의 references/lessons.md와 '
                       'SKILL.md 작업 표가 가리키는 문서(예: 보고서는 csharp references/reports.md)를 읽고, 고친 내용을 '
                       '그 규칙과 다시 맞춰 본 뒤 답변을 마쳐라.' % ', '.join(unread))
    return reasons


def analyze(turn):
    """Reasons to block; empty when fine."""
    files = doc_files(turn)
    small = small_change(files, turn)
    return doc_reasons(turn, small) + sql_reasons(turn) + csharp_reasons(turn, force=small)


def stop_hook(data, host):
    path = data.get('agent_transcript_path') or data.get('transcript_path')
    if not path or not os.path.isfile(os.path.expanduser(path)):
        return None
    records = ace_hosts.read_jsonl(os.path.expanduser(path))
    if host == 'auto':
        host = ace_hosts.detect_host(records)
    turn = (ace_hosts.codex_turn if host == 'codex' else ace_hosts.claude_turn)(records, data)
    turn.host = host
    reasons = analyze(turn)
    return {'decision': 'block', 'reason': '[ACE] ' + '\n\n'.join(reasons)} if reasons else None


def main(argv):
    host = argv[argv.index('--host') + 1] if '--host' in argv[:-1] else 'auto'
    event = next((a for a in argv if a in ('PreInvocation', 'PreToolUse', 'PostToolUse', 'Stop')), 'Stop')
    out = None
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8-sig', 'replace') or '{}')
        if not isinstance(data, dict) or os.environ.get('ACE_HOOK', '').strip().lower() == 'off':
            pass
        elif host == 'antigravity':
            out = ace_antigravity.antigravity(event, data, analyze)
        elif not data.get('stop_hook_active'):
            out = stop_hook(data, host)
    except Exception:
        out = None
    if host == 'antigravity':  # this host always expects one JSON object
        out = out if isinstance(out, dict) else ({'decision': 'allow'} if event == 'PreToolUse' else {})
    if out is not None:
        sys.stdout.write(json.dumps(out))


if __name__ == '__main__':
    main(sys.argv[1:])
    sys.exit(0)
