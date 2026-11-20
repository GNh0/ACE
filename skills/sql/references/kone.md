# KONE 프로젝트 공통 함수·SP

C_KONE 계열 DB(C_KONE060, C_KONE110 등)에서 근호·KH 작성 SP가 자주 부르는 공통 개체다. 다른 DB에서는 같은 이름이 있는지, 인자가 같은지 먼저 확인한다. 공통 개체 자체는 요청 없이 고치지 않는다.

| 개체 | 종류 | 쓰는 곳 |
| --- | --- | --- |
| `SP_XML_LOG_SAVE` | SP | 모든 SAVE의 첫 실행문 |
| `SP_SYSTEM_BA100T_KEYCODE` | SP | 문서번호 채번 |
| `RETURN_KEYCODE` | 테이블 함수 | 화면 표시 키를 복합키로 분해 |
| `F_CHECK_CLOSE` | 스칼라 함수 | 년·월 마감 검증 |
| `F_FIND_USERNM` | 스칼라 함수 | 사용자 이름(기존 코드) |
| `F_BA011T_FIND_SUBNM` | 스칼라 함수 | 공통코드 이름(기존 코드) |

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

## 이름 조회 함수 (F_FIND_USERNM, F_BA011T_FIND_SUBNM)

행마다 실행되는 스칼라 함수다. 새로 쓰는 조회에서는 함수 대신 JOIN으로 이름을 가져온다.

```sql
SELECT A.DOCNUM
     , A.REGEMPNO
     , D.USERNM AS REGEMPNM
     , B1.SUBNM AS PROCNM
FROM DOC_HEADER A
        LEFT OUTER JOIN BA095T D
                     ON A.ORGDIV = D.ORGDIV
                     AND A.REGEMPNO = D.USERID
        LEFT OUTER JOIN BA011T B1
                     ON B1.MAINCD = 'PR001'
                     AND A.PROCCD = B1.SUBCD
```

- 기존 SP에 있는 함수 호출은 요청 없이 JOIN으로 바꾸지 않는다. 바꿀 때는 함수 정의를 읽고 조건 차이(사업장 조건 유무, 사용 여부 조건, 중복 행)를 확인한다.
