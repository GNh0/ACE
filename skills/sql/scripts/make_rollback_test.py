"""저장 SP 롤백 테스트 배치 초안을 만든다. 사용법:
python make_rollback_test.py <SP정의.sql> [--out <배치.sql>]
SP 정의에서 뽑을 수 있는 것은 채우고, 정해야 하는 것만 '-- TODO:'로 남긴다. 틀은 references/verify.md 3절.
"""
import argparse
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_sql import mask, read_sql, write_targets, statement_end  # noqa: E402

GBN = {'NEW': 'NEW', 'EDIT': 'MOD', 'DELETE': 'DEL'}


def split_top(s):
    """괄호 밖 쉼표로 나눈다."""
    out, depth, cur = [], 0, ''
    for ch in s:
        depth += (ch == '(') - (ch == ')')
        if ch == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def close_paren(code, i):
    """code[i] == '(' 의 짝 위치."""
    depth = 0
    for k in range(i, len(code)):
        depth += (code[k] == '(') - (code[k] == ')')
        if depth == 0:
            return k
    return len(code) - 1


def parse(raw):
    code = mask(raw)
    up = code.upper()
    info = {}
    m = re.search(r'\b(?:CREATE|ALTER)\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\s+([\w.\[\]]+)', up)
    if not m:
        raise ValueError('CREATE/ALTER PROCEDURE를 찾지 못함')
    name = raw[m.start(1):m.end(1)].replace('[', '').replace(']', '')
    info['name'] = name.split('.')[-1]
    a = re.search(r'^\s*AS\b', up[m.end():], re.M)
    head_raw = raw[m.end():m.end() + a.start()]
    head = code[m.end():m.end() + a.start()]
    if head.strip().startswith('(') and head.strip().endswith(')'):
        off = head.index('(') + 1
        head_raw = head_raw[off:head.rindex(')')]
        head = head[off:head.rindex(')')]
    params = []
    pos = 0
    for part in split_top(head):
        i = head.index(part, pos)
        pos = i + len(part)
        p_raw = head_raw[i:i + len(part)]
        pm = re.match(r'(@\w+)\s+(?:AS\s+)?(.+?)(?:\s*=\s*(.+?))?(\s+(?:OUTPUT|OUT))?(\s+READONLY)?$',
                      p_raw.strip(), re.I | re.S)
        if pm:
            params.append({'name': pm.group(1).upper(), 'type': pm.group(2).strip().upper(),
                           'default': pm.group(3), 'output': bool(pm.group(4))})
    info['params'] = params
    xmls = []
    for om in re.finditer(r'\bOPENXML\s*\(\s*(@\w+)\s*,\s*\'', up):
        handle = om.group(1)
        q = om.end()
        path = raw[q:raw.index("'", q)]
        prep = None
        for pm in re.finditer(r'\bSP_XML_PREPAREDOCUMENT\s+%s\s+OUTPUT\s*,\s*(@\w+)' % re.escape(handle),
                              up[:om.start()]):
            prep = pm.group(1)
        cols = []
        wm = re.compile(r'\)\s*WITH\s*\(').search(up, close_paren(up, up.index('(', om.start())))
        if wm:
            body = code[wm.end() - 1 + 1:close_paren(code, wm.end() - 1)]
            for c in split_top(body):
                cm = re.match(r'(\w+)\s+(\w+(?:\s*\([^)]*\))?)', c.strip())
                if cm:
                    cols.append((cm.group(1).upper(), re.sub(r'\s+', '', cm.group(2)).upper()))
        xmls.append({'param': prep, 'path': path, 'node': path.rstrip('/').split('/')[-1], 'cols': cols})
    info['xmls'] = xmls
    wt = []
    for wm in re.finditer(r'@WORKTYPE\s*(?:=|<>|!=)\s*\'|@WORKTYPE\s+(?:NOT\s+)?IN\s*\(', up):
        if wm.group(0).endswith("'"):
            seg = raw[wm.end() - 1:raw.index("'", wm.end()) + 1]
        else:
            seg = raw[wm.end():close_paren(up, wm.end() - 1)]
        for lit in re.findall(r"'([^']*)'", seg):
            if re.match(r'^\w+$', lit) and lit.upper() not in wt:
                wt.append(lit.upper())
    order = ['NEW', 'EDIT', 'DELETE']
    info['worktypes'] = sorted(wt, key=lambda w: (order.index(w) if w in order else 9, wt.index(w)))
    info['targets'] = targets_with_conds(raw, code)
    return info


