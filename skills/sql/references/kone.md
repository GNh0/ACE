# KONE 프로젝트 공통 함수·SP

C_KONE 계열 DB(C_KONE060, C_KONE110 등)에서 근호·KH 작성 SP가 자주 부르는 공통 개체다. 다른 DB에서는 같은 이름이 있는지, 인자가 같은지 먼저 확인한다. 공통 개체 자체는 요청 없이 고치지 않는다.

| 개체 | 종류 | 쓰는 곳 |
| --- | --- | --- |
| `SP_XML_LOG_SAVE` | SP | 모든 SAVE의 첫 실행문 |
| `SP_SYSTEM_BA100T_KEYCODE` | SP | 문서번호 채번 |
| `RETURN_KEYCODE` | 테이블 함수 | 화면 표시 키를 복합키로 분해 |
| `F_CHECK_CLOSE` | 스칼라 함수 | 년·월 마감 검증 |
| `F_FIND_USERNM` | 스칼라 함수 | 사용자 이름 |
| `F_BA011T_FIND_SUBNM` | 스칼라 함수 | 공통코드 이름. 기존 코드에만 있다. 새로 쓸 때는 `BA011T` JOIN |

## SP_XML_LOG_SAVE

SAVE가 받은 XML을 기록한다. `SET NOCOUNT ON` 바로 다음에 둔다. XML 인자가 여러 개면 모두 넘긴다.

```sql
EXEC SP_XML_LOG_SAVE @@PROCID, @WORKTYPE, @USERID, @XML, @XMLDETAIL;
```

## SP_SYSTEM_BA100T_KEYCODE

기준일별 다음 순번을 OUTPUT으로 돌려준다. 인자는 사업장, 테이블 구분, 기준일(YYYYMMDD), 순번(OUTPUT)이다. EXEC 인자에는 식을 쓸 수 없으므로 기준일과 순번은 변수로 둔다.

```sql
EXEC SP_SYSTEM_BA100T_KEYCODE @ORGDIV, 'BA100T', @DOCDT, @NEWSEQ OUTPUT;

SET @DOCNUM = @DOCDT + '-' + CONVERT(VARCHAR(10), @NEWSEQ);
```

- 테이블 구분 값은 같은 업무의 기존 SAVE가 쓰는 값을 따른다.
- 헤더 번호만 이 SP로 채번한다. 상세 순번은 INSERT 안에서 파생 MAX + `ROW_NUMBER()`로 매긴다.
- 화면에서 순번을 계산해 넘기지 않는다.
- **채번 테이블(`BA100T`)을 SP에서 직접 UPDATE·INSERT하지 않는다.** 번호는 항상 이 공통 SP로 받는다. 루프를 없애려고 채번 SP를 우회하지 않는다.
- 한 번의 저장에서 문서번호가 여러 개 필요하면(행마다 다른 번호), 채번 `EXEC`만 도는 작은 루프를 쓴다. 이것은 "행 단위 루프 금지"의 예외다. 루프 안에는 채번 호출과 받은 번호를 스테이징에 적는 문장만 두고, 실제 INSERT·UPDATE·DELETE는 루프 밖에서 집합으로 한다. 답변에 이 루프를 남긴 이유를 적는다.

## RETURN_KEYCODE

화면이 `20260129-1-11` 같은 표시용 키 하나를 넘길 때 `CODE`, `SEQ1`, `SEQ2`로 나눈다. 하이픈이 하나면 `SEQ2`는 NULL이다.

```sql
DELETE A
FROM STOCK_OUT A
        INNER JOIN (
                    SELECT T.GBN
                         , T1.CODE
                         , T1.SEQ1
                         , T1.SEQ2
                    FROM @TMP_LIST T
                            CROSS APPLY DBO.RETURN_KEYCODE(T.KEYCODE) T1
                   ) B
                   ON A.RECDT = B.CODE
                   AND A.SEQ1 = B.SEQ1
                   AND A.SEQ2 = B.SEQ2
WHERE A.ORGDIV = @ORGDIV
  AND B.GBN = 'DEL';
```

- 키를 문자열로 이어 붙여 비교하지 않는다(`A.RECDT + '-' + CONVERT(…) = B.KEYCODE` 금지). 분해해서 구성 열 전부로 JOIN한다.

## F_CHECK_CLOSE

`F_CHECK_CLOSE(@ORGDIV, 업무구분, 년월구분, 대상기간, '1')`은 마감 여부를 돌려준다.

- 업무구분: `'MA'`(자재) 등 업무 모듈 코드. 같은 업무의 기존 SAVE가 쓰는 값을 따른다.
- 년월구분: `'1'` 년마감(대상기간은 `LEFT(일자, 4)`), `'2'` 월마감(대상기간은 `LEFT(일자, 6)`).
- 반환: `''` 마감 정보 없음, `'Y'` 마감 완료, 그 밖은 처리 가능.

수불에 영향을 주는 SAVE는 쓰기 전에 네 가지를 차례로 검증한다. 메시지와 `16, 9`는 기존 SAVE와 같게 쓴다.

