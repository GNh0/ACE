# 동작별 이벤트와 공통 메서드

"이 동작을 하려면 어떤 이벤트에, 어떤 공통 메서드를 쓰는가"를 정리한 표다. 근호·KH 작성 SP를 부르는 화면 100개(C_KONE110_1)의 핸들러 본문을 집계했다(2026-11-20). 괄호의 %는 그 핸들러 중 해당 메서드를 부르는 비율이다.

새 동작을 넣을 때는 먼저 이 표에서 같은 동작을 찾고, 없을 때만 비교 화면을 더 찾아본다. 새 헬퍼 메서드를 만드는 것은 마지막 수단이다.

## 툴바 명령 (폼 이벤트)

| 동작 | 이벤트 | 핸들러 안에서 하는 일 |
| --- | --- | --- |
| 화면 초기화 | `Load` | 콤보 바인딩 `syCode.BindingCode`(66%), 날짜 초기값 `ymd.SetToDay(n)`(67%), 처음엔 잠금 `devFnc.Usr_ControlsProtect(…, true)`(67%). 열자마자 조회하려면 끝에 `CallCommand(BizCommand.Search)`(25%) |
| 조회 | `SearchCommand` | `m_Editmode` 확인 → `CallSelectProcedure(…)`(72%) → `DataSource` 대입 → `BestFitColumns()`(83%) → `Usr_ControlsProtect(…, true)`(56%). 상세 영역은 `devFnc.InitControl(그룹)`으로 비운다(52%) |
| 신규 | `NewCommand` | `m_Editmode` 확인·변경(60%) → `devFnc.InitControl`(50%) → `Usr_ControlsProtect(…, false)`(52%) → 필요한 날짜 초기값 `SetToDay`(20%) |
| 수정 | `EditCommand` | `m_Editmode` 확인(75%) → 선택 행이 없으면 `ShowMessageWaring` 후 return(51%) → `m_Editmode` 변경 → `Usr_ControlsProtect(…, false)`(68%) |
| 저장 | `SaveCommand` | `m_Editmode` 확인(67%) → `ShowMessageYesNO`로 확인(35%) → `CallSaveProcedure()`(62%) → 성공하면 `ShowMessage("정상처리되었습니다.")`(55%) → `CallCommand(BizCommand.Search)`(67%) |
| 취소 | `ClearCommand` | `m_Editmode = DataEditMode.Default`(60%) → `CallCommand(BizCommand.Search)`(65%) |
| 삭제 | `DeleteCommand` | `m_Editmode` 확인(70%) → 선택이 없으면 `ShowMessageWaring`(61%) → `ShowMessageYesNO`(75%) → `gvw.DeleteSelectedRows()`(38%) → `CallSaveProcedure()`(54%) → `ShowMessage`(63%) → `CallCommand(BizCommand.Search)`(66%) |
| 출력 | `PrintCommand` | `GetFocusedDataRow()`로 대상 확인 → `CallSelectProcedure(SelectType.PRINT, …)` → 보고서 생성 → `ShowRibbonPreview()` |
| 복사 | `CopyCommand` | 선택 행 확인 → `m_Editmode` 변경 → `Usr_ControlsProtect(…, false)` → 키·일자만 새로 초기화 |

- 모든 명령 핸들러는 **`m_Editmode` 확인으로 시작**한다. 집계한 화면 코드에서 `m_Editmode`가 883번 나온다.
- 저장·삭제 후 화면 갱신은 조회 코드를 다시 쓰지 않고 `CallCommand(BizCommand.Search)`로 한다.

## 그리드

