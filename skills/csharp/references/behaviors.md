# Events and common methods per behaviour

"Which event and which shared method does this behaviour use." Counted from handler bodies of 100 user screens calling KH-written SPs (C_KONE110_1, 2026-11-20); % = share of those handlers calling the method. Look here first; only then search more sibling screens; a new helper is the last resort.

## Toolbar commands

| Behaviour | Event | Inside the handler |
| --- | --- | --- |
| Init | `Load` | `syCode.BindingCode` (66%), `ymd.SetToDay(n)` (67%), lock with `devFnc.Usr_ControlsProtect(…, true)` (67%); search on open: `CallCommand(BizCommand.Search)` last (25%) |
| Search | `SearchCommand` | mode check → `CallSelectProcedure` (72%) → `DataSource` → `BestFitColumns()` (83%) → `Usr_ControlsProtect(…, true)` (56%); clear detail with `devFnc.InitControl(group)` (52%) |
| New | `NewCommand` | mode check/change (60%) → `InitControl` (50%) → `Usr_ControlsProtect(…, false)` (52%) → needed `SetToDay` (20%) |
| Edit | `EditCommand` | mode check (75%) → no row: `ShowMessageWaring` and return (51%) → change mode → `Usr_ControlsProtect(…, false)` (68%) |
| Save | `SaveCommand` | mode check (67%) → `ShowMessageYesNO` (35%) → `CallSaveProcedure()` (62%) → `ShowMessage("정상처리되었습니다.")` (55%) → `CallCommand(BizCommand.Search)` (67%) |
| Cancel | `ClearCommand` | `m_Editmode = DataEditMode.Default` (60%) → `CallCommand(BizCommand.Search)` (65%) |
| Delete | `DeleteCommand` | mode check (70%) → nothing selected: `ShowMessageWaring` (61%) → `ShowMessageYesNO` (75%) → `gvw.DeleteSelectedRows()` (38%) → `CallSaveProcedure()` (54%) → `ShowMessage` (63%) → search (66%) |
| Print | `PrintCommand` | `GetFocusedDataRow()` → `CallSelectProcedure(SelectType.PRINT, …)` → build report → `ShowRibbonPreview()` |
| Copy | `CopyCommand` | check selection → change mode → `Usr_ControlsProtect(…, false)` → re-init keys and dates only |

- **Every command handler starts with the `m_Editmode` check** (883 occurrences).
- After save/delete refresh with `CallCommand(BizCommand.Search)`, never a second copy of the query code.

## Grid

| Behaviour | Event (subscriptions in 100 screens) | Inside the handler |
| --- | --- | --- |
| Show the focused row's detail | `gvw.FocusedRowChanged` (68) | block while editing (mode check 52%, `ShowMessageWaring`); no row: `InitControl(group)` (41%) and return; `GetFocusedDataRow()` → `CallSelectProcedure(DETAIL)` or `DataRowToPanel` |
| Recalculate other cells | `gvw.CellValueChanged` (26) | check `e.Column.FieldName` → `GetRowCellValue` (73%) → `SetRowCellValue` (69%) |
| Block editing by condition | `gvw.ShowingEditor` (17) | `GetFocusedDataRow()` (76%), mode (58%) → `e.Cancel = true` |
| Open/select by double-click | `gvw.DoubleClick` (11) | `GetFocusedDataRow()` (63%) → popup `ShowDialog()`, or pass the row back and close |
| Block leaving a row while editing | `gvw.BeforeLeaveRow` | mode check → `ShowMessage` → cancel |
| Cell find button (item, customer popup) | `rpsbtn.ButtonClick` (51) | mode check → `GetFocusedDataRow()` (68%) → popup gets `userInfo`, `dbClient` → `ShowDialog() == DialogResult.OK` (86%) → copy the selected row (`drItem`) into `dr["FIELD"]` |
| Detail add/delete | `grp.CustomButtonClick` (17) or `btn.Click` (105) | add: `NewRow()` → assign → `Rows.Add()`; delete: `DeleteSelectedRows()` |

## Inputs

| Behaviour | Event | Inside the handler |
| --- | --- | --- |
| Quantity/amount → totals | `spin.EditValueChanged` (32) | `m_Editmode == Default` → return (100%) → compute |
| Combo → refresh others | `cbo.EditValueChanged` (24) | mode check (70%) → assign or re-query |
| Date → recalc/re-query | `ymd.EditValueChanged` (15) | mode check (86%) → `ymd.YYYYMMDD()` |
| Input find button | `btn.ButtonClick` (`u_ButtonEdit`, 39) | mode check → popup `ShowDialog()` (66%) → assign; attachments `ShowAttPop` |
| Button action (approve, finish, copy) | `btn.Click` | mode check → `ShowMessageYesNO` → save → `ShowMessage` → search |
| Tab change | `tab.SelectedPageChanged` (25) | `CallCommand(BizCommand.Search)` (28%), `Usr_ControlsProtect` (24%) |