```sql
IF EXISTS (
           SELECT 1
           FROM @TMP_DETAIL A
           WHERE DBO.F_CHECK_CLOSE(@ORGDIV, 'MA', '1', LEFT(A.OUTDT, 4), '1') = ''
          )
BEGIN
    RAISERROR('년마감 정보가 없습니다. 년/월마감 프로그램에서 년마감 정보를 생성한 후 처리 가능합니다.', 16, 9);
    RETURN;
END

IF EXISTS (
           SELECT 1
           FROM @TMP_DETAIL A
           WHERE DBO.F_CHECK_CLOSE(@ORGDIV, 'MA', '1', LEFT(A.OUTDT, 4), '1') = 'Y'
          )
BEGIN
    RAISERROR('년 마감이 완료되었습니다. 년/월마감 프로그램에서 년마감 해제 후 처리 가능합니다.', 16, 9);
    RETURN;
END

IF EXISTS (
           SELECT 1
           FROM @TMP_DETAIL A
           WHERE DBO.F_CHECK_CLOSE(@ORGDIV, 'MA', '2', LEFT(A.OUTDT, 6), '1') = ''
          )
BEGIN
    RAISERROR('월마감 정보가 없습니다. 년/월마감 프로그램에서 월마감 정보를 생성한 후 처리 가능합니다.', 16, 9);
    RETURN;
END

IF EXISTS (
           SELECT 1
           FROM @TMP_DETAIL A
           WHERE DBO.F_CHECK_CLOSE(@ORGDIV, 'MA', '2', LEFT(A.OUTDT, 6), '1') = 'Y'
          )
BEGIN
    RAISERROR('월 마감이 완료되었습니다. 년/월마감 프로그램에서 월마감 해제 후 처리 가능합니다.', 16, 9);
    RETURN;
END
```

- 검증하는 일자는 실제로 수불이 잡히는 일자다(입고일, 출고일 등). 수정이면 바뀌기 전 일자와 바뀐 뒤 일자가 다를 수 있는지 확인한다.

## 이름 조회 (사용자 이름은 함수, 공통코드 이름은 JOIN)

둘을 다르게 쓴다.

| 가져오는 이름 | 방법 |
| --- | --- |
| 사용자 이름(등록자·수정자·담당자 등) | **함수** `DBO.F_FIND_USERNM(사용자ID)` |
| 공통코드 이름(공정명, 구분명 등) | **JOIN** `BA011T`. `F_BA011T_FIND_SUBNM`은 새로 쓰지 않는다. |

```sql
SELECT A.DOCNUM
     , A.PROCCD
     , B.SUBNM AS PROCNM
     , A.REGEMPNO
     , DBO.F_FIND_USERNM(A.REGEMPNO) AS REGEMPNM
     , A.MODEMPNO
     , DBO.F_FIND_USERNM(A.MODEMPNO) AS MODEMPNM
FROM DOC_HEADER A
        LEFT OUTER JOIN BA011T B
                     ON B.MAINCD = 'PR001'
                     AND A.PROCCD = B.SUBCD
WHERE A.ORGDIV = @ORGDIV
```

- 공통코드 이름은 `BA011T`를 `MAINCD = '코드구분'`과 코드 값으로 LEFT OUTER JOIN한다. PK가 `(MAINCD, SUBCD)`라서 JOIN해도 행이 늘지 않는다. 코드 구분이 여러 개면 구분마다 한 번씩 JOIN하고 별칭을 나눈다(`B`, `B1`).
- 사용자 이름은 등록자·수정자처럼 한 조회에 여러 번 나온다. 이름마다 JOIN을 붙이면 같은 테이블이 여러 번 들어가므로 **화면에 뿌리는 최종 결과**에서는 함수를 쓴다.
- **함수는 JOIN보다 느리다.** 그래서 함수는 **가장 바깥 SELECT 목록**에서만, 최종 결과 행(보통 수천~수만 건)에 대해 쓴다. 대량 테이블을 훑는 파생 테이블 안, 집계 전 단계, WHERE·GROUP BY·ORDER BY에는 쓰지 않는다. 수십만 건을 그대로 돌려주거나 집계하는 조회(수불장, 현황 집계 등)에서는 사용자 이름도 JOIN으로 가져온다.
- 사용자 이름을 JOIN할 때는 행 수를 확인한다. `BA095T`의 PK는 `(USERID, PRSNNUM)`이다. 지금은 `USERID`가 중복 없이 한 건씩이지만 PK가 보장하지는 않는다.
- JOIN이 필요한 다른 경우: 사용자 테이블의 다른 열이 함께 필요할 때, 사업장(`ORGDIV`)까지 맞춰야 할 때. `F_FIND_USERNM`은 사용자 ID만으로 찾고 사업장 조건이 없다.
- 기존 SP에 있는 함수 호출이나 JOIN은 요청 없이 서로 바꾸지 않는다.

실측(C_KONE110, SQL Server 2019, 2026-11-20, 입고 테이블 약 58만 건 전체에 이름 1개):

| 방법 | 걸린 시간 |
| --- | --- |
| JOIN | 약 0.08초 |
| 함수(인라인 적용, 기본 상태) | 약 1.1초 |
| 함수 2개(등록자 + 수정자) | 약 2.3초 (JOIN 2개는 약 0.09초) |
| 함수(인라인 끔) | 약 13.7초 |

1,000건만 가져올 때는 함수와 JOIN 모두 0.2~0.3초로 차이가 없었다. 인라인이 안 되는 서버(2017 이하, 또는 `SYS.SQL_MODULES.IS_INLINEABLE = 0`)에서는 함수가 훨씬 느리므로 JOIN을 기본으로 한다.
