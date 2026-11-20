# Contract check (EDD)

The user does not build or run by default, so screen verification is a **table comparing screen calls with the SP contract, with line numbers on both sides**. Copy the strings from both sides; never "should match". How to find the lines and an example: [verify-evidence.md](verify-evidence.md).

- If the user asked for or allowed build/run, use the results. A passing build proves no display, binding or query timing.
- SP changed and the dev DB may be used: sql skill `references/verify-save.md` (rollback test; SELECT comparison in `references/verify.md`).
- Screen-only changes that touch SP-calling code still fill the table.

## Scope

Fill only the rows the change touches and write `범위 밖` for the rest in one line under the table. A whole screen (two .cs/Designer files, some libraries, two SP definitions, ~20 tool calls) only for a new screen or when the user asks for a full review.

| Changed | Rows to fill |
| --- | --- |
| Save call (`ExecSPTrn`/`ExecSP`), SP name | 1, 2 |
| `DbParameter` added/removed/reordered/value | 2, 3 |
| `@WORKTYPE`, `enum SelectType`, `m_Editmode` assignment/check | 4 |
| `dt.TableName`, the saved table | 5, 6, 7 |
| `DataTableToXml` state, `SetModified`/`AcceptChanges`/`DeleteSelectedRows` | 6 |
| Panel control or `BindingField`, `MasterToDataTable` call | 7, 10 |
| Grid column or `FieldName` | 9 |
| `ds.Tables[n]`, `DataSource =` | 8, 9 |
| `dr["…"]` read/write, `NewRow` assignment, `Select` filter | 11 |
| `@OUTPUT`, re-query/focus after save | 12 |
| SP arguments, XML path, `WITH`, branches, `SELECT` columns | every screen row the change reaches |

## Contract table

| # | Contract | Screen (file:line) | SP (file:line) | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Save call | `ExecSPTrn(` / `ExecSP(` | transaction code or not | `ExecSPTrn` + no SP transaction, or `ExecSP` + `BEGIN TRAN`/`COMMIT`/`CATCH` rollback = match; crossed = mismatch |
| 2 | Arguments | SP name, each `new DbParameter("@…"`, Output direction/size | `CREATE PROCEDURE`, each argument | name, order, count, `OUTPUT`; commented arguments must be commented on both sides |
| 3 | Null arguments | arguments that can be `null` | their default (`= NULL`) | no default = **mismatch**: null values are not sent ([kone120.md](kone120.md#library-behaviour)) |
| 4 | `@WORKTYPE` | every value the screen **can** send (enum members, `ToString()`/`ToUpper()`, `DEFAULT` when no mode check) | `IF @WORKTYPE = '…'` branches, allowed-value check | each value has a branch or is rejected with an error = match; silently passing = mismatch |
| 5 | XML TableName | `dt.TableName = "…"` | `OPENXML(…, '/ROOT/…', 1)` | case-sensitive; the name is set on the same table object (a getter returning a new table each time loses it) |
| 6 | Row states | `DataTableToXml` state, lines changing state | `GBN` branches | each sent state handled or intentionally skipped; SP not reading that XML's `GBN` = match |
| 7 | XML columns | saved table's columns and **value source**: grid schema, panel `BindingField`, code assignment | `WITH` columns | every column the SP reads exists and is filled; a missing column used in `UPDATE … SET` overwrites with NULL |
| 8 | Result tables | each `ds.Tables[n]`, paired with its mode | `SELECT` order in the branch | per mode and n |
| 9 | Grid columns | `FieldName` of columns in `Columns.AddRange`, the mode feeding that grid | that mode's result columns (`AS …`) | all visible columns match; hidden ones per the criteria below |
| 10 | Panel binding | `BindingField` of panel controls | result columns of the row shown | per control; per result when several fill one panel |
| 11 | Column names in code | `dr["…"]`, `NewRow` assignments, `Select`/`GetGridRowIndex` filters | result columns of the mode that built the row/table | per column; generated values have the SP's format (separators) |
| 12 | Key after save | line reading `@OUTPUT` → re-query/focus | `SET @OUTPUT = …` (which branch) | screen survives branches without a value (delete); unused = `해당 없음` |

- Every cell: file path and line, with the compared strings (`dt.TableName = "DOC_DETAIL"` ↔ `'/ROOT/DOC_DETAIL'`).
- Wide rows (7, 9, 11): counts like `24/24 일치`, plus name and line of each mismatch.
- `OPENXML` paths and `WITH` names are **case-sensitive**. A `WITH` column missing from the XML becomes NULL silently, so a missing column still "saves". A column present with a NULL value goes out as an empty string or 0 ([kone120.md](kone120.md#library-behaviour)).
- `DataTableToXml` defaults to Added/Modified/Deleted. If the SP expects `UNC`, check that the screen adds Unchanged. Deleted rows go out with Original values.
- `ExecSP` saves: never drop the SP's transaction ([save-flow.md](save-flow.md#saving-rules)); quote the call line.
- Unfound cell: `미확인` plus reason. Any `불일치`: fix it or put it at the top of the answer; unexecuted ones as `불일치(정적, 실행 미확인)`.

## Judgement criteria

- **One SELECT SP, several modes**: pair each mode with its grid/panel/table via `DataSource =`/`DataRowToPanel(`; fill rows 8-11 per mode.
- **Schema from an empty key**: a getter calling `CallSelectProcedure(DETAIL, string.Empty)` when `DataSource == null` makes that mode's result the source of the save XML columns (row 7).
- **Hidden columns/controls**: not in the result, `Visible = false`, not in `WITH`, not read by code → `영향 없음`, count only (copied hidden columns can be dozens). Any one of the three hit → mismatch.
- **Values set in code, not bound**: `MasterToDataTable` fills only columns with a `BindingField`. For `WITH` columns without binding cite the assignment (`dtMaster.Rows[0]["…"] = …`); none = mismatch.
- **Header XML `GBN`**: panel headers use `MasterToDataTable(New)`, so they go out as `NEW` even in edit mode. SP ignores header `GBN` = match; reads it = mismatch.
- **Delete sent as list rows**: cite the `ImportRow` (state kept, usually Unchanged) or `SetModified` line together with the `DataTableToXml` state; check in row 3 whether other XML arguments stay `null`.
- **Values from popups/other grids**: compare the popup result row (`pop.drCust["…"]`) or other grid row with the SP/mode that built it (rows 10, 11); popup SP unread = `미확인`.
- **Columns built in code**: cite `Columns.Add`/`FieldName` lines; auto-generated columns from `DataSource` are result columns as is, so row 9 is `해당 없음`.
