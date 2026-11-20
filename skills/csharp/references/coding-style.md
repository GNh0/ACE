# C# coding style

## Priority of requirements

- The latest request and agreed rules win. Change only the requested members; keep the target's existing properties, events, branches, transactions, bindings and user edits (width, order, Font, Visible) outside the request.
- **Reference vs target.** A screen from another project that the user names ("C_KONE110_1 DE100100 참조만") is a reference for layout and function only. Code and Designer style follow sibling screens of the same role **in the target project**. Members, signatures, helpers and flags that exist only in the reference are used only if the target project has them. Copying the reference verbatim was the most frequent correction (264 cases).
- When the user names no reference, ask for one in the target project. Other UI structures follow their own project.

## Syntax and naming

- 4 spaces, braces on their own lines. (c) `if`/`else`/loops always have braces, even one-liners (`if (...) return;` never) — also when the existing screen has brace-less ifs. Keep existing else-if and early-return structure.
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

- Follow the real `FrmDevBase` screen order: enum, state/data properties, constructor, commands, query/save methods.
- Static layout in the Designer; named handlers where the target subscribes after `InitializeComponent`. Check both files for double subscriptions, dynamic removal, and duplicate popups from Repository `ButtonClick` and grid `RowCellClick`.
- For existing query/save calls check arguments and returns, failure/cancel, and init/protect/re-query; use shared handlers and helpers as they really are.

## Database and rows

- `DbParameter` one per line in real argument order with leading commas. Keep `ExecSP`/`ExecSPTrn`, edit mode, XML TableName and row states, result-table order.
- Add to `DataTable`/`DataRow` directly. Before cloning a schema or building an intermediate table check what existing helpers return. Compare checked vs focused rows and the real exception/`ShowMessage` path.

```csharp
DataRow drNew = dtList.NewRow();
drNew["ITEMCD"] = drItem["ITEMCD"];
dtList.Rows.Add(drNew);
```

## Use existing APIs

| Don't | Instead |
| --- | --- |
| Assign `DateTime.Today` to a date control | its `SetToDay(int)` |
| Delete selected rows in a loop | `DeleteSelectedRows()` |
| MAX+1 sequence in the screen | the SAVE SP numbers rows |
| Compare original values to find changed rows | `DataRowState` and the `DataTableToXml` state argument |
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
