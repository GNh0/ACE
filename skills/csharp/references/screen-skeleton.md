# 화면 골격

실제 근호 작성 화면(FrmDevBase 상속)에서 뽑은 공통 골격이다. 프로그램·컨트롤·테이블 이름은 가상이다. 실제 이름과 흐름은 비교 프로그램과 대상 화면에서 가져온다.

멤버 순서: `enum SelectType` → 생성자(이벤트 구독) → Load → 명령 핸들러(Search, New, Edit, Clear, Save, Delete) → 그리드 이벤트 → `CallSelectProcedure` → `CallSaveProcedure`.

```csharp
using KoneLib.DataBase;
using KoneLib.DevBase;
using KoneLib.PgmBase;
using System;
using System.Data;
using System.Windows.Forms;

namespace Konesystem.XX01
{
    public partial class XX000100 : FrmDevBase
    {
        enum SelectType
        {
            LIST
          , DETAIL
        }

        public XX000100()
        {
            InitializeComponent();
            this.Load += XX000100_Load;
            this.SearchCommand += XX000100_SearchCommand;
            this.EditCommand += XX000100_EditCommand;
            this.ClearCommand += XX000100_ClearCommand;
            this.SaveCommand += XX000100_SaveCommand;
            this.DeleteCommand += XX000100_DeleteCommand;
            gvwList.FocusedRowChanged += GvwList_FocusedRowChanged;
        }

        private void XX000100_Load(object sender, EventArgs e)
        {
            try
            {
                syCode.BindingorgdivCode("PRODUSER", userInfo.Orgdiv, rpscboPERSON);
                syCode.BindingCode("PR001", rpscboPROCCD);

                ymdFRDT.SetToDay(-90);
                ymdTODT.SetToDay(0);

                devFnc.Usr_ControlsProtect(grdList, true);
            }
            catch (Exception ee)
            {
                ShowMessageError(ee.Message);
            }
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

        private void XX000100_EditCommand(object sender, EditCommandEventArgs e)
        {
            if (!(m_Editmode == DataEditMode.Default))
            {
                return;
            }

            if (gvwList.FocusedRowHandle < 0)
            {
                ShowMessageWaring("수정 할 행이 선택되지 않았습니다.");
                return;
            }

            m_Editmode = DataEditMode.Update;
            devFnc.Usr_ControlsProtect(grdList, false);
        }

        private void XX000100_ClearCommand(object sender, ClearCommandEventArgs e)
        {
            if (m_Editmode == DataEditMode.Default)
            {
                return;
            }

            m_Editmode = DataEditMode.Default;
            CallCommand(BizCommand.Search);
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

        private void XX000100_DeleteCommand(object sender, DeleteCommandEventArgs e)
        {
            if (!(m_Editmode == DataEditMode.Default))
            {
                return;
            }

            if (gvwList.GetSelectedRows().Length == 0)
            {
                ShowMessageWaring("삭제 할 행이 선택되지 않았습니다.");
                return;
            }

            if (ShowMessageYesNO("정말로 선택하신 항목을 삭제하시겠습니까?") != DialogResult.Yes)
            {
                return;
            }

            m_Editmode = DataEditMode.Delete;
            gvwList.DeleteSelectedRows();

            bool isSave = CallSaveProcedure();
            m_Editmode = DataEditMode.Default;

            if (isSave == true)
            {
                ShowMessage("정상처리되었습니다.");
                CallCommand(BizCommand.Search);
            }
        }

        private void GvwList_FocusedRowChanged(object sender, DevExpress.XtraGrid.Views.Base.FocusedRowChangedEventArgs e)
        {
            if (gvwList.FocusedRowHandle < 0)
            {
                devFnc.InitControl(grpDetail);
                return;
            }

            DataSet ds = CallSelectProcedure(SelectType.DETAIL);
            if (ds == null || ds.Tables.Count == 0)
            {
                return;
            }

            grdDetail.DataSource = ds.Tables[0];
            gvwDetail.BestFitColumns();
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

        private bool CallSaveProcedure()
        {
            try
            {
                DataTable dt = grdList.DataSource as DataTable;
                if (dt == null)
                {
                    return false;
                }

                dt.TableName = "DOC_DETAIL";
                string strXml = string.Empty;

                if (m_Editmode.Equals(DataEditMode.Delete))
                {
                    strXml = DataUtil.DataTableToXml(dt, DataRowState.Deleted);
                }
                else
                {
                    strXml = DataUtil.DataTableToXml(dt, DataRowState.Modified);
                }

                if (string.IsNullOrEmpty(strXml))
                {
                    return false;
                }

                dbClient.ExecSPTrn("sp_XX000100_SAVE"
                        , new DbParameter("@WORKTYPE", m_Editmode.ToString().ToUpper())
                        , new DbParameter("@ORGDIV", userInfo.Orgdiv)
                        , new DbParameter("@USERID", userInfo.UserId)
                        , new DbParameter("@USERIP", devFnc.GetUserPCData())
                        , new DbParameter("@XML", strXml)
                        );

                m_Editmode = DataEditMode.Default;
                return true;
            }
            catch (Exception ee)
            {
                ShowMessageError(ee.Message);
                return false;
            }
        }
    }
}
```

## 이 골격에서 지킬 점

- 이벤트 구독은 생성자에서 `InitializeComponent()` 다음에 이름 있는 핸들러로 한 번씩 한다.
- 명령 핸들러 첫 줄은 `m_Editmode` 확인이다. 조건이 한 줄이어도 **항상 중괄호**를 쓴다.
- 조회는 `CallSelectProcedure(SelectType)` 하나로 모은다. `enum SelectType` 멤버 이름이 SP의 `@WORKTYPE` 값이다.
- 저장은 `CallSaveProcedure()` 하나로 모으고 `bool`을 돌려준다. 성공 메시지와 재조회는 호출한 명령 핸들러의 성공 경로에 둔다.
- `dt.TableName`이 SAVE SP의 XML 경로(`/ROOT/<TableName>`)가 된다. 저장할 행은 `DataUtil.DataTableToXml(dt, DataRowState…)`의 행 상태로 고른다. 원본 값을 열마다 직접 비교하지 않는다.
- 저장은 `dbClient.ExecSPTrn`으로 부른다. 트랜잭션 시작·커밋·롤백은 이 메서드가 한다. 화면에서 따로 트랜잭션을 만들지 않는다.
- 삭제는 `gvwList.DeleteSelectedRows()`로 행을 Deleted 상태로 만든 뒤 저장을 부른다. 선택 행을 직접 루프로 지우지 않는다.
- 날짜 초기화는 `ymdXXX.SetToDay(n)`을 쓴다.
- DbParameter는 한 줄에 하나, 선행 쉼표, SP 인자 순서대로 쓴다. 닫는 괄호 `);`는 따로 한 줄이다.
- 예외는 `catch (Exception ee)`에서 `ShowMessageError(ee.Message)`로 보여준다.
