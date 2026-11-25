# Contract check (EDD)

The user does not build or run by default, so screen verification is a **table comparing screen calls with the SP contract, with line numbers on both sides**. Copy the strings from both sides; never "should match". How to find the lines: [verify-evidence.md](verify-evidence.md). **framework-based screens**: the framework strings per row (`SaveTrn`/`SaveNoTrn`, `DbParameter`, `m_EditState`, `TableToXml`/`GBN`, `PanelToTable`/`BindingField`), framework judgement criteria and a worked example are in [erp contract.md](../../erp/references/contract.md).

- If the user asked for or allowed build/run, use the results. A passing build proves no display, binding or query timing.
- SP changed and the dev DB may be used: sql skill `references/verify-save.md` (rollback test; SELECT comparison in `references/verify.md`).
- Screen-only changes that touch SP-calling code still fill the table.

## Scope

Fill only the rows the change touches and write `범위 밖` for the rest in one line under the table. A whole screen (two .cs/Designer files, some libraries, two SP definitions, ~20 tool calls) only for a new screen or when the user asks for a full review.

| Changed | Rows to fill |
| --- | --- |
| Save call, SP name | 1, 2 |
| Parameter added/removed/reordered/value | 2, 3 |
| Mode value the screen sends, mode assignment/check | 4 |
| Name of the serialized (XML) table, the saved table | 5, 6, 7 |
| Row-state changes before serializing | 6 |
| Panel control binding, panel → table copy | 7, 10 |
| Grid column or `FieldName` | 9 |
| Result table index, `DataSource =` | 8, 9 |
| `dr["…"]` read/write, `NewRow` assignment, `Select` filter | 11 |
| Output argument, re-query/focus after save | 12 |
| SP arguments, XML path, parsed columns, branches, `SELECT` columns | every screen row the change reaches |

## Contract table

| # | Contract | Screen (file:line) | SP (file:line) | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Transaction owner | the save call: does it wrap a transaction | transaction code or not | exactly one owner = match; both or neither = mismatch |
| 2 | Arguments | SP name, each parameter added, Output direction/size | `CREATE PROCEDURE`, each argument | name, order, count, `OUTPUT`; commented arguments must be commented on both sides |
| 3 | Null arguments | arguments that can be `null` | their default (`= NULL`) | ADO.NET does not send a parameter whose value is `null`: no default = **mismatch** ("not supplied") |
| 4 | Mode value | every value the screen **can** send (enum members, string conversions, the default mode when the handler has no mode check) | mode branches, allowed-value check | each value has a branch or is rejected with an error = match; silently passing = mismatch |
| 5 | Serialized table name | the name set on the table the screen serializes | the path the SP parses | case-sensitive |
| 6 | Row states | states the screen sends, lines changing state | state branches | each sent state handled or intentionally skipped |
| 7 | Serialized columns | saved table's columns and **value source** (grid schema, panel binding, code assignment) | parsed columns | every column the SP reads exists and is filled |
| 8 | Result tables | each `ds.Tables[n]`, paired with its mode | `SELECT` order in the branch | per mode and n |
| 9 | Grid columns | `FieldName` of columns in `Columns.AddRange`, the mode feeding that grid | that mode's result columns (`AS …`) | all visible columns match; hidden ones per the criteria below |
| 10 | Panel binding | bound field of each panel control | result columns of the row shown | per control; per result when several fill one panel |
| 11 | Column names in code | `dr["…"]`, `NewRow` assignments, `Select`/`GridRowIndex` filters | result columns of the mode that built the row/table | per column; generated values have the SP's format (separators) |
| 12 | Key after save | line reading the Output argument → re-query/focus | `SET @OUTPUT = …` (which branch) | screen survives branches without a value (delete); unused = `해당 없음` |

- Every cell: file path and line, with the compared strings (`dt.TableName = "DOC_DETAIL"` ↔ `'/ROOT/DOC_DETAIL'`).
- Wide rows (7, 9, 11): counts like `24/24 일치`, plus name and line of each mismatch.
- Parse paths and parsed column names are **case-sensitive**; a parsed column missing from the payload becomes NULL silently, so a missing column still "saves".
- Unfound cell: `미확인` plus reason. Any `불일치`: fix it or put it at the top of the answer; unexecuted ones as `불일치(정적, 실행 미확인)`.

## Judgement criteria

- **One SELECT SP, several modes**: pair each mode with its grid/panel/table via `DataSource =` or the panel fill call; fill rows 8-11 per mode.
- **Hidden columns/controls**: not in the result, `Visible = false`, not parsed by the SP, not read by code → `영향 없음`, count only (copied hidden columns can be dozens). Any one of the three hit → mismatch.
- **Values from popups/other grids**: compare the popup result row or other grid row with the SP/mode that built it (rows 10, 11); popup SP unread = `미확인`.
- **Columns built in code**: cite `Columns.Add`/`FieldName` lines; auto-generated columns from `DataSource` are result columns as is, so row 9 is `해당 없음`.
