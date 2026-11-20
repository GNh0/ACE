# C_KONE120 · FrmDevBase data binding

Applies to C_KONE120 `KonesystemPlatform/KoneLib.DevBase`. In other checkouts check the overloads and real calls first. Below are where to find the implementation and the data contract.

## Library behaviour

| Task | Verified behaviour | Source |
| --- | --- | --- |
| Edit mode | `enum DataEditMode` is `DEFAULT`, `EDIT`, `NEW`, `DELETE` (uppercase, unlike other projects' `Default`/`Edit`), so it decides what `m_Editmode.ToString()` sends. `GetEditModeWorkType()` maps NEW→`EDIT`, EDIT→`UPDATE`; screens using it are compared with that value. Back in `DEFAULT` the toolbar follows `SetButtonEnable`'s `isSave`, so Save may stay enabled; without a mode check in the save handler `DEFAULT` can reach the SP | `Base/FrmDevBase.cs` · `DataEditMode`, `GetEditModeWorkType`, `EditModeChanged`, `SetButtonEnable` |
| Row → panel | `devFnc.DataRowToPanel` walks child controls recursively and shows a value where a supported editor's `BindingField` has a column. Hidden controls are not skipped | `DevFunction.cs` · `DataRowToPanel` |
| Panel → master | `MasterToDataTable` clones the input schema; `MakeDataRow` walks the panel and fills matching columns with the control's `Text`/`EditValue` as string (dates via `ToShortDateString()`). Controls without `BindingField` or columns not in the schema are skipped, so unbound columns stay NULL. One row; after `AcceptChanges` New → Added, Mod → Modified | `DevFunction.cs` · `MasterToDataTable`, `MakeDataRow` |
| Hidden keys | `_isPKValue` is used by edit protection. Panel↔row mapping is decided by supported controls' `BindingField`, the schema and the container | `DevFunction.cs`, `PR200100.Designer.cs` · hidden PRODSEQ, PRODNUM |
| Table → XML | `DataTableToXml(dt)` ends editing and takes Added/Modified/Deleted rows. The state argument is a bit mask; adding Unchanged includes untouched queried rows. Deleted rows use Original values | `DataUtil.cs` · `DataTableToXml` |
| XML rows | Root `ROOT`, row name = `TableName` (empty → `Table`). Each row gets a state `GBN` attribute first (NEW/MOD/DEL/UNC); don't add a GBN column to the table. A same-named column would overwrite it. No rows → root only | `DataUtil.cs` · row creation, column loop |
| NULL values | A column missing from the table has no attribute → NULL in the SP. Present but NULL: non-deleted rows send `0` for Decimal (attribute omitted when the third argument is `false`) and an **empty string** otherwise; deleted rows omit NULL attributes. The default overload passes `true` | `DataUtil.cs` · three-argument overload, NULL branch |
| Dates, strings | DateTime with zero time → `yyyyMMdd`, else `yyyy-MM-dd HH:mm:ss`, `0001-01-01` → empty. Deleted rows always `yyyyMMdd`. String columns ending in `DT` lose `-` | `DataUtil.cs` · DateTime branch, `DT` suffix |
| Null argument | `new DbParameter("@X", null)` passes a `SqlParameter` whose value is `null` (not `DBNull`). ADO.NET does not send it, so an SP argument without a default fails with "expects parameter … which was not supplied" | `KoneLib.DataBase/DbParameter.cs` · constructor, `DBConnect.cs` · argument loop |
| Save call | `ExecSPTrn` begins and commits a transaction on the connection, sets Output sizes to 8000, writes Output values back to `DbParameter.Value` and returns the last Output value as string. `ExecSP` has no transaction and does not write Output back (read `.parm.Value`) | `KoneLib.DataBase/DBConnect.cs` · `ExecSPTrn`, `ExecSP` |
| Code combos | `syCode.BindingCode(id, …)` and `BindingorgdivCode(id, orgdiv, …)` take the same CODE/NAME path when the id is in the common code list; that path adds no site filter. Other ids are queried with `GetCode(id)` / `GetorgdivCode(id, orgdiv)` and bound | `SystemCode.cs` · both Binding methods, `BindControls` |

Example: when the schema and a hidden control's `BindingField` are both `ROW_KEY`, the key lands in the master row. With row name `SAMPLE_ROWS` the SAVE path must be `/ROOT/SAMPLE_ROWS`. SAVEs consuming GBN are compared down to row states and real XML attributes ([verify.md](verify.md#contract-table)).

Screen usage: `Konesystem.PR/PR200100.cs` (combo init, detail binding, XML). `Base/FrmDevBase.cs` shows the `devFnc` and `syCode` it provides.
