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

## 헤더 패널 + 상세 그리드 화면

위 골격은 목록 그리드 하나를 저장하는 화면이다. 헤더(패널의 입력 컨트롤)와 상세(그리드)를 함께 저장하는 화면은 조회·저장·행 추가가 아래처럼 달라진다.

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
    drNew["ITEMCD"] = string.Empty;
    drNew["QTY"] = 1;
    dtDetail.Rows.Add(drNew);
}

private void BtnDEL_Click(object sender, EventArgs e)
{
    if (m_Editmode != DataEditMode.Update)
    {
        return;
    }

    gvwDetail.DeleteSelectedRows();
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
                , new DbParameter("@USERIP", userInfo.UserIP)
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

- 헤더는 조회한 한 행을 `devFnc.DataRowToPanel`로 패널에 뿌리고, 저장할 때 `devFnc.MasterToDataTable`로 패널 값을 다시 한 행짜리 DataTable로 만든다. 스키마는 조회한 헤더 표를 `Clone()`해서 쓴다. 컨트롤의 `BindingField`가 열 이름과 같아야 값이 들어간다.
- 상세는 그리드의 DataTable을 그대로 XML로 만든다. 추가·수정·삭제 행을 한 번에 보내고 SP가 `GBN`으로 나눠 처리한다.
- 새 상세 행은 `NewRow()` → 필드 대입 → `Rows.Add()`다. 순번(`SEQ`)은 0으로 두고 SP가 매긴다. 헤더 값은 상세가 실제로 필요한 키만 넣는다.
- 헤더 XML과 상세 XML의 `TableName`이 SP의 두 XML 경로와 각각 같아야 한다.

## 화면에서 쓰는 공통 함수

새로 만들기 전에 아래에 있는지 먼저 본다. 실제 인자와 동작은 대상 프로젝트의 `KoneLib` 소스에서 확인한다.

| 하는 일 | 쓰는 것 |
| --- | --- |
| 컨트롤·그리드 편집 잠금/해제 | `devFnc.Usr_ControlsProtect(컨트롤, true/false)` |
| 그룹 안 입력 컨트롤 비우기 | `devFnc.InitControl(그룹)` |
| 한 행 → 패널 표시 | `devFnc.DataRowToPanel(행, 패널)` |
| 패널 → 한 행짜리 DataTable | `devFnc.MasterToDataTable(상태, 스키마, 그룹)` |
| DataTable → 저장 XML | `DataUtil.DataTableToXml(표, 행 상태)` |
| 공통코드 콤보 바인딩 | `syCode.BindingCode(코드, 컨트롤)`, 사업장별은 `syCode.BindingorgdivCode(코드, 사업장, 컨트롤)` |
| 날짜 초기화, SP용 문자열 | `ymdXXX.SetToDay(n)`, `ymdXXX.YYYYMMDD()` |
| 조회 / 저장 | `dbClient.GetDataSetFromSP(…)` / `dbClient.ExecSPTrn(…)` |
| 툴바 명령 다시 실행(저장 후 재조회 등) | `CallCommand(BizCommand.Search)` |
| 메시지 | `ShowMessage`, `ShowMessageWaring`, `ShowMessageError`, `ShowMessageYesNO`, `ShowExcetion(ee)` |
| 로그인 정보 | `userInfo.Orgdiv`, `userInfo.UserId`, `userInfo.UserIP` |
| 품목 등 선택 팝업 | 팝업 폼에 `userInfo`·`dbClient`를 넘기고 `ShowDialog() == DialogResult.OK`이면 선택 행(`drItem`)에서 값을 가져온다 |

메서드 이름의 오타(`ShowMessageWaring`, `ShowExcetion`)는 실제 이름이므로 그대로 쓴다.
