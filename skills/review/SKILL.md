---
name: review
description: SP·화면 변경을 ACE 규칙으로 따로 검토한다. 조용히 실패를 숨기는 코드, 화면↔SP 계약 불일치, 규칙 위반을 근거(파일:줄)와 함께 찾는다. "리뷰해줘", "검토해줘", "이거 맞아?", 작업을 끝내기 전 자체 검토에 사용한다. 고치지는 않고 찾기만 한다.
---

# ACE review

Review a change against the ACE rules with fresh eyes. **Find, don't fix**: report findings; the author decides. Ideas from ECC csharp-reviewer, database-reviewer and silent-failure-hunter (MIT), rewritten for SQL Server SPs and WinForms/DevExpress screens.

## Start

1. Scope = the files the change touched (diff against the original copy, `_BAK`, SVN base or the DB definition). Read each changed file whole, and the other side of the contract: a changed SP → its calling screen(s); a changed screen → the SP(s) it calls.
2. Read the rules of the layers involved: [sql](../sql/SKILL.md), [csharp](../csharp/SKILL.md), [erp](../erp/SKILL.md) (profile names: [profile](../erp/references/profile.md)) and their `lessons.md`.
3. Run the checkers on every changed file and keep their `[실패]`/`[확인]` lines:
   `python <ACE>/skills/sql/scripts/check_sql.py <file.sql> --caller trn|plain|unknown --original <orig>` and
   `python <ACE>/skills/csharp/scripts/check_designer.py <file> --original <orig>`.

## What to look for (beyond the checkers)

**Silent failures** — a wrong result with no error:
- `RAISERROR` without `RETURN` outside TRY; a check placed after the write it guards; a pre-check that ignores this save's own rows.
- A LEFT OUTER JOINed value compared or multiplied without `ISNULL(X, 0)` (a missing row passes the check).
- `ISNULL`/`COALESCE` falling back to another column; `NULLIF … IS NULL` in conditions; CASE without ELSE feeding a NOT NULL column.
- A LEFT JOIN whose joined-table filter sits in WHERE (silently INNER); an INNER JOIN that drops rows the user expects (master tables).
- Empty `catch { }`, `catch` that only logs; `QuerySP(...).Tables[0]` without a null check; a save path that returns `true` after a failed call.
- Debug `SELECT` left in a SAVE (the screen reads the wrong result set).

**Screen ↔ SP contract** ([contract](../erp/references/contract.md)):
- Every `DbParameter` name exists in the SP with a compatible type; arguments the screen may send as null have `= NULL`.
- `dt.TableName` = the SP's `OPENXML` path; row states sent (`TableToXml` mask) = the GBN values the SP handles.
- `@WORKTYPE` values the screen sends = the SP's branches (project mode names).
- Result columns the grid binds (`FieldName`) exist in the SELECT; the key shown and the `@OUTPUT` key are the same expression.
- Transaction place matches the call (`SaveTrn` → no SP transaction).

**Not findings** (user decided they are fine either way): the empty-XML early `RETURN`, `SELECT *` vs a column list when staging OPENXML, header comment form.

**Scope and behaviour**: changes outside the request; behaviour changed without being listed in the answer; existing user edits (widths, order, captions) undone.

## Report

Write Korean, most severe first, one line each, then the evidence:

| 심각도 | 위치 | 문제 | 근거 |
| --- | --- | --- | --- |
| 오류 / 위험 / 규칙 | `file:line` | what breaks or which rule | the quoted line, the rule link, or the other side of the contract (`file:line`) |

End with `검토 결과: 오류 N, 위험 N, 규칙 N` and the checker last lines. Nothing found → say so and list what was checked. Never claim a finding you did not see in the file.