def targets_with_conds(raw, code):
    """실제 대상 테이블과, 그 테이블의 UPDATE/DELETE 모두에 공통인 '별칭.열 = @인자/리터럴' 조건."""
    lines, raw_lines = code.upper().split('\n'), raw.split('\n')
    res = {}
    for t, ln in write_targets(raw, code):
        if t.startswith(('@', '#')):
            continue
        res.setdefault(t, None)
        head = lines[ln - 1].lstrip()
        if not head.startswith(('UPDATE', 'DELETE')):
            continue
        end = statement_end(lines, ln - 1)
        seg_u = '\n'.join(lines[ln - 1:end + 1])
        seg_r = '\n'.join(raw_lines[ln - 1:end + 1])
        am = re.search(r'(?:FROM|JOIN)\s+[\w.\[\]]*%s\]?\s+(?:AS\s+)?(\w+)' % t, seg_u)
        alias = am.group(1) if am else t
        conds = set()
        cut = re.search(r'\n\s*(FROM|WHERE)\b', seg_u) if head.startswith('UPDATE') else None
        start = cut.start() if cut else 0
        for cm in re.finditer(r'\b%s\.(\w+)\s*=\s*(@\w+|\'_*\')' % alias, seg_u[start:]):
            cm_s, cm_e = cm.start(2) + start, cm.end(2) + start
            val = seg_r[cm_s:cm_e]
            conds.add('%s = %s' % (cm.group(1), val.upper() if val.startswith('@') else val))
        res[t] = conds if res[t] is None else (res[t] & conds)
    return res


def value_for(p):
    n = p['name']
    if re.search(r'USERID|EMPNO|USERNM', n):
        return "'ACETEST'"
    if re.search(r'IP$', n):
        return "'ACE'"
    if p['default'] is not None and p['default'].strip().upper() != 'NULL':
        return p['default'].strip()
    return None


def xml_select(x, state, indent, targets):
    pad = ' ' * indent
    cols = []
    for c, typ in x['cols']:
        if c == 'GBN':
            cols.append("'%s' AS GBN" % state)
        elif typ == 'VARCHAR(8)' and c.endswith('DT'):
            cols.append('CONVERT(VARCHAR(8), A.%s, 112) AS %s' % (c, c))
        else:
            cols.append('A.' + c)
    # 모르는 원천은 문법 오류로 남긴다. 없는 테이블 이름은 CATCH로 잡히지 않고 트랜잭션을 연 채 끊긴다
    src = x['node'].upper() if x['node'].upper() in targets else '<원천>'
    out = ['%sSET %s = @XMLHEAD' % (pad, x['param']), '%s    + (' % pad]
    p2 = pad + ' ' * 7
    out.append('%sSELECT %s' % (p2, cols[0] if cols else "'%s' AS GBN" % state))
    out += ['%s     , %s' % (p2, c) for c in cols[1:]]
    out.append('%sFROM %s A -- TODO: 원천 테이블과 키(%s 행 상태 %s에 맞는 실제 행)' % (p2, src, x['node'], state))
    out.append('%sWHERE 1 = 0 -- TODO: 키 조건' % p2)
    out.append("%sFOR XML RAW('%s'), ROOT('ROOT')" % (p2, x['node']))
    out.append('%s   );' % pad)
    out.append("%sIF %s IS NULL RAISERROR('%s 행이 없다(%s)', 16, 1);" % (pad, x['param'], x['param'], state))
    return out


def snapshot(scn, targets, indent):
    pad = ' ' * indent
    out = ['%s-- TODO: %s 키 조건' % (pad, t) for t, c in targets.items() if not c]
    out.append('%sINSERT INTO @RESULT (SCENARIO, TBL, CNT)' % pad)
    rows = []
    for t, conds in targets.items():
        where = ' AND '.join('A.' + c for c in sorted(conds or [])) or '1 = 1'
        rows.append("%sSELECT '%s', '%s', COUNT(*) FROM %s A WHERE %s" % (pad, scn, t, t, where))
    out.append(('\n%sUNION ALL\n' % pad).join(rows) + ';')
    return out


