# SQL lessons enforced by check_sql.py

Bodies of the (c) entries indexed in [lessons.md](lessons.md). Open this file only when `check_sql.py` fails one of these items or when promoting lessons. Titles are anchors.

## Layout

### All identifiers uppercase (v3.6.3)
- Mistake: kept the original case of output column names (after `AS`) or function/procedure names.
- Rule: everything uppercase except literals, comments and `[...]`. [style.md](style.md#sql-layout)
- Check: `리터럴·주석·[...] 밖 소문자 없음`

### Long INSERT values go at the line end (v3.6.8)
- Mistake: a 30+ character value mid-line pushed other lines' columns dozens of spaces apart.
- Rule: a long value is the last item on its line; the next column starts on the next line. [style-insert.md](style-insert.md#insert-column-grid)
- Check: `긴 값 때문에 벌어진 칸(20칸 이상 공백) 없음`

### Clauses are left-aligned (2026-11-20)
- Mistake: right-aligned FROM/WHERE/AND to the end of SELECT (`  FROM`, ` WHERE`, `   AND`).
- Rule: FROM/WHERE/GROUP BY/ORDER BY start in SELECT's column; do not copy right alignment from existing SPs. [style.md](style.md#sql-layout)
- Check: `오른쪽 맞춤 절(  FROM / WHERE) 없음`

### Do not break the INSERT grid into one-cell lines (2026-11-20, PROJECT_A XM100500)
- Mistake: a long `ROW_NUMBER()` passed 120, so I put it alone on a line (`, SEQ2`) and split it, breaking the grid.
- Rule: keep the long value at the end of a shared line; if still over 120, shorten it with a staging `SEQ IDENTITY`. [style-insert.md](style-insert.md#insert-column-grid)
- Check: `INSERT 열 목록에 한 칸짜리 줄 없음(마지막 줄 제외)`, `120자 이하`

## SELECT

### No CTE, no #temp tables (2026-11-20, PROJECT_A XQ500100)
- Mistake: Codex used a CTE in `SP_XQ500100_SELECT` since the rule allowed one "when hard without"; user: "CTE랑 #임시테이블 내가 존나 싫어하는것들인데".
- Rule: never use CTE or `#temp` tables; derived JOINs, table variables only for staging. [style.md](style.md#sql-layout)
- Check: `CTE(WITH … AS) 없음`, `#임시 테이블 없음`

### Banning one pattern made the model swap to another (2026-11-20, PROJECT_A XQ500100)
- Mistake: after "no CTE", Codex rewrote `SP_XQ500100_SELECT` with `#FORGINGLOT/#STOCK/#STOCKLOT` temp tables.
- Rule: ban both; use derived-table JOINs / `@table` variables and check the whole SP with `check_sql.py`, not only the corrected item. [style.md](style.md#sql-layout), [work](../../work/SKILL.md#scope)
- Check: `CTE(WITH … AS) 없음`, `#임시 테이블 없음` over the whole file

### EXISTS/IN subquery → JOIN (v3.6.4)
- Mistake: left EXISTS/IN subqueries in WHERE.
- Rule: JOIN a derived table grouped by the link key. [select.md](select.md#exists--join)
- Check: `WHERE의 EXISTS/IN 서브쿼리 없음`

## SAVE structure

### No lock hints (repeated since before 2026-11-20)
- Mistake: added `WITH (UPDLOCK, HOLDLOCK)` to a SAVE or kept one from the original.
- Rule: never use lock hints; remove them even from the original or reference SP. [save.md](save.md#lock-hints)
- Check: `잠금 힌트 없음`

### Sequence MAX derived table shape (2026-11-24, ACE comply run 3)
- Mistake: Claude wrote the sequence base as `CROSS JOIN (SELECT MAX(B.PURSEQ2) AS MAXSEQ FROM XX110T B …)` under the "급하니까" prompt, and without the T alias in the derived query under the supportive prompt.
- Rule: LEFT OUTER JOIN MAX derived table with GROUP BY and T-family alias. [common-sp.md](../../erp/references/common-sp.md)
- Check: check_sql `파생 테이블 안 별칭은 T 계열`, `MAX 파생 테이블은 CROSS JOIN이 아닌 LEFT OUTER JOIN(GROUP BY)` (new lines only).

### PROJECT_B style analysis (2026-11-24, 119 SPs + 30 screens by the user and the earlier AI plugin)
- Found: debug `SELECT * FROM @tmp` and preview SELECTs left in 10+ SAVEs; `MODIP = @USERID` in 2; `16, 9` used only for closing messages, `16, 1` for every business check; staging tables named after the target table; `SELECT * FROM OPENXML` preferred (user: "SELECT * FROM OPENXML 를 선호하긴해 하나씩 다 선언해야할땐 그렇게"); clauses left-aligned (user: "절 정렬은 왼쪽정렬"); header block form loose but block/JOIN indentation strict (user: "블럭구분,join 같은 그런 들여쓰기들은 다 중요해").
- Rule: [sp-save.md](../../erp/references/sp-save.md), [common-sp.md](../../erp/references/common-sp.md), [complex-select.md](complex-select.md#search-condition-arguments), [style.md](style.md#sql-layout).
- Check: check_sql `SAVE에 결과 집합 SELECT 없음`, `MODIP에는 @USERIP` (new lines only); master INNER JOIN inside `IF EXISTS (…)` is allowed as the existence check.

### LEFT JOIN values in comparisons need ISNULL (2026-11-24, PROJECT_A XM200150 / XM100500)
- Mistake: `WHERE ISNULL(C.INQTY, 0) > B.QTY` with XS210T B LEFT OUTER JOINed: no issue row → NULL → the over-quantity check passed silently (a MOD row saved 6 with no issue). Same in XM100500 (`> B.QTY`). User: "ISNULL,0 처리하면 되잖아", "비교대상으로 필요한항목은 ISNULL처리를 하라고", "NULL 방지가 필요한부분들은 다 ISNULL처리가 되어있잖아".
- Rule: LEFT OUTER JOINed values in comparisons and calculations get `ISNULL(X, 0)`. [style.md](style.md#sql-layout)
- Check: check_sql `LEFT JOIN 값 비교·계산은 ISNULL(X, 0)` (new lines only; aliases looked up per statement).

