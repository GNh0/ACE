# 계약 대조 (EDD)

사용자는 빌드·실행을 기본으로 하지 않는다. 그래서 화면 검증의 기본은 **화면 호출 ↔ SP 계약을 줄 번호 근거로 대조하는 표**다. "맞을 것이다"가 아니라 양쪽 줄을 찾아 문자열을 옮겨 적는다.

- 사용자가 빌드·실행을 요청했거나 허락했으면 실행 결과를 근거로 쓴다. 빌드 성공은 표시·바인딩·조회 시점을 증명하지 않는다.
- SP도 바뀌었고 개발 DB에서 실행해도 되면 sql 스킬의 `references/verify.md`(롤백 테스트)를 따른다.
- 화면만 바뀌어도 SP를 부르는 코드를 건드렸으면 표를 채운다.

## 채울 범위

전체 표를 매번 채우지 않는다. 화면 하나를 처음부터 끝까지 채우면 화면·Designer 2개, 공통 라이브러리 몇 개, SP 정의 2개를 읽고 도구 호출이 20번 안팎 든다. **바꾼 부분에 해당하는 행만 채우고**, 채우지 않은 행은 표 아래에 `범위 밖`으로 한 줄 적는다. 새 화면이거나 사용자가 전체 검토를 요청했으면 전부 채운다.

| 바꾼 것 | 반드시 채울 행 |
| --- | --- |
| 저장 호출 줄(`ExecSPTrn`/`ExecSP`), SP 이름 | 1 저장 호출, 2 인자 |
| `DbParameter` 추가·삭제·순서·값 | 2 인자, 3 null 인자 |
| `@WORKTYPE` 값, `enum SelectType`, `m_Editmode` 대입·확인 | 4 `@WORKTYPE` |
| `dt.TableName`, 저장할 표 | 5 TableName, 6 행 상태, 7 XML 열 |
| `DataTableToXml`의 상태 인자, `SetModified`·`AcceptChanges`·`DeleteSelectedRows` | 6 행 상태 |
| 패널 컨트롤 추가·`BindingField`, `MasterToDataTable` 호출 | 7 XML 열, 10 패널 바인딩 |
| 그리드 열 추가·`FieldName` | 9 그리드 열 |
| `ds.Tables[n]`, `DataSource` 대입 | 8 결과표, 9 그리드 열 |
| `dr["…"]` 읽기·쓰기, `NewRow` 대입, `Select` 필터 | 11 코드의 열 이름 |
| `@OUTPUT`, 저장 후 재조회·포커스 | 12 저장 후 키 |
| SP의 인자·XML 경로·`WITH`·분기·`SELECT` 열 | SP에서 바뀐 것이 닿는 화면 쪽 행 전부 |

## 근거를 찾는 순서

화면 파일부터 읽고, 호출 줄을 기준으로 SP와 Designer로 넓힌다.

1. **호출 줄**: 화면 `.cs`에서 `GetDataSetFromSP(`, `ExecSPTrn(`, `ExecSP(`를 찾는다. SP 이름과 `DbParameter` 줄 범위를 적는다.
2. **값의 출처**: 인자마다 값이 어디서 오는지 본다. `null`이 될 수 있는 값(기본값 `null`인 메서드 인자, `int?`, 분기에서만 대입하는 지역 변수, `EditValue`)을 표시한다.
3. **모드**: `enum SelectType` 멤버와 `m_Editmode`를 대입하는 줄을 모두 찾는다. `enum DataEditMode`의 멤버 이름은 대상 프로젝트의 `FrmDevBase.cs`에서 확인한다([kone120.md](kone120.md)). `GetEditModeWorkType()`을 쓰면 그 변환 결과가 값이다.
4. **표와 열**: `TableName =`, `DataTableToXml(`, `MasterToDataTable(`, `.DataSource =`, `Tables[`을 찾는다. 저장할 표의 스키마가 어느 조회 모드의 결과인지 따라간다(빈 키로 스키마만 조회하는 속성 게터가 흔하다).
5. **Designer**: 아래 패턴으로 찾는다. 열 이름 접두어(`colXXX_`)는 그리드 소속을 보장하지 않으므로 소속은 `Columns.AddRange` 목록으로 정한다.
   - 열 소속과 순서: `^\s+this\.col\w+[,}]` (AddRange 안의 줄만 걸린다)
   - 필드: `\.FieldName = `, `\.BindingField = `, `\.Visible = true`, `\.Visible = false`
   - 패널 소속: `<패널>\.Controls\.Add\(`
   - 식: `Expression = ` (FormatRule·Unbound 열)
