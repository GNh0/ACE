# 실행 검증 (EDD)

시나리오 표를 채우는 것만으로는 검증이 아니다. 정적 대조로 만점을 받은 저장 SP도 실제로 돌리면 틀린 경우가 있었다. **실행할 수 있으면 실행이 기본이고, 정적 대조는 실행할 수 없을 때만 쓴다.**

## 1. 실행해도 되는지

| 대상 DB | 할 일 |
| --- | --- |
| 사용자가 개발 DB라고 했거나, 이번 작업에서 테스트 실행을 허락한 DB | 실행 검증한다 |
| 운영 DB, 또는 어느 쪽인지 모름 | 실행하지 않는다. 정적 대조만 하고 근거를 `미확인`으로 적는다. 실행하려면 사용자에게 묻는다 |

- 실행 검증은 **읽기 조회**이거나, **트랜잭션 안에서 실행하고 전부 롤백**한다. 데이터를 남기지 않는다.
- 롤백 테스트 동안 트랜잭션이 대상 테이블과 채번 테이블에 잠금을 잡는다. 같은 DB를 다른 사람이 쓰므로 한 배치로 짧게 끝내고, 트랜잭션을 연 채로 다음 호출로 넘기지 않는다.
- 아직 적용하지 않은 SP를 돌려야 하면:
  - 개발 DB에 적용해도 된다고 허락받았으면 ALTER한 뒤 테스트한다.
  - 아니면 `CREATE PROCEDURE #sp_XX000100_SAVE`(세션 한정 임시 프로시저)로 만들어 실행한다. 영구 개체를 새로 만들지 않는다.
  - `CREATE PROCEDURE`는 배치의 첫 문장이어야 하므로 만들기와 실행은 호출을 나눈다. 임시 프로시저는 만든 세션에서만 보이므로 두 호출의 `@@SPID`가 같은지 본다.
  - 임시 프로시저 안에서는 `OBJECT_NAME(@@PROCID)`가 NULL이라 `SP_XML_LOG_SAVE`의 SP 이름이 비어 들어간다. 롤백되므로 문제는 없다.
- 조회 SP의 새 분기는 적용하지 않고 분기의 SELECT 문을 변수 선언과 함께 ad-hoc으로 실행한다.

## 2. 조회(SELECT) SP

원본과 새 조회문을 **같은 인자로** 실행해 건수와 내용을 비교한다. 분기(`@WORKTYPE`)마다 한다.

- 인자는 실제 데이터에서 결과가 나오는 값을 골라 쓴다. **0건끼리 비교하고 같다고 하지 않는다.** 결과가 0건이면 인자를 바꾼다.
- 내용은 `EXCEPT`를 양방향으로 본다. 한쪽만 보면 새 쪽에 더 생긴 행을 놓친다.
- `ORDER BY`는 결과 비교로 잡히지 않는다. 원본과 문장을 대조한다.
- 원본 결과는 `INSERT INTO @OLD EXEC 원본SP …`로 받는다. 새 조회문은 분기의 SELECT를 그대로 `INSERT INTO @NEW SELECT …`로 실행한다.
- 테이블 변수의 열과 타입은 분기 SELECT 문을 `SYS.DM_EXEC_DESCRIBE_FIRST_RESULT_SET`에 넣어 얻는다. SP 전체(`…_FOR_OBJECT`)를 넣으면 분기마다 결과 모양이 달라 실패한다.
- 원본 SP가 안에서 `INSERT … EXEC`를 쓰거나 한 분기가 결과표를 여러 개 돌려주면 `INSERT … EXEC`로 받을 수 없다. 그때는 원본 분기도 ad-hoc으로 실행한다.

```sql
SELECT COLUMN_ORDINAL
     , NAME
     , SYSTEM_TYPE_NAME
FROM SYS.DM_EXEC_DESCRIBE_FIRST_RESULT_SET(@SQL, N'@ORGDIV VARCHAR(2), @FRDT VARCHAR(8), @TODT VARCHAR(8)', 0)
ORDER BY COLUMN_ORDINAL;
```

조회 비교 틀:

