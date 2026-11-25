"""ACE style mining: count the user's SQL habits in a set of SP files (idea from ECC inherit-legacy-style, MIT).

  python -B mine_style.py <folder or .sql files...> [--author <name>] [--md out.md]

For each dimension it counts files/occurrences that follow form A versus form B and labels the split:
  rule   one form dominates (minority < 5% and < 10 hits, or >= 90% with 50+ files): write it as a rule
  dont   the dominant form is the absence of B: B goes to the DON'T list
  ask    near-even (35-65%) or a small corpus (< 50 files) without a clear majority: ask the user, one at a time
It also lists golden files (most conforming, largest) to cite as exemplars. Counts are on masked code
(comments and literals blanked by check_sql.mask). Dump definitions first, e.g. one file per SP from
sys.sql_modules of the reference DB (PROJECT_B for framework).
"""
import argparse
import glob
import io
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_sql  # noqa: E402

MASTER = '(?:' + check_sql.MASTER + ')' if check_sql.MASTER else r'(?!x)x'  # local profile master_table_regex


def case_counts(up):
    with_else = without = 0
    for m in re.finditer(r'\bCASE\b', up):
        depth, has_else = 1, False
        for w in re.finditer(r'\b(CASE|END|ELSE)\b', up[m.end():]):
            if w.group(1) == 'CASE':
                depth += 1
            elif w.group(1) == 'END':
                depth -= 1
                if depth == 0:
                    break
            elif depth == 1:
                has_else = True
        with_else += has_else
        without += not has_else
    return with_else, without


def n(p, up):
    return len(re.findall(p, up))


# (id, question, form A, form B, counter(up) -> (a, b))
DIMS = [
    ('case-else', 'CASE has ELSE', 'with ELSE', 'without ELSE', case_counts),
    ('left-outer', 'LEFT JOIN spelling', 'LEFT OUTER JOIN', 'LEFT JOIN',
     lambda u: (n(r'\bLEFT\s+OUTER\s+JOIN\b', u), n(r'\bLEFT\s+JOIN\b', u))),
    ('master-join', 'master tables (profile master_table_regex) join', 'LEFT OUTER JOIN', 'INNER JOIN',
     lambda u: (n(r'\bLEFT\s+(?:OUTER\s+)?JOIN\s+' + MASTER, u),
                n(r'\bJOIN\s+' + MASTER, u) - n(r'\b(?:LEFT|RIGHT|FULL)\s+(?:OUTER\s+)?JOIN\s+' + MASTER, u))),
    ('empty-check', 'empty check in conditions', "ISNULL(X, '') <> ''/= ''", 'IS [NOT] NULL / NULLIF … IS',
     lambda u: (n(r"\bISNULL\s*\([^()]*,\s*'_*'\s*\)\s*(<>|=|!=)\s*'", u), n(r'\bIS\s+(NOT\s+)?NULL\b', u))),
    ('cte', 'CTE', 'no CTE', 'WITH … AS (', lambda u: (0, n(r'(^|;)\s*WITH\s+\w+\s*(\([^)]*\))?\s+AS\s*\(', u))),
    ('temp', 'temp tables', '@table variables', '#temp tables',
     lambda u: (n(r'\bDECLARE\s+@\w+\s+TABLE\b', u), n(r'\b(?:CREATE\s+TABLE|INTO)\s+#\w+', u))),
    ('format', 'number/date to text', 'CONVERT', 'FORMAT(', lambda u: (n(r'\bCONVERT\s*\(\s*N?VARCHAR', u), n(r'\bFORMAT\s*\(', u))),
    ('having', 'aggregate filter', 'outer WHERE', 'HAVING', lambda u: (0, n(r'\bHAVING\b', u))),
    ('exists', 'existence filter in WHERE', 'LEFT JOIN + key check', 'WHERE [NOT] EXISTS/IN (SELECT',
     lambda u: (0, n(r'\b(?:NOT\s+)?(?:EXISTS|IN)\s*\(\s*SELECT\b', u) - n(r'\bIF\s+(?:NOT\s+)?EXISTS\s*\(\s*SELECT\b', u))),
    ('comma', 'column list commas', 'leading comma', 'trailing comma',
     lambda u: (n(r'(?m)^\s*,\s*\S', u), n(r'(?m)\S\s*,\s*$', u))),
    ('dbo', 'schema prefix on tables', 'no DBO.', 'DBO.table', lambda u: (0, n(r'\b(?:FROM|JOIN)\s+DBO\.\w+', u))),
    ('loop', 'loops', 'set-based', 'WHILE / CURSOR', lambda u: (0, n(r'\bWHILE\b|\bCURSOR\b', u))),
]


