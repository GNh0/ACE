# Screen skeleton (list screen)

Common skeleton of the user's `FrmBase` screens; names are fictional, real ones come from target-project siblings. Header + detail saving: [save-flow.md](save-flow.md).

`EditMode` names differ per project: use the target `FrmBase.cs` enum (PROJECT_A `DEFAULT`/`EDIT`/`NEW`/`DELETE`, `<profile>/projects/<PROJECT>.md`); `m_EditState.ToString()` is the SP's `@WORKTYPE`. Below: `Default`/`Update`/`Delete`.

Follow the real `FrmBase` screen order: enum, state/data properties, constructor, commands, query/save methods. Member order: `enum SelectType` → constructor → Load → command handlers (Search, New, Edit, Clear, Save, Delete) → grid events → `QuerySP` → `CallSaveProcedure`.

## Constructor

```csharp
public XX000100()
{
    InitializeComponent();
    this.Load += XX000100_Load;
    this.SearchCommand += XX000100_SearchCommand;
    this.NewCommand += XX000100_NewCommand;
    this.EditCommand += XX000100_EditCommand;
    this.SaveCommand += XX000100_SaveCommand;
    this.ClearCommand += XX000100_ClearCommand;
    this.DeleteCommand += XX000100_DeleteCommand;

    gvwList.FocusedRowChanged += GvwList_FocusedRowChanged;
    btnADD.Click += BtnADD_Click;
    rpsbtnITEMCD.ButtonClick += RpsbtnITEMCD_ButtonClick;
}
```

Subscription rules: csharp [coding-style.md](../../csharp/references/coding-style.md#event-subscriptions).

## Body

```csharp
        enum SelectType
        {
            LIST
          , DETAIL
        }

        private void XX000100_SearchCommand(object sender, SearchCommandEventArgs e)
        {
            if (!(m_EditState == EditMode.Default))
            {
                return;
            }

            DataSet ds = QuerySP(SelectType.LIST);
            if (ds == null || ds.Tables.Count == 0)
            {
                return;
            }

            grdList.DataSource = ds.Tables[0];
            gvwList.BestFitColumns();
            ui.ProtectControls(grdList, true);
        }

        private void XX000100_SaveCommand(object sender, SaveCommandEventArgs e)
        {
            if (!(m_EditState == EditMode.Update))
            {
                return;
            }

            if (MsgYesNo("정말로 선택한 데이터를 저장하시겠습니까?") == DialogResult.Yes)
            {
                if (CallSaveProcedure() == true)
                {
                    Msg("정상처리되었습니다.");
                    RunCommand(Cmd.Search);
                }
            }
        }

        private DataSet QuerySP(SelectType _selectType)
        {
            try
            {
                string strDocnum = string.Empty;

                if (_selectType == SelectType.DETAIL)
                {
                    DataRow dr = gvwList.GetFocusedDataRow();
                    if (dr == null)
                    {
                        return null;
                    }

                    strDocnum = dr["DOCNUM"].ToString();
                }

                return db.GetDataSetFromSP("sp_XX000100_SELECT"
                        , new DbParameter("@WORKTYPE", _selectType.ToString())
                        , new DbParameter("@ORGDIV", userInfo.Orgdiv)
                        , new DbParameter("@FRDT", ymdFRDT.YYYYMMDD())
                        , new DbParameter("@TODT", ymdTODT.YYYYMMDD())
                        , new DbParameter("@DOCNUM", strDocnum)
                        );
            }
            catch (Exception ee)
            {
                MsgError(ee.Message);
            }
            return null;
        }
```

- Load: `code.Bind`/`BindByOrg` for combos and repositories, `ymdFRDT.SetToDay(-90)`, `ymdTODT.SetToDay(0)`, `ui.ProtectControls(grdList, true)` inside `try`/`catch (Exception ee)`.
- Edit: mode check → `FocusedRowHandle < 0` → `MsgWarn("수정 할 행이 선택되지 않았습니다.")` and return → `m_EditState = EditMode.Update;` → `ui.ProtectControls(grdList, false);`.
- Clear: if `m_EditState` is already `Default` return; else set `Default` and `RunCommand(Cmd.Search)`.
- Delete: mode check → `GetSelectedRows().Length == 0` → `MsgWarn("삭제 할 행이 선택되지 않았습니다.")` → `MsgYesNo(…) != DialogResult.Yes` return → `m_EditState = EditMode.Delete;` → `gvwList.DeleteSelectedRows();` → `bool isSave = CallSaveProcedure();` → `m_EditState = EditMode.Default;` → on success `Msg("정상처리되었습니다.")` and search.
- `GvwList_FocusedRowChanged`: row `< 0` → `ui.InitControl(grpDetail)` and return; else `QuerySP(SelectType.DETAIL)` → `grdDetail.DataSource = ds.Tables[0]` → `gvwDetail.BestFitColumns()`. An edit-mode move guard goes **before** the `< 0` return ([coding-style.md](../../csharp/references/coding-style.md#use-existing-apis)).
- `CallSaveProcedure` for this list: `DataTable dt = grdList.DataSource as DataTable;` → `dt.TableName = "DOC_DETAIL";` → `DataUtil.TableToXml(dt, DataRowState.Deleted)` in delete mode, else `Modified` → empty XML returns false → `SaveTrn` as in [save-flow.md](save-flow.md) → `m_EditState = Default; return true;`.

## Rules in this skeleton

- Command handlers start with the `m_EditState` check ([behaviors.md](behaviors.md#toolbar-commands)).
- Queries go through `QuerySP(SelectType)`; `SelectType` members are the `@WORKTYPE` values. Optional keys are `string` (`string strKeycode = null`), not `DataRow`s.
- Saves go through `CallSaveProcedure()` returning `bool`; success message and re-query sit in the caller's success path.
- `DbParameter` one per line in real argument order with leading commas. Keep `SaveNoTrn`/`SaveTrn`, edit mode, XML TableName and row states, result-table order.
- Dates: `SetToDay(n)` to initialise, `YYYYMMDD()` for SP arguments. `DbParameter`: one per line, leading commas, SP order, `);` on its own line.
- Exceptions: `catch (Exception ee)` → `MsgError(ee.Message)` (or the screen's `ShowExcetion(ee)`).
- No invented flags or names (`isBindingList`): use the sibling's (`isFlagRowChanged`).
