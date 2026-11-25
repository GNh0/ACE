# C# coding style

## Priority of requirements

- The latest request and agreed rules win. Change only the requested members; keep the target's existing properties, events, branches, transactions, bindings and user edits (width, order, Font, Visible) outside the request.
- **Reference vs target**: [work skill](../../work/SKILL.md#reference-vs-target). Other UI structures follow their own project.

## Syntax and naming

- 4 spaces, braces on their own lines. A one-statement guard on the same line is fine (`if (m_EditState != EditMode.Default) return;`, 269 uses in 29 of 30 PROJECT_B screens), and so is the braced form (user, 2026-11-24: both allowed, not checked). Keep existing else-if and early-return structure.
- Declare `DataTable`, `DataRow`, `DataSet` and primitive types explicitly. Keep get blocks, explicit assignments and switch branches. Locals: `str`/`dt`/`dr`/`ds` plus the screen's habits.
- Check `TryParse` success and value in separate ifs. Display strings use interpolation. Keep SQL/XML/key formats and external identifiers. Action `Tag`s and their cases are uppercase.
- Multi-line arguments and enum members use leading commas. Date inputs: `ymd` + field.

```csharp
DataTable dtList
{
    get
    {
        return grdList.DataSource as DataTable;
    }
}
```

## Structure and events

- Static layout in the Designer; named handlers where the target subscribes after `InitializeComponent`. Check both files for double subscriptions, dynamic removal, and duplicate popups from Repository `ButtonClick` and grid `RowCellClick`.
- For existing query/save calls check arguments and returns, failure/cancel, and init/protect/re-query; use shared handlers and helpers as they really are.

## Event subscriptions

Example constructor: erp [screen-skeleton.md](../../erp/references/screen-skeleton.md#constructor).

- Subscriptions here, after `InitializeComponent()` (90% of the user's); don't move existing Designer ones unasked.
- Form events in this order, only those needed (`Shown`, `PrintCommand` in order too). Handler name: control name with a capital first letter + `_` + event (`gvwList` → `GvwList_FocusedRowChanged`); form events `<screen ID>_<event>`.
- Named methods only, no lambdas; never twice (check Designer and constructor). Value changes: `EditValueChanged`, not `TextChanged`/`Leave`/`Validating`.

## Database and rows

- Add to `DataTable`/`DataRow` directly. Before cloning a schema or building an intermediate table check what existing helpers return. Compare checked vs focused rows and the real exception/`Msg` path.

```csharp
DataRow drNew = dtList.NewRow();
drNew["ITEMCD"] = drItem["ITEMCD"];
dtList.Rows.Add(drNew);
```

## Use existing APIs

framework API rows: erp [behaviors.md](../../erp/references/behaviors.md#use-these-apis).

| Don't | Instead |
| --- | --- |
| Delete selected rows in a loop | `DeleteSelectedRows()` |
| MAX+1 sequence in the screen | the SAVE SP numbers rows |
| Pass a control's `Tag` to the SP | `EditValue` or a separate key control |
| Add a UI/data helper because it is shorter | keep existing event and save boundaries |
| Add unrequested save blocks or confirmations | existing UI/XML/SP checks; propose new limits |
| Re-query on entering NEW/EDIT | reuse loaded header, detail, schema |
| Copy every header value into a new detail row | only fields XML/SP need |

A `FocusedRowChanged` guard against moving while editing goes **before** the `FocusedRowHandle < 0` early return; on the filter row the guard would be skipped otherwise.

## Numeric display formats

| Request | Format | Hide zero requested |
| --- | --- | --- |
| Thousands, integer | `#,##0` | `#,###` |
| Up to two decimals | `#,##0.##` | `#,###.##` |
| Exactly two decimals | `#,##0.00` | confirm the notation |

- Use a required format as given; otherwise prefer custom formats over `N0`/`N2`. Check constructor and shared repository init first.
- Totals go to `SummaryItem.DisplayFormat`/`GridColumnSummaryItem`; keep suffix, alignment, `SummaryType`, FieldName, and align related `ToString`/`string.Format`/interpolation.
- Keep type, precision, rounding, culture and negative/zero notation. Change cell display, input masks or repositories only when that property must change. [Numeric formats](https://learn.microsoft.com/en-us/dotnet/standard/base-types/custom-numeric-format-strings), [DevExpress summaries](https://docs.devexpress.com/WindowsForms/DevExpress.XtraGrid.GridSummaryItem.DisplayFormat).

## Not used

Counted in the user's framework screens; the "Instead" column names framework APIs ([erp behaviors](../../erp/references/behaviors.md#common-methods)). (c) = `check_designer.py` on code-behind; with `--original` only added lines count.

| Not used | Instead |
| --- | --- |
| (c) `MessageBox.Show` (9 in 3 screens) | `Msg…` (823 in 92 screens) |
| Own `SqlConnection`/`SqlCommand` (0) | `db` |
| `DateTime….ToString("yyyyMMdd")` (0) | `ymd.YYYYMMDD()` |
| `TextChanged`, `Leave`, `Validating` (0) | `EditValueChanged` |
| (c) lambda/`delegate` subscriptions (3/0) | named handlers |
| (c) `PostEditor()` / `CloseEditor()` / `UpdateCurrentRow()` before saving | nothing; the save path reads the DataTable (user corrected this 10+ times) |
| (c) `P_Add`/`P_Edit`/`P_Save`/`P_Delete`/`P_Copy`/`P_Print = …` | toolbar permissions come from program registration (MS060T) |
| (c) `ColumnFilterInfo` / `FilterInfo =` | `gvw.ActiveFilterString` as sibling screens do |
| (c) `FocusedRowHandle = GetRowHandle(…)`/a number after search or add | `ui.GridRowIndex` restore only where siblings do it |
| (c) column `MinWidth =` in code; `grp….Text =` in code | Designer values |
| `BestFitColumns()` beyond the sibling pattern (`[확인]`) | after search as in the skeleton; skip it where the user asked for fixed widths |
