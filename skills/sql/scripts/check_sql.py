"""ACE sql 기계 점검. 사용법:
python check_sql.py <파일.sql> [--caller trn|plain|unknown|<프로필의 저장 호출 이름>] [--original <원본.sql>]
프레임워크 이름(채번 테이블·채번 SP·마스터 테이블·저장 호출)은 로컬 프로필 <profile>/profile.json에서 읽는다
(기본 ~/.claude/ace/profile, $ACE_PROFILE_DIR; 형식 skills/erp/data/profile.example.json). 없으면 그 항목은 건너뛴다.
마지막 줄은 'ACE-CHECK: PASS 통과/판정' 또는 'ACE-CHECK: FAIL 통과/판정'. 실패가 있으면 종료 코드 1.
"""
import argparse
import io
import json
import os
import re
import sys

PASS, FAIL, CHECK = '통과', '실패', '확인'


def load_profile():
    d = os.environ.get('ACE_PROFILE_DIR') or os.path.join(os.path.expanduser('~'), '.claude', 'ace', 'profile')
    try:
        with io.open(os.path.join(d, 'profile.json'), encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


PROFILE = load_profile()
NUMBER_TABLE = (PROFILE.get('number_table') or '').upper()      # 채번 테이블: 직접 쓰기 금지
NUMBERING_SP = (PROFILE.get('numbering_sp') or '').upper()      # 공통 채번 SP: 행마다 부르는 루프만 예외
MASTER = PROFILE.get('master_table_regex') or ''                # 마스터 테이블 이름 정규식: LEFT OUTER JOIN
SAVE_CALLS = {k.lower(): v for k, v in (PROFILE.get('save_calls') or {}).items()}  # 저장 호출 이름 → trn/plain
STMT = (r'INSERT|UPDATE|DELETE|MERGE|IF|ELSE|EXEC|EXECUTE|SET|DECLARE|END|BEGIN|WHILE|RETURN|RAISERROR'
        r'|PRINT|TRUNCATE|DROP|CREATE|ALTER|COMMIT|ROLLBACK|THROW|FETCH|OPEN|CLOSE|DEALLOCATE')
TYPES = (r'\b(VARCHAR|NVARCHAR|CHAR|NCHAR|INT|BIGINT|SMALLINT|TINYINT|NUMERIC|DECIMAL|DATETIME2?|DATE'
         r'|BIT|FLOAT|MONEY|TEXT|NTEXT|XML|UNIQUEIDENTIFIER|VARBINARY)\b')


def read_sql(path):
    """utf-8-sig → utf-16 → cp949. utf-16은 BOM이나 NUL 바이트가 있을 때만 시도한다(오판 방지)."""
    with io.open(path, 'rb') as f:
        data = f.read()
    encs = ['utf-8-sig', 'cp949']
    if data[:2] in (b'\xff\xfe', b'\xfe\xff') or b'\x00' in data[:200]:
        encs.insert(1, 'utf-16' if data[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-16-le')
    for enc in encs:
        try:
            return data.decode(enc).replace('\r\n', '\n').replace('\r', '\n')
        except UnicodeError:
            continue
    raise ValueError('인코딩을 읽을 수 없음: ' + path)


def mask(sql):
    """주석은 공백, 문자열·[...]·"..." 안은 '_'로 바꾼다. 길이와 줄 위치는 그대로."""
    out, i, n = list(sql), 0, len(sql)

    def blank(a, b, ch):
        for k in range(a, b):
            if out[k] != '\n':
                out[k] = ch

    while i < n:
        c = sql[i]
        if sql.startswith('--', i):
            j = sql.find('\n', i)
            j = n if j < 0 else j
            blank(i, j, ' ')
            i = j
        elif sql.startswith('/*', i):
            depth, j = 1, i + 2
            while j < n and depth:
                if sql.startswith('/*', j):
                    depth, j = depth + 1, j + 2
                elif sql.startswith('*/', j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            blank(i, j, ' ')
            i = j
        elif c in "'[\"":
            close = {'\'': '\'', '[': ']', '"': '"'}[c]
            j = i + 1
            while j < n:
                if sql[j] == close:
                    if j + 1 < n and sql[j + 1] == close:
                        j += 2
                        continue
                    break
                j += 1
            blank(i + 1, j, '_')
            i = j + 1
        else:
            i += 1
    return ''.join(out)


def line_of(text, pos):
    return text.count('\n', 0, pos) + 1


def find_lines(pattern, code, flags=0):
    return sorted({line_of(code, m.start()) for m in re.finditer(pattern, code, flags)})


def statement_end(lines, start):
    """start 줄(0부터)에서 시작한 문장이 끝나는 줄. 같은 들여쓰기 이하의 다음 문장 앞까지."""
    base = len(lines[start]) - len(lines[start].lstrip())
    if ';' in lines[start]:
        return start
    is_update = re.match(r'\s*UPDATE\b', lines[start].upper())
    for k in range(start + 1, len(lines)):
        s = lines[k].strip()
        if not s:
            continue
        ind = len(lines[k]) - len(lines[k].lstrip())
        if is_update and re.match(r'SET\b', s.upper()):
            continue
        if ind <= base and re.match(r'(%s)\b' % STMT, s.upper()):
            return k - 1
        if ';' in s:
            return k
    return len(lines) - 1


LJ_OP = r'(?:>=|<=|<>|!=|>|<|\*|/)'
LJ_START = re.compile(r'\s*(SELECT|UPDATE|DELETE|INSERT|IF|WHILE|SET)\b')


def left_join_bare(up, lines):
    """Lines where a column of a LEFT OUTER JOINed alias is compared or multiplied/divided without ISNULL.
    The alias is looked up only inside the statement that joins it (aliases are reused across statements)."""
    offs = [0]
    for l in lines:
        offs.append(offs[-1] + len(l) + 1)
    hits = set()
    for m in re.finditer(r'\bLEFT\s+(?:OUTER\s+)?JOIN\s+', up):
        k = m.end()
        if k < len(up) and up[k] == '(':
            depth = 0
            while k < len(up):
                depth += {'(': 1, ')': -1}.get(up[k], 0)
                k += 1
                if depth == 0:
                    break
            a = re.match(r'\s*(?:AS\s+)?(\w+)', up[k:])
        else:
            a = re.match(r'[\w\.\[\]@#]+\s+(?:AS\s+)?(?!ON\b)(\w+)', up[k:])
        if not a:
            continue
        alias, jl = a.group(1), line_of(up, m.start()) - 1
        ind = len(lines[jl]) - len(lines[jl].lstrip())
        st = next((i for i in range(jl - 1, -1, -1)
                   if LJ_START.match(lines[i]) and len(lines[i]) - len(lines[i].lstrip()) < ind), 0)
        en = statement_end(lines, st)
        seg = up[offs[st]:offs[en + 1]]
        for u in re.finditer(r'(?<![\w.])%s\.\w+' % re.escape(alias), seg):
            s, e = u.start(), u.end()
            if re.search(r'ISNULL\s*\(\s*$', seg[max(0, s - 12):s]):
                continue
            if re.match(r'\s*' + LJ_OP, seg[e:e + 4]) or re.search(LJ_OP + r'\s*$', seg[max(0, s - 4):s]):
                hits.add(line_of(up, offs[st] + s))
    return sorted(hits)


def write_targets(raw, code):
    """INSERT/UPDATE/DELETE/MERGE 대상. [(테이블, 줄)] 별칭은 같은 문장의 FROM/JOIN에서 찾는다."""
    lines, up = code.split('\n'), code.upper()
    raw_lines = raw.split('\n')
    res = []
    pat = r'\b(?:INSERT\s+(?:INTO\s+)?|MERGE\s+(?:INTO\s+)?|UPDATE\s+|DELETE\s+(?:FROM\s+)?)([@#\w.\[\]]+)'
    for m in re.finditer(pat, up):
        ln = line_of(up, m.start())
        tok_raw = raw[m.start(1):m.end(1)]
        name = tok_raw.replace('[', '').replace(']', '').split('.')[-1].upper()
        if name in ('SET', 'FROM', 'TOP', 'STATISTICS'):
            continue
        if not name.startswith(('@', '#')):
            end = statement_end(lines, ln - 1)
            seg = '\n'.join(raw_lines[ln - 1:end + 1]).upper()
            alias = re.search(r'(?:FROM|JOIN)\s+([@#\w.\[\]]+)\s+(?:AS\s+)?%s\b' % re.escape(name), seg)
            if alias and re.match(r'(?:UPDATE|DELETE)', m.group(0)):
                name = alias.group(1).replace('[', '').replace(']', '').split('.')[-1].upper()
        res.append((name, ln))
    return res


def is_save_sql(raw, code):
    if re.search(r'\bOPENXML\b', code, re.I):
        return True
    return any(not t.startswith(('@', '#')) for t, _ in write_targets(raw, code))


def raiserror_msgs(raw, code):
    msgs = {}
    for m in re.finditer(r'\bRAISERROR\s*\(\s*N?\'', code, re.I):
        s = m.end()
        e = raw.find("'", s)
        while e >= 0 and raw.startswith("''", e):
            e = raw.find("'", e + 2)
        msgs.setdefault(raw[s:e], line_of(code, m.start()))
    return msgs


def run_checks(raw, caller='unknown', original=None):
    """[(상태, 항목, [줄], 비고)], is_save"""
    code = mask(raw)
    up = code.upper()
    lines, raw_lines = up.split('\n'), raw.split('\n')
    save = is_save_sql(raw, code)
    r = []

    def item(name, hit_lines, note='', fail_state=FAIL):
        r.append((fail_state if hit_lines else PASS, name, hit_lines, note))

    if save:
        tx = find_lines(r'\bBEGIN\s+TRAN(SACTION)?\b|\bSAVE\s+TRAN(SACTION)?\b|\bCOMMIT\b|\bROLLBACK\b'
                        r'|\bBEGIN\s+TRY\b|\bBEGIN\s+CATCH\b|\bTHROW\b|\bXACT_ABORT\b|\bXACT_STATE\b'
                        r'|\w*TRANCOUNT\b', up)
        # 프레임워크: 호출부 저장 호출이 트랜잭션 위치를 정한다(erp save-call.md). trn = 호출부 트랜잭션, plain = 없음
        c = (caller or 'unknown').lower()
        c = SAVE_CALLS.get(c, c)
        if c == 'trn':
            item('트랜잭션 코드 없음(호출부가 트랜잭션)', tx)
        elif c == 'plain':
            r.append((PASS if tx else FAIL, '트랜잭션 코드 유지(호출부 트랜잭션 없음)', [],
                      '' if tx else '트랜잭션 없는 호출인데 SP에 트랜잭션이 없다'))
        else:
            r.append((CHECK, '트랜잭션 코드(호출부 미확인)', tx,
                      '트랜잭션 코드 있음' if tx else '트랜잭션 코드 없음. 호출부가 트랜잭션을 열 때만 맞다'))
        # 프레임워크: 공통 채번 SP를 행마다 부르는 루프만 예외(erp common-sp.md)
        loops = find_lines(r'\bWHILE\b|\bCURSOR\b', up)
        if loops and NUMBERING_SP and NUMBERING_SP in up:
            r.append((CHECK, '루프(WHILE·커서) 없음', loops, '채번 SP를 행마다 부르는 예외인지 확인'))
        else:
            item('루프(WHILE·커서) 없음', loops)
        item('건수 변수·@@ROWCOUNT 없음', find_lines(r'@@ROWCOUNT\b|@(?!\w*TRANCOUNT\b)\w*(CNT|COUNT)\b', up))
        item('MAX 순번 변수 없음', find_lines(r'\bSELECT\s+@\w+\s*=\s*(ISNULL\s*\(\s*)?MAX\s*\(', up))
        inter = []
        for m in re.finditer(r'\bINSERT\s+(INTO\s+)?[@#]\w+', up):
            ln = line_of(up, m.start())
            seg = '\n'.join(lines[ln - 1:statement_end(lines, ln - 1) + 1])
            if 'OPENXML' not in seg:
                inter.append(ln)
        item('중간 결과 테이블(XML 파싱 외) 없음', inter)
        item('OUTPUT INSERTED/DELETED 없음', find_lines(r'\bOUTPUT\s+(INSERTED|DELETED)\b', up))
        # 프레임워크: 채번은 공통 채번 SP로만
        if NUMBER_TABLE:
            item('채번 테이블(%s) 직접 쓰기 없음' % NUMBER_TABLE,
                 sorted({ln for t, ln in write_targets(raw, code) if t == NUMBER_TABLE}))
    item('잠금 힌트 없음', find_lines(r'\b(UPDLOCK|HOLDLOCK|ROWLOCK|PAGLOCK|TABLOCKX?|XLOCK|NOLOCK|READPAST)\b', up))
    item('120자 이하', [i + 1 for i, l in enumerate(raw_lines) if len(l) > 120])
    item('탭 문자 없음', [i + 1 for i, l in enumerate(raw_lines) if '\t' in l])
    lower = [i + 1 for i, l in enumerate(code.split('\n'))
             if any(re.search('[a-z]', t) for t in re.findall(r'(?<![\w@#$])[A-Za-z_@#][\w@#$]*', l))]
    item('리터럴·주석·[...] 밖 소문자 없음', lower)
    item('LEFT/RIGHT/FULL JOIN에 OUTER', find_lines(r'\b(LEFT|RIGHT|FULL)\s+JOIN\b', up))
    item('선행 쉼표(줄 끝 쉼표 없음)', [i + 1 for i, l in enumerate(lines) if l.rstrip().endswith(',')])
    right = []
    for i, l in enumerate(lines):
        m = re.match(r'( *)(FROM|WHERE)\b', l)
        head = next((x for x in reversed(lines[max(0, i - 40):i]) if re.match(r'\s*SELECT\b', x)), None)
        if m and head is not None:
            diff = len(m.group(1)) - (len(head) - len(head.lstrip()))
            if diff == {'FROM': 2, 'WHERE': 1}[m.group(2)]:
                right.append(i + 1)
    item('오른쪽 맞춤 절(  FROM / WHERE) 없음', right)
    sub = re.sub(r'\bIF\s+(NOT\s+)?EXISTS\b', lambda m: ' ' * len(m.group(0)), up)
    item('WHERE의 EXISTS/IN 서브쿼리 없음',
         find_lines(r'\b(WHERE|AND|OR)\s+(NOT\s+)?EXISTS\s*\(|\bIN\s*\(\s*SELECT\b', sub))
    item('모드 조건을 쿼리 WHERE에 넣지 않음', find_lines(r'\bWHERE\s+\(?\s*@WORKTYPE\s*(IN\b|=|<>)', up))
    one = [line_of(up, m.start()) for m in re.finditer(r'\bINSERT\s+(INTO\s+)?[@#\w.\[\]_]+\s*\(([^)\n]*)\)', up)
           if m.group(2).count(',') >= 2]
    item('INSERT 열 목록을 한 줄로 쓰지 않음', one)
    single = []
    for m in re.finditer(r'\bINSERT\s+(INTO\s+)?[@#\w.\[\]_]+\s*\n\s*\(\s*\n(.*?)\n\s*\)', up, re.S):
        rows = m.group(2).split('\n')
        first = line_of(up, m.start(2))
        for k, row in enumerate(rows[:-1]):
            if re.match(r'^\s*,?\s*[\w@#]+\s*$', row):
                single.append(first + k)
    item('INSERT 열 목록에 한 칸짜리 줄 없음(마지막 줄 제외)', single)
    multi = []
    for m in re.finditer(r'(\bDECLARE\s+@\w+\s+TABLE|\bOPENXML\s*\([^)]*\)\s*WITH)\s*\((.*?)\n\s*\)', up, re.S):
        first = line_of(up, m.start(2))
        for k, row in enumerate(m.group(2).split('\n')):
            if len(re.findall(TYPES, row)) >= 2:
                multi.append(first + k)
    item('테이블 변수·OPENXML WITH 열은 한 줄에 하나', sorted(set(multi)))
    item('긴 값 때문에 벌어진 칸(20칸 이상 공백) 없음', find_lines(r'\S {20,},', up))
    agg = [line_of(up, m.start()) for m in re.finditer(r'\b(SUM|MAX|MIN|AVG)\s*\([^()]*(\([^()]*\)[^()]*)*\)\s+AS\s+QTY\b', up)
           if up[:m.start()].count('(') > up[:m.start()].count(')')]
    item('파생 테이블 집계 열 이름이 QTY가 아님', agg)
    twice = []
    for i, l in enumerate(lines):
        # AND/OR 등으로 나눈 비교식 하나에 QTY가 두 번 이상
        for part in re.split(r'\b(?:AND|OR|WHERE|ON|WHEN|THEN|ELSE|IF|CASE|END)\b', l):
            if re.search(r'<=|>=|<(?!>)|(?<!<)>', part) and len(re.findall(r'(?<!@)\bQTY\b', part)) >= 2:
                twice.append(i + 1)
                break
    item('한 비교식에 QTY 두 번 없음', twice)
    # 사용자는 CTE와 #임시 테이블을 쓰지 않는다. 파생 테이블 JOIN이나 테이블 변수로 쓴다.
    item('CTE(WITH … AS) 없음', find_lines(r'(^|;)\s*WITH\s+\w+\s*(\([^)]*\))?\s*AS\s*\(', up, re.M))
    item('#임시 테이블 없음', find_lines(r'\bCREATE\s+TABLE\s+#|\bINTO\s+#\w+', up))
    # JOIN 줄에 ON을 붙이지 않는다(ON은 다음 줄, JOIN의 I 아래). 한 줄짜리 IF EXISTS 검증은 제외
    item('ON은 JOIN 다음 줄', [i + 1 for i, l in enumerate(lines)
                               if re.search(r'\bJOIN\b.*\bON\b', l)
                               and not re.match(r'\s*IF\s+(NOT\s+)?EXISTS\b', l)
                               and not re.search(r'\bON\s*\(?\s*1\s*=\s*1\b', l)])
    # OPENXML 파싱과 테이블 함수 결과를 받는 SELECT *는 사용자 방식이다
    star = []
    for ln in find_lines(r'\bSELECT\s+(DISTINCT\s+)?(TOP\s*\(?\d+\)?\s+)?(\w+\.)?\*', up):
        near = ' '.join(lines[ln - 1:ln + 2])
        prev = ' '.join(lines[max(0, ln - 2):ln])
        if not re.search(r'\bOPENXML\b|\bFROM\s+(DBO\.)?\w+\s*\(', near) and not re.search(r'\bEXISTS\s*\(\s*(SELECT\b|$)', prev):
            star.append(ln)
    item('SELECT * 없음(OPENXML·테이블 함수 제외)', star)
    # 사용자 SP(기준 프로젝트 참조 SP 6개)는 테이블에 DBO.를 거의 붙이지 않는다(141개 중 3개). 함수 호출 DBO.X(는 그대로
    item('FROM/JOIN 테이블에 DBO. 스키마 없음',
         find_lines(r'\b(FROM|JOIN)\s+DBO\s*\.\s*\w+\b(?!\s*\()', up))
    # ON에는 연결 키만 둔다. 필터·수량 비교는 LEFT OUTER JOIN 뒤 바깥 WHERE로(사용자 방식, 2026-11-24)
    onf, in_on = [], False
    for i, l in enumerate(lines):
        s = l.strip()
        if re.match(r'ON\b', s):
            in_on = True
        elif not re.match(r'(AND|OR)\b', s):
            in_on = False
        if in_on and re.match(r'(ON|AND|OR)\s+\w+\.\w+\s*(=|<>|!=|<=|>=|<|>|IN\b|LIKE\b|BETWEEN\b|IS\b)\s*(\'|@|\d|\(|NULL|NOT)', s) \
                and not re.search(r'\.(MAINCD|CODEID)\s*=', s):
            onf.append(i + 1)
    if onf:
        r.append((CHECK, 'ON에 키 외 필터', onf, 'LEFT OUTER JOIN + 바깥 WHERE로 옮길 수 있는지 확인'))
    # 조건의 빈 값 확인은 ISNULL(X, '') <> '' 방식(사용자 SP 25건, NULLIF IS NULL 0건). NULLIF는 출력 표시용
    item("조건의 빈 값 확인은 ISNULL(X, '') <> ''",
         find_lines(r'\bNULLIF\s*\([^()]*(\([^()]*\)[^()]*)*\)\s*IS\s+(NOT\s+)?NULL\b', up))
    # IS NULL / IS NOT NULL도 쓰지 않는다(사용자 SP: ISNULL 형태 25건, IS (NOT) NULL 4건). 원본에 있던 줄은 제외
    def norm(s):  # 서식만 바뀐 원본 줄도 같은 줄로 본다
        return re.sub(r'\s+', '', s).strip(',;')
    prior = {norm(x) for x in mask(original).upper().split('\n')} if original is not None else set()
    # 다른 열로 대체하는 ISNULL/COALESCE는 쓰지 않는다(값의 원천을 하나로 정한다). 원본에 있던 줄은 제외
    item('ISNULL/COALESCE로 다른 열 대체 없음',
         [ln for ln in find_lines(r'\b(ISNULL|COALESCE)\s*\(\s*[\w@]+\.\w+\s*,\s*(ISNULL\s*\(\s*)?[\w@]+\.\w+', up)
          if norm(lines[ln - 1]) not in prior])
    item('IS NULL / IS NOT NULL 대신 ISNULL(X, \'\') = \'\' / <> \'\'',
         [ln for ln in find_lines(r'\bIS\s+(NOT\s+)?NULL\b', up) if norm(lines[ln - 1]) not in prior])
    # CASE에는 항상 ELSE를 쓴다(사용자 SP 26곳 중 24곳). 원본에 있던 CASE는 제외
    noelse = []
    for m in re.finditer(r'\bCASE\b', up):
        depth, j, has_else = 1, m.end(), False
        for w in re.finditer(r'\b(CASE|END|ELSE)\b', up[m.end():]):
            if w.group(1) == 'CASE':
                depth += 1
            elif w.group(1) == 'END':
                depth -= 1
                if depth == 0:
                    break
            elif depth == 1:
                has_else = True
        ln = line_of(up, m.start())
        if not has_else and norm(lines[ln - 1]) not in prior:
            noelse.append(ln)
    item('CASE에는 ELSE', sorted(set(noelse)))
    # 파생 테이블(JOIN (SELECT …)) 안의 첫 FROM 테이블은 T 계열 별칭(T, T1, TT). 사용자 SP 144곳 vs 별칭 없음 59·기타 11
    noalias = []
    for m in re.finditer(r'\bJOIN\s*\(\s*SELECT\b', up):
        fm = re.search(r'\bFROM\s+(@?\w+)(?:\s+(?:AS\s+)?(?!WHERE\b|GROUP\b|INNER\b|LEFT\b|RIGHT\b|FULL\b|JOIN\b'
                       r'|CROSS\b|OUTER\b|ORDER\b|UNION\b|WITH\b)(\w+))?', up[m.end():m.end() + 4000])
        if fm and not re.fullmatch(r'T\w*', fm.group(2) or '') and not fm.group(1).startswith('@'):
            ln = line_of(up, m.end() + fm.start())
            if norm(lines[ln - 1]) not in prior:
                noalias.append(ln)
    item('파생 테이블 안 별칭은 T 계열(FROM <테이블> T)', sorted(set(noalias)))
    # 순번 기준 MAX는 LEFT OUTER JOIN (… MAX … GROUP BY …) 파생 테이블로. CROSS JOIN 파생 MAX는 사용자 SP 0곳
    item('MAX 파생 테이블은 CROSS JOIN이 아닌 LEFT OUTER JOIN(GROUP BY)',
         [ln for ln in find_lines(r'\bCROSS\s+JOIN\s*\(\s*SELECT\b(?:(?!\bFROM\b)[\s\S]){0,400}\bMAX\s*\(', up)
          if norm(lines[ln - 1]) not in prior])
    # 프레임워크: 마스터 테이블(프로필 master_table_regex)은 LEFT OUTER JOIN. 꼭 있어야 하면 IF EXISTS 검증(요청 시). 원본에 있던 줄은 제외
    # IF EXISTS (…) 안의 중복·존재 확인은 마스터 INNER JOIN이 그 확인 자체라 제외(사용자: 있어야 하면 IF EXISTS로 예외처리)
    exists_spans = []
    for m in re.finditer(r'\bIF\s+(NOT\s+)?EXISTS\s*\(', up):
        depth, k = 1, m.end()
        while k < len(up) and depth:
            depth += {'(': 1, ')': -1}.get(up[k], 0)
            k += 1
        exists_spans.append((line_of(up, m.start()), line_of(up, k - 1)))
    if MASTER:
        item('마스터 테이블은 LEFT OUTER JOIN',
             [ln for ln in find_lines(r'\bINNER\s+JOIN\s+(DBO\.)?(' + MASTER + r')\b', up)
              if norm(lines[ln - 1]) not in prior and not any(a <= ln <= b for a, b in exists_spans)])
    # LEFT OUTER JOIN 쪽 값을 비교(> < >= <= <>)·곱셈·나눗셈에 쓰면 ISNULL(X, 0). 사용자 SP 138곳 감쌈 vs 25곳(옛·AI 작성)
    item('LEFT JOIN 값 비교·계산은 ISNULL(X, 0)', [ln for ln in left_join_bare(up, lines) if norm(lines[ln - 1]) not in prior])
    if save:
        # SAVE에 남은 디버그 결과 집합: 화면이 엉뚱한 결과를 읽는다(기준 프로젝트 SAVE 10여 곳). INSERT … SELECT·IF EXISTS·파생 테이블 안은 제외
        dbg = []
        for m in re.finditer(r'(?m)^[ \t]*(SELECT\b)', up):
            ln = line_of(up, m.start(1))
            before = up[:m.start(1)].rstrip()
            last = before.split('\n')[-1].strip() if before else ''
            if (any(a <= ln <= b for a, b in exists_spans)
                    or before.endswith((')', '(', 'UNION', 'ALL', 'EXCEPT', 'INTERSECT'))
                    or re.match(r'INSERT\s+(INTO\s+)?[@\w]', last) or re.search(r'\bFOR$', last)):
                continue
            stmt = up[m.start(1):m.start(1) + 600]
            head = re.match(r'SELECT\s+(TOP\s*\(?\s*\d+\s*\)?\s*)?@\w+\s*[-+*/|&]?=', stmt)  # 변수 대입 SELECT @X = …는 허용
            if not head and norm(lines[ln - 1]) not in prior:
                dbg.append(ln)
        item('SAVE에 결과 집합 SELECT 없음(디버그 SELECT 제거)', dbg)
        item('MODIP에는 @USERIP', [ln for ln in find_lines(r'\bMODIP\s*=\s*@USERID\b', up) if norm(lines[ln - 1]) not in prior])
    # 기본은 LEFT OUTER JOIN. INNER JOIN은 SAVE의 @TMP 스테이징 연결이나 사용자가 필수라고 한 경우만
    inner = [ln for ln in find_lines(r'\bINNER\s+JOIN\s+(DBO\.)?' + (r'(?!(' + MASTER + r')\b)' if MASTER else '') + r'[A-Z]\w*', up)
             if norm(lines[ln - 1]) not in prior]
    if inner:
        r.append((CHECK, 'INNER JOIN(스테이징 @TMP 외)', inner, '필수 연결이 아니면 LEFT OUTER JOIN'))
    fmt = find_lines(r'\bFORMAT\s*\(', up)
    if fmt:
        r.append((CHECK, 'FORMAT 사용', fmt, '고정 표시 형식(자릿수·천단위·마스크)이 아니면 CONVERT'))
    hav = find_lines(r'\bHAVING\b', up)
    if hav:
        r.append((CHECK, 'HAVING 사용', hav, '집계 비교는 파생 열로 내보내 바깥 WHERE에서 비교'))
    for name, pat, note in (('CONCAT( 없음(문자열은 +로 잇는다)', r'\bCONCAT(_WS)?\s*\(', '사용자 SP에 CONCAT 0건'),
                            ("N'…' 리터럴 없음", r"(?<![\w@#$])N'", "사용자 SP에 N' 0건")):
        hit = find_lines(pat, up)
        if hit:
            r.append((CHECK, name, hit, note))
    if not save:
        # INSERT … SELECT는 열 격자(style-insert.md)라 제외한다
        grid = set()
        for m in re.finditer(r'\bINSERT\s+(INTO\s+)?[@#\w.\[\]_]+', up):
            ln = line_of(up, m.start())
            grid.update(range(ln, statement_end(lines, ln - 1) + 2))
        old_lines = {x.strip() for x in mask(original).upper().split('\n')} if original is not None else set()
        many = []
        for i, l in enumerate(lines):
            m = re.match(r'\s*(SELECT\s+(DISTINCT\s+)?|,\s*)(.*)$', l)
            if not m or re.match(r'\s*SELECT\s+1\b', l) or (i + 1) in grid or l.strip() in old_lines:
                continue
            body, depth, cut = m.group(3), 0, False
            for ch in body:
                depth += ch == '('
                depth -= ch == ')'
                if ch == ',' and depth == 0:
                    cut = True
                    break
            if cut:
                many.append(i + 1)
        item('SELECT 열은 한 줄에 하나(선행 쉼표)', many, '--original이면 원본에 없던 줄만' if many else '')
    if original is not None:
        old = raiserror_msgs(original, mask(original))
        for msg, ln in raiserror_msgs(raw, code).items():
            if msg not in old:
                r.append((CHECK, '요청에 없는 검증일 수 있음', [ln], "RAISERROR '%s'" % msg))
    return r, save


def fmt_lines(ls, limit=12):
    s = ', '.join(str(x) for x in ls[:limit])
    return ('줄 ' + s + (' 외 %d줄' % (len(ls) - limit) if len(ls) > limit else '')) if ls else ''


def report(results):
    out = []
    for st, name, ls, note in results:
        tail = ' / '.join(x for x in (fmt_lines(ls), note) if x)
        out.append('[%s] %s%s' % (st, name, (': ' + tail) if tail else ''))
    judged = [x for x in results if x[0] in (PASS, FAIL)]
    ok = sum(1 for x in judged if x[0] == PASS)
    verdict = 'PASS' if ok == len(judged) else 'FAIL'
    out.append('ACE-CHECK: %s %d/%d' % (verdict, ok, len(judged)))
    return out, verdict == 'PASS'


def main(argv=None):
    ap = argparse.ArgumentParser(description='ACE sql 기계 점검')
    ap.add_argument('file')
    ap.add_argument('--caller', default='unknown',
                    help='trn (caller owns the transaction), plain (no transaction), unknown, or a save-call name '
                         'mapped in the local profile.json save_calls')
    ap.add_argument('--original')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        raw = read_sql(a.file)
        orig = read_sql(a.original) if a.original else None
    except (OSError, ValueError) as e:
        print('ACE-CHECK: ERROR %s' % e)
        return 2
    results, save = run_checks(raw, a.caller, orig)
    lines, ok = report(results)
    print('대상: %s (%s SP, 호출부 %s)' % (a.file, '저장' if save else '조회', a.caller))
    print('\n'.join(lines))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
