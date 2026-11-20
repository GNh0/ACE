---
name: sql
description: SQL Server 쿼리·프로시저(SP)를 사용자 방식으로 작성·수정·정리·검토한다. SQL 정리, 쿼리 작성, 조회(SELECT) SP, 저장(SAVE) SP, T-SQL 리뷰 요청에 사용한다.
---

# SQL

필요한 참조 문서만 하나씩 연다. 여러 문서를 한 번에 출력하지 않는다(잘린다).

Reply to the user in Korean. Don't delegate this skill.

## Start

1. Read [lessons](references/lessons.md) and `~/.claude/ace/lessons/sql.md` (newer); they override rules.
2. Changing an SP: read it all and its real caller (C#/PB). New SP: ask for the author and a same-role SP; read it fully (rules beat its formatting).

| Task | Read |
| --- | --- |
| Format only (report logic; drop lock hints) | [style](references/style.md), [style-insert](references/style-insert.md) |
| SELECT, new SELECT SP (BOM/pivot: [complex-select](references/complex-select.md)) | [select](references/select.md), [procedure](references/procedure.md), [style](references/style.md) |
| New SAVE SP | [procedure-save](references/procedure-save.md), [save](references/save.md) |
| Change SAVE SP (allocation/stock: [save-stock](references/save-stock.md)) | [save](references/save.md), [save-edit](references/save-edit.md), [save-tran](references/save-tran.md) |
| Closing, numbering, keys, names | [kone](references/kone.md) |
| Run checks | [verify](references/verify.md), [verify-save](references/verify-save.md), [verify-report](references/verify-report.md) |

## Always-keep rules

(c) = checked by `check_sql.py`.

- (c) Uppercase, leading commas, left-aligned clauses, ON on its own line, `OUTER`, no `SELECT *`, ≤120 chars. [style](references/style.md#sql-layout)
- Keep JOINs, conditions, column order, literals, comments; add no NULL replacement. [style](references/style.md#sql-layout)
- (c) No CTE or `#temp` tables: derived JOINs; table variables for staging. [style](references/style.md#sql-layout)
- (c) INSERT grid: long value last on its line. [style-insert](references/style-insert.md#insert-column-grid)
- Business comment above key conditions; (c) no derived `AS QTY`. [style-insert](references/style-insert.md#condition-comments)
- Logic change: format untouched parts too. [style](references/style.md#formatting-untouched-parts)
- (c) WHERE EXISTS/IN → JOIN; keep SAVE `IF EXISTS`. [select](references/select.md#exists--join)
- Code names JOIN `BA011T`; user names `F_FIND_USERNM` outermost only. [kone](references/kone.md#name-lookup)
- (c) **No lock hints**, even from the original. [save](references/save.md#lock-hints)
- (c) SAVE: no count/MAX-seq vars, intermediate tables, loops, NEW/EDIT copies; few `@vars`. [save](references/save.md#save-fixed-rules)
- (c) Numbering only via the common SP, never `BA100T`. [kone](references/kone.md#sp_system_ba100t_keycode)
- Transaction follows the caller: `ExecSPTrn` none; `ExecSP`/unknown keep. [save-tran](references/save-tran.md#transactions)
- Args the screen may send `null`: `= NULL`. [save-tran](references/save-tran.md#arguments-the-screen-may-pass-as-null)
- EDIT: `DEL` delete, only `MOD` UPDATE (pairs too), only `NEW` INSERT. [save-edit](references/save-edit.md#row-states-in-edit)
- Saved detail row = DETAIL row unit. [save-edit](references/save-edit.md#same-row-unit-for-select-and-save)
- No unrequested validation; propose it. [save](references/save.md#unrequested-validation)
- Rollback test calls the SP like the screen. [verify-save](references/verify-save.md#must-keep)
- Never break one rule for another; pick the safer one, state the conflict at the top.
- "Keep behavior": if a result may change, don't; if you must, put "원본과 달라지는 경우" at the top.
- No LINQ, staging tables or builds unless very hard/slow without; say why.

## Work files and cleanup

- Work files (drafts, copies, tests, logs) go to a task folder in `%TEMP%`, never the source.
- **`.sql` files never go inside the solution folder**: use `SQL\<YYYYMMDD>\` in the `.sln` folder's parent (`…\고객사\SQL\20261120\`). Never use an `SQL` folder inside it; propose moving it. No commit. Unsure: ask.
- Write only the final deliverables to the source folder, and only to the path you were given.
- Leave processes and services you did not start alone.
- Temp files still needed for the next step may stay; give their paths in the answer.
- Stop your processes; remove your temp files (`git status`); report unknown ones.

## Self-check

1. Diff original vs final: nothing unrequested.
2. Check every rule and lesson; rules without (c): yes/no with evidence (caller file:line; hash if applied).
3. Scenario table: [verify-report](references/verify-report.md). Run by default; else write exactly: `실행 검증: 하지 않음 - <이유>`
4. Run, fix `[실패]`, rerun; paste the last line (`ACE-CHECK: PASS 22/22`); judge `[확인]` lines:

   ```
   python <스킬 폴더>/scripts/check_sql.py <최종.sql> --caller ExecSPTrn --original <원본 사본.sql>
   ```

   `--caller` is `ExecSPTrn`/`ExecSP`/`unknown`.
5. Clean up.

## Compound

After a correction, fix it and, without asking, add it to `~/.claude/ace/lessons/sql.md` and write `교정 기록에 추가: <제목>`. [compound.md](references/compound.md)