```sql
SET NOCOUNT ON;

DECLARE @ORGDIV VARCHAR(2) = '01';
DECLARE @FRDT   VARCHAR(8) = '20261101';
DECLARE @TODT   VARCHAR(8) = '20261130';

DECLARE @OLD TABLE
(
      DOCNUM  VARCHAR(20)
    , DOCDT   DATE
    , CUSTCD  VARCHAR(20)
    , QTY     NUMERIC(38, 4)
    , REGDT   DATETIME
);

DECLARE @NEW TABLE
(
      DOCNUM  VARCHAR(20)
    , DOCDT   DATE
    , CUSTCD  VARCHAR(20)
    , QTY     NUMERIC(38, 4)
    , REGDT   DATETIME
);

INSERT INTO @OLD
EXEC SP_XX000100_SELECT @WORKTYPE = 'LIST', @ORGDIV = @ORGDIV, @FRDT = @FRDT, @TODT = @TODT;

-- 새 LIST 분기의 SELECT를 그대로 붙인다(ORDER BY는 빼고 따로 대조)
INSERT INTO @NEW
SELECT A.DOCNUM
     , CONVERT(DATE, A.DOCDT) AS DOCDT
     , A.CUSTCD
     , ISNULL(A1.QTY, 0) AS QTY
     , A.REGDT
FROM DOC_HEADER A
        LEFT OUTER JOIN (
                         SELECT T.ORGDIV
                              , T.DOCNUM
                              , SUM(T.QTY) AS QTY
                         FROM DOC_DETAIL T
                         WHERE T.ORGDIV = @ORGDIV
                         GROUP BY T.ORGDIV, T.DOCNUM
                        ) A1
                        ON A.ORGDIV = A1.ORGDIV
                        AND A.DOCNUM = A1.DOCNUM
WHERE A.ORGDIV = @ORGDIV
  AND A.DOCDT BETWEEN @FRDT AND @TODT;

SELECT 'LIST' AS WORKTYPE
     , (SELECT COUNT(*) FROM @OLD) AS OLDCNT
     , (SELECT COUNT(*) FROM @NEW) AS NEWCNT
     , (SELECT COUNT(*) FROM (SELECT * FROM @OLD EXCEPT SELECT * FROM @NEW) T) AS OLDONLY
     , (SELECT COUNT(*) FROM (SELECT * FROM @NEW EXCEPT SELECT * FROM @OLD) T) AS NEWONLY;
```

판정: `OLDCNT = NEWCNT > 0`이고 `OLDONLY = NEWONLY = 0`이면 같다. 다르면 `EXCEPT` 결과 행을 직접 띄워 어느 열이 다른지 본다.

## 3. 저장(SAVE) SP: 롤백 테스트

### 초안 만들기

