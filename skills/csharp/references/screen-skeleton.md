# Screen skeleton (list screen)

Common skeleton of the user's `FrmDevBase` screens; names are fictional, real ones come from target-project siblings. Header + detail saving: [save-flow.md](save-flow.md).

`DataEditMode` names differ per project: use the target `FrmDevBase.cs` enum (C_KONE120 `DEFAULT`/`EDIT`/`NEW`/`DELETE`, [kone120.md](kone120.md)); `m_Editmode.ToString()` is the SP's `@WORKTYPE`. Below: `Default`/`Update`/`Delete`.

Member order: `enum SelectType` → constructor → Load → command handlers (Search, New, Edit, Clear, Save, Delete) → grid events → `CallSelectProcedure` → `CallSaveProcedure`.

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

- Subscriptions here, after `InitializeComponent()` (90% of the user's); don't move existing Designer ones unasked.
- Form events in this order, only those needed (`Shown`, `PrintCommand` in order too). Handler name: control name with a capital first letter + `_` + event (`gvwList` → `GvwList_FocusedRowChanged`); form events `<screen ID>_<event>`.
- Named methods only, no lambdas; never twice (check Designer and constructor). Value changes: `EditValueChanged`, not `TextChanged`/`Leave`/`Validating`.

## Body

```csharp
        enum SelectType
        {
            LIST
          , DETAIL
        }

        private void XX000100_SearchCommand(object sender, SearchCommandEventArgs e)
        {
            if (!(m_Editmode == DataEditMode.Default))
            {
                return;
            }

            DataSet ds = CallSelectProcedure(SelectType.LIST);
            if (ds == null || ds.Tables.Count == 0)
            {
                return;
            }

            grdList.DataSource = ds.Tables[0];
            gvwList.BestFitColumns();
            devFnc.Usr_ControlsProtect(grdList, true);
        }

        private void XX000100_SaveCommand(object sender, SaveCommandEventArgs e)
        {
            if (!(m_Editmode == DataEditMode.Update))
            {
                return;
            }

            if (ShowMessageYesNO("정말로 선택한 데이터를 저장하시겠습니까?") == DialogResult.Yes)
            {
                if (CallSaveProcedure() == true)
                {
                    ShowMessage("정상처리되었습니다.");
                    CallCommand(BizCommand.Search);
                }
            }
        }

        private DataSet CallSelectProcedure(SelectType _selectType)
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

                return dbClient.GetDataSetFromSP("sp_XX000100_SELECT"
                        , new DbParameter("@WORKTYPE", _selectType.ToString())
                        , new DbParameter("@ORGDIV", userInfo.Orgdiv)
                        , new DbParameter("@FRDT", ymdFRDT.YYYYMMDD())
                        , new DbParameter("@TODT", ymdTODT.YYYYMMDD())
                        , new DbParameter("@DOCNUM", strDocnum)
                        );
            }
            catch (Exception ee)
            {
                ShowMessageError(ee.Message);
            }
            return null;
        }
```

- Load: `syCode.BindingCode`/`BindingorgdivCode` for combos and repositories, `ymdFRDT.SetToDay(-90)`, `ymdTODT.SetToDay(0)`, `devFnc.Usr_ControlsProtect(grdList, true)` inside `try`/`catch (Exception ee)`.
- Edit: mode check → `FocusedRowHandle < 0` → `ShowMessageWaring("수정 할 행이 선택되지 않았습니다.")` and return → `m_Editmode = DataEditMode.Update;` → `devFnc.Usr_ControlsProtect(grdList, false);`.
- Clear: if `m_Editmode` is already `Default` return; else set `Default` and `CallCommand(BizCommand.Search)`.
- Delete: mode check → `GetSelectedRows().Length == 0` → `ShowMessageWaring("삭제 할 행이 선택되지 않았습니다.")` → `ShowMessageYesNO(…) != DialogResult.Yes` return → `m_Editmode = DataEditMode.Delete;` → `gvwList.DeleteSelectedRows();` → `bool isSave = CallSaveProcedure();` → `m_Editmode = DataEditMode.Default;` → on success `ShowMessage("정상처리되었습니다.")` and search.
- `GvwList_FocusedRowChanged`: row `< 0` → `devFnc.InitControl(grpDetail)` and return; else `CallSelectProcedure(SelectType.DETAIL)` → `grdDetail.DataSource = ds.Tables[0]` → `gvwDetail.BestFitColumns()`. An edit-mode move guard goes **before** the `< 0` return ([coding-style.md](coding-style.md#use-existing-apis)).
- `CallSaveProcedure` for this list: `DataTable dt = grdList.DataSource as DataTable;` → `dt.TableName = "DOC_DETAIL";` → `DataUtil.DataTableToXml(dt, DataRowState.Deleted)` in delete mode, else `Modified` → empty XML returns false → `ExecSPTrn` as in [save-flow.md](save-flow.md) → `m_Editmode = Default; return true;`.

## Rules in this skeleton

- Command handlers start with the `m_Editmode` check ([behaviors.md](behaviors.md#toolbar-commands)).
- Queries go through `CallSelectProcedure(SelectType)`; `SelectType` members are the `@WORKTYPE` values. Optional keys are `string` (`string strKeycode = null`), not `DataRow`s.
- Saves go through `CallSaveProcedure()` returning `bool`; success message and re-query sit in the caller's success path.
- Dates: `SetToDay(n)` to initialise, `YYYYMMDD()` for SP arguments. `DbParameter`: one per line, leading commas, SP order, `);` on its own line.
- Exceptions: `catch (Exception ee)` → `ShowMessageError(ee.Message)` (or the screen's `ShowExcetion(ee)`).
- No invented flags or names (`isBindingList`): use the sibling's (`isFlagRowChanged`).
