# Save flow

How screens save, delete and connect new functions. List-screen skeleton: [screen-skeleton.md](screen-skeleton.md). C_KONE120 library behaviour: [kone120.md](kone120.md).

## Saving rules

- **Save with `dbClient.ExecSPTrn`.** It begins, commits and rolls back the transaction. No transaction in the screen and none in a new SP. `ExecSP` has no transaction: never for new saves. If an existing screen saves with `ExecSP`, the SP's transaction is its only protection: keep it, only propose switching to `ExecSPTrn`, and change neither side before the user agrees (sql skill `references/save-tran.md#transactions`).
- `dt.TableName` becomes the SAVE SP's XML path `/ROOT/<TableName>`; take the name from the SP's `OPENXML` path.
- Choose rows with the row-state argument of `DataUtil.DataTableToXml(dt, DataRowState…)`. Never compare original values column by column.
- Delete = `gvw.DeleteSelectedRows()` (rows become Deleted) then save. Never loop over selected rows deleting them.
- `@WORKTYPE` = `m_Editmode.ToString().ToUpper()`; `@USERID` = `userInfo.UserId`; `@USERIP` = `devFnc.GetUserPCData()` (76%; keep `userInfo.UserIP` where a screen already uses it).
- Sequence numbers (`SEQ`) are 0 in new rows; the SAVE SP numbers them. No MAX+1 in the screen.

## Header panel + detail grid

```csharp
DataTable dtMaster = null;
string strKeycode = string.Empty;

private void XX000100_SearchCommand(object sender, SearchCommandEventArgs e)
{
    m_Editmode = DataEditMode.Default;
    devFnc.Usr_ControlsProtect(pnMaster, true);
    devFnc.Usr_ControlsProtect(grpDetail, true);
    devFnc.InitControl(grpMaster);
    dtMaster = null;

    DataSet ds = CallSelectProcedure(SelectType.HEADER, strKeycode);
    if (ds == null)
    {
        return;
    }

    dtMaster = ds.Tables[0];
    if (dtMaster.Rows.Count == 0)
    {
        return;
    }

    devFnc.DataRowToPanel(dtMaster.Rows[0], pnMaster);

    ds = CallSelectProcedure(SelectType.DETAIL, strKeycode);
    if (ds == null)
    {
        return;
    }

    grdDetail.DataSource = ds.Tables[0];
    gvwDetail.BestFitColumns();
}

private void BtnADD_Click(object sender, EventArgs e)
{
    if (m_Editmode != DataEditMode.Update)
    {
        return;
    }

    DataTable dtDetail = grdDetail.DataSource as DataTable;
    if (dtDetail == null)
    {
        return;
    }

    DataRow drNew = dtDetail.NewRow();
    drNew["DOCNUM"] = strKeycode;
    drNew["SEQ"] = 0;
    drNew["QTY"] = 1;
    dtDetail.Rows.Add(drNew);
}

private bool CallSaveProcedure()
{
    try
    {
        if (m_Editmode == DataEditMode.Default)
        {
            return false;
        }

        DataTable dtDetail = grdDetail.DataSource as DataTable;
        if (dtDetail == null)
        {
            return false;
        }

        dtDetail.TableName = "DOC_DETAIL";
        string strXmlDetail = DataUtil.DataTableToXml(dtDetail, DataRowState.Added | DataRowState.Modified | DataRowState.Deleted);

        DataTable dtHeader = devFnc.MasterToDataTable(DevFunction.MasterDataRowState.New, dtMaster.Clone(), grpMaster);
        dtHeader.TableName = "DOC_HEADER";
        string strXml = DataUtil.DataTableToXml(dtHeader, DataRowState.Added | DataRowState.Modified | DataRowState.Deleted);

        dbClient.ExecSPTrn("sp_XX000100_SAVE"
                , new DbParameter("@WORKTYPE", m_Editmode.ToString().ToUpper())
                , new DbParameter("@ORGDIV", userInfo.Orgdiv)
                , new DbParameter("@USERID", userInfo.UserId)
                , new DbParameter("@USERIP", devFnc.GetUserPCData())
                , new DbParameter("@XML", strXml)
                , new DbParameter("@XMLDETAIL", strXmlDetail)
                );

        m_Editmode = DataEditMode.Default;
        return true;
    }
    catch (Exception ee)
    {
        ShowExcetion(ee);
        return false;
    }
}
```

- Header: the one queried row goes to the panel with `devFnc.DataRowToPanel`; on save `devFnc.MasterToDataTable` turns the panel back into a one-row table with the queried header's schema (C_KONE120 clones inside, so the original table may be passed). Values arrive only where a control's `BindingField` equals the column; columns without a bound control stay empty, so assign them in code if the SP reads them.
- Detail: the grid's DataTable goes to XML as is; added, modified and deleted rows travel together and the SP splits them by `GBN`.
- New detail row: `NewRow()` → assign fields → `Rows.Add()`. Copy only the header keys the detail really needs (row delete button: `gvwDetail.DeleteSelectedRows()` after the same mode check).
- Header and detail `TableName` must equal the SP's two XML paths.

## Connecting a function to an existing screen

Whole screen: follow Load/init → search → detail → edit lock → commands → re-query and focus. Local change: follow only the related events, permissions, toolbar and user buttons.

| Task | What to keep |
| --- | --- |
| New / edit | Reuse init and the existing schema; query an empty DETAIL only when a schema is needed. Edit keeps bound values and selects the existing mode/tab |
| Detail add / delete | NewRow → assign → Rows.Add; numbering stays with its owner; delete with the existing GridView API |
| Delete saved documents | Send all checked master keys as one XML batch. Distinguish focused row, display order and real selection |
| Save error | Keep existing confirmations, checks, messages and unsaved changes; re-query only on success |
| Dates, amounts | Check the real control and same-screen usage; keep type, precision and NULL from DB expression → DataColumn → editor/output |

- Save type and row selection: read the real caller and the same-role reference. Normal saves use the existing edit-mode API; only dedicated actions use a fixed mode; match the SP strings.
- Link checked keys, changed rows, TableName/XML, transaction and re-query on success. Use `Clone`/`ImportRow` for selected master keys when needed; check deleted rows' Original keys. Don't split a save batch because printing is per row.
- Connect display names and save codes to their own controls; a hidden USERID is read from its `EditValue`. Compare FieldName, XML and SP arguments by real names on both sides.
- Movement guards go before bypassing early returns; keep selection and detail; leave colour/enable to the existing protect routine. No new limits from a status column alone.
- Helpers, state flags, re-queries, extra checks or delete-and-reinsert only when existing handling cannot meet the requirement. Return a server `GETDATE()` save time only when the caller needs it.
- When the SP changes too, follow the sql skill and compare arguments, XML and result columns on both sides.

## Keeping original integrations as comments

- "Stop the integration": keep the original body and existing commented JOINs/filters; only block execution. Check call, fields, bindings and schema separately.
- Uploads: check real headers, types, dates and keys; iterate the DataTable the target's way. "Save valid rows, collect errors" applies to that upload.
- TY: query `RTRUSER` and edit `USER` are different. Feedback fixes look at declaration, init, assignment and use together and keep the user's later edits.
