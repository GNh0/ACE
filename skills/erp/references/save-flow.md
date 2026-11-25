# Save flow

How framework screens save and delete. List-screen skeleton: [screen-skeleton.md](screen-skeleton.md). Library behaviour: [framework.md](framework.md). Connecting functions to an existing screen: csharp [screen-change.md](../../csharp/references/screen-change.md).

## Saving rules

- **Save with `db.SaveTrn`.** It begins, commits and rolls back the transaction. No transaction in the screen and none in a new SP. `SaveNoTrn` has no transaction: never for new saves. If an existing screen saves with `SaveNoTrn`, the SP's transaction is its only protection: keep it, only propose switching to `SaveTrn`, and change neither side before the user agrees ([save-call.md](save-call.md#transactions)).
- `dt.TableName` becomes the SAVE SP's XML path `/ROOT/<TableName>`; take the name from the SP's `OPENXML` path.
- Choose rows with the row-state argument of `DataUtil.TableToXml(dt, DataRowState…)`. Never compare original values column by column.
- Delete = `gvw.DeleteSelectedRows()` (rows become Deleted) then save. Never loop over selected rows deleting them.
- `@WORKTYPE` = `m_EditState.ToString().ToUpper()`; `@USERID` = `userInfo.UserId`; `@USERIP` = `ui.GetUserPCData()` (76%; keep `userInfo.UserIP` where a screen already uses it).
- Sequence numbers (`SEQ`) are 0 in new rows; the SAVE SP numbers them. No MAX+1 in the screen.

## Header panel + detail grid

```csharp
DataTable dtMaster = null;
string strKeycode = string.Empty;

private void XX000100_SearchCommand(object sender, SearchCommandEventArgs e)
{
    m_EditState = EditMode.Default;
    ui.ProtectControls(pnMaster, true);
    ui.ProtectControls(grpDetail, true);
    ui.InitControl(grpMaster);
    dtMaster = null;

    DataSet ds = QuerySP(SelectType.HEADER, strKeycode);
    if (ds == null)
    {
        return;
    }

    dtMaster = ds.Tables[0];
    if (dtMaster.Rows.Count == 0)
    {
        return;
    }

    ui.RowToPanel(dtMaster.Rows[0], pnMaster);

    ds = QuerySP(SelectType.DETAIL, strKeycode);
    if (ds == null)
    {
        return;
    }

    grdDetail.DataSource = ds.Tables[0];
    gvwDetail.BestFitColumns();
}

private void BtnADD_Click(object sender, EventArgs e)
{
    if (m_EditState != EditMode.Update)
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
        if (m_EditState == EditMode.Default)
        {
            return false;
        }

        DataTable dtDetail = grdDetail.DataSource as DataTable;
        if (dtDetail == null)
        {
            return false;
        }

        dtDetail.TableName = "DOC_DETAIL";
        string strXmlDetail = DataUtil.TableToXml(dtDetail, DataRowState.Added | DataRowState.Modified | DataRowState.Deleted);

        DataTable dtHeader = ui.PanelToTable(DevFunction.MasterDataRowState.New, dtMaster.Clone(), grpMaster);
        dtHeader.TableName = "DOC_HEADER";
        string strXml = DataUtil.TableToXml(dtHeader, DataRowState.Added | DataRowState.Modified | DataRowState.Deleted);

        db.SaveTrn("sp_XX000100_SAVE"
                , new DbParameter("@WORKTYPE", m_EditState.ToString().ToUpper())
                , new DbParameter("@ORGDIV", userInfo.Orgdiv)
                , new DbParameter("@USERID", userInfo.UserId)
                , new DbParameter("@USERIP", ui.GetUserPCData())
                , new DbParameter("@XML", strXml)
                , new DbParameter("@XMLDETAIL", strXmlDetail)
                );

        m_EditState = EditMode.Default;
        return true;
    }
    catch (Exception ee)
    {
        ShowExcetion(ee);
        return false;
    }
}
```

- Header: the one queried row goes to the panel with `ui.RowToPanel`; on save `ui.PanelToTable` turns the panel back into a one-row table with the queried header's schema (PROJECT_A clones inside, so the original table may be passed). Values arrive only where a control's `BindingField` equals the column; columns without a bound control stay empty, so assign them in code if the SP reads them.
- Detail: the grid's DataTable goes to XML as is; added, modified and deleted rows travel together and the SP splits them by `GBN`.
- New detail row: `NewRow()` → assign fields → `Rows.Add()`. Copy only the header keys the detail really needs (row delete button: `gvwDetail.DeleteSelectedRows()` after the same mode check).
- Header and detail `TableName` must equal the SP's two XML paths.