def label(a, b, files_a, files_b, nfiles):
    tot = a + b
    if not tot:
        return 'n/a'
    minority = min(a, b)
    share = max(a, b) / float(tot)
    if a == 0 or b == 0:
        return 'rule' if a else ('dont' if nfiles >= 50 or files_b <= 1 else 'ask')
    if minority < 0.05 * tot and minority < 10:
        return 'rule' if a > b else 'ask'
    if 0.35 <= share <= 0.65 or nfiles < 50:
        return 'ask'
    return 'rule' if share >= 0.9 and a > b else ('ask' if a < b else 'lean')


def load(paths, author):
    files = []
    for p in paths:
        files += sorted(glob.glob(os.path.join(p, '**', '*.sql'), recursive=True)) if os.path.isdir(p) else [p]
    out = []
    for f in files:
        if re.search(r'before|_bak|backup|원본', os.path.basename(f), re.I):
            continue
        try:
            raw = check_sql.read_sql(f)
        except (OSError, ValueError):
            continue
        if not re.search(r'\bPROC(EDURE)?\b', raw, re.I):
            continue
        if author and not re.search(r'AUTHOR\s*:\s*' + re.escape(author), raw, re.I):
            continue
        out.append((f, check_sql.mask(raw).upper()))
    return out


def main(argv):
    ap = argparse.ArgumentParser(description='ACE style mining')
    ap.add_argument('paths', nargs='+')
    ap.add_argument('--author', help='only SPs whose header AUTHOR matches (the user’s own code)')
    ap.add_argument('--md')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    docs = load(a.paths, a.author)
    nf = len(docs)
    lines = ['# SQL style mining: %d SP files%s' % (nf, ' (author %s)' % a.author if a.author else ''), '',
             '| dimension | A | B | files A/B | verdict |', '|---|---|---|---|---|']
    score = {f: 0 for f, _ in docs}
    for did, q, fa, fb, fn in DIMS:
        a_tot = b_tot = files_a = files_b = 0
        for f, up in docs:
            x, y = fn(up)
            a_tot += x
            b_tot += y
            files_a += x > 0
            files_b += y > 0
            score[f] += (y == 0)
        absence = a_tot == 0  # form A is "B never appears": compare files, not hits
        if absence:
            files_a = nf - files_b
            verdict = label(files_a, files_b, files_a, files_b, nf).replace('rule', 'dont')
            a_txt, b_txt = '%s %d files' % (fa, files_a), '%s %d (%d files)' % (fb, b_tot, files_b)
        else:
            verdict = label(a_tot, b_tot, files_a, files_b, nf)
            a_txt, b_txt = '%s %d' % (fa, a_tot), '%s %d' % (fb, b_tot)
        lines.append('| %s: %s | %s | %s | %d/%d | %s |' % (did, q, a_txt, b_txt, files_a, files_b, verdict))
    best = sorted(docs, key=lambda d: (-score[d[0]], -len(d[1])))[:5]
    lines += ['', 'Golden files (fewest B forms, then largest):', '']
    lines += ['- %s (%d/%d dimensions clean)' % (f, score[f], len(DIMS)) for f, _ in best]
    lines += ['', 'rule: write it as a rule. dont: put B on the DON\'T list. ask: ask the user (one at a time). '
              'lean: majority without a clear rule.']
    text = '\n'.join(lines) + '\n'
    if a.md:
        io.open(a.md, 'w', encoding='utf-8').write(text)
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