6. **SP 정의**: 아래 방법으로 줄 번호를 붙여 읽고, 인자 선언, `IF @WORKTYPE`, `OPENXML`, `WITH`, `GBN`, 분기별 `SELECT` 목록을 적는다.

## SP 쪽 줄 번호 얻기

- `.sql` 파일이 있으면 그 파일의 줄 번호를 쓴다.
- 없으면 DB 정의를 읽는다. 정의를 읽는 것은 실행이 아니다. 근거에 `DB 정의`라고 적는다. 줄 번호를 붙여 읽으려면 아래처럼 나눈다(`STRING_SPLIT`의 순번 인자는 호환성 수준이 낮은 DB에서 쓸 수 없다).

```sql
WITH D AS (SELECT REPLACE(OBJECT_DEFINITION(OBJECT_ID('sp_XX000100_SAVE')), CHAR(13), '') + CHAR(10) AS T),
L AS (SELECT CAST(1 AS INT) AS LN, CAST(1 AS BIGINT) AS S, CAST(CHARINDEX(CHAR(10), T) AS BIGINT) AS E, T FROM D
      UNION ALL
      SELECT LN + 1, E + 1, CAST(CHARINDEX(CHAR(10), T, E + 1) AS BIGINT), T FROM L WHERE CHARINDEX(CHAR(10), T, E + 1) > 0)
SELECT LN, SUBSTRING(T, S, E - S) AS TXT FROM L OPTION (MAXRECURSION 0)
```

- 이 줄 번호는 SSMS "수정" 스크립트의 줄 번호와 다르다(SSMS는 앞에 `SET` 줄을 붙인다). 정의 앞에 빈 줄이 있으면 1행이 빈 줄이다.
- `/* */` 안의 옛 분기·인자도 문자열 검색에 걸린다. 주석 안인지 확인하고 주석이면 근거로 쓰지 않는다.
- DB도 파일도 없으면 SP 쪽 칸은 `미확인`이다.

## 대조표

| # | 계약 | 화면 쪽 (파일:줄) | SP 쪽 (파일:줄) | 판단 |
| --- | --- | --- | --- | --- |
| 1 | 저장 호출 | `ExecSPTrn(` / `ExecSP(` | 트랜잭션 코드 유무 | `ExecSPTrn` + SP에 트랜잭션 없음, 또는 `ExecSP` + SP에 `BEGIN TRAN`·`COMMIT`·`CATCH` 롤백이 있으면 일치. 교차면 불일치 |
| 2 | 인자 | SP 이름, `new DbParameter("@…"` 줄마다, Output 방향·크기 | `CREATE PROCEDURE` 줄, 인자 선언 줄마다 | 이름·순서·개수·`OUTPUT`. 주석 처리된 인자는 양쪽 다 주석이어야 일치 |
| 3 | null 인자 | `null`이 될 수 있는 인자 | 그 인자의 기본값(`= NULL`) | 기본값이 없으면 **불일치**. null 값은 보내지지 않는다([kone120.md](kone120.md)) |
| 4 | `@WORKTYPE` | 화면이 **보낼 수 있는** 값 전부(`enum` 멤버, `ToString()`/`ToUpper()` 유무, 모드 확인이 없어 갈 수 있는 `DEFAULT`) | `IF @WORKTYPE = '…'` 분기, 허용 값 검사 | 값마다 분기가 있거나 SP가 오류로 거부하면 일치. 아무 처리 없이 지나가면 불일치 |
| 5 | XML TableName | `dt.TableName = "…"` | `OPENXML(…, '/ROOT/…', 1)` | 대소문자까지. 같은 표 객체에 이름을 붙였는지(게터가 매번 새 표를 주면 이름이 안 이어진다) |
| 6 | 행 상태 | `DataTableToXml`의 상태 인자, 상태를 바꾸는 줄 | `GBN` 분기 | 보내는 상태마다 처리 또는 의도된 제외가 있는지. SP가 그 XML의 `GBN`을 아예 안 읽으면 일치 |
| 7 | XML 열 | 저장 표의 열과 **값의 출처**: 그리드 DataTable 스키마, 패널 `BindingField`, 코드 대입 | `WITH` 열 | SP가 읽는 열이 표에 있고 값이 채워지는지. 표에 없는 열이 `UPDATE … SET`에 쓰이면 기존 값을 NULL로 덮는다 |
| 8 | 결과표 | `ds.Tables[n]` 줄마다, 모드와 짝지어 | 분기 안 `SELECT` 순서 | 모드·n마다 |
| 9 | 그리드 열 | `Columns.AddRange` 소속 열의 `FieldName`, 그 그리드에 넣는 모드 | 그 모드의 결과 열(`AS …`) | 보이는 열은 전부 맞아야 한다. 숨은 열은 아래 판단 기준 |
| 10 | 패널 바인딩 | 패널 안 컨트롤의 `BindingField` | 패널에 뿌리는 행의 결과 열 | 컨트롤마다. 한 패널에 여러 결과를 뿌리면 결과마다 |
| 11 | 코드의 열 이름 | `dr["…"]` 읽기·쓰기, `NewRow` 대입, `Select`·`GetGridRowIndex` 필터의 열 | 그 행·표를 만든 모드의 결과 열 | 열마다. 코드가 만드는 값의 형식이 SP 식과 같은지(구분자 등) |
| 12 | 저장 후 키 | `@OUTPUT`을 읽는 줄 → 재조회·포커스 줄 | `SET @OUTPUT = …`(어느 분기에서) | 값이 없는 분기(삭제 등)에서 화면이 견디는지. 쓰지 않으면 `해당 없음` |

