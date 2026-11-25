# SQL layout

INSERT grid and condition comments: [style-insert.md](style-insert.md).

## SQL layout

Lines marked (checked) are verified by `check_sql.py`.

Reference SPs, even recent PROJECT_B ones, carry old habits (tab indentation, lowercase `@tmp`/`sp_…` names, lines over 120, one-cell INSERT rows, ON on the JOIN line). When a reference SP conflicts with these rules, the rules win: take structure and business logic from it, not its formatting.

- Choose aliases by [alias role](style-alias.md#alias-roles). (checked) Inside derived queries use the T family: the first table of a `JOIN (SELECT …)` gets `T`/`T1`/`TT` (`FROM XX110T T`). Do not pick E/F from the table name or MAINCD alone. "Format only / keep aliases" keeps the original aliases.
- (checked) Everything outside literals and comments is **UPPERCASE**: keywords, functions, tables, columns, aliases, output column names (after `AS`), user functions, procedures, variables (e.g. `DBO.F_CODE_NAME`). A case change of an output column or object name is no reason to keep the original spelling. Only string literals, comments and identifiers in `[...]`/`"..."` keep their text.
- (checked) FROM, WHERE, GROUP BY, ORDER BY start in the same column as SELECT (left-aligned). AND/OR in WHERE are indented two spaces. No right alignment to keyword ends (`  FROM`, ` WHERE`, `   AND`), even if the existing SP has it.
- (checked) Aim for ≤100 characters, never over 120. (checked) One SELECT column per line with a leading comma (INSERT…SELECT grids follow [style-insert.md](style-insert.md#insert-column-grid)); short simple GROUP BY/ORDER BY items on one line.
- JOIN is indented 8 spaces from FROM. (checked) LEFT/RIGHT/FULL JOIN always has `OUTER`.
- Default join is `LEFT OUTER JOIN`. Use `INNER JOIN` only (a) to join the XML staging table / `@` table variable in a SAVE write (`UPDATE A … FROM XX110T A INNER JOIN @TMPXX110T B`), or (b) when the user said the related rows are required. Not for masters, codes, details, history or sums. User SPs: 108 LEFT vs 13 INNER, and 11 of the 13 INNER join `@TMP…`/derived staging.
- (checked) Master/lookup tables (framework: `MS020T` customers, `MS030T` items, other `MS0xxT`) are joined with `LEFT OUTER JOIN`, in SELECTs and in SAVE `INSERT … SELECT`. An INNER JOIN silently drops the row when the master row is missing. If the user wants a missing master row to stop the save, that is an explicit `IF EXISTS (… LEFT OUTER JOIN … WHERE ISNULL(B.KEY, '') = '') RAISERROR` check — add it only when asked. User SPs: 42 LEFT vs 1 INNER join to `MS0xxT`.
- Joins: ON holds only the join keys (plus a fixed code-table key such as `B.MAINCD = 'BA030'`). Filters that decide which rows the result has — states, flags, dates, quantity comparisons, i.e. what an INNER JOIN's ON list was doing — go in the outer WHERE. A filter on an optional lookup that must keep the outer row stays in ON: the code-table `USEYN = 'Y'` (`ON F1.MAINCD = 'SA050' AND A.X = F1.SUBCD AND F1.USEYN = 'Y'`, 48 uses in PROJECT_B) and fixed literals on a LEFT OUTER JOINed lookup (`AND C1.DWG = 'D'`); moving them to WHERE drops rows. The company key `A.ORGDIV = @ORGDIV` may sit in ON with the other keys. Prefer `LEFT OUTER JOIN` + outer WHERE over an INNER JOIN with a long ON list or a derived table filtered by `HAVING`; compare aggregates in WHERE (`A.QTY > ISNULL(B.OUTQTY, 0)`). This is the user's current style. Exception: an exclusion join (`LEFT OUTER JOIN … WHERE ISNULL(B.KEY, '') = ''`) keeps the joined table's filters in ON — moving them to WHERE changes the result.
- (checked) Never use a CTE (`WITH … AS`) or a `#temp` table. Use derived-table JOINs, and a table variable (`@TMP…`) where staging is needed (XML parsing etc.). Hierarchies: `CROSS APPLY` the existing table function ([complex-select.md](complex-select.md#bom-expansion--reverse-expansion)).
- Do not wrap CONVERT twice in the same NUMERIC/DECIMAL type.
- From the user's own SPs (six PROJECT_B reference SPs, 2026-11-20: `DBO.` on 3 of 141 tables, `CONCAT(` 0, `N'` 0): (checked) no `DBO.` schema prefix on tables in FROM/JOIN (keep it on function calls such as `DBO.F_SPLIT_KEY(`, `DBO.F_FIND_USERNM(`); concatenate with `+`, not `CONCAT(`; no `N'…'` literals (both `[확인]` in the checker).
- (checked) No `SELECT *`, except from `OPENXML` or a table function.
- (checked) Leading commas. Keep the order of SELECT list, UPDATE SET, SP arguments and defaults aligned. Distinguish alias AS from output column AS.
- (checked) ON goes on the line after JOIN. ON of a plain JOIN and its ANDs align with the I of JOIN. Derived FROM/JOIN: opening and closing parentheses align, inner clauses one more space. ON/AND/OR of a derived JOIN sit in the opening-parenthesis column. Nesting and UNION follow each parenthesis.
- EXISTS: parenthesis in the same column, inner SQL on the next line one more space. CASE follows [CASE](#case). BETWEEN's AND stays inside its expression.
- (checked) INSERT columns and values form a grid: [style-insert.md](style-insert.md#insert-column-grid). UPDATE SET is a vertical list.
- Do not add new NULL/empty replacements to an existing SP. Adding `ISNULL(..., 0)` to arithmetic there needs a user request. In a new SP, totals from a LEFT OUTER JOIN that the screen shows or calculates with are written `ISNULL(B.AMT, 0)` (the screen expects 0, not NULL); this is a default, not a column fallback.
- (checked) Every `CASE` has an `ELSE` (`ELSE ''`, `ELSE 0`, or the current value); a CASE without ELSE silently yields NULL. User SPs: 24 of 26 CASEs have ELSE.
- Number/date to text: `CONVERT(VARCHAR(n), x[, style])` first (faster). `FORMAT` only when the output needs a fixed display format: fixed leading digits, thousands separators, a specific mask.
- (checked) Never fall back to another column with `ISNULL`/`COALESCE` (`ISNULL(B.INVUNIT, A.INVUNIT)`, `ISNULL(A.CT, ISNULL(B.CYCLETIME, …))`). Decide the one correct source table for the value and select it from there; in a SAVE, use the value from the XML staging table as it is.
- (checked) A value from a LEFT OUTER JOINed table that takes part in a comparison (`>`, `<`, `>=`, `<=`, `<>`) or a calculation (`*`, `/`, sums of products) is wrapped in `ISNULL(X, 0)`: `WHERE A.PURQTY + ISNULL(C.OUTQTY, 0) > ISNULL(B.QTY, 0)`; a header total from detail rows `SUM(ISNULL(B.QTY, 0) * ISNULL(B.UNP, 0))`. Without it a missing row makes the comparison unknown and the check passes silently. Display-only columns may stay NULL. User SPs: 138 wrapped vs 25 bare (old or AI-written).
- (checked) Null/empty checks in conditions use `ISNULL(A.LOTNUM, '') <> ''` (has a value) and `ISNULL(@LOTNUM, '') = ''` (empty); numbers `ISNULL(X, 0) = 0` / `<> 0` when 0 is not a valid value (otherwise test a string key of the same row). This includes "row found / not found" after a LEFT OUTER JOIN (`ISNULL(B.ITEMCD, '') = ''`) and variables (`IF ISNULL(@X, '') <> ''`). Avoid `IS NULL` / `IS NOT NULL` and `NULLIF(…) IS (NOT) NULL` — the user's SPs use the ISNULL form 25 times and IS (NOT) NULL 4 times. `NULLIF` is only for output columns that should show NULL instead of an empty string.
- Keep output column order/type/fields, literals, Korean text and existing comments; keep JOIN kind/order/conditions in a format-only task. A comment-out request keeps the original text. Keep the real meaning of required JOINs, IF EXISTS, business functions and constants.
- <a id="style-rules-win"></a>Cleanup, rewrite or "우리 스타일로" on an existing SP, and every new SP: the user's style rules win over the original's habits ("규칙 기준"). Master INNER JOIN → LEFT OUTER JOIN, column fallback → its one source, `FORMAT` → `CONVERT`, `HAVING`/ON filters → outer WHERE, `IS NULL` → ISNULL form are intended changes: make them and list in the answer which rows or values can now differ. Never leave a checker `[실패]` in place to "preserve behavior"; only a format-only request, or the user naming the line, keeps it.
- When converting to JOIN check full key, NULL, duplicates, aggregation unit, the function's original and run semantics. For several result sets match period, filter, aggregation key, UNION and ratios.
- A request for one UPDATE completes that UPDATE FROM/CROSS APPLY. DB changes: confirm the given connection/DB/key, transaction, and changed/excluded rows. Staging tables only when hard without.

## Formatting untouched parts

When the task changes an SP's logic, also bring the untouched parts to this layout so the whole SP follows the rules. Do not leave the original's one-line `INSERT INTO @T (A, B, C…)` lists, table variables with several columns per line, `WHERE @WORKTYPE IN (…)` inside `EXISTS`, or lines over 120 characters. `SET XACT_ABORT ON` and `THROW` are transaction code too ([transactions](../../erp/references/save-call.md#transactions)). Before finishing, run the SKILL.md check on the whole SP. This differs from format-only requests, where logic is not changed.

## Derived JOIN and UNION examples

The closing parenthesis, ON and AND of a derived JOIN are in the opening-parenthesis column. The real parenthesis position is the reference.

```sql
SELECT A.ORDERNO
     , B.QTY
FROM ORDERS A
        LEFT OUTER JOIN (
                         SELECT T.ORDERNO
                              , SUM(T.QTY) AS QTY
                         FROM WORK_LOG T
                         GROUP BY T.ORDERNO
                        ) B
                        ON A.ORDERNO = B.ORDERNO
                        AND A.QTY = B.QTY
```

```sql
    SELECT A.PERIOD
         , A.QTY
    FROM (
          SELECT T.PERIOD
               , SUM(T.QTY) AS QTY
          FROM (
                SELECT T.PERIOD
                     , T.QTY
                FROM HISTORY T

                UNION ALL

                SELECT T.PERIOD
                     , T.QTY
                FROM ORDERS T
               ) T
          GROUP BY T.PERIOD
         ) A
    ORDER BY A.PERIOD
```

## CASE

Short: one line. Long: align WHEN/ELSE/END one column after CASE. Wrap the whole CASE in parentheses.

```sql
UPDATE A
SET A.PLANTIME = (CASE WHEN A.QTY = 0 THEN A.PLANTIME
                       ELSE ROUND(A.PLANTIME / A.QTY, 0) * B.PLANQTY
                  END)
  , A.QTY = B.PLANQTY
FROM DOC_HEADER A
        INNER JOIN @TMP_DETAIL B
                ON A.DOCNUM = B.DOCNUM
WHERE A.ORGDIV = @ORGDIV
```

```sql
SELECT B.ITEMNM + (CASE WHEN ISNULL(B.SPEC, '') = '' THEN '' ELSE ' ' + B.SPEC END) AS ITEMNM
```
