# framework screen ↔ SP contract

framework strings for the generic contract table ([csharp verify.md](../../csharp/references/verify.md#contract-table)) and the XML rules for SAVE rollback tests ([sql verify-save.md](../../sql/references/verify-save.md#must-keep)). Library facts behind them: [framework.md](framework.md#library-behaviour).

## Contract rows

| # | Screen side (framework) | SP side | Verdict |
| --- | --- | --- | --- |
| 1 | `SaveTrn(` / `SaveNoTrn(` | transaction code or not | `SaveTrn` + no SP transaction, or `SaveNoTrn` + `BEGIN TRAN`/`COMMIT`/`CATCH` rollback = match; crossed = mismatch. Never drop the SP transaction of an `SaveNoTrn` save ([save-flow.md](save-flow.md#saving-rules)); quote the call line |
| 2, 3 | each `new DbParameter("@…"`; `null` values (method arguments defaulting to `null`, locals set only in some branches, `EditValue`) | argument list, `= NULL` defaults | `new DbParameter("@X", null)` is not sent: no default = mismatch |
| 4 | `enum SelectType` members, `m_EditState.ToString()`/`ToUpper()`, `GetEditModeWorkType()`; `DEFAULT` when the handler has no mode check. `EditMode` names from the target `FrmBase.cs` (`<profile>/projects/<PROJECT>.md`) | `IF @WORKTYPE = '…'`, allowed-value check | each value has a branch or is rejected |
| 5 | `dt.TableName = "…"` on the same table object (a getter returning a new table each time loses it) | `OPENXML(…, '/ROOT/…', 1)` | case-sensitive |
| 6 | `TableToXml` state argument; `SetModified`/`AcceptChanges`/`DeleteSelectedRows`/`ImportRow` lines | `GBN` branches (`NEW`/`MOD`/`DEL`/`UNC`) | each sent state handled or skipped on purpose; SP not reading that XML's `GBN` = match |
| 7 | saved table columns and value source: grid schema, panel `BindingField` via `PanelToTable`, code assignment | `WITH` columns | a `WITH` column missing from the XML is NULL silently; in `UPDATE … SET` it overwrites with NULL |
| 10 | panel `BindingField` (`RowToPanel`) | result columns of the row shown | per control |
| 12 | `parmOutput.Value` (`SaveTrn`) or `.parm.Value` (`SaveNoTrn`) → `GridRowIndex` | `SET @OUTPUT = …` per branch | the screen survives branches without a value (delete) |

## framework judgement criteria

- **`TableToXml`** defaults to Added/Modified/Deleted. If the SP expects `UNC`, the screen must add Unchanged. Deleted rows go out with Original values. A column present with a NULL value goes out as an empty string or `0`.
- **Schema from an empty key**: a getter calling `QuerySP(DETAIL, string.Empty)` when `DataSource == null` makes that mode's result the source of the save XML columns (row 7).
- **Values set in code**: `PanelToTable` fills only columns with a `BindingField`. For `WITH` columns without binding cite the assignment (`dtMaster.Rows[0]["…"] = …`); none = mismatch.
- **Header XML `GBN`**: panel headers use `PanelToTable(New)`, so they go out as `NEW` even in edit mode. SP ignores header `GBN` = match; reads it = mismatch.
- **Delete sent as list rows**: cite the `ImportRow` (state kept, usually Unchanged) or `SetModified` line together with the `TableToXml` state; check in row 3 whether other XML arguments stay `null`.
- **Popups**: compare `pop.drCust["…"]` with the SP/mode that built it (rows 10, 11).

## Rollback test XML

Build each XML argument exactly as `TableToXml` would send it:

| Rule | Why |
| --- | --- |
| `FOR XML RAW('<TableName>'), ROOT('ROOT')`; TableName is the screen's `dt.TableName` | The SP's `OPENXML` path is `/ROOT/<TableName>` |
| Row state as a column: `'NEW' AS GBN` | `TableToXml` adds a `GBN` attribute per row |
| With Korean text prefix `<?xml version="1.0" encoding="euc-kr"?>` | The SP takes XML as `VARCHAR`; without it `SP_XML_PREPAREDOCUMENT` fails with "텍스트 내용에 잘못된 문자가 있습니다". The screen adds the same declaration |
| Dates as `CONVERT(VARCHAR(8), col, 112)` | The screen sends `yyyyMMdd` (`yyyy-MM-dd HH:mm:ss` with time); `FOR XML` writes `2026-11-19`, truncated in `VARCHAR(8)` |

Check the serialization (NULL columns omitted, `GBN`/`NUM` attributes, DateTime format) once in the target project's `DataUtil.cs`. `FOR XML RAW` also omits NULL columns.

Common SPs' writes (`SP_LOG_XML` log, `SP_NEW_KEY` sequence) are in the same transaction and roll back too. In a failed-check scenario the log is written before the failure, so judge "nothing written" by business tables.

## Example

From two real screens (header panel + detail grid saved with `SaveTrn`; two XMLs saved with `SaveNoTrn`), names changed, matching rows trimmed.

| # | Contract | Screen | SP | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Save call | `XX000200.cs:336` `SaveNoTrn("sp_XX000200_SAVE"` | DB 정의 `:214-215` `BEGIN TRY`·`BEGIN TRANSACTION`, `:546` COMMIT, `:551` ROLLBACK | 일치 |
| 3 | Null arguments | `XX000100.cs:253` `string strXmlDetail = null;`, delete branch (254-265) never assigns → `:283` `@XML_DETAIL` | DB 정의 `:12` `@XML_DETAIL VARCHAR(MAX)` no default | **불일치(정적, 실행 미확인)**: "not supplied" on delete |
| 4 | `@WORKTYPE` | `XX000100.cs:278` `m_EditState.ToString()`, `FrmBase.cs:108-114` DEFAULT·EDIT·NEW·DELETE; no mode check in the save handler → DEFAULT possible | DB 정의 `:70` `NOT IN ('NEW', 'EDIT', 'DELETE')` → RAISERROR | 일치 (SP rejects DEFAULT) |
| 7 | XML columns | detail schema = `sp_XX000200_SELECT` DETAIL `:71-102` | `sp_XX000200_SAVE` `:131-153` `WITH` 23 columns | **불일치 20/23**: `SPEC1` (`:137`), `SPEC2` (`:138`) missing → NULL; `:370-371` MOD UPDATE overwrites both with NULL |
| 12 | Key after save | `XX000100.cs:287` `strFindKey = parmOutput.Value` → `:121` `GridRowIndex(…, "DOCNUM", strFindKey)` | `:529` `SET @OUTPUT = @DOCNUM` (NEW·EDIT only) | 일치 (delete → NULL → empty string) |

Rows 2, 5, 6, 8-11 matched and were left out here. Real answers never leave rows out: write `범위 밖` or counts.

## Impact before changing an SP

Before changing an existing SP (its parameters, result columns, rows written or errors raised), list what depends on it, with evidence:

- Screens: search the solution for the SP name (`.cs`, also `.Designer.cs` and string constants); note each call (`SaveTrn`/`SaveNoTrn`, `DbParameter` list, columns the grid binds).
- Other SPs and functions: `SELECT OBJECT_NAME(object_id) FROM sys.sql_modules WHERE definition LIKE '%<SP name>%'` on the project DB.
- Tables written: tables in INSERT/UPDATE/DELETE and the screens that read them (a changed key or sequence shows up there).

Write the list before the change ("영향: 화면 A·B, SP C, 테이블 D") and mark what you could not verify as `미확인`. After the change, compare it with the real diff: every changed parameter, result column or raised error must appear in the list; the scenario table covers each affected caller. (Idea from ECC change-impact, MIT.)

