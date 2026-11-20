# SQL layout

INSERT grid and condition comments: [style-insert.md](style-insert.md).

## SQL layout

Lines marked (checked) are verified by `check_sql.py`.

Reference SPs, even recent C_KONE110 ones, carry old habits (tab indentation, lowercase `@tmp`/`sp_…` names, lines over 120, one-cell INSERT rows, ON on the JOIN line). When a reference SP conflicts with these rules, the rules win: take structure and business logic from it, not its formatting.

- Choose aliases by [alias role](#alias-roles). Inside derived queries use the T family. Do not pick E/F from the table name or MAINCD alone. "Format only / keep aliases" keeps the original aliases.
- (checked) Everything outside literals and comments is **UPPERCASE**: keywords, functions, tables, columns, aliases, output column names (after `AS`), user functions, procedures, variables (e.g. `DBO.F_BA011T_FIND_SUBNM`). A case change of an output column or object name is no reason to keep the original spelling. Only string literals, comments and identifiers in `[...]`/`"..."` keep their text.
- (checked) FROM, WHERE, GROUP BY, ORDER BY start in the same column as SELECT (left-aligned). AND/OR in WHERE are indented two spaces. No right alignment to keyword ends (`  FROM`, ` WHERE`, `   AND`), even if the existing SP has it.
- (checked) Aim for ≤100 characters, never over 120. One SELECT item per line by default; short simple GROUP BY/ORDER BY items on one line.
- JOIN is indented 8 spaces from FROM. (checked) LEFT/RIGHT/FULL JOIN always has `OUTER`.
- (checked) Never use a CTE (`WITH … AS`) or a `#temp` table. Use derived-table JOINs, and a table variable (`@TMP…`) where staging is needed (XML parsing etc.). Hierarchies: `CROSS APPLY` the existing table function ([complex-select.md](complex-select.md#bom-expansion--reverse-expansion)).
- Do not wrap CONVERT twice in the same NUMERIC/DECIMAL type.
- (checked) No `SELECT *`, except from `OPENXML` or a table function.
- (checked) Leading commas. Keep the order of SELECT list, UPDATE SET, SP arguments and defaults aligned. Distinguish alias AS from output column AS.
- (checked) ON goes on the line after JOIN. ON of a plain JOIN and its ANDs align with the I of JOIN. Derived FROM/JOIN: opening and closing parentheses align, inner clauses one more space. ON/AND/OR of a derived JOIN sit in the opening-parenthesis column. Nesting and UNION follow each parenthesis.
- EXISTS: parenthesis in the same column, inner SQL on the next line one more space. CASE follows [procedure.md CASE](procedure.md#case). BETWEEN's AND stays inside its expression.
- (checked) INSERT columns and values form a grid: [style-insert.md](style-insert.md#insert-column-grid). UPDATE SET is a vertical list.
- Do not add new NULL/empty replacements. Adding `ISNULL(..., 0)` to arithmetic needs a user request.
- Keep JOIN kind/order/conditions, output column order/type/fields, literals, Korean text and existing comments. A comment-out request keeps the original text. Keep the real meaning of required JOINs, IF EXISTS, business functions and constants.
- When converting to JOIN check full key, NULL, duplicates, aggregation unit, the function's original and run semantics. For several result sets match period, filter, aggregation key, UNION and ratios.
- A request for one UPDATE completes that UPDATE FROM/CROSS APPLY. DB changes: confirm the given connection/DB/key, transaction, and changed/excluded rows. Staging tables only when hard without.

## Formatting untouched parts

When the task changes an SP's logic, also bring the untouched parts to this layout so the whole SP follows the rules. Do not leave the original's one-line `INSERT INTO @T (A, B, C…)` lists, table variables with several columns per line, `WHERE @WORKTYPE IN (…)` inside `EXISTS`, or lines over 120 characters. `SET XACT_ABORT ON` and `THROW` are transaction code too ([save-tran.md](save-tran.md#transactions)). Before finishing, run the SKILL.md check on the whole SP. This differs from format-only requests, where logic is not changed.

## Alias roles

Before changing aliases in a general cleanup, write `alias | table | business role | link key` for each table. Aliases follow this role, not JOIN order or the table name's first letter. One rule for every table (FROM, plain JOIN, derived JOIN). The main FROM target comes first, so it is always **A**.

- **Same business as a table that already has a letter → that letter plus a number**: helper tables adding standard/setting/approval values to its rows, a header's detail, derived tables splitting the same source by condition. A's → A1, A2; B's → B1, B2; the same for any letter.
- **New business → next letter** (B, C, D…) in order of appearance, even if it joins on an earlier table's key.
- A same-business table appearing before its base still takes the business letter. Do not change JOIN order.

| Original | Alias | Basis |
| --- | --- | --- |
| `PR110T` process plan | `A` | main target |
| `PR100T` standard time | `A1` | A's process/item standard (same business), not `B` |
| `SA100T` order header | `B` | new business |
| `BA011T` process name code | `C` | new business |
| `SA110T` order detail | `B1` | B's detail, B family regardless of C before it |
| `PR210T` result total (PARTCD <> 'Y') | `D` | new business |
| `PR210T` result total (PARTCD = 'Y') | `D1` | same source as D by condition |
| `BA905T` drawing file | `E` | new business |

Judge "same business" from the table description, real link keys and used columns. If evidence is thin, write `미확인` and the reason in the role table and ask the user. In the answer, list original → new alias with the role basis.

```sql
SELECT A.GONUM
     , A1.STDTIME
     , B.HULLNO
     , B1.ITEMNM
     , C.SUBNM3
FROM PR110T A
        LEFT OUTER JOIN PR100T A1
                     ON A.ORGDIV = A1.ORGDIV
                     AND A.PROCCD = A1.PROCCD
        LEFT OUTER JOIN SA100T B
                     ON A.ORGDIV = B.ORGDIV
                     AND A.ORDNUM = B.ORDNUM
        LEFT OUTER JOIN BA011T C
                     ON A.PROCCD = C.SUBCD
        LEFT OUTER JOIN SA110T B1
                     ON A.ORGDIV = B1.ORGDIV
                     AND A.ORDSEQ = B1.ORDSEQ
```

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
                SELECT T.PERIOD, T.QTY
                FROM HISTORY T

                UNION ALL

                SELECT T.PERIOD, T.QTY
                FROM ORDERS T
               ) T
          GROUP BY T.PERIOD
         ) A
    ORDER BY A.PERIOD
```
