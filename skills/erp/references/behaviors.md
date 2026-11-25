# Events and common methods per behaviour

"Which event and which shared method does this behaviour use." Counted from handler bodies of 100 user screens calling SPs written with the earlier AI plugin (PROJECT_B_1, 2026-11-20); % = share of those handlers calling the method. Look here first; only then search more sibling screens; a new helper is the last resort.

## Toolbar commands

| Behaviour | Event | Inside the handler |
| --- | --- | --- |
| Init | `Load` | `code.Bind` (66%), `ymd.SetToDay(n)` (67%), lock with `ui.ProtectControls(…, true)` (67%); search on open only when asked: PROJECT_B keeps `//RunCommand(Cmd.Search);` commented out at the end of Load in 26 of 30 screens |
| Search | `SearchCommand` | mode check → `QuerySP` (72%) → `DataSource` → `BestFitColumns()` (83%) → `ProtectControls(…, true)` (56%); clear detail with `ui.InitControl(group)` (52%) |
| New | `NewCommand` | mode check/change (60%) → `InitControl` (50%) → `ProtectControls(…, false)` (52%) → needed `SetToDay` (20%) |
| Edit | `EditCommand` | mode check (75%) → no row: `MsgWarn` and return (51%) → change mode → `ProtectControls(…, false)` (68%) |
| Save | `SaveCommand` | mode check (67%) → `MsgYesNo` (35%) → `CallSaveProcedure()` (62%) → `Msg("정상처리되었습니다.")` (55%) → `RunCommand(Cmd.Search)` (67%) |
| Cancel | `ClearCommand` | `m_EditState = EditMode.Default` (60%) → `RunCommand(Cmd.Search)` (65%) |
| Delete | `DeleteCommand` | mode check (70%) → nothing selected: `MsgWarn` (61%) → `MsgYesNo` (75%) → `gvw.DeleteSelectedRows()` (38%) → `CallSaveProcedure()` (54%) → `Msg` (63%) → search (66%) |
| Print | `PrintCommand` | `GetFocusedDataRow()` → `QuerySP(SelectType.PRINT, …)` → build report → `ShowRibbonPreview()` |
| Copy | `CopyCommand` | check selection → change mode → `ProtectControls(…, false)` → re-init keys and dates only |

- **Every command handler starts with the `m_EditState` check** (883 occurrences).
- After save/delete refresh with `RunCommand(Cmd.Search)`, never a second copy of the query code.

## Grid

| Behaviour | Event (subscriptions in 100 screens) | Inside the handler |
| --- | --- | --- |
| Show the focused row's detail | `gvw.FocusedRowChanged` (68) | block while editing (mode check 52%, `MsgWarn`); no row: `InitControl(group)` (41%) and return; `GetFocusedDataRow()` → `QuerySP(DETAIL)` or `RowToPanel` |
| Recalculate other cells | `gvw.CellValueChanged` (26) | check `e.Column.FieldName` → `GetRowCellValue` (73%) → `SetRowCellValue` (69%) |
| Block editing by condition | `gvw.ShowingEditor` (17) | `GetFocusedDataRow()` (76%), mode (58%) → `e.Cancel = true` |
| Open/select by double-click | `gvw.DoubleClick` (11) | `GetFocusedDataRow()` (63%) → popup `ShowDialog()`, or pass the row back and close |
| Block leaving a row while editing | `gvw.BeforeLeaveRow` | mode check → `Msg` → cancel |
| Cell find button (item, customer popup) | `rpsbtn.ButtonClick` (51) | mode check → `GetFocusedDataRow()` (68%) → popup gets `userInfo`, `db` → `ShowDialog() == DialogResult.OK` (86%) → copy the selected row (`drItem`) into `dr["FIELD"]` |
| Detail add/delete | `grp.CustomButtonClick` (17) or `btn.Click` (105) | add: `NewRow()` → assign → `Rows.Add()`; delete: `DeleteSelectedRows()` |

## Inputs

| Behaviour | Event | Inside the handler |
| --- | --- | --- |
| Quantity/amount → totals | `spin.EditValueChanged` (32) | `m_EditState == Default` → return (100%) → compute |
| Combo → refresh others | `cbo.EditValueChanged` (24) | mode check (70%) → assign or re-query |
| Date → recalc/re-query | `ymd.EditValueChanged` (15) | mode check (86%) → `ymd.YYYYMMDD()` |
| Input find button | `btn.ButtonClick` (`uxButtonEdit`, 39) | mode check → popup `ShowDialog()` (66%) → assign; attachments `ShowAttPop` |
| Button action (approve, finish, copy) | `btn.Click` | mode check → `MsgYesNo` → save → `Msg` → search |
| Tab change | `tab.SelectedPageChanged` (25) | `RunCommand(Cmd.Search)` (28%), `ProtectControls` (24%) |

- Value-change handlers **also fire when a query fills the control**, so their first line returns when `m_EditState == EditMode.Default`; otherwise every search reruns the calculation and overwrites values. Grid `CellValueChanged` and command handlers check the mode first too.

## Common methods

Most used first; check here before writing anything new. Real signatures: the target project's `ExampleLib` source.