아래 [틀](#틀)을 대상 SP마다 손으로 맞추지 않는다. 생성기로 초안을 만들고 `-- TODO:`만 채운다.

1. 대상 SP 정의를 파일로 둔다(고친 `.sql`, 또는 DB에서 읽은 정의).
2. 초안을 만든다. 출력은 `%TEMP%` 아래 작업 폴더에 둔다.

   ```
   python <스킬 폴더>/scripts/make_rollback_test.py <SP정의.sql> --out <작업 폴더>\<SP>_test.sql
   ```

3. 초안에 들어 있는 것: 인자 선언(등록자 `'ACETEST'`), XML마다 `FOR XML RAW('<TableName>'), ROOT('ROOT')` SELECT(`OPENXML … WITH` 열 전부, `VARCHAR(8)` 날짜 열은 `CONVERT(…, 112)`), 대상 테이블 건수 스냅샷(SP의 UPDATE·DELETE에 공통인 조건을 뽑아 씀), `@WORKTYPE` 값마다 EXEC 블록, 롤백과 롤백 후 확인. 맨 위 주석에 필수 시나리오와 주의사항, 뽑은 인자·XML 경로·WORKTYPE·대상 테이블이 있다. 추출 결과가 SP와 맞는지 먼저 본다.
4. `-- TODO:`를 채운다. 인자 값, XML의 원천 테이블과 키, 값 스냅샷이다. `WITH`에 있지만 원천 테이블에 없는 열(짝 테이블의 키 등)이 필요하면 `FROM`만 파생 테이블로 바꾸면 SELECT 목록을 그대로 쓸 수 있다. 혼합 수정·검증 실패 같은 시나리오는 WORKTYPE 블록을 복사해 만들고 아래 [반드시 지킬 것](#반드시-지킬-것)을 따른다.
5. 실행 전에 채운 XML 원천 SELECT를 따로(트랜잭션 없이) 돌려 행이 나오는지 본다. 없는 테이블·열 이름 같은 이름 해석 오류는 `CATCH`로 잡히지 않고 배치가 트랜잭션을 연 채 끊기기 때문이다. 끊겼으면 같은 연결에서 `IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;`을 실행한다.
6. 실행한다. 원천을 모르는 XML에는 `<원천>`이 남아 있어 채우지 않으면 문법 오류로 아무것도 실행되지 않는다. `WHERE 1 = 0`이 남으면 `… 행이 없다` 오류가 `ERROR` 행에 찍히고 전부 롤백된다. 빈 XML을 일부러 보내는 블록(삭제의 상세 등)은 그 `IF … IS NULL` 줄을 지운다.

### 형태

1. 결과를 모을 테이블 변수(`@RESULT`)와 테스트 전 건수
2. 실제 데이터에서 XML 만들기
3. `BEGIN TRANSACTION` → `BEGIN TRY` 안에서 시나리오마다 SP `EXEC`와 스냅샷 `INSERT INTO @RESULT`
4. `END TRY / BEGIN CATCH`에서 오류 메시지와 줄 번호 기록
5. `IF @@TRANCOUNT > @TRANCOUNT ROLLBACK TRANSACTION`
6. 롤백 뒤 건수가 테스트 전과 같은지, `@@TRANCOUNT`가 0인지 기록
7. `SELECT * FROM @RESULT`

테이블 변수는 롤백되지 않는다. 그래서 스냅샷을 테이블 변수에 모으면 롤백 뒤에도 남는다. DB 도구가 첫 결과표만 돌려주는 경우가 있으므로 결과는 **마지막에 `@RESULT` 하나로** 돌려준다.

### 반드시 지킬 것

| 규칙 | 이유 |
| --- | --- |
| XML은 `FOR XML RAW('<TableName>'), ROOT('ROOT')`로 만든다. TableName은 화면이 `dt.TableName`에 넣는 값이다 | SP의 `OPENXML` 경로가 `/ROOT/<TableName>`이다 |
| 행 상태는 `'NEW' AS GBN`처럼 직접 넣는다 | 화면의 `DataTableToXml`이 행마다 `GBN` 속성을 붙인다 |
| 한글이 들어가면 XML 앞에 `<?xml version="1.0" encoding="euc-kr"?>`를 붙인다 | SP가 XML을 `VARCHAR`로 받으므로 선언이 없으면 `SP_XML_PREPAREDOCUMENT`가 "텍스트 내용에 잘못된 문자가 있습니다"로 실패한다. 화면도 같은 선언을 붙인다 |
| 날짜 열은 `CONVERT(VARCHAR(8), 열, 112)`로 넣는다 | 화면은 DateTime을 `yyyyMMdd`(시각이 있으면 `yyyy-MM-dd HH:mm:ss`)로 보낸다. `FOR XML`은 `2026-11-19`로 써서 `VARCHAR(8)` 열에서 잘린다 |
| 테스트 배치에 `SET XACT_ABORT ON`을 쓰지 않는다 | 쓰면 "차단되는지 보는" 오류 한 번에 트랜잭션이 죽어 뒤 시나리오를 못 돌린다 |
| 오류가 나야 정상인 시나리오는 안쪽 `BEGIN TRY / BEGIN CATCH`로 따로 감싼다 | `RAISERROR … 16`은 트랜잭션을 죽이지 않는다(`XACT_STATE() = 1`). 바깥 TRY까지 가지 않게 한다 |
| 등록자 인자는 `'ACETEST'`처럼 구분되는 값, 수정은 `'ACETEST2'`처럼 다른 값을 쓴다 | 스냅샷에서 등록자·수정자가 어느 저장에서 찍혔는지 보인다 |
| 왕복 XML은 조회 SP 결과를 `INSERT INTO @DETAIL EXEC …`로 받아 만든다 | 화면이 실제로 다시 보내는 값과 같아야 왕복이 증명된다 |
| 건수 스냅샷은 키 목록을 `VALUES`로 두고 `LEFT OUTER JOIN`으로 센다 | `GROUP BY` 건수는 0건인 키가 결과에서 사라져 "지워졌다"가 보이지 않는다 |
| SP는 화면이 부르는 그대로 부른다. 화면이 어떤 모드에서 인자를 빼거나 `null`로 두면(삭제 때 상세 XML 등) 그 모드의 테스트도 그 인자를 빼고 부른다 | ADO.NET은 값이 `null`인 인자를 보내지 않는다. 항상 인자를 넘긴 테스트는 기본값 없는 인자의 "not supplied" 오류를 잡지 못한다([save.md](save.md#화면이-null로-넘길-수-있는-인자)) |

`DataTableToXml`의 직렬화(NULL 열은 속성 생략, 행마다 `GBN`·`NUM` 속성, DateTime 형식)는 대상 프로젝트의 `DataUtil.cs`에서 한 번 확인한다. `FOR XML RAW`도 NULL 열을 생략하므로 그 부분은 같다.

공통 SP가 쓰는 것(`SP_XML_LOG_SAVE`의 로그, `SP_SYSTEM_BA100T_KEYCODE`의 채번 순번)도 같은 트랜잭션이라 함께 롤백된다. 검증 실패 시나리오에서는 로그가 실패 전에 이미 쓰여 있으므로 "아무것도 안 써졌는지"는 **업무 테이블**로 본다.

### 필수 시나리오

| 시나리오 | 확인할 것 |
| --- | --- |
| 신규(NEW) | 헤더·상세·짝 테이블에 맞는 행이 생기는지, 순번 짝(상세 순번 ↔ 짝 테이블 순번)이 맞는지. 상세는 2행 이상 |
| 왕복 | 조회한 그대로 수정 저장 → 수량·금액·순번·번호가 그대로인지. 같은 저장을 한 번 더 해도 그대로인지 |
| 혼합 수정 | `MOD` 1행, `DEL` 1행, `NEW` 1행, `UNC` 1행을 한 번에 → `MOD`만 값과 수정자가 바뀌고, `UNC`는 그대로, 등록자·등록일 유지. `DEL`은 짝 테이블에서도 지워지고, `NEW`는 마지막 순번 다음 번호 |
| 검증 실패 | 한도를 넘는 값 등으로 차단 메시지가 나오는지, 업무 테이블에 아무것도 안 써졌는지 |
| 삭제 | 대상 문서만 지워지고 다른 문서는 그대로인지 |
| 롤백 후 | 건수와 값이 테스트 전과 같은지, `@@TRANCOUNT`가 0인지 |

조건에 맞는 데이터가 없는 등 검증할 수 없는 시나리오는 이유와 함께 `미확인`으로 남긴다. 실행한 시나리오의 숫자로 나머지를 추정하지 않는다.

### 틀

가상 계약이다. `SP_XX000100_SAVE`는 [procedure.md](procedure.md#저장save-sp--헤더--상세)의 골격에 짝 테이블 `DOC_ISSUE`(상세 1행마다 1행, `DOCSEQ`로 짝)가 붙은 형태다. 실제 인자·XML 경로·열은 `OBJECT_DEFINITION`으로 읽은 대상 SP를 따른다.

```sql
SET NOCOUNT ON;

DECLARE @TRANCOUNT INT          = @@TRANCOUNT;
DECLARE @ORGDIV    VARCHAR(2)   = '01';
DECLARE @XML       VARCHAR(MAX);
DECLARE @XMLDETAIL VARCHAR(MAX);
DECLARE @OUTPUT    VARCHAR(20);
DECLARE @DOCNUM    VARCHAR(20);

DECLARE @RESULT TABLE
(
      STEP     INT IDENTITY(1, 1)
    , SCENARIO VARCHAR(20)
    , TBL      VARCHAR(20)
    , DOCNUM   VARCHAR(20)
    , SEQ      VARCHAR(30)
    , QTY      NUMERIC(18, 4)
    , AMT      NUMERIC(18, 4)
    , REGEMPNO VARCHAR(50)
    , MODEMPNO VARCHAR(50)
    , REGDT    VARCHAR(23)
    , MSG      VARCHAR(1000)
);

-- 조회 SP의 DETAIL 결과(열·타입은 DESCRIBE_FIRST_RESULT_SET으로 얻는다)
DECLARE @DETAIL TABLE
(
      DOCNUM  VARCHAR(20)
    , SEQ     INT
    , ITEMCD  VARCHAR(20)
    , QTY     NUMERIC(18, 4)
    , UNP     NUMERIC(18, 4)
    , AMT     NUMERIC(18, 4)
    , DLVDT   DATE
    , REMARK  VARCHAR(500)
);

-- 0. 테스트 전 건수
INSERT INTO @RESULT (SCENARIO, TBL, QTY)
SELECT '0.BEFORE', 'DOC_HEADER', COUNT(*) FROM DOC_HEADER WHERE ORGDIV = @ORGDIV
UNION ALL
SELECT '0.BEFORE', 'DOC_DETAIL', COUNT(*) FROM DOC_DETAIL WHERE ORGDIV = @ORGDIV
UNION ALL
SELECT '0.BEFORE', 'DOC_ISSUE', COUNT(*) FROM DOC_ISSUE WHERE ORGDIV = @ORGDIV;

BEGIN TRANSACTION;

BEGIN TRY
    -- 1. 신규: 실제 품목 3행
    SET @XML = '<?xml version="1.0" encoding="euc-kr"?>'
             + (
                SELECT 'NEW' AS GBN
                     , '20261120' AS DOCDT
                     , A.CUSTCD
                     , 'ACE 롤백 테스트' AS REMARK
                FROM CUSTOMER_MASTER A
                WHERE A.CUSTCD = '10012'
                FOR XML RAW('DOC_HEADER'), ROOT('ROOT')
               );

    SET @XMLDETAIL = '<?xml version="1.0" encoding="euc-kr"?>'
                   + (
                      SELECT 'NEW' AS GBN
                           , B.ITEMCD
                           , K.QTY
                           , 10000 AS UNP
                           , K.QTY * 10000 AS AMT
                           , '20261127' AS DLVDT
                      FROM (
                            VALUES (1, 'ITEM-A', 5)
                                 , (2, 'ITEM-B', 4)
                                 , (3, 'ITEM-C', 3)
                           ) K(ORD, ITEMCD, QTY)
                              INNER JOIN ITEM_MASTER B
                                      ON K.ITEMCD = B.ITEMCD
                      ORDER BY K.ORD
                      FOR XML RAW('DOC_DETAIL'), ROOT('ROOT')
                     );

    EXEC SP_XX000100_SAVE @WORKTYPE = 'NEW', @ORGDIV = @ORGDIV, @USERID = 'ACETEST', @USERIP = 'ACE'
                        , @XML = @XML, @XMLDETAIL = @XMLDETAIL, @OUTPUT = @OUTPUT OUTPUT;

    SET @DOCNUM = @OUTPUT;

    INSERT INTO @RESULT (SCENARIO, TBL, DOCNUM, SEQ, QTY, AMT, REGEMPNO, MODEMPNO, REGDT)
    SELECT '1.NEW', 'DOC_DETAIL', A.DOCNUM, CONVERT(VARCHAR(10), A.SEQ), A.QTY, A.AMT, A.REGEMPNO, A.MODEMPNO
         , CONVERT(VARCHAR(23), A.REGDT, 121)
    FROM DOC_DETAIL A
    WHERE A.ORGDIV = @ORGDIV
      AND A.DOCNUM = @DOCNUM
    UNION ALL
    SELECT '1.NEW', 'DOC_ISSUE', A.DOCNUM, CONVERT(VARCHAR(10), A.DOCSEQ) + '/' + A.ISSUENUM, A.QTY, NULL
         , A.REGEMPNO, A.MODEMPNO, CONVERT(VARCHAR(23), A.REGDT, 121)
    FROM DOC_ISSUE A
    WHERE A.ORGDIV = @ORGDIV
      AND A.DOCNUM = @DOCNUM;

    -- 2. 왕복: 기존 문서를 조회한 그대로 두 번 저장
    INSERT INTO @DETAIL
    EXEC SP_XX000100_SELECT @WORKTYPE = 'DETAIL', @ORGDIV = @ORGDIV, @DOCNUM = '20261119-1';

    SET @XML = '<?xml version="1.0" encoding="euc-kr"?>'
             + (
                SELECT 'MOD' AS GBN
                     , A.DOCNUM
                     , A.DOCDT
                     , A.CUSTCD
                     , A.REMARK
                FROM DOC_HEADER A
                WHERE A.ORGDIV = @ORGDIV
                  AND A.DOCNUM = '20261119-1'
                FOR XML RAW('DOC_HEADER'), ROOT('ROOT')
               );

    SET @XMLDETAIL = '<?xml version="1.0" encoding="euc-kr"?>'
                   + (
                      SELECT 'MOD' AS GBN
                           , A.DOCNUM
                           , A.SEQ
                           , A.ITEMCD
                           , A.QTY
                           , A.UNP
                           , A.AMT
                           , CONVERT(VARCHAR(8), A.DLVDT, 112) AS DLVDT
                           , A.REMARK
                      FROM @DETAIL A
                      ORDER BY A.SEQ
                      FOR XML RAW('DOC_DETAIL'), ROOT('ROOT')
                     );

    EXEC SP_XX000100_SAVE @WORKTYPE = 'EDIT', @ORGDIV = @ORGDIV, @USERID = 'ACETEST', @USERIP = 'ACE'
                        , @XML = @XML, @XMLDETAIL = @XMLDETAIL, @OUTPUT = @OUTPUT OUTPUT;

    EXEC SP_XX000100_SAVE @WORKTYPE = 'EDIT', @ORGDIV = @ORGDIV, @USERID = 'ACETEST', @USERIP = 'ACE'
                        , @XML = @XML, @XMLDETAIL = @XMLDETAIL, @OUTPUT = @OUTPUT OUTPUT;

    INSERT INTO @RESULT (SCENARIO, TBL, DOCNUM, SEQ, QTY, AMT)
    SELECT '2.ROUNDTRIP-BEFORE', 'DOC_DETAIL', A.DOCNUM, CONVERT(VARCHAR(10), A.SEQ), A.QTY, A.AMT
    FROM @DETAIL A
    UNION ALL
    SELECT '2.ROUNDTRIP-AFTER2', 'DOC_DETAIL', A.DOCNUM, CONVERT(VARCHAR(10), A.SEQ), A.QTY, A.AMT
    FROM DOC_DETAIL A
    WHERE A.ORGDIV = @ORGDIV
      AND A.DOCNUM = '20261119-1';

    -- 3. 혼합 수정: SEQ 1 MOD(수량 5 → 6), SEQ 2 DEL, SEQ 3 UNC, NEW 1행
    DELETE FROM @DETAIL;

    INSERT INTO @DETAIL
    EXEC SP_XX000100_SELECT @WORKTYPE = 'DETAIL', @ORGDIV = @ORGDIV, @DOCNUM = @DOCNUM;

    SET @XML = '<?xml version="1.0" encoding="euc-kr"?>'
             + (
                SELECT 'MOD' AS GBN
                     , A.DOCNUM
                     , A.DOCDT
                     , A.CUSTCD
                     , A.REMARK
                FROM DOC_HEADER A
                WHERE A.ORGDIV = @ORGDIV
                  AND A.DOCNUM = @DOCNUM
                FOR XML RAW('DOC_HEADER'), ROOT('ROOT')
               );

    SET @XMLDETAIL = '<?xml version="1.0" encoding="euc-kr"?>'
                   + (
                      SELECT T.*
                      FROM (
                            SELECT (CASE A.SEQ WHEN 1 THEN 'MOD' WHEN 2 THEN 'DEL' ELSE 'UNC' END) AS GBN
                                 , A.DOCNUM
                                 , A.SEQ
                                 , A.ITEMCD
                                 , (CASE WHEN A.SEQ = 1 THEN 6 ELSE A.QTY END) AS QTY
                                 , A.UNP
                                 , (CASE WHEN A.SEQ = 1 THEN 6 * A.UNP ELSE A.AMT END) AS AMT
                                 , CONVERT(VARCHAR(8), A.DLVDT, 112) AS DLVDT
                            FROM @DETAIL A

                            UNION ALL

                            SELECT 'NEW', @DOCNUM, NULL, 'ITEM-D', 2, 10000, 20000, '20261127'
                           ) T
                      ORDER BY ISNULL(T.SEQ, 9999)
                      FOR XML RAW('DOC_DETAIL'), ROOT('ROOT')
                     );

    EXEC SP_XX000100_SAVE @WORKTYPE = 'EDIT', @ORGDIV = @ORGDIV, @USERID = 'ACETEST2', @USERIP = 'ACE'
                        , @XML = @XML, @XMLDETAIL = @XMLDETAIL, @OUTPUT = @OUTPUT OUTPUT;

    INSERT INTO @RESULT (SCENARIO, TBL, DOCNUM, SEQ, QTY, AMT, REGEMPNO, MODEMPNO, REGDT)
    SELECT '3.MIXED', 'DOC_DETAIL', A.DOCNUM, CONVERT(VARCHAR(10), A.SEQ), A.QTY, A.AMT, A.REGEMPNO, A.MODEMPNO
         , CONVERT(VARCHAR(23), A.REGDT, 121)
    FROM DOC_DETAIL A
    WHERE A.ORGDIV = @ORGDIV
      AND A.DOCNUM = @DOCNUM
    UNION ALL
    SELECT '3.MIXED', 'DOC_ISSUE', A.DOCNUM, CONVERT(VARCHAR(10), A.DOCSEQ) + '/' + A.ISSUENUM, A.QTY, NULL
         , A.REGEMPNO, A.MODEMPNO, CONVERT(VARCHAR(23), A.REGDT, 121)
    FROM DOC_ISSUE A
    WHERE A.ORGDIV = @ORGDIV
      AND A.DOCNUM = @DOCNUM;

    -- 4. 검증 실패: 오류가 나야 정상이므로 안쪽 TRY로 감싼다
    SET @XMLDETAIL = '<?xml version="1.0" encoding="euc-kr"?>'
                   + (
                      SELECT 'MOD' AS GBN
                           , A.DOCNUM
                           , A.SEQ
                           , A.ITEMCD
                           , 999999 AS QTY
                           , A.UNP
                           , 999999 * A.UNP AS AMT
                           , A.DLVDT
                      FROM DOC_DETAIL A
                      WHERE A.ORGDIV = @ORGDIV
                        AND A.DOCNUM = @DOCNUM
                        AND A.SEQ = 1
                      FOR XML RAW('DOC_DETAIL'), ROOT('ROOT')
                     );

    INSERT INTO @RESULT (SCENARIO, TBL, DOCNUM, QTY, AMT)
    SELECT '4.FAIL-BEFORE', 'DOC_DETAIL', @DOCNUM, SUM(A.QTY), COUNT(*)
    FROM DOC_DETAIL A
    WHERE A.ORGDIV = @ORGDIV
      AND A.DOCNUM = @DOCNUM;

    BEGIN TRY
        EXEC SP_XX000100_SAVE @WORKTYPE = 'EDIT', @ORGDIV = @ORGDIV, @USERID = 'ACETEST2', @USERIP = 'ACE'
                            , @XML = @XML, @XMLDETAIL = @XMLDETAIL, @OUTPUT = @OUTPUT OUTPUT;

        INSERT INTO @RESULT (SCENARIO, MSG) VALUES ('4.FAIL', '차단되지 않음');
    END TRY
    BEGIN CATCH
        INSERT INTO @RESULT (SCENARIO, MSG)
        VALUES ('4.FAIL', ERROR_MESSAGE() + ' / XACT_STATE = ' + CONVERT(VARCHAR(2), XACT_STATE()));
    END CATCH

    INSERT INTO @RESULT (SCENARIO, TBL, DOCNUM, QTY, AMT)
    SELECT '4.FAIL-AFTER', 'DOC_DETAIL', @DOCNUM, SUM(A.QTY), COUNT(*)
    FROM DOC_DETAIL A
    WHERE A.ORGDIV = @ORGDIV
      AND A.DOCNUM = @DOCNUM;

    -- 5. 삭제: 테스트 문서만 지워지는지
    EXEC SP_XX000100_SAVE @WORKTYPE = 'DELETE', @ORGDIV = @ORGDIV, @USERID = 'ACETEST', @USERIP = 'ACE'
                        , @XML = @XML, @XMLDETAIL = '<ROOT/>', @OUTPUT = @OUTPUT OUTPUT;

    INSERT INTO @RESULT (SCENARIO, TBL, DOCNUM, QTY)
    SELECT '5.DELETE', K.TBL, K.DOCNUM, COUNT(B.DOCNUM) + COUNT(C.DOCNUM) + COUNT(D.DOCNUM)
    FROM (
          VALUES ('DOC_HEADER', @DOCNUM), ('DOC_DETAIL', @DOCNUM), ('DOC_ISSUE', @DOCNUM)
               , ('DOC_HEADER', '20261119-1'), ('DOC_DETAIL', '20261119-1'), ('DOC_ISSUE', '20261119-1')
         ) K(TBL, DOCNUM)
            LEFT OUTER JOIN DOC_HEADER B
                         ON K.TBL = 'DOC_HEADER'
                         AND B.ORGDIV = @ORGDIV
                         AND K.DOCNUM = B.DOCNUM
            LEFT OUTER JOIN DOC_DETAIL C
                         ON K.TBL = 'DOC_DETAIL'
                         AND C.ORGDIV = @ORGDIV
                         AND K.DOCNUM = C.DOCNUM
            LEFT OUTER JOIN DOC_ISSUE D
                         ON K.TBL = 'DOC_ISSUE'
                         AND D.ORGDIV = @ORGDIV
                         AND K.DOCNUM = D.DOCNUM
    GROUP BY K.TBL, K.DOCNUM;
END TRY
BEGIN CATCH
    INSERT INTO @RESULT (SCENARIO, MSG)
    VALUES ('ERROR', ERROR_MESSAGE() + ' (LINE ' + CONVERT(VARCHAR(10), ERROR_LINE()) + ')');
END CATCH

IF @@TRANCOUNT > @TRANCOUNT
    ROLLBACK TRANSACTION;

-- 6. 롤백 후 건수
INSERT INTO @RESULT (SCENARIO, TBL, QTY, MSG)
SELECT '6.AFTER', 'DOC_HEADER', COUNT(*), 'TRANCOUNT = ' + CONVERT(VARCHAR(2), @@TRANCOUNT)
FROM DOC_HEADER
WHERE ORGDIV = @ORGDIV
UNION ALL
SELECT '6.AFTER', 'DOC_DETAIL', COUNT(*), NULL FROM DOC_DETAIL WHERE ORGDIV = @ORGDIV
UNION ALL
SELECT '6.AFTER', 'DOC_ISSUE', COUNT(*), NULL FROM DOC_ISSUE WHERE ORGDIV = @ORGDIV;

SELECT * FROM @RESULT ORDER BY STEP;
```

- 삭제 블록의 `@XMLDETAIL = '<ROOT/>'`는 화면이 삭제 때 빈 XML을 보내는 경우의 형태다. 화면이 `null`로 두면 [반드시 지킬 것](#반드시-지킬-것)대로 이 인자를 빼고 부른다.
- 시나리오 사이에 앞 시나리오가 만든 문서를 이어서 쓴다(신규 → 혼합 수정 → 검증 실패 → 삭제). 앞 단계가 실패하면 `ERROR` 행에 줄 번호가 찍히고 뒤 시나리오는 돌지 않는다. 그 시나리오들은 `미확인`이다.
- 신규 상세의 원천(재고·선행 입고 등)은 조회 SP의 후보 분기를 먼저 실행해 잔량이 있는 실제 키를 고른다. 수량은 잔량 안에서 정한다.
- 검증 실패용 값은 대상 SP의 검증식을 읽고 정한다. 다른 검증에 먼저 걸리면 의도한 차단을 확인한 것이 아니다. 메시지를 대상 검증의 메시지와 대조한다.
- 테스트 뒤에 한 번 더, 트랜잭션 밖에서 건수를 직접 조회해 테스트 전과 같은지 본다.

## 4. 적용 확인

DB에 적용했으면 DB의 정의와 `.sql` 파일이 같은지 해시로 확인한다. 눈으로 비교하지 않는다.

- SQL Server는 ALTER로 적용해도 정의를 `CREATE PROCEDURE …`로 저장한다. 파일 쪽은 첫 `ALTER PROC`를 `CREATE PROC`로 바꿔서 계산한다.
- 저장된 정의의 끝 줄바꿈은 적용한 도구에 따라 다르다(`END` 뒤 LF 하나인 SP도, LF·CRLF 두 개인 SP도 있었다). 양쪽 모두 CR을 지우고 앞뒤의 공백·탭·LF를 잘라서 계산한다.
- `HASHBYTES`는 `NVARCHAR`를 UTF-16LE 바이트로 해시한다. 파일 쪽도 UTF-16LE로 인코딩해서 SHA-256을 낸다. 파일의 BOM은 읽을 때 빠진다.

```sql
SELECT A.NAME
     , CONVERT(VARCHAR(64), HASHBYTES('SHA2_256', TRIM(CHAR(32) + CHAR(9) + CHAR(10)
                                                       FROM REPLACE(B.DEFINITION, CHAR(13), ''))), 2) AS DBHASH
FROM SYS.OBJECTS A
        INNER JOIN SYS.SQL_MODULES B
                ON A.OBJECT_ID = B.OBJECT_ID
WHERE A.NAME = 'sp_XX000100_SAVE';
```

```powershell
$t = [System.IO.File]::ReadAllText('<경로>\sp_XX000100_SAVE.sql').Replace("`r", "")
$t = [regex]::Replace($t, '^(\s*(?:--[^\n]*\n\s*)*)ALTER(\s+PROC)', '${1}CREATE${2}', 'IgnoreCase')
$t = $t.Trim(" `t`n".ToCharArray())
$sha = [System.Security.Cryptography.SHA256]::Create()
($sha.ComputeHash([System.Text.Encoding]::Unicode.GetBytes($t)) | ForEach-Object { $_.ToString('X2') }) -join ''
```

`TRIM(문자 FROM …)`은 SQL Server 2017 이상이다. 그 아래 버전에서는 DB 정의를 그대로 가져와 파일 쪽과 같은 방식으로 PowerShell에서 계산한다. 두 해시가 같아야 "적용했다"고 쓴다.

## 5. 보고

시나리오 표의 근거 칸에 무엇으로 확인했는지와 실제 숫자를 적는다.

| 근거 | 쓰는 법 |
| --- | --- |
| 실행 결과 | `실행 결과: 수량 18 → 18, 금액 180,000 유지, 순번 1, 불출 20261119-1-1 유지`처럼 전후 숫자를 적는다 |
| 정적 대조 | 실행하지 못한 이유를 함께 적는다(`운영 DB라 실행 안 함`, `대상 데이터 없음`) |
| 미확인 | 왜 확인하지 못했는지 적는다 |

C_KONE120 `sp_MA100500_SAVE`를 위 틀로 돌린 예(2026-11-20, 전부 롤백):

| 구분 | 확인한 사례 | 근거 |
| --- | --- | --- |
| 정상 | 신규 상세 3행 | 실행 결과: 발주 상세 3행(수량 5·4·3, 금액 50,000·40,000·30,000), 불출 3행 순번 1·2·3 짝 일치, 등록자 ACETEST |
| 왕복 | 20261119-1을 조회한 그대로 두 번 수정 저장 | 실행 결과: 수량 18 → 18, 금액 180,000 유지, 순번 1, 불출 20261119-1-1 유지, 등록자 admin·등록일 유지 |
| 혼합 수정 | MOD·DEL·UNC·NEW 각 1행 | 실행 결과: MOD 수량 5 → 6·수정자 ACETEST2, DEL 행은 상세·불출 모두 삭제, UNC 수정자 없음, NEW 순번 4·새 불출번호, 등록일 유지 |
| 검증 실패 | 입고수량 12를 넘는 999 | 실행 결과: "외주발주 수량이 이전공정의 단조 LOT 재고수량을 초과합니다", XACT_STATE 1, 상세 합계 11·3행 전후 같음 |
| 삭제 | 테스트 문서 삭제 | 실행 결과: 테스트 문서 0건, 20261119-1은 헤더·상세·불출 1건씩 유지 |
| 롤백 후 | 전체 건수 | 실행 결과: MA100T(PURDIV 2) 1 → 1, SA210T(MA100500) 1 → 1, SP_LOG 691 → 691, `@@TRANCOUNT` 0 |
