# C# 작성 방식

## Priority of requirements

최신 요청과 합의한 규칙을 우선한다. 지정 비교 프로그램은 미지정 작성 방식의 근거다. 요청한 멤버만 바꾼다. 대상의 기존 속성·이벤트·분기·트랜잭션·바인딩과 사용자 편집(폭, 순서, Font, Visible)은 보존하고 요청 범위에서만 바꾼다. 다른 UI 구조는 해당 프로젝트를 따른다.

## Syntax and naming

- 공백 4칸, 괄호는 별도 줄. if/else·반복문은 한 줄이어도 항상 중괄호를 쓴다(`if (...) return;` 형태는 쓰지 않는다). 기존 화면에 중괄호 없는 한 줄 if가 있어도 새로 쓰는 코드는 중괄호를 쓴다. 기존 else-if와 조기 반환 구조는 유지한다.
- DataTable·DataRow·DataSet·기본형을 명시한다. get 블록, 명시적 대입, switch 분기를 유지한다. 지역명은 str/dt/dr/ds와 화면 관례를 따른다.
- TryParse 성공 여부와 변환 값은 별도 if로 확인한다. 화면 표시 문자열 조합은 보간을 쓴다. SQL·XML·키의 형식과 외부 식별자는 보존한다. 앱 액션 Tag와 대응 case는 대문자로 맞춘다.

```csharp
DataTable dtList
{
    get
    {
        return grdList.DataSource as DataTable;
    }
}
```

## Screen structure and events

- FrmDevBase에서 실제 화면의 enum, 상태/데이터 속성, 생성자, 명령, 조회·저장 메서드 순서를 따른다. 여러 줄 인자와 enum 멤버는 선행 쉼표로 맞춘다. 날짜 입력명은 ymd와 필드명이다.
- 정적 배치는 Designer에 둔다. 대상이 InitializeComponent 후 구독하면 그곳에 이름 있는 핸들러를 연결한다. 양쪽 파일에서 중복 구독, 동적 해제, Repository ButtonClick·Grid RowCellClick의 중복 팝업을 확인한다.
- 기존 조회·저장 호출에서 인자·반환, 실패·취소, 초기화·보호·재조회를 확인한다. 공유 핸들러·헬퍼는 실제 필요에 맞춰 쓴다.

## Database and row handling

- DbParameter는 한 줄에 하나씩, 실제 인자 순서와 선행 쉼표를 쓴다. ExecSP/ExecSPTrn, 편집 모드, XML TableName과 행 상태, 결과표 순서를 보존한다.
- DataTable·DataRow에 직접 추가한다. 스키마 복제나 중간 표가 필요하면 기존 헬퍼의 반환을 먼저 확인한다. 체크/포커스 행, 실제 예외와 ShowMessage 경로를 대조한다.

```csharp
DataRow drNew = dtList.NewRow();
drNew["ITEMCD"] = drItem["ITEMCD"];
dtList.Rows.Add(drNew);
```

## Numeric display formats

| 요청 | 형식 | 0 숨김을 요청한 경우 |
| --- | --- | --- |
| 천 단위 정수 | `#,##0` | `#,###` |
| 소수 최대 두 자리 | `#,##0.##` | `#,###.##` |
| 소수 두 자리 고정 | `#,##0.00` | 요청한 표기를 확인 |

- 요구 형식이 있으면 그대로 쓰고 그 외에는 N0/N2보다 사용자 지정 형식을 우선한다. 생성자·공통 Repository 초기화를 먼저 확인한다.
- 합계는 SummaryItem.DisplayFormat 또는 GridColumnSummaryItem에 둔다. 접미사·정렬·SummaryType·FieldName을 보존하고 관련 ToString·string.Format·보간 표기도 맞춘다.
- 타입·정밀도·반올림·문화권·음수/0 표기를 보존한다. 셀 표시·입력 마스크·Repository는 해당 속성 변경이 필요할 때 수정한다. [숫자 형식](https://learn.microsoft.com/en-us/dotnet/standard/base-types/custom-numeric-format-strings), [DevExpress 합계](https://docs.devexpress.com/WindowsForms/DevExpress.XtraGrid.GridSummaryItem.DisplayFormat).

## 기존 API를 쓴다

새 헬퍼나 직접 구현을 만들기 전에 대상 프로젝트에 이미 있는 방법을 쓴다. 전체 형태는 [화면 골격](screen-skeleton.md)을 본다.

| 하지 않는 것 | 대신 |
| --- | --- |
| 날짜 컨트롤에 `DateTime.Today` 등을 직접 대입 | 컨트롤의 `SetToDay(int)` |
| 선택 행을 루프로 하나씩 삭제 | 그리드의 `DeleteSelectedRows()` |
| 화면에서 MAX+1로 순번 계산 | SAVE SP가 채번한다. 화면은 순번을 만들지 않는다. |
| 원본 값을 열마다 비교해 바뀐 행 고르기 | `DataRowState`와 `DataTableToXml`의 행 상태 인자 |
| 입력 컨트롤의 `Tag`를 SP 값으로 전달 | 컨트롤의 `EditValue`나 별도 키 컨트롤 |
| 짧다는 이유로 새 UI·데이터 헬퍼 추가 | 기존 이벤트·저장 경계를 유지한다. |
| 요청에 없는 저장 차단 조건·확인창 추가 | 기존 UI/XML/SP 검증을 따른다. 업무 제한을 새로 만들지 않는다. |
| NEW/EDIT 진입 때 불필요한 재조회 | 이미 있는 헤더·상세·스키마를 재사용한다. |
| 새 상세 행에 헤더 값을 전부 복사 | XML/SP가 상세에 요구하는 필드만 대입한다. |

`FocusedRowChanged`에서 편집 중 행 이동을 막아야 하면, 그 보호 코드를 `FocusedRowHandle < 0` 조기 반환보다 **앞에** 둔다. 필터 행에 포커스가 가면 보호를 건너뛰기 때문이다.