| 동작 | 이벤트 | 핸들러 안에서 하는 일 |
| --- | --- | --- |
| 선택 행의 상세 표시 | `gvw.FocusedRowChanged` | 편집 중이면 막는다(`m_Editmode` 확인 52%, 필요하면 `ShowMessageWaring`). 행이 없으면 `devFnc.InitControl(그룹)`(41%) 후 return. `GetFocusedDataRow()` → `CallSelectProcedure(SelectType.DETAIL)` 또는 `devFnc.DataRowToPanel` |
| 셀 값이 바뀌면 다른 셀 계산 | `gvw.CellValueChanged` | `e.Column.FieldName`으로 대상 열 확인 → `GetRowCellValue`(73%) → `SetRowCellValue`(69%) |
| 조건에 따라 셀 편집 막기 | `gvw.ShowingEditor` | `GetFocusedDataRow()`(76%)와 `m_Editmode`(58%)로 판단 → `e.Cancel = true`(100%) |
| 행 더블클릭으로 선택·열기 | `gvw.DoubleClick` | `GetFocusedDataRow()`(63%) → 팝업이면 `ShowDialog()`, 선택 팝업 안이면 선택 행을 넘기고 닫기 |
| 편집 중 다른 행으로 이동 막기 | `gvw.BeforeLeaveRow` | `m_Editmode` 확인(100%) → `ShowMessage`(100%) → 이동 취소 |
| 셀의 찾기 버튼(품목·거래처 팝업) | `rpsbtn.ButtonClick` | `m_Editmode` 확인 → `GetFocusedDataRow()`(68%) → 팝업에 `userInfo`·`dbClient` 전달 → `ShowDialog() == DialogResult.OK`(86%)이면 선택 행 값을 `dr["필드"]`에 대입 |
| 상세 행 추가·삭제(그룹 머리글 버튼) | `grp.CustomButtonClick` | 추가: `NewRow()` → 필드 대입 → `Rows.Add()`(47%). 삭제: `DeleteSelectedRows()`(47%) |
| 상세 행 추가·삭제(일반 버튼) | `btn.Click` | 위와 같다. 버튼 종류만 다르다 |

## 입력 컨트롤

| 동작 | 이벤트 | 핸들러 안에서 하는 일 |
| --- | --- | --- |
| 수량·금액이 바뀌면 합계 다시 계산 | `spin.EditValueChanged` | `m_Editmode == Default`이면 return(100%) → 다른 `spin.Value` 계산 |
| 콤보 선택에 따라 다른 컨트롤 갱신 | `cbo.EditValueChanged` | `m_Editmode` 확인(70%) → 값 대입 또는 재조회 |
| 일자가 바뀌면 재계산·재조회 | `ymd.EditValueChanged` | `m_Editmode` 확인(86%) → `ymd.YYYYMMDD()`(46%)로 값 읽기 |
| 입력란의 찾기 버튼 | `btn.ButtonClick` (`u_ButtonEdit`) | `m_Editmode` 확인(43%) → 팝업 `ShowDialog()`(66%) → 선택 값 대입. 첨부 파일이면 `ShowAttPop`(33%) |
| 버튼 동작(승인, 완료, 복사 등) | `btn.Click` (`u_ButtonControl`) | `m_Editmode` 확인 → `ShowMessageYesNO` → 저장 호출 → `ShowMessage` → `CallCommand(BizCommand.Search)` |
| 탭 전환 | `tab.SelectedPageChanged` | 탭에 맞게 `CallCommand(BizCommand.Search)`(28%), `Usr_ControlsProtect`(24%) |

- 입력 컨트롤의 값 변경 핸들러는 **조회로 값이 채워질 때도 불린다.** 그래서 첫 줄에서 `m_Editmode == DataEditMode.Default`이면 return한다. 이 확인을 빼면 조회할 때마다 계산이 돌아 값이 덮인다.

## 조회·저장 메서드

| 메서드 | 안에서 쓰는 것 |
| --- | --- |
| `CallSelectProcedure` | `dbClient.GetDataSetFromSP`(79%), `userInfo.Orgdiv`(84%), `ymd.YYYYMMDD()`(67%), 예외는 `ShowMessageError(ee.Message)`(62%) |
| `CallSaveProcedure` | `DataUtil.DataTableToXml`(95%), `dbClient.ExecSPTrn`(78%), `m_Editmode.ToString().ToUpper()`, `userInfo.Orgdiv`(97%), `userInfo.UserId`(100%), `devFnc.GetUserPCData()`(76%), 예외는 `ShowMessageError(ee.Message)`(76%) |