def build(info, src):
    p, xmls, tg = info['params'], info['xmls'], info['targets']
    xml_params = {x['param'] for x in xmls}
    wts = info['worktypes'] or ['NEW']
    L = ['-- =============================================',
         '-- ACE 저장 롤백 테스트 초안: %s' % info['name'],
         '-- 원본: %s' % os.path.basename(src),
         '-- make_rollback_test.py가 만든 초안이다. "-- TODO:"를 모두 채운 뒤 실행한다.',
         '-- 주의',
         '--   - 개발 DB에서만 실행한다. 운영 DB이거나 어느 DB인지 모르면 실행하지 않는다.',
         '--   - SET XACT_ABORT ON을 쓰지 않는다. 한 배치로 짧게 끝내고 트랜잭션을 연 채로 넘기지 않는다.',
         '--   - 오류가 나야 정상인 시나리오는 안쪽 BEGIN TRY / BEGIN CATCH로 따로 감싼다.',
         '--   - 없는 테이블·열 이름은 CATCH로 잡히지 않고 트랜잭션을 연 채 끊긴다. XML 원천 SELECT를 먼저 따로 돌려 본다.',
         '--     끊겼으면 같은 연결에서 IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION; 을 실행한다.',
         '--   - 끝난 뒤 트랜잭션 밖에서 건수를 다시 조회해 테스트 전과 같은지 본다.',
         '-- 필수 시나리오(verify.md 3절). 아래 WORKTYPE 블록을 복사해 채운다',
         '--   [ ] 1 신규(NEW): 헤더·상세·짝 테이블 행, 순번 짝. 상세 2행 이상',
         '--   [ ] 2 왕복: 조회 SP 결과 그대로 EDIT 두 번 → 수량·금액·순번 그대로',
         '--   [ ] 3 혼합 수정: MOD·DEL·NEW·UNC 각 1행 → MOD만 바뀜, 등록자 유지',
         '--   [ ] 4 검증 실패: 차단 메시지, 업무 테이블 전후 같음',
         '--   [ ] 5 삭제: 대상 문서만 지워짐',
         '--   [ ] 6 롤백 후: 건수 같음, @@TRANCOUNT 0',
         '-- 추출 결과',
         '--   인자:']
    L += ['--     %s %s%s' % (x['name'], x['type'], ' OUTPUT' if x['output'] else '') for x in p]
    for x in xmls:
        miss = '' if x['param'] in {q['name'] for q in p} else '  ※ 인자 목록에 없음'
        L.append('--   XML: %s → %s (%d열)%s' % (x['param'], x['path'], len(x['cols']), miss))
    L += ['--   WORKTYPE: ' + (', '.join(info['worktypes']) or '찾지 못함'),
          '--   대상 테이블: ' + (', '.join(tg) or '찾지 못함'),
          '-- =============================================',
          'SET NOCOUNT ON;', '',
          'DECLARE @TRANCOUNT INT = @@TRANCOUNT;',
          'DECLARE @XMLHEAD VARCHAR(50) = \'<?xml version="1.0" encoding="euc-kr"?>\';']
    for x in p:
        if x['name'] == '@WORKTYPE':
            continue
        if x['name'] in xml_params or x['output']:
            L.append('DECLARE %s %s;' % (x['name'], x['type']))
            continue
        v = value_for(x)
        L.append('DECLARE %s %s = %s' % (x['name'], x['type'], (v + ';') if v else 'NULL; -- TODO: 값'))
    for x in xmls:
        if x['param'] and x['param'] not in {q['name'] for q in p}:
            L.append('DECLARE %s VARCHAR(MAX); -- 인자 목록에 없음. SP를 확인한다' % x['param'])
    L += ['', 'DECLARE @RESULT TABLE', '(',
          '      STEP     INT IDENTITY(1, 1)', '    , SCENARIO VARCHAR(30)', '    , TBL      VARCHAR(30)',
          '    , KEYVAL   VARCHAR(100)', '    , CNT      INT', '    , QTY      NUMERIC(18, 4)',
          '    , AMT      NUMERIC(18, 4)', '    , REGEMPNO VARCHAR(50)', '    , MODEMPNO VARCHAR(50)',
          '    , MSG      VARCHAR(2000)', ');', '', '-- 0. 테스트 전 건수']
    L += snapshot('0.BEFORE', tg, 0)
    L += ['', 'BEGIN TRANSACTION;', '', 'BEGIN TRY']
    for n, w in enumerate(wts, 1):
        st = GBN.get(w, 'NEW')
        L.append('    -- %d. WORKTYPE = %s (행 상태 %s). TODO: 시나리오에 맞게 행과 값을 정한다' % (n, w, st))
        for x in xmls:
            if x['param']:
                L += xml_select(x, st, 4, tg) + ['']
        args = ['@WORKTYPE = \'%s\'' % w] + ['%s = %s%s' % (x['name'], x['name'], ' OUTPUT' if x['output'] else '')
                                             for x in p if x['name'] != '@WORKTYPE']
        L.append('    EXEC %s %s' % (info['name'], args[0]))
        L += ['    %s, %s' % (' ' * (len(info['name']) + 4), a) for a in args[1:]]
        L[-1] += ';'
        L.append('')
        L += snapshot('%d.%s' % (n, w), tg, 4)
        L.append('    -- TODO: 값 스냅샷(수량·금액·순번·등록자·수정자)을 @RESULT에 추가한다')
        L.append('')
    L += ['END TRY', 'BEGIN CATCH', '    INSERT INTO @RESULT (SCENARIO, MSG)',
          "    VALUES ('ERROR', ERROR_MESSAGE() + ' (LINE ' + CONVERT(VARCHAR(10), ERROR_LINE()) + ')');",
          'END CATCH', '', 'IF @@TRANCOUNT > @TRANCOUNT', '    ROLLBACK TRANSACTION;', '', '-- 롤백 후 건수']
    L += snapshot('9.AFTER', tg, 0)
    L += ['', 'INSERT INTO @RESULT (SCENARIO, MSG)',
          "VALUES ('9.AFTER', 'TRANCOUNT = ' + CONVERT(VARCHAR(2), @@TRANCOUNT));", '',
          'SELECT * FROM @RESULT ORDER BY STEP;', '']
    return '\n'.join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description='저장 SP 롤백 테스트 초안')
    ap.add_argument('file')
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        info = parse(read_sql(a.file))
    except (OSError, ValueError) as e:
        print('오류: %s' % e)
        return 2
    text = build(info, a.file)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, 'w', encoding='utf-8-sig', newline='\r\n') as f:
            f.write(text)
        print('초안: %s (TODO %d곳)' % (a.out, text.count('TODO:') - 1))  # 머리 주석의 안내 한 줄 제외
    else:
        print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
