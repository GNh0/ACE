# 계약 대조 (EDD)

사용자는 빌드·실행을 기본으로 하지 않는다. 그래서 화면 검증의 기본은 **화면 호출 ↔ SP 계약을 줄 번호 근거로 대조하는 표**다. "맞을 것이다"가 아니라 양쪽 줄을 찾아 문자열을 옮겨 적는다.

- 사용자가 빌드·실행을 요청했거나 허락했으면 실행 결과를 근거로 쓴다. 빌드 성공은 표시·바인딩·조회 시점을 증명하지 않는다.
- SP도 바뀌었고 개발 DB에서 실행해도 되면 sql 스킬의 `references/verify.md`(롤백 테스트)를 따른다.
- 화면만 바뀌어도 SP를 부르는 코드를 건드렸으면 표를 채운다.

## SP 쪽 줄 번호 얻기

- `.sql` 파일이 있으면 그 파일의 줄 번호를 쓴다.
- 없으면 DB의 정의(`OBJECT_DEFINITION(OBJECT_ID('sp_…'))`)를 읽어 작업용 임시 폴더에 저장하고 그 파일의 줄 번호를 쓴다. 정의를 읽는 것은 실행이 아니다. 근거에 `DB 정의`라고 적는다.
- DB도 파일도 없으면 SP 쪽 칸은 `미확인`이다.

## 대조표

| 계약 | 화면 쪽 (파일:줄) | SP 쪽 (파일:줄) | 일치 |
| --- | --- | --- | --- |
| 저장 호출 방식 | `dbClient.ExecSPTrn("sp_…_SAVE"` 또는 `ExecSP(` | (트랜잭션 코드 유무) | `ExecSPTrn` / `ExecSP` |
| SP 이름 | 호출 문자열 | `CREATE PROCEDURE` 줄 | |
| 인자 이름·순서 | `new DbParameter("@…"` 줄마다 | 인자 선언 줄마다 | 이름·순서·누락·OUTPUT 방향 |
| `@WORKTYPE` 값 | `enum SelectType` 멤버 / `m_Editmode.ToString().ToUpper()`가 낼 수 있는 값 | `IF @WORKTYPE = '…'` 분기 | 값마다 |
| XML TableName | `dt.TableName = "…"` | `OPENXML(@DOC_ID, '/ROOT/…', 1)` | 대소문자까지 |
| 행 상태 | `DataUtil.DataTableToXml(dt, DataRowState.…)`가 고르는 상태 | `GBN = 'NEW'/'MOD'/'DEL'/'UNC'` 분기 | 보내는 상태마다 처리 분기가 있는지 |
| XML 열 | DataTable 열 이름(조회 결과 열·`MasterToDataTable` 스키마) | `OPENXML … WITH` 열 | SP가 읽는 열이 XML에 있는지 |
| 결과표 순서 | `ds.Tables[n]`을 쓰는 줄마다 | 분기 안 `SELECT` 순서 | n마다 |
| 그리드 열 | `col….FieldName = "…"` | 결과 열 이름(`AS …`) | 열마다 |
| 패널 바인딩 | `….BindingField = "…"` | 결과 열 이름 | 컨트롤마다 |
| 저장 후 키 | `@OUTPUT` 값을 읽어 재조회하는 줄 | `SET @OUTPUT = …` | |

- 각 칸에 **파일 경로와 줄 번호**를 적고, 비교한 문자열을 그대로 옮긴다(`dt.TableName = "MA110T"` ↔ `'/ROOT/MA110T'`).
- `OPENXML`의 경로와 `WITH` 열 이름은 XML이라 **대소문자를 구분**한다. `WITH`에 있는데 XML에 없는 열은 오류 없이 NULL로 들어간다. 그래서 열이 빠져도 저장은 "성공"한다.
- `DataTableToXml`의 기본 상태는 Added·Modified·Deleted다. `UNC`(Unchanged)를 SP가 기대하면 화면이 상태 인자에 Unchanged를 넣는지 확인한다. 삭제 행은 Original 값으로 나간다. 자세한 직렬화는 [kone120.md](kone120.md).
- 저장이 `ExecSP`면 SP의 트랜잭션을 빼면 안 된다. sql 스킬의 트랜잭션 규칙을 따르고 답변에 호출 줄을 적는다.
- 찾지 못한 칸은 `미확인`과 이유를 적는다. 한 칸이라도 `불일치`면 고치거나 답변 맨 위에 적는다.

## 예 (가상)

| 계약 | 화면 쪽 | SP 쪽 | 일치 |
| --- | --- | --- | --- |
| 저장 호출 방식 | `XX000100.cs:412` `dbClient.ExecSPTrn("sp_XX000100_SAVE"` | `sp_XX000100_SAVE.sql` 트랜잭션 코드 없음 | `ExecSPTrn` |
| 인자 이름·순서 | `XX000100.cs:413-419` `@WORKTYPE, @ORGDIV, @USERID, @USERIP, @XML, @XMLDETAIL, @OUTPUT` | `sp_XX000100_SAVE.sql:7-13` 같은 순서 | 일치 |
| `@WORKTYPE` 값 | `XX000100.cs:413` `m_Editmode.ToString().ToUpper()` → NEW·EDIT·DELETE | `:172` `DELETE`, `:198` `IN ('NEW', 'EDIT')` | 일치 |
| XML TableName | `XX000100.cs:405` `"DOC_HEADER"`, `:408` `"DOC_DETAIL"` | `:125` `'/ROOT/DOC_HEADER'`, `:148` `'/ROOT/DOC_DETAIL'` | 일치 |
| 행 상태 | `XX000100.cs:409` 기본 상태(NEW·MOD·DEL) | `:255` DEL, `:269` MOD, `:293` NEW | 일치 |
| 결과표 순서 | `XX000100.cs:290` `ds.Tables[0]` 헤더, `:296` `ds.Tables[1]` 상세 | `sp_XX000100_SELECT.sql:48-57` DETAIL 분기 SELECT 1개 | **불일치**: 상세 표 없음 |
| 그리드 열 | `XX000100.Designer.cs:530` `"ITEMNM"` | `sp_XX000100_SELECT.sql:51` `A.ITEMCD`만 | **불일치**: ITEMNM 없음 |