- `@USERIP`에는 `devFnc.GetUserPCData()`를 넘긴다(76%). `userInfo.UserIP`를 쓰는 화면(19%)도 있으므로 기존 화면을 고칠 때는 그 화면의 방식을 유지한다.
- 저장은 `ExecSPTrn`이 기본이다. `ExecSP`(21%)는 트랜잭션이 없으므로 새 저장에 쓰지 않는다.

## 공통 메서드 사용 빈도

많이 쓰는 순서다. 위쪽일수록 이 프로젝트의 기본 도구다.

| 메서드 | 횟수 | 하는 일 |
| --- | --- | --- |
| `devFnc.Usr_ControlsProtect(컨트롤, bool)` | 418 | 컨테이너·그리드 편집 잠금(true)/해제(false) |
| `syCode.BindingCode(코드구분, 컨트롤)` | 352 | 공통코드 콤보·Repository 목록 채우기 |
| `devFnc.InitControl(컨테이너)` | 325 | 컨테이너 안 입력값 비우기 |
| `CallCommand(BizCommand.…)` | 276 | 툴바 명령을 코드에서 실행 |
| `gvw.BestFitColumns()` | 267 | 조회 후 열 폭 맞춤 |
| `ShowMessage(…)` | 253 | 완료 안내 |
| `ymd.YYYYMMDD()` | 246 | 날짜를 SP 인자용 8자리 문자열로 |
| `ShowMessageWaring(…)` | 226 | 선택 없음 등 경고 |
| `gvw.GetFocusedDataRow()` | 206 | 현재 행을 `DataRow`로 |
| `ShowMessageError(…)` | 195 | 오류 표시 |
| `ymd.SetToDay(n)` | 173 | 오늘 기준 n일 날짜 넣기 |
| `DataUtil.DataTableToXml(표, 상태)` | 155 | 저장 XML 만들기 |
| `gvw.GetRowCellValue` / `SetRowCellValue` | 152 / 123 | 셀 값 읽기 / 쓰기 |
| `ShowMessageYesNO(…)` | 149 | 저장·삭제 확인 |
| `gvw.GetDataRow(handle)` | 112 | 지정 행을 `DataRow`로 |
| `ShowExcetion(ee)` | 108 | 예외 표시(일부 화면은 `ShowMessageError(ee.Message)` 대신 사용) |
| `gvw.GetSelectedRows()` | 76 | 체크·선택한 행 핸들 목록 |
| `devFnc.GetUserPCData()` | 64 | `@USERIP` 값 |
| `gvw.DeleteSelectedRows()` | 59 | 선택 행을 Deleted 상태로 |
| `devFnc.GetGridRowIndex(…)` | 35 | 재조회 후 이전 행 위치로 되돌리기 |
| `devFnc.DataRowToPanel(행, 패널)` | 32 | 한 행을 패널 컨트롤에 표시 |
| `syCode.BindingorgdivCode(코드구분, 사업장, 컨트롤)` | 31 | 사업장별 코드 목록 채우기 |
| `devFnc.MasterToDataTable` / `dtMasterToDataTable` | 21 / 16 | 패널 값을 한 행짜리 DataTable로 |

## 쓰지 않는 것

같은 100개 화면에서 센 횟수다.

| 쓰지 않는 것 | 횟수 | 대신 |
| --- | --- | --- |
| `MessageBox.Show` | 9 (3개 화면) | `ShowMessage`, `ShowMessageWaring`, `ShowMessageError`, `ShowMessageYesNO` (823회, 92개 화면) |
| 직접 만든 `SqlConnection`·`SqlCommand` | 0 | `dbClient` |
| `DateTime.….ToString("yyyyMMdd")` | 0 | `ymd.YYYYMMDD()` |
| `TextChanged`, `Leave`, `Validating` 구독 | 0 | `EditValueChanged` |
| 람다·`delegate`로 이벤트 구독 | 3 / 0 | 이름 있는 핸들러 메서드 |

영역 전체의 편집 잠금은 `Usr_ControlsProtect`로 한다. 특정 버튼이나 입력란 하나만 상태에 따라 켜고 끌 때는 `.Enabled = …`(23개 화면)나 `.ReadOnly = …`(16개 화면)를 직접 쓴다.