| Method | Count | Does |
| --- | --- | --- |
| `ui.ProtectControls(control, bool)` | 418 | lock (true) / unlock a container or grid |
| `code.Bind(code, control)` / `BindByOrg(code, orgdiv, control)` | 352 / 31 | fill combo or repository lists |
| `ui.InitControl(container)` | 325 | clear inputs in a container |
| `RunCommand(Cmd.…)` | 276 | run a toolbar command from code |
| `gvw.BestFitColumns()` | 267 | fit columns after a query |
| `Msg` / `MsgWarn` / `MsgError` / `MsgYesNo` / `ShowExcetion(ee)` | 253 / 226 / 195 / 149 / 108 | messages (typos are the real names) |
| `ymd.YYYYMMDD()` / `ymd.SetToDay(n)` | 246 / 173 | date as 8-char SP argument / today ± n |
| `gvw.GetFocusedDataRow()` / `GetDataRow(handle)` / `GetSelectedRows()` | 206 / 112 / 76 | rows |
| `DataUtil.TableToXml(table, state)` | 155 | save XML |
| `gvw.GetRowCellValue` / `SetRowCellValue` | 152 / 123 | cell values |
| `ui.GetUserPCData()` | 64 | `@USERIP` |
| `gvw.DeleteSelectedRows()` | 59 | mark selected rows Deleted |
| `ui.GridRowIndex(…)` | 35 | return to the previous row after a re-query |
| `ui.RowToPanel(row, panel)` / `PanelToTable` (`dtPanelToTable`) | 32 / 21 (16) | row ↔ panel |
| `userInfo.Orgdiv`, `userInfo.UserId`, `db.GetDataSetFromSP` / `SaveTrn` | | login info, query / save |

Inside `QuerySP`: `GetDataSetFromSP` (79%), `userInfo.Orgdiv` (84%), `YYYYMMDD()` (67%). Inside `CallSaveProcedure`: `TableToXml` (95%), `SaveTrn` (78%; `SaveNoTrn` 21%, see [save-flow.md](save-flow.md#saving-rules)), `UserId` (100%).

## Locking

Whole-area locking is `ProtectControls`. A single button or input toggled by state may set `.Enabled` (23 screens) or `.ReadOnly` (16) directly.

## Use these APIs

Generic rows: csharp [coding-style.md](../../csharp/references/coding-style.md#use-existing-apis).

| Don't | Instead |
| --- | --- |
| Assign `DateTime.Today` to a date control | its `SetToDay(int)` |
| Compare original values to find changed rows | `DataRowState` and the `TableToXml` state argument |

## PROJECT_B screen patterns (2026-11-24, 30 screens by the user)

Recurring forms to reuse when a screen needs that behaviour:

- **Search bar:** `cboSelectType` (`MainCode = "<screen ID>"`) + `txtSelectText`; every select SP gets `@TYPE = cboSelectType.EditValue`, `@TEXT = txtSelectText.EditValue` as the last arguments (25 of 30). `Shown`: `cboSelectType.Properties.Columns["CODE"].Visible = false; cboSelectType.ItemIndex = 0;`. Date-basis combo `cboDTGB` filled in Load from a `DataTable` with CODE/NAME rows → `@DTGB`.
- **Key after save:** `DbParameter dbOutput = new DbParameter("@OUTPUT", ParameterDirection.Output, DbType.String, 20)` last → `strFindKey = dbOutput.Value?.ToString() ?? string.Empty;` → in Search `int irow = ui.GridRowIndex(grd, "KEYCODE", strFindKey); if (irow >= 0) gvw.FocusedRowHandle = irow; strFindKey = string.Empty;` (10 screens).
- **No row change while editing:** Edit/New store `nEditBeforeRow = gvw.FocusedRowHandle`; FocusedRowChanged returns to it with `MsgWarn("작업 중입니다. 다른행을 선택하실 수 없습니다.")` while `m_EditState` is Edit/Update (8 screens). FocusedRowChanged calls a separate `fnFocusedRowChanged()` that queries the detail and runs `RowToPanel` (13).
- **List/edit tabs:** New shows `tabProcess`, hides `tabList`; Save and Clear return to the list; `SelectedPageChanged` on the list tab runs Search; Load sets `isBtnEditModeSearch = true` (11 screens).
- **Selected-row actions:** `foreach (int i in gvw.GetSelectedRows())` → `if (dr.RowState == DataRowState.Unchanged) dr.SetModified();` → `TableToXml(dt, DataRowState.Modified)` with a literal WORKTYPE (`"APP"`, `"FIN"`…) (15 screens).
- **List → detail screen:** double-click builds `Hashtable ht["ROW"] = dr; OpenMenuProgram("<namespace>", "<screen>", "<title>", ht)`; the detail screen overrides `OnTabCallChanged(Hashtable ht)` and searches (6 screens).
- **Grid table getter:** `DataTable dtList { get { if (grd.DataSource == null) { … QuerySP … } return grd.DataSource as DataTable; } }` (16 screens).
- **Caption button panel:** a `pn<Role>Button` panel placed in a `uxGroupControl` caption with `SetCaptionPanel(grp, pn)` in Load (14 screens); otherwise `CustomHeaderButtons` with Tag `"ADD"`/`"DEL"` + `grp.CustomButtonClick`.
- **Errors in catch:** `MsgError(ee.Message)` (25 screens); never an empty `catch {}`.

