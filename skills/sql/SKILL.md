---
name: sql
description: SQL Server 쿼리·프로시저(SP)를 사용자 방식으로 작성·수정·정리·검토한다. SQL 정리, 쿼리 작성, 조회(SELECT) SP, 저장(SAVE) SP, T-SQL 리뷰 요청에 사용한다.
---

# SQL 작성·정리

이 스킬은 메인 에이전트가 직접 따른다. 별도 에이전트에 넘기지 않는다.

## 시작 전에

1. 교정 기록을 읽는다. 플러그인의 [lessons.md](references/lessons.md)와 로컬 기록 `~/.claude/ace/lessons/sql.md`(없으면 넘어간다) 둘 다다. 둘이 다르면 로컬이 최신이다. 이번 작업에 해당하는 항목은 아래 규칙보다 우선한다. [compound.md](references/compound.md)
2. 요청 종류를 정한다.

| 요청 | 할 일 | 볼 문서 |
| --- | --- | --- |
| 정렬·정리만 | 의미를 바꾸지 않고 서식만 고친다. 로직 규칙 위반은 고치지 말고 위치만 보고한다(잠금 힌트는 지운다). | [style.md](references/style.md) |
| SELECT 작성·수정 | 결과 한 행의 단위, 포함·제외 조건, 표시용 JOIN과 필수 JOIN을 먼저 정한다. | [select.md](references/select.md), [style.md](references/style.md) |
| SP를 새로 만들기 | 인자 선언, XML 파싱, 헤더+상세 저장 골격을 그대로 따른다. | [procedure.md](references/procedure.md) |
| BOM 전개, 월별 피벗 등 복잡한 조회 | 결과 한 행의 단위를 먼저 적고, 파생마다 그 단위를 지키는지 확인한다. | [complex-select.md](references/complex-select.md) |
| 마감 검증, 채번, 키 분해 등 공통 함수 | 기존 공통 개체를 쓴다. 새로 만들지 않는다. | [kone.md](references/kone.md) |
| SAVE 작성·수정 | 호출 모드(WORKTYPE), 선택 키, XML 행 상태(NEW/MOD/DEL)를 호출부와 맞춘다. | [save.md](references/save.md), [style.md](references/style.md) |