- Value-change handlers **also fire when a query fills the control**, so their first line returns when `m_Editmode == DataEditMode.Default`; otherwise every search reruns the calculation and overwrites values. Grid `CellValueChanged` and command handlers check the mode first too.

## Common methods

Most used first; check here before writing anything new. Real signatures: the target project's `KoneLib` source.

| Method | Count | Does |
| --- | --- | --- |
| `devFnc.Usr_ControlsProtect(control, bool)` | 418 | lock (true) / unlock a container or grid |
| `syCode.BindingCode(code, control)` / `BindingorgdivCode(code, orgdiv, control)` | 352 / 31 | fill combo or repository lists |
| `devFnc.InitControl(container)` | 325 | clear inputs in a container |
| `CallCommand(BizCommand.…)` | 276 | run a toolbar command from code |
| `gvw.BestFitColumns()` | 267 | fit columns after a query |
| `ShowMessage` / `ShowMessageWaring` / `ShowMessageError` / `ShowMessageYesNO` / `ShowExcetion(ee)` | 253 / 226 / 195 / 149 / 108 | messages (typos are the real names) |
| `ymd.YYYYMMDD()` / `ymd.SetToDay(n)` | 246 / 173 | date as 8-char SP argument / today ± n |
| `gvw.GetFocusedDataRow()` / `GetDataRow(handle)` / `GetSelectedRows()` | 206 / 112 / 76 | rows |
| `DataUtil.DataTableToXml(table, state)` | 155 | save XML |
| `gvw.GetRowCellValue` / `SetRowCellValue` | 152 / 123 | cell values |
| `devFnc.GetUserPCData()` | 64 | `@USERIP` |
| `gvw.DeleteSelectedRows()` | 59 | mark selected rows Deleted |
| `devFnc.GetGridRowIndex(…)` | 35 | return to the previous row after a re-query |
| `devFnc.DataRowToPanel(row, panel)` / `MasterToDataTable` (`dtMasterToDataTable`) | 32 / 21 (16) | row ↔ panel |
| `userInfo.Orgdiv`, `userInfo.UserId`, `dbClient.GetDataSetFromSP` / `ExecSPTrn` | | login info, query / save |

Inside `CallSelectProcedure`: `GetDataSetFromSP` (79%), `userInfo.Orgdiv` (84%), `YYYYMMDD()` (67%). Inside `CallSaveProcedure`: `DataTableToXml` (95%), `ExecSPTrn` (78%; `ExecSP` 21%, see [save-flow.md](save-flow.md#saving-rules)), `UserId` (100%).

## Not used

(c) = `check_designer.py` on code-behind; with `--original` only added lines count.

| Not used | Instead |
| --- | --- |
| (c) `MessageBox.Show` (9 in 3 screens) | `ShowMessage…` (823 in 92 screens) |
| Own `SqlConnection`/`SqlCommand` (0) | `dbClient` |
| `DateTime….ToString("yyyyMMdd")` (0) | `ymd.YYYYMMDD()` |
| `TextChanged`, `Leave`, `Validating` (0) | `EditValueChanged` |
| (c) lambda/`delegate` subscriptions (3/0) | named handlers |
| (c) `PostEditor()` / `CloseEditor()` / `UpdateCurrentRow()` before saving | nothing; the save path reads the DataTable (user corrected this 10+ times) |
| (c) `P_Add`/`P_Edit`/`P_Save`/`P_Delete`/`P_Copy`/`P_Print = …` | toolbar permissions come from program registration (BA060T) |
| (c) `ColumnFilterInfo` / `FilterInfo =` | `gvw.ActiveFilterString` as sibling screens do |
| (c) `FocusedRowHandle = GetRowHandle(…)`/a number after search or add | `devFnc.GetGridRowIndex` restore only where siblings do it |
| (c) column `MinWidth =` in code; `grp….Text =` in code | Designer values |
| `BestFitColumns()` beyond the sibling pattern (`[확인]`) | after search as in the skeleton; skip it where the user asked for fixed widths |

Whole-area locking is `Usr_ControlsProtect`. A single button or input toggled by state may set `.Enabled` (23 screens) or `.ReadOnly` (16) directly.