- 각 칸에 **파일 경로와 줄 번호**를 적고, 비교한 문자열을 그대로 옮긴다(`dt.TableName = "DOC_DETAIL"` ↔ `'/ROOT/DOC_DETAIL'`).
- 열이 많은 행(7, 9, 11)은 `24/24 일치`처럼 개수로 적고, 어긋난 열만 이름과 줄을 적는다.
- `OPENXML`의 경로와 `WITH` 열 이름은 XML이라 **대소문자를 구분**한다. `WITH`에 있는데 XML에 없는 열은 오류 없이 NULL로 들어간다. 그래서 열이 빠져도 저장은 "성공"한다. 표에 있는데 값이 NULL인 열은 NULL이 아니라 빈 문자열이나 0으로 나간다([kone120.md](kone120.md)).
- `DataTableToXml`의 기본 상태는 Added·Modified·Deleted다. `UNC`(Unchanged)를 SP가 기대하면 화면이 상태 인자에 Unchanged를 넣는지 확인한다. 삭제 행은 Original 값으로 나간다.
- 저장이 `ExecSP`면 SP의 트랜잭션을 빼면 안 된다([screen-skeleton.md](screen-skeleton.md#이-골격에서-지킬-점)). 답변에 호출 줄을 적는다.
- 찾지 못한 칸은 `미확인`과 이유를 적는다. 한 칸이라도 `불일치`면 고치거나 답변 맨 위에 적는다. 실행으로 확인하지 못한 불일치는 `불일치(정적, 실행 미확인)`로 적는다.

## 판단 기준

실제 화면에서 애매했던 경우다.

- **조회 SP를 여러 모드로 부른다**: 모드마다 "어느 그리드·패널·표에 들어가는가"를 `DataSource =`·`DataRowToPanel(` 줄로 짝짓고, 행 8·9·10·11을 모드별로 채운다.
- **빈 키로 스키마만 받는다**: `grd.DataSource == null`이면 `CallSelectProcedure(DETAIL, string.Empty)`를 부르는 게터가 있으면, 그 모드의 결과 열이 저장 XML 열(행 7)의 원천이다.
- **숨은 열·숨은 컨트롤**: 결과에 없는 열이 `Visible = false`이고, 저장 `WITH`에 없고, 코드가 읽지 않으면 `영향 없음`으로 적고 넘어간다. 셋 중 하나라도 걸리면 불일치다. 다른 화면에서 복사해 온 숨은 열이 수십 개일 수 있으므로 하나씩 적지 않고 개수만 적는다.
- **바인딩 없이 코드로 값을 넣는다**: `MasterToDataTable`은 `BindingField`가 있는 컨트롤의 열만 채운다. `WITH`가 읽는 열 중 바인딩이 없는 열은 `dtMaster.Rows[0]["…"] = …` 같은 대입 줄을 근거로 적는다. 대입도 없으면 불일치다.
- **헤더 XML의 `GBN`**: 패널 헤더는 `MasterToDataTable(New)`라 수정 모드에서도 `NEW`로 나간다. SP가 헤더 `GBN`을 읽지 않으면 일치, 읽으면 불일치다.
- **삭제를 목록 행으로 보낸다**: `ImportRow`(상태 유지, 보통 Unchanged)나 `SetModified`로 상태를 바꾼 줄과 `DataTableToXml`의 상태 인자를 함께 적는다. 이때 다른 XML 인자를 `null`로 두는지 행 3에서 본다.
- **팝업·다른 그리드에서 받은 값**: 팝업의 결과 행(`pop.drCust["…"]`)이나 다른 그리드 행을 패널에 뿌리면, 그 행을 만든 SP·모드의 결과 열과 대조한다(행 10·11). 팝업 SP를 읽지 못했으면 `미확인`.
- **그리드 열을 코드에서 만든다**: Designer 대신 코드의 `Columns.Add`·`FieldName` 줄을 근거로 쓴다. 코드에서 만든 열이 `DataSource`의 자동 생성 열이면 결과 열 그대로이므로 행 9는 `해당 없음`이다.

## 예

실제 화면 두 개(헤더 패널 + 상세 그리드를 `ExecSPTrn`으로 저장하는 화면, XML 두 개를 `ExecSP`로 저장하는 화면)를 채운 결과에서 이름만 바꿨다. 일치한 행은 줄였다.

| # | 계약 | 화면 쪽 | SP 쪽 | 판단 |
| --- | --- | --- | --- | --- |
| 1 | 저장 호출 | `XX000100.cs:277` `ExecSPTrn("sp_XX000100_SAVE"` | `sp_XX000100_SAVE` DB 정의 1-531 트랜잭션 코드 없음 | 일치 |
| 1 | 저장 호출 | `XX000200.cs:336` `ExecSP("sp_XX000200_SAVE"` | DB 정의 `:214-215` `BEGIN TRY`·`BEGIN TRANSACTION`, `:546` COMMIT, `:551` ROLLBACK | 일치 |
| 3 | null 인자 | `XX000100.cs:253` `string strXmlDetail = null;` 삭제 분기(254-265)는 대입 안 함 → `:283` `@XML_DETAIL` | DB 정의 `:12` `@XML_DETAIL VARCHAR(MAX)` 기본값 없음 | **불일치(정적, 실행 미확인)**: 삭제 때 "not supplied" 오류 |
| 4 | `@WORKTYPE` | `XX000100.cs:278` `m_Editmode.ToString()`, `FrmDevBase.cs:108-114` DEFAULT·EDIT·NEW·DELETE. 저장 핸들러에 모드 확인 없음 → DEFAULT 가능 | DB 정의 `:70` `NOT IN ('NEW', 'EDIT', 'DELETE')` → RAISERROR | 일치(DEFAULT는 SP가 거부) |
| 6 | 행 상태 | `XX000100.cs:271` 상세 Added·Modified·Deleted·Unchanged | `:485` NEW, `:417` MOD, `:361` DEL, UNC는 `:212` `GBN <> 'DEL'` 검증에만 | 일치(UNC는 의도적 포함) |
| 7 | XML 열 | 헤더: `XX000100.Designer.cs` `BindingField` 10개 + `XX000100.cs:269` `dtMaster.Rows[0]["EXRATE"] = …` | DB 정의 `:90-100` `WITH` 11열 | 11/11 일치 |
| 7 | XML 열 | 상세 스키마 = `sp_XX000200_SELECT` DETAIL 결과 `:71-102` | `sp_XX000200_SAVE` `:131-153` `WITH` 23열 | **불일치 20/23**: `SPEC1`(`:137`), `SPEC2`(`:138`)가 표에 없어 NULL. `:370-371` MOD UPDATE가 두 열을 NULL로 덮음 |
| 9 | 그리드 열 | `XX000200.Designer.cs` 보이는 열 13개 | DETAIL 결과 `:71-102` | 13/13 일치. 숨은 열 5개는 결과에 없으나 영향 없음 |
| 11 | 코드의 열 이름 | `XX000200.cs:570` `drNew["ORDKEY"] = ORDNUM + "-" + ORDSEQ` | DETAIL `:94` `ORDNUM + CONVERT(…, ORDSEQ)`(구분자 없음) | 형식 불일치: 새 행과 조회 행의 표시가 다름(저장 `WITH`에 없음) |
| 12 | 저장 후 키 | `XX000100.cs:287` `strFindKey = parmOutput.Value` → `:121` `GetGridRowIndex(…, "DOCNUM", strFindKey)` | `:529` `SET @OUTPUT = @DOCNUM`(NEW·EDIT만) | 일치(삭제는 NULL → 빈 문자열) |

2, 5, 8, 10행은 모두 일치해 생략했다. 실제로 쓸 때는 생략하지 않고 `범위 밖`이나 개수로 적는다.
