# C_KONE120 · FrmDevBase의 데이터 바인딩

적용 대상은 C_KONE120의 `KonesystemPlatform/KoneLib.DevBase`다. 다른 체크아웃에서는 같은 메서드의 오버로드와 실제 호출을 먼저 확인한다. 아래는 구현을 찾아갈 기준과 데이터 계약이다.

| 작업 | 확인된 동작 | 소스 위치 |
| --- | --- | --- |
| 편집 모드 | `enum DataEditMode`는 `DEFAULT`, `EDIT`, `NEW`, `DELETE`다(대문자). 다른 프로젝트의 `Default`·`Edit`와 이름이 다르므로 `m_Editmode.ToString()`이 SP에 가는 값은 이 enum으로 정한다. `GetEditModeWorkType()`은 NEW→`EDIT`, EDIT→`UPDATE`로 바꿔 돌려주므로 쓰는 화면은 그 값으로 대조한다. `DEFAULT`로 돌아가면 툴바는 `SetButtonEnable`의 `isSave` 값을 따르므로 저장 버튼이 켜져 있을 수 있다. 저장 핸들러에 모드 확인이 없으면 `DEFAULT`가 SP까지 갈 수 있다. | `Base/FrmDevBase.cs` · `DataEditMode`, `GetEditModeWorkType`, `EditModeChanged`, `SetButtonEnable` |
| 한 행 → 패널 | `devFnc.DataRowToPanel`이 자식 컨트롤을 재귀 순회한다. 지원 편집기의 `BindingField`에 해당하는 열이 있을 때 값을 표시한다. 숨김 여부로 제외하지 않는다. | `DevFunction.cs` · `DataRowToPanel` |
| 패널 → 마스터 | `MasterToDataTable`은 입력 스키마를 안에서 `Clone()`하고 `MakeDataRow`가 패널 자식을 재귀 순회해 대응 열을 채운다. 값은 컨트롤의 `Text`·`EditValue`를 문자열로 넣고(날짜는 `ToShortDateString()` 기반 문자열), `BindingField`가 없거나 스키마에 없는 열은 건너뛴다. 그래서 바인딩된 컨트롤이 없는 열은 NULL로 남는다. 반환 표에는 한 행이 있다. `AcceptChanges` 후 New는 Added, Mod는 Modified로 표시한다. | `DevFunction.cs` · `MasterToDataTable`, `MakeDataRow` |
| 숨은 키 | `_isPKValue`는 편집 보호에서 사용한다. 패널↔행 매핑은 지원 컨트롤의 `BindingField`, 스키마, 컨테이너가 결정한다. | `DevFunction.cs`, `PR200100.Designer.cs` · 숨은 PRODSEQ·PRODNUM |
| 표 → XML | `DataTableToXml(dt)`는 편집을 끝내고 Added·Modified·Deleted 행을 고른다. 상태 인자는 비트 조합이다. Unchanged를 명시하면 조회한 원본 행도 포함한다. 삭제 행은 Original 값을 쓴다. | `DataUtil.cs` · `DataTableToXml` |
| XML 행·속성 | 루트는 `ROOT`, 행명은 `TableName`(빈 이름은 `Table`)이다. 각 행에 상태별 `GBN` 속성(NEW·MOD·DEL·UNC)을 먼저 쓴다. 원본 표에 GBN 열을 추가하지 않는다. 원본에 같은 이름의 열이 있으면 뒤의 열 직렬화가 해당 속성을 덮을 수 있다. 대상 행이 없으면 루트만 반환한다. | `DataUtil.cs` · 행 생성 및 열 순회 |
| NULL 값 | 표에 없는 열은 속성이 없어 SP에서 NULL이다. 표에 있는데 값이 NULL이면: 비삭제 행은 Decimal이면 `0`(세 번째 인자 `false`면 속성 생략), 그 밖의 형식은 **빈 문자열 속성**으로 나간다. 삭제 행은 NULL 속성을 생략한다. 기본 오버로드는 세 번째 인자에 `true`를 넘긴다. | `DataUtil.cs` · 세 인자 오버로드, NULL 분기 |
| 날짜·문자 형식 | DateTime 값은 시·분이 0이면 `yyyyMMdd`, 아니면 `yyyy-MM-dd HH:mm:ss`, `0001-01-01`이면 빈 문자열이다. 삭제 행은 항상 `yyyyMMdd`다. 이름이 `DT`로 끝나는 문자열 열은 `-`를 지운다. | `DataUtil.cs` · DateTime 분기, `DT` 접미 분기 |
| 인자 null | `new DbParameter("@X", null)`은 값이 `null`인 `SqlParameter`를 그대로 넘긴다(`DBNull`로 바꾸지 않는다). ADO.NET은 값이 `null`인 인자를 보내지 않으므로 SP 인자에 기본값이 없으면 "expects parameter … which was not supplied" 오류가 난다. | `KoneLib.DataBase/DbParameter.cs` · 생성자, `DBConnect.cs` · 인자 추가 루프 |
| 저장 호출 | `ExecSPTrn`은 연결에서 트랜잭션을 시작하고 커밋한다. Output 인자의 크기를 8000으로 바꾸고, 실행 뒤 Output 값을 `DbParameter.Value`에 다시 넣고 마지막 Output 값을 문자열로 돌려준다. `ExecSP`는 트랜잭션이 없고 Output 값을 `DbParameter.Value`에 다시 넣지 않는다(읽으려면 `.parm.Value`). | `KoneLib.DataBase/DBConnect.cs` · `ExecSPTrn`, `ExecSP` |
| 콤보 코드 | `syCode.BindingCode(id, …)`와 `BindingorgdivCode(id, orgdiv, …)`는 공통 코드 목록에 id가 있으면 같은 CODE/NAME 경로를 사용한다. 이 경로는 사업장 필터를 추가하지 않는다. 목록 밖의 id는 각각 `GetCode(id)`, `GetorgdivCode(id, orgdiv)`로 조회한 뒤 편집기에 바인딩한다. | `SystemCode.cs` · 두 Binding 메서드, `BindControls` |

예를 들어 스키마와 숨은 컨트롤의 `BindingField`가 모두 `ROW_KEY`면 해당 키가 마스터 행에 들어간다. 예시 행명이 `SAMPLE_ROWS`이면 SAVE의 경로는 `/ROOT/SAMPLE_ROWS`와 맞아야 한다. GBN을 소비하는 SAVE는 행 상태와 실제 XML 속성까지 대조한다. 계약 대조표에서 이 표를 쓰는 곳은 [verify.md](verify.md#대조표)다.

화면 사용처는 `Konesystem.PR/PR200100.cs`의 콤보 초기화, 상세 바인딩, XML 작성이다. `Base/FrmDevBase.cs`에서 이 화면에 제공하는 `devFnc`와 `syCode`를 확인할 수 있다.
