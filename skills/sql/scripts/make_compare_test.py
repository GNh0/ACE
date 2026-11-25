"""Old vs new SP comparison batch (ideas from ECC module-regression / ai-regression-testing, MIT). Usage:

  python make_compare_test.py --sp dbo.sp_X_SAVE --new <new.sql> --cases <cases.json> [--out <batch.sql>]

Builds ONE T-SQL batch that
1. creates the new definition as a temp procedure #ACE_<name>_NEW (the real SP is not touched),
2. runs every case against the current SP and the temp one, each inside BEGIN TRAN … ROLLBACK,
3. snapshots what each case left (your SELECT … FOR XML) and returns SAME/DIFF per case plus @@TRANCOUNT.

cases.json:
  {"setup": "DECLARE @OUT VARCHAR(20), @XML VARCHAR(MAX) = (SELECT … FOR XML RAW('XM210T'), ROOT('ROOT'));",
   "cases": [{"name": "T1.NEW",
              "sql": "EXEC @PROC @WORKTYPE = 'NEW', @ORGDIV = '01', @XML_XM210T = @XML, @OUTPUT = @OUT OUTPUT;",
              "snapshot": "SELECT A.SEQ2, A.QTY FROM XM210T A … FOR XML RAW('R')"}]}
`@PROC` in a case is the procedure under test. EXEC arguments must be variables or literals (no expressions):
build values in "setup" or at the start of a case. Batch locals are prefixed `@V_` so they never collide with
the SP's parameter names. Run it on a development DB; the live-DB guard blocks it elsewhere.
"""
import argparse
import base64
import gzip
import io
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_sql import read_sql  # noqa: E402


def temp_body(text, sp):
    short = sp.replace('[', '').replace(']', '').split('.')[-1]
    tmp = '#ACE_%s_NEW' % re.sub(r'\W', '_', short)[:100]
    pat = re.compile(r'\b(CREATE|ALTER)(\s+OR\s+ALTER)?\s+PROC(EDURE)?\s+[\w\[\]\.]+', re.I)
    if not pat.search(text):
        raise ValueError('CREATE/ALTER PROCEDURE not found in the new definition')
    return pat.sub('CREATE PROCEDURE ' + tmp, text, count=1), tmp


def encode(text):
    return base64.b64encode(gzip.compress(text.encode('utf-16-le'))).decode('ascii')


def lit(s):
    return "N'" + s.replace("'", "''") + "'"


def build(sp, new_text, spec):
    body, tmp = temp_body(new_text.replace('\r\n', '\n'), sp)
    out = ['SET NOCOUNT ON;',
           "IF OBJECT_ID('tempdb..%s') IS NOT NULL DROP PROCEDURE %s;" % (tmp, tmp),
           "DECLARE @V_B64 VARCHAR(MAX) = '%s';" % encode(body),
           "DECLARE @V_NEWSP NVARCHAR(MAX) = CAST(DECOMPRESS(CAST('' AS XML).value('xs:base64Binary(sql:variable(\"@V_B64\"))', 'VARBINARY(MAX)')) AS NVARCHAR(MAX));",
           'EXEC (@V_NEWSP);',
           'DECLARE @V_R TABLE (PROCNM NVARCHAR(200), TEST NVARCHAR(100), VAL NVARCHAR(MAX));',
           'DECLARE @V_PROC NVARCHAR(200), @V_I INT = 1, @V_SNAP NVARCHAR(MAX);',
           spec.get('setup', '').strip(),
           'WHILE @V_I <= 2',
           'BEGIN',
           "    SET @V_PROC = CASE WHEN @V_I = 1 THEN %s ELSE %s END;" % (lit(sp), lit(tmp))]
    for c in spec['cases']:
        sql = re.sub(r'@PROC\b', '@V_PROC', c['sql'])
        out += ['    -- %s' % c['name'],
                '    BEGIN TRAN;',
                '    BEGIN TRY',
                '        ' + sql.strip(),
                '        SET @V_SNAP = (%s);' % c.get('snapshot', "SELECT 'NO SNAPSHOT'").strip().rstrip(';'),
                "        INSERT INTO @V_R VALUES (@V_PROC, %s, ISNULL(@V_SNAP, 'NO ROWS'));" % lit(c['name']),
                '    END TRY',
                '    BEGIN CATCH',
                "        INSERT INTO @V_R VALUES (@V_PROC, %s, 'ERR ' + ERROR_MESSAGE());" % lit(c['name']),
                '    END CATCH',
                '    IF @@TRANCOUNT > 0 ROLLBACK;']
    out += ['    SET @V_I += 1;',
            'END',
            'DROP PROCEDURE %s;' % tmp,
            "SELECT O.TEST, CASE WHEN O.VAL = N.VAL THEN 'SAME' ELSE 'DIFF' END AS CMP",
            '     , LEFT(O.VAL, 900) AS OLD_VAL',
            "     , CASE WHEN O.VAL = N.VAL THEN '' ELSE LEFT(N.VAL, 900) END AS NEW_VAL",
            '     , @@TRANCOUNT AS TRANCNT',
            'FROM @V_R O',
            '        INNER JOIN @V_R N',
            '                ON N.TEST = O.TEST',
            '               AND N.PROCNM = %s' % lit(tmp),
            'WHERE O.PROCNM = %s;' % lit(sp)]
    return '\n'.join(x for x in out if x != '')


def main(argv=None):
    ap = argparse.ArgumentParser(description='old vs new SP comparison batch')
    ap.add_argument('--sp', required=True, help='current procedure, e.g. dbo.sp_XM200150_SAVE')
    ap.add_argument('--new', required=True, help='file with the new CREATE/ALTER PROCEDURE')
    ap.add_argument('--cases', required=True)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    spec = json.load(io.open(a.cases, encoding='utf-8-sig'))
    sql = build(a.sp, read_sql(a.new), spec)
    if a.out:
        io.open(a.out, 'w', encoding='utf-8').write(sql + '\n')
        print('written: %s (%d chars, %d cases)' % (a.out, len(sql), len(spec['cases'])))
    else:
        sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
        print(sql)
    return 0


if __name__ == '__main__':
    sys.exit(main())
