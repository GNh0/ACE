# SQL lessons

Corrected mistakes; a matching entry overrides other rules. Format and promotion: [compound.md](compound.md). `Rule:` links to the rule's home. Titles are anchors.

Topics: [Layout](#layout), [SELECT](#select), [SAVE structure](#save-structure), [Transactions and numbering](#transactions-and-numbering), [Way of working](#way-of-working).

---

## Layout

### Aliases by business role (KH 3.6.2)
- Mistake: chose aliases by JOIN order or the table name's first letter.
- Rule: same-business tables take the base letter plus a number; only a new business takes the next letter. [style.md](style.md#alias-roles)

### All identifiers uppercase (KH 3.6.3)
- Mistake: kept the original case of output column names (after `AS`) or function/procedure names.
- Rule: everything uppercase except literals, comments and `[...]`. [style.md](style.md#sql-layout)

### Long INSERT values go at the line end (KH 3.6.8)
- Mistake: a 30+ character value mid-line pushed other lines' columns dozens of spaces apart.
- Rule: a long value is the last item on its line; the next column starts on the next line. [style-insert.md](style-insert.md#insert-column-grid)

### Clauses are left-aligned (2026-11-20)
- Mistake: right-aligned FROM/WHERE/AND to the end of SELECT (`  FROM`, ` WHERE`, `   AND`).
- Rule: FROM/WHERE/GROUP BY/ORDER BY start in SELECT's column; do not copy right alignment from existing SPs. [style.md](style.md#sql-layout)

### Key conditions get a business comment (2026-11-20)
- Mistake: wrote quantity/exclusion conditions without a comment, or with a comment that just repeated column names.
- Rule: comment directly above in business terms with the same operator, and name derived aggregates `OUTQTY`/`INQTY`. [style-insert.md](style-insert.md#condition-comments)

### Do not break the INSERT grid into one-cell lines (2026-11-20, C_KONE120 MA100500)
- Mistake: a long `ROW_NUMBER()` passed 120, so I put it alone on a line (`, SEQ2`) and split it, breaking the grid.
- Rule: keep the long value at the end of a shared line; if still over 120, shorten it with a staging `SEQ IDENTITY`. [style-insert.md](style-insert.md#insert-column-grid)

### Also format the untouched original parts (2026-11-20, three-model test)
- Mistake: all three models kept the original's one-line `INSERT INTO @T (…)`, multi-column table variable lines, 120+ lines and `SET XACT_ABORT ON`.
- Rule: when the task changes logic, bring the whole SP to the rules. [style.md](style.md#formatting-untouched-parts)

## SELECT

### No CTE, no #temp tables (2026-11-20, C_KONE120 QC500100)
- Mistake: Codex used a CTE in `SP_QC500100_SELECT` since the rule allowed one "when hard without"; user: "CTE랑 #임시테이블 내가 존나 싫어하는것들인데".
- Rule: never use CTE or `#temp` tables; derived JOINs, table variables only for staging. [style.md](style.md#sql-layout)

### EXISTS/IN subquery → JOIN (KH 3.6.4)
- Mistake: left EXISTS/IN subqueries in WHERE.
- Rule: JOIN a derived table grouped by the link key. [select.md](select.md#exists--join)

### Common-code names by JOIN, user names by function (2026-11-20)
- Mistake: fetched common-code names with the `F_BA011T_FIND_SUBNM` function too.
- Rule: common-code names JOIN `BA011T`; user names use `F_FIND_USERNM` only in the outermost SELECT, JOIN in bulk queries. [kone.md](kone.md#name-lookup)

## SAVE structure

### No lock hints (repeated since before 2026-11-20)
- Mistake: added `WITH (UPDLOCK, HOLDLOCK)` to a SAVE or kept one from the original.
- Rule: never use lock hints; remove them even from the original or reference SP. [save.md](save.md#lock-hints)

### Fix SAVE fixed-rule violations even in the original (KH 3.6.5)
- Mistake: kept count variables, several COMMITs and early RETURNs because the original had them.
- Rule: when changing SAVE logic apply the fixed rules; in format-only work just report locations. [save.md](save.md#save-fixed-rules)

### Minimize @variables (KH 3.6.6)
- Mistake: created assign-once-read-once variables and variables copying header values.
- Rule: write the expression in place or JOIN the table variable / target rows. [save.md](save.md#save-fixed-rules)

### Set-based allocation (KH 3.6.7)
- Mistake: allocated row by row with WHILE/cursor/`SELECT TOP 1 @var` and copied the code into NEW and EDIT.
- Rule: one INSERT with a running-range JOIN; shared processing once. [save-stock.md](save-stock.md#allocation-insert)

### Same row unit for SELECT and SAVE (2026-11-20, C_KONE120 MA100500)
- Mistake: the save merged rows with `GROUP BY` but DETAIL returned child rows with the merged amount; re-saves multiplied it.
- Rule: check that one saved detail row and one DETAIL row are the same unit. [save-edit.md](save-edit.md#same-row-unit-for-select-and-save)

### EDIT works by row state (2026-11-20, C_KONE120 MA100500)
- Mistake: EDIT deleted and re-inserted all details, overwriting registrant/date and renumbering.
- Rule: split by `GBN`: DEL deletes, only MOD updates, only NEW inserts, number only when NEW rows exist. [save-edit.md](save-edit.md#row-states-in-edit)

### MOD rows also UPDATE the paired table (2026-11-20, three-model test)
- Mistake: updated `MOD` details but deleted/re-inserted their paired issue rows, renumbering them.
- Rule: `MOD` rows are UPDATEd in every target table. [save-edit.md](save-edit.md#row-states-in-edit)

### No unrequested validation (2026-11-20, three-model test)
- Mistake: added "duplicate selection" / "unregistered item" checks to keep sequence pairs or JOINs safe.
- Rule: make it work without new checks; propose needed ones in the answer. [save.md](save.md#unrequested-validation)

### XML arguments the screen passes as null get a default (2026-11-20, C_KONE120 MA100500)
- Mistake: `@XML_MA110T` had no default; the screen sends `null` on delete (`MA100500.cs:253`), so delete failed "not supplied"; the test always passed it.
- Rule: give `= NULL` and omit the argument in the rollback test like the screen. [save-tran.md](save-tran.md#arguments-the-screen-may-pass-as-null), [verify-save.md](verify-save.md#must-keep)

## Transactions and numbering

### No transaction code in SAVE SPs (2026-11-20)
- Mistake: put `BEGIN TRANSACTION`/`COMMIT`/`ROLLBACK`/`TRY/CATCH` or `@STARTTRANCOUNT` in a SAVE SP.
- Rule: with an `ExecSPTrn` caller write no transaction code; check the next entry first. [save-tran.md](save-tran.md#transactions)

### Keep the SP transaction for ExecSP saves (2026-11-20, C_KONE120 SA200100)
- Mistake: removed the transaction from `sp_SA200100_SAVE`, whose screen uses `ExecSP`; it was the only protection.
- Rule: find the call line before removing; with `ExecSP` or when you cannot ask, keep it. [save-tran.md](save-tran.md#transactions)

### Do not bypass the common numbering SP to remove a loop (2026-11-20, C_KONE120 PR000100)
- Mistake: to drop a numbering cursor, wrote `BA100T` directly with `ROW_NUMBER()`; no other SP does.
- Rule: number only through the common SP; keep a small loop around just the numbering call. [kone.md](kone.md#sp_system_ba100t_keycode), conflicts: [SKILL.md](../SKILL.md#always-keep-rules)

## Way of working

### SQL files go in the solution's parent folder (2026-11-20, C_KONE120 MA100500)
- Mistake: saved the SP under `SQL\date\` inside the solution, then moved it wrongly twice more.
- Rule: write `.sql` files to `SQL\<YYYYMMDD>\` under the parent of the `.sln` folder; ask when unsure. [SKILL.md](../SKILL.md#work-files-and-cleanup)

### Do not hide cases that change behavior (2026-11-20, three complex-SP test)
- Mistake: a set-based rewrite changed results for "delete then re-add" and "same key twice"; noted low in the report, change made anyway.
- Rule: if results can differ, do not make the change; if it must be made, say so at the top of the answer. [SKILL.md](../SKILL.md#always-keep-rules)
