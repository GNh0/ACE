"""ACE sql 기계 점검. 사용법:
python check_sql.py <파일.sql> [--caller ExecSPTrn|ExecSP|unknown] [--original <원본.sql>]
마지막 줄은 'ACE-CHECK: PASS 통과/판정' 또는 'ACE-CHECK: FAIL 통과/판정'. 실패가 있으면 종료 코드 1.
"""
import argparse
import io
import re
import sys

PASS, FAIL, CHECK = '통과', '실패', '확인'
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
        c = (caller or 'unknown').lower()
        if c == 'execsptrn':
            item('트랜잭션 코드 없음(호출부 ExecSPTrn)', tx)
        elif c == 'execsp':
            r.append((PASS if tx else FAIL, '트랜잭션 코드 유지(호출부 ExecSP)', [],
                      '' if tx else 'ExecSP 호출인데 SP에 트랜잭션이 없다'))
        else:
            r.append((CHECK, '트랜잭션 코드(호출부 미확인)', tx,
                      '트랜잭션 코드 있음' if tx else '트랜잭션 코드 없음. ExecSPTrn 호출일 때만 맞다'))
        loops = find_lines(r'\bWHILE\b|\bCURSOR\b', up)
        if loops and 'SP_SYSTEM_BA100T_KEYCODE' in up:
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
        item('채번 테이블(BA100T) 직접 쓰기 없음',
             sorted({ln for t, ln in write_targets(raw, code) if t == 'BA100T'}))
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
    if not save:
        many = []
        for i, l in enumerate(lines):
            m = re.match(r'\s*(SELECT\s+(DISTINCT\s+)?|,\s*)(.*)$', l)
            if not m or re.match(r'\s*SELECT\s+1\b', l):
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
        if many:
            r.append((CHECK, 'SELECT 열은 한 줄에 하나(선행 쉼표)', many, '원본에 없던 한 줄 나열이면 나눈다'))
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
    ap.add_argument('--caller', default='unknown', choices=['ExecSPTrn', 'ExecSP', 'unknown'],
                    type=lambda s: {'execsptrn': 'ExecSPTrn', 'execsp': 'ExecSP'}.get(s.lower(), s))
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
