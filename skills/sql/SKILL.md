---
name: sql
description: SQL Server 쿼리·프로시저(SP)를 사용자 방식으로 작성·수정·정리·검토한다. SQL 정리, 쿼리 작성, 조회(SELECT) SP, 저장(SAVE) SP, T-SQL 리뷰 요청에 사용한다.
---

# SQL

Follow the [work](../work/SKILL.md) skill (Korean replies, lessons, scope, finish, cleanup, Compound). Open only the references below, one per read. framework-based project (ExampleLib / FrmBase / PROJECT_*): also the [erp](../erp/SKILL.md) skill, **except format-only tasks**.

## Start

1. Read [lessons](references/lessons.md) and the local `sql.md` record.
2. Changing an SP: read it all and its real caller (C#/PB). New SP: ask for the author and a same-role SP; read it fully (rules beat its formatting).

| Task | Read |
| --- | --- |
| Format only (report logic; drop lock hints); no erp skill | [style](references/style.md), [style-insert](references/style-insert.md); aliases change: [style-alias](references/style-alias.md) |
| SELECT, new SELECT SP (BOM/pivot: [complex-select](references/complex-select.md)) | [select](references/select.md), [style](references/style.md) |
| New SAVE SP | [save](references/save.md) |
| Change SAVE SP (allocation, quantity limits: [save-stock](references/save-stock.md)) | [save](references/save.md), [save-edit](references/save-edit.md) |
| Run checks | [verify](references/verify.md), [verify-save](references/verify-save.md), [verify-report](references/verify-report.md) |
| Change an existing SP: compare old vs new | `python <스킬 폴더>/scripts/make_compare_test.py --sp dbo.<SP> --new <new.sql> --cases <cases.json>` → one batch: new version as a temp proc, each case on both inside rollback, SAME/DIFF per case ([verify-save](references/verify-save.md#shape)) |

New project or style reference (a DB whose SPs show the user's style): count habits first with `python <스킬 폴더>/scripts/mine_style.py <SP 폴더> [--author <이름>]`; write `rule`/`dont` rows as rules, ask the user about `ask` rows one at a time, cite the golden files.

framework SP skeletons, common SPs (numbering, closing, names), transactions, null arguments, rollback-test XML: erp skill.

## Always-keep rules

(c) = checked by `check_sql.py`.

- (c) Uppercase, leading commas, one SELECT column per line, left-aligned clauses, ON on its own line, `OUTER`, no `SELECT *`, no `DBO.` on tables, ≤120 chars. [style](references/style.md#sql-layout)
- Keep column order, literals, comments; add no NULL replacement. Format-only keeps JOINs and conditions too. Cleanup/"우리 스타일로"/new SP: the style rules below win over the original (master LEFT, no fallback, CONVERT, outer WHERE); change and list differing rows/values, never keep a `[실패]` to preserve behavior. [style](references/style.md#style-rules-win)
- `IF EXISTS` validations come first: all checks run before the first write; never write and then check ("롤백에 기대지 않는다"). [save](references/save.md#save-fixed-rules)
- (c) Every `CASE` has an `ELSE`. [style](references/style.md#sql-layout)
- `CONVERT` before `FORMAT`; `FORMAT` only for a fixed display format (padding, separators, mask). [style](references/style.md#sql-layout)
- (c) No column fallback `ISNULL(B.X, A.X)` / `COALESCE(…)`: take the value from its one correct source. [style](references/style.md#sql-layout)
- (c) A LEFT OUTER JOINed value used in a comparison or calculation is wrapped: `A.QTY > ISNULL(B.OUTQTY, 0)`, `ISNULL(B.QTY, 0) * ISNULL(B.UNP, 0)`; display columns may stay NULL. [style](references/style.md#sql-layout)
- (c) Null/empty checks in conditions (incl. LEFT JOIN found/not found): `ISNULL(X, '') <> ''` / `= ''`; avoid `IS (NOT) NULL` and `NULLIF … IS NULL`. [style](references/style.md#sql-layout)
- (c) No CTE or `#temp` tables: derived JOINs; table variables for staging. [style](references/style.md#sql-layout)
- (c) INSERT grid: long value last on its line. [style-insert](references/style-insert.md#insert-column-grid)
- Business comment above key conditions; (c) no derived `AS QTY`. [style-insert](references/style-insert.md#condition-comments)
- Logic change: format untouched parts too. [style](references/style.md#formatting-untouched-parts)
- (c) WHERE EXISTS/IN → JOIN; keep SAVE `IF EXISTS`. [select](references/select.md#exists--join)
- Default `LEFT OUTER JOIN`; `INNER JOIN` only for the `@TMP` staging table in SAVE writes or rows the user called required. [style](references/style.md#sql-layout)
- (c) Master tables (`MS020T`, `MS030T`, `MS0xxT`): `LEFT OUTER JOIN`, never INNER; required existence = an `IF EXISTS` check only when asked. [style](references/style.md#sql-layout)
- ON = join keys only; filters and aggregate comparisons in the outer WHERE with `LEFT OUTER JOIN`, not long INNER JOIN ON lists or `HAVING`. [style](references/style.md#sql-layout)
- (c) **No lock hints**, even from the original. [save](references/save.md#lock-hints)
- (c) SAVE: no debug/preview result `SELECT`; `MODIP = @USERIP`; business `RAISERROR(…, 16, 1)`, closing `16, 9`; staging named `@TMP<TABLE>`. Optional, never a finding: the empty-XML `RETURN`, `SELECT *` vs a column list from OPENXML. [sp-save](../erp/references/sp-save.md)
- (c) SAVE: no count/MAX-seq vars, intermediate tables, loops, NEW/EDIT copies; few `@vars`. [save](references/save.md#save-fixed-rules)
- EDIT: `DEL` delete, only `MOD` UPDATE (pairs too), only `NEW` INSERT. [save-edit](references/save-edit.md#row-states-in-edit)
- Saved detail row = DETAIL row unit. [save-edit](references/save-edit.md#same-row-unit-for-select-and-save)
- No unrequested validation; propose it. [save](references/save.md#unrequested-validation)
- Rollback test calls the SP like the screen. [verify-save](references/verify-save.md#must-keep)

## Self-check

Run the checker yourself every time; a host hook may not run.

1. Check every rule and lesson; rules without (c): yes/no with evidence (caller file:line; hash if applied).
2. Scenario table: [verify-report](references/verify-report.md). Run by default; else write exactly: `실행 검증: 하지 않음 - <이유>`
3. Run, fix `[실패]`, rerun; paste the last line (`ACE-CHECK: PASS 22/22`); judge `[확인]` lines:

   ```
   python <스킬 폴더>/scripts/check_sql.py <최종.sql> --caller trn --original <원본 사본.sql>
   ```

   `--caller` is `SaveTrn`/`SaveNoTrn`/`unknown` (`unknown` when the caller is not known or the project has no such call).