3. 기존 SP를 고치면 **원본 전체**와 **실제 호출부(C# 또는 PB)**를 먼저 읽는다. 새 SP는 사용자에게 헤더에 쓸 작성자 이름과, 작성 방식을 참고할 기존 SP(같은 역할의 SELECT 또는 SAVE)를 확인하고 그 SP를 처음부터 끝까지 읽는다.

## 항상 지키는 규칙

한 줄에 규칙 하나다. 전체 내용·예시·예외는 링크한 문서가 규칙의 자리다. 링크가 없는 줄은 이 목록이 자리다.

- 리터럴·주석 밖의 SQL은 모두 대문자, 선행 쉼표. [style.md](references/style.md#sql-layout)
- 원래 JOIN 종류·순서, 조건, 출력 열 순서, 리터럴, 한글, 주석을 보존한다. [style.md](references/style.md#sql-layout)
- **잠금 힌트(UPDLOCK·HOLDLOCK 등)를 쓰지 않는다.** 원본·참고 SP에 있어도 지운다. [save.md](references/save.md#잠금-힌트)
- NULL·빈 값을 새로 대체하지 않는다(`ISNULL(..., 0)` 추가 포함). [style.md](references/style.md#sql-layout)
- FROM·WHERE·ORDER BY는 SELECT와 같은 열에서 시작하고(왼쪽 맞춤), LEFT/RIGHT JOIN에는 `OUTER`, CTE는 꼭 필요할 때만. [style.md](references/style.md#sql-layout)
- INSERT의 긴 값은 줄의 마지막 항목으로 두고, 긴 값만 한 줄에 따로 두지 않는다. [style.md](references/style.md#insert-열-대응)
- 핵심 조건 바로 윗줄에 업무 뜻 주석을 달고, 파생 테이블의 집계 열은 `QTY`가 아니라 `OUTQTY`·`INQTY`처럼 이름을 준다. [style.md](references/style.md#조건-주석)
- SP의 로직을 고칠 때는 손대지 않은 부분의 서식도 고친다. [style.md](references/style.md#손대지-않은-부분의-서식)
- WHERE 안의 EXISTS·IN 서브쿼리는 JOIN으로 바꾼다. SAVE의 `IF EXISTS` 검증은 유지한다. [select.md](references/select.md#exists--join)
- 공통코드 이름은 `BA011T` JOIN, 사용자 이름은 가장 바깥 SELECT에서만 `F_FIND_USERNM`. [kone.md](references/kone.md#이름-조회-사용자-이름은-함수-공통코드-이름은-join)
- SAVE에서 건수 변수, MAX 순번 변수, 중간 결과 테이블 변수, WHILE·커서 행 단위 처리, NEW/EDIT 분기 복사를 쓰지 않는다. 원본에 있어도 고친다. [save.md](references/save.md#save-고정-규칙)
- `@변수`는 문법상 꼭 필요한 것만 둔다. [save.md](references/save.md#save-고정-규칙)
- 채번은 공통 채번 SP로만 한다. 루프를 없애려고 `BA100T`를 직접 쓰지 않는다. [kone.md](references/kone.md#sp_system_ba100t_keycode)
- **SAVE SP의 트랜잭션은 호출부를 먼저 확인하고 정한다.** `ExecSPTrn`이면 SP에 트랜잭션 코드를 쓰지 않고, `ExecSP`이거나 호출부를 모르면 빼지 않는다. [save.md](references/save.md#트랜잭션)
- 화면이 `null`로 넘길 수 있는 XML·선택 인자는 SP 선언에 `= NULL` 기본값을 둔다. [save.md](references/save.md#화면이-null로-넘길-수-있는-인자)
- EDIT의 상세는 `DEL` 삭제, `MOD`만 UPDATE(짝 테이블 포함), `NEW`만 INSERT한다. 전부 지우고 다시 넣지 않는다. [save.md](references/save.md#수정-저장의-행-상태)
- 저장이 쓰는 상세 한 행과 DETAIL 조회의 한 행은 같은 단위여야 한다. [save.md](references/save.md#조회와-저장의-행-단위)
- 요청에 없는 검증(`IF EXISTS … RAISERROR`)을 새로 넣지 않는다. 필요해 보이면 답변에서 제안한다. [save.md](references/save.md#요청에-없는-검증)
- 롤백 테스트는 화면이 부르는 그대로 SP를 부른다(화면이 빼는 인자는 빼고). [verify.md](references/verify.md#반드시-지킬-것)
- 규칙 하나를 지키려고 다른 규칙을 깨지 않는다. 두 규칙이 부딪히면(예: 루프를 없애려면 공통 채번 SP를 우회해야 함) 더 안전한 쪽을 택하고, 무엇이 부딪혔는지 답변 맨 위에 적어 사용자가 정하게 한다.
- "동작은 그대로"라는 요청에서 결과가 달라질 수 있는 경우를 하나라도 찾으면 그 변경을 하지 않는다. 꼭 해야 하면 답변 맨 위에 "원본과 달라지는 경우"로 적고 사용자가 정하게 한다.
- LINQ·중간 테이블·빌드는 기본적으로 쓰지 않는다. 없으면 구현이 어렵거나 성능 차이가 극단적일 때만 쓰고 이유를 말한다.

## 작업 파일과 정리

- **소스 프로젝트 폴더에 작업용 파일을 만들지 않는다.** 비교용 사본, 초안, 추출물, 테스트 스크립트, 실행 결과, 로그는 시스템 임시 폴더(`%TEMP%`) 아래 작업별 폴더에 둔다.
- 소스 폴더에는 사용자가 요청한 최종 결과물만 쓴다. 파일 위치를 지정받으면 그 경로에만 쓴다.
- **SP·쿼리 `.sql` 파일은 솔루션 폴더 안에 만들지 않는다.** `.sln`이 있는 폴더의 **상위 폴더**에 `SQL\<YYYYMMDD>\` 폴더를 두고 거기에 쓴다(예: 솔루션이 `…\고객사\C_KONE120\`이면 `…\고객사\SQL\20261120\sp_XX000100_SAVE.sql`). SP는 DB에 적용하고 이 파일은 날짜별 기록으로 남긴다. 솔루션 안에 `SQL` 폴더가 이미 있어도 거기에 쓰지 않고, 사용자에게 알리고 상위로 옮기자고 제안한다. 이 폴더는 형상관리 대상이 아니므로 `.sql` 파일의 커밋을 할 일로 적지 않는다. 위치가 헷갈리면 추측해서 옮기지 말고 사용자에게 묻는다.
- 작업 중 띄운 빌드, 앱 실행, DB 연결, 백그라운드 터미널·프로세스는 끝나면 종료한다. 사용자가 띄운 것이나 다른 작업이 같이 쓰는 서비스는 건드리지 않는다.
- 끝내기 전에 소스 폴더에 내가 만든 임시 파일이 남았는지 확인하고(git 저장소면 `git status`), 남았으면 지운다. 출처를 모르는 파일은 지우지 말고 보고한다.
- 다음 작업에 계속 필요한 임시 파일은 남기되, 경로를 답변에 적는다.

## 끝내기 전에 (자체 점검)

작성이 끝나면 별도 검토 에이전트 없이 직접 아래를 확인하고 결과를 답변에 넣는다.

1. **원본 대조**: 기존 SP면 원본과 최종본을 나란히 비교해 요청하지 않은 변경이 없는지 본다.
2. **규칙 대조**: 위 규칙과 교정 기록(플러그인·로컬) 항목을 하나씩 대조한다. 위반이면 고친다.
3. **시나리오 표**: 바꾼 조회·저장 경로마다 채운다. 한쪽만 맞으면 완료가 아니다. **실행할 수 있으면 실행이 기본이고, 정적 대조는 실행할 수 없을 때만 쓴다.** 실행해도 되는 DB인지, 조회 비교와 저장 롤백 테스트의 틀, 근거 적는 법은 [verify.md](references/verify.md)에 있다.

| 구분 | 확인할 사례 | 근거 |
| --- | --- | --- |
| 정상 | 포함·갱신되어야 할 행 | 실행 결과(숫자) / 정적 대조(실행 못 한 이유) / 미확인 |
| 왕복 | 조회한 그대로 수정 저장한 뒤 다시 조회해도 수량·금액·순번이 그대로인지(조회와 저장의 행 단위가 같은지) | 실행 결과(숫자) / 정적 대조(실행 못 한 이유) / 미확인 |
| 제외·경계 | 완료된 이전·현재 공정 행, EDIT에서 자기 문서의 기존 수량, 복합키 일부 불일치, 요청하지 않은 WORKTYPE 분기, NULL·빈 값·0, 여러 행·선택 없음 | 실행 결과(숫자) / 정적 대조(실행 못 한 이유) / 미확인 |

해당 없는 칸은 이유를 적는다. 실행 결과에는 `수량 18 → 18, 금액 180,000 유지`처럼 실제 숫자를 적는다. 운영 DB이거나 어느 DB인지 모르면 실행하지 않는다. **실행하지 못했으면 답변에 `실행 검증: 하지 않음 - <이유>` 한 줄을 그대로 적는다.** SP를 고치고 실행 흔적도 이 줄도 없으면 끝낼 때 훅이 한 번 막는다.

4. **기계 점검**: 이 스킬 폴더의 스크립트로 최종 파일을 검사한다. `--caller`는 호출부에서 확인한 값(`ExecSPTrn`, `ExecSP`, 못 찾았으면 `unknown`)이다. 기존 SP면 `--original`에 원본 사본을 준다.

   ```
   python <스킬 폴더>/scripts/check_sql.py <최종.sql> --caller ExecSPTrn --original <원본 사본.sql>
   ```

   `[실패]` 줄은 줄 번호를 보고 고친 뒤 다시 돌린다. 출력의 **마지막 줄**(`ACE-CHECK: PASS 22/22`, 숫자는 통과 항목/판정 항목)을 답변에 그대로 넣는다. `[확인]` 줄(호출부 미확인, CTE, 원본에 없던 `RAISERROR`)은 직접 판단해 답변에 적는다. 스크립트가 보지 못하는 아래만 직접 확인해 표로 넣는다.

| 점검 | 예/아니오 |
| --- | --- |
| 호출부가 `ExecSPTrn`인지 `ExecSP`인지 실제 화면 코드에서 확인했다(파일과 줄 번호를 적는다). `ExecSP`이면 원본의 트랜잭션을 그대로 뒀다([트랜잭션](references/save.md#트랜잭션)) | |
| 화면이 `null`로 넘길 수 있는 인자에 `= NULL` 기본값이 있다([save.md](references/save.md#화면이-null로-넘길-수-있는-인자)) | |
| EDIT에서 상세를 전부 지우고 다시 넣지 않는다. `DEL`은 삭제, `MOD`만 UPDATE, `NEW`만 INSERT다([행 상태](references/save.md#수정-저장의-행-상태)) | |
| `MOD` 행은 짝이 되는 테이블(불출 등)도 UPDATE한다. 지웠다가 다시 넣지 않는다 | |
| 채번 `EXEC`은 NEW 모드 또는 `NEW` 행이 있을 때만 한다 | |
| 헷갈리는 수량·상태 비교 위에 업무 뜻 주석이 있다 | |
| 요청에 없는 검증을 새로 넣지 않았다 | |
| DB에 적용했으면 정의와 파일의 해시가 같다 | |

마지막으로 [작업 파일과 정리](#작업-파일과-정리)대로 임시 파일과 띄운 프로세스를 정리했는지 확인한다.

## 교정을 받으면 (Compound)

사용자가 결과를 교정했거나 실행 검증의 실패 원인이 규칙에 없거나 틀렸으면, 고친 뒤 **묻지 않고** 로컬 기록 `~/.claude/ace/lessons/sql.md`에 적고 답변에 `교정 기록에 추가: <제목>` 한 줄로 알린다. 사용자가 이 대화에서 파일을 만들거나 고치지 말라고 했으면 쓰지 않고 답변에만 보인다. 언제 적는지, 항목 형식, 저장소로 옮기는 승격(사용자가 요청할 때만)은 [compound.md](references/compound.md)가 자리다.
