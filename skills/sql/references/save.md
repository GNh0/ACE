# 저장 예시

아래는 가상 계약이다. 실제 키·자료형·상태문자·XML 경로는 대상 원본과 동작하는 같은 역할의 SAVE를 따른다.

## SAVE 고정 규칙

사용자가 따로 말하지 않아도 SAVE를 새로 쓰거나 기존 SAVE의 로직을 고칠 때 지킨다. 원본에 아래와 다른 형태가 있으면 그것도 고친다. 서식 정리만 맡았으면 바꾸지 않고 해당 위치를 보고한다.

| 금지 | 대신 |
| --- | --- |
| `WITH (UPDLOCK, HOLDLOCK)` 등 잠금 힌트(원본·참고 SP에 있던 것 포함) | 힌트 없이 조회한다. 사용자가 이번 작업에서 명시 요청한 힌트만 남긴다. |
| `IF @WORKTYPE = 'DELETE' BEGIN … RETURN END` 뒤에 나머지 모드를 조건 없이 이어 쓰기 | 아래 골격의 IF/ELSE IF 분기 |
| SP 안의 `BEGIN TRANSACTION`·`COMMIT`·`ROLLBACK`·`BEGIN TRY/CATCH`·`THROW`, `SET XACT_ABORT ON`, `@STARTTRANCOUNT`(원본에 있던 것 포함) | 호출부가 `ExecSPTrn`이면 쓰지 않는다. `ExecSP`이면 원본의 트랜잭션을 그대로 둔다. 먼저 호출부를 확인한다. [트랜잭션](#트랜잭션) |
| `@NEWCOUNT`·`@MODCOUNT`·`@DELCOUNT` 같은 건수 변수, `IF @@ROWCOUNT <> @변수`, `IF @CNT > 0` | 쓰기 전 `IF EXISTS` / `IF NOT EXISTS` 검증(전체 키, LEFT OUTER JOIN … IS NULL, 중복 키 GROUP BY HAVING) |
| `SELECT @LASTSEQ = ISNULL(MAX(…), 0)` 뒤 `@LASTSEQ + RN`, 스테이징에 순번을 먼저 `UPDATE` | INSERT 안에서 `ISNULL(C.SEQ, 0) + ROW_NUMBER() OVER (ORDER BY …)`와 파생 MAX JOIN. 뒤 단계는 쓴 대상 행을 업무 키로 JOIN한다. |
| 쓰기 문장을 감싼 WHILE·커서 루프에서 중첩 루프·`SELECT TOP 1 @변수`·루프 변수 여러 개로 한 행씩 처리 | [배분 INSERT](#배분-insert)처럼 한 문장 안의 JOIN·파생(누적 비교)으로 쓴다. 루프는 집합으로 풀 수 없을 때만 쓰고 이유를 밝힌다. |
| NEW·EDIT 분기에 같은 상세 INSERT·배분·사후 검증을 복사 | `ELSE IF @WORKTYPE IN ('NEW', 'EDIT')` 안의 모드별 부분 뒤에 한 번만 둔다. |
| `OUTPUT INSERTED.… INTO @테이블`로 쓴 키를 모아 다시 읽기 | 뒤 단계가 쓴 대상 행을 업무 키로 JOIN한다. |
| 한 번 대입하고 한 번 읽는 변수, 선언만 하거나 대입만 하고 읽지 않는 변수, 헤더 테이블 변수 값을 복사한 변수 | 그 자리에서 식을 쓰거나 테이블 변수·대상 행을 JOIN해 읽는다. |
| `INSERT INTO @TMPISSUE … SELECT … FROM 실제 테이블`처럼 중간 결과를 테이블 변수·임시 테이블에 담았다가 다시 읽기 | 최종 INSERT/UPDATE/DELETE 안의 JOIN·파생 테이블로 바로 계산한다. 테이블 변수는 XML 파싱(`FROM OPENXML`)에만 쓴다. |

`@변수`는 최소화한다. 남기는 변수는 T-SQL이 변수를 요구하는 경우뿐이다.

| 남기는 변수 | 이유 |
| --- | --- |
| `@DOC_ID` | `SP_XML_PREPAREDOCUMENT`의 OUTPUT 핸들 |
| `@NEWSEQ`, `@OUTSEQ` | 채번 프로시저의 OUTPUT 인자 |
| `@PURDT` 같은 채번 기준일 | EXEC 인자에는 식·하위 쿼리를 쓸 수 없다 |
| `@PURNUM` 같은 문서번호 | NEW에서 생성해 여러 문장에서 쓴다 |

Codex 산출물 폴더를 거치지 않은 근호 작성 SAVE(`sp_MA000100_SAVE`의 `@REQNUM`·`@REQDT`·`@NEWSEQ`, `sp_QC100100_SAVE`의 `@QCNUM`)도 이 범위다. 그 밖의 헤더 값은 `@TMP_HEADER`를 JOIN해 읽는다.

```sql
IF @WORKTYPE IN ('EDIT', 'DELETE')
BEGIN
    IF EXISTS (
               SELECT 1
               FROM @TMP_HEADER A
                       LEFT OUTER JOIN DOCUMENT_HEADER B
                                    ON B.COMPANY_ID = @COMPANY_ID
                                    AND A.DOCUMENT_NO = B.DOCUMENT_NO
               WHERE B.DOCUMENT_NO IS NULL
              )
    BEGIN
        RAISERROR('The document does not exist.', 16, 1);
        RETURN;
    END
END

IF @WORKTYPE = 'DELETE'
BEGIN
    DELETE A
    FROM DOCUMENT_DETAIL A
            INNER JOIN @TMP_HEADER B
                    ON A.DOCUMENT_NO = B.DOCUMENT_NO
    WHERE A.COMPANY_ID = @COMPANY_ID

    DELETE A
    FROM DOCUMENT_HEADER A
            INNER JOIN @TMP_HEADER B
                    ON A.DOCUMENT_NO = B.DOCUMENT_NO
    WHERE A.COMPANY_ID = @COMPANY_ID
END
ELSE IF @WORKTYPE IN ('NEW', 'EDIT')
BEGIN
    -- NEW/EDIT 공통 상세 XML 파싱·검증

    IF @WORKTYPE = 'NEW'
    BEGIN
        EXEC SP_DOCUMENT_KEYCODE @COMPANY_ID, @DOCUMENT_DT, @NEWSEQ OUTPUT
        SET @DOCUMENT_NO = @DOCUMENT_DT + '-' + CONVERT(VARCHAR(10), @NEWSEQ)

        -- 헤더 INSERT
    END
    ELSE IF @WORKTYPE = 'EDIT'
    BEGIN
        IF EXISTS (
                   SELECT 1
                   FROM @TMP_DETAIL A
                           LEFT OUTER JOIN DOCUMENT_DETAIL B
                                        ON B.COMPANY_ID = @COMPANY_ID
                                        AND B.DOCUMENT_NO = @DOCUMENT_NO
                                        AND A.LINE_NO = B.LINE_NO
                   WHERE A.CHANGE_STATE IN ('MOD', 'DEL')
                     AND B.LINE_NO IS NULL
                  )
        BEGIN
            RAISERROR('A modified or deleted line does not exist.', 16, 1);
            RETURN;
        END

        -- 헤더 UPDATE, 상세 MOD UPDATE / DEL DELETE
    END

    INSERT INTO DOCUMENT_DETAIL
    (
           COMPANY_ID  , DOCUMENT_NO  , LINE_NO
         , ITEM_CODE
    )
    SELECT @COMPANY_ID , @DOCUMENT_NO , ISNULL(C.LINE_NO, 0) + ROW_NUMBER() OVER (ORDER BY A.SEQ)
         , A.ITEM_CODE
    FROM @TMP_DETAIL A
            LEFT OUTER JOIN (
                             SELECT T.COMPANY_ID
                                  , T.DOCUMENT_NO
                                  , MAX(T.LINE_NO) AS LINE_NO
                             FROM DOCUMENT_DETAIL T
                             WHERE T.COMPANY_ID = @COMPANY_ID
                               AND T.DOCUMENT_NO = @DOCUMENT_NO
                             GROUP BY T.COMPANY_ID, T.DOCUMENT_NO
                            ) C
                            ON C.COMPANY_ID = @COMPANY_ID
                            AND C.DOCUMENT_NO = @DOCUMENT_NO
    WHERE A.CHANGE_STATE = 'NEW'

    SET @OUTPUT = @DOCUMENT_NO
END
```

검증 실패는 분기 안에서 `RAISERROR … RETURN`으로 끝낸다. C#의 `ExecSPTrn`이 예외를 받아 롤백한다. 쓰기 뒤에 건수를 다시 세지 않는다. 같은 업무의 모드 조건을 준비·검증·쓰기마다 반복하지 않는다. 참고 SP에 같은 형태가 있어도 유지할 근거가 아니다.

## 트랜잭션

트랜잭션을 어디서 잡는지는 **호출부가 정한다.** SP를 고치기 전에 화면 코드에서 이 SP를 부르는 줄을 찾아 확인한다.

| 호출부 | SP 안의 트랜잭션 |
| --- | --- |
| `dbClient.ExecSPTrn("sp_…_SAVE", …)` | 쓰지 않는다. 원본에 있으면 뺀다. |
| `dbClient.ExecSP("sp_…_SAVE", …)` | **빼지 않는다.** 원본의 `BEGIN TRY / BEGIN TRANSACTION / COMMIT / CATCH ROLLBACK`을 그대로 둔다. |
| 다른 SP·외부 시스템이 부르거나, 호출부를 찾지 못함 | 빼지 않고 사용자에게 묻는다. |

- `ExecSPTrn`은 호출 전에 트랜잭션을 시작하고, 성공하면 커밋하고, 예외가 나면 롤백한다. SP는 검증 실패 시 `RAISERROR('메시지', 16, 1); RETURN;`만 하면 그때까지의 쓰기가 전부 롤백된다. 이 경우 SP 안에서 따로 `ROLLBACK`하면 바깥 트랜잭션까지 끝나서 266 오류(트랜잭션 수 불일치)가 난다.
- `ExecSP`는 트랜잭션을 걸지 않는다. 이때 SP의 트랜잭션을 빼면, 쓰는 도중 오류(문자열 잘림, NOT NULL 위반, 교착 등)가 났을 때 앞에서 쓴 행이 남는다. 검증을 쓰기 앞으로 옮겨도 이 위험은 없어지지 않는다.
- `ExecSP`로 부르는 저장을 발견하면 답변에 호출부 위치(파일, 줄)를 적고, 호출을 `ExecSPTrn`으로 바꾼 뒤 SP의 트랜잭션을 빼는 방법을 제안한다. 사용자가 동의하기 전에는 화면도 SP의 트랜잭션도 바꾸지 않는다.
- 같은 프로젝트 안에도 두 방식이 섞여 있다(C_KONE120은 저장 호출 141곳 중 17곳이 `ExecSP`). 다른 화면이 `ExecSPTrn`이라고 이 화면도 그럴 거라고 가정하지 않는다.

## 배분 INSERT

재고·선행 입고를 요청 행에 먼저 들어온 순서대로 나눠 쓰는 경우다. 한 행씩 꺼내는 루프나 중간 테이블 없이 INSERT 한 문장으로 쓴다. 요청 행(A)과 잔량이 있는 재고(B)에 각각 같은 묶음 키별 누적 시작·끝 수량을 파생으로 만들고, 두 구간이 겹치는 행을 JOIN한다. 배분량은 `작은 끝 - 큰 시작`이다. 가상 스키마이며 STOCK_RECEIPT는 COMPANY_ID/RECEIPT_NO/RECEIPT_LINE이 유일하다.

```sql
INSERT INTO STOCK_ISSUE
(
       COMPANY_ID  , ISSUE_NO  , ISSUE_LINE
     , RECEIPT_NO  , RECEIPT_LINE , DOCUMENT_NO
     , LINE_NO     , QTY
)
SELECT @COMPANY_ID , @ISSUE_NO , ROW_NUMBER() OVER (ORDER BY A.LINE_NO, B.RECEIPT_DT, B.RECEIPT_NO, B.RECEIPT_LINE)
     , B.RECEIPT_NO , B.RECEIPT_LINE , @DOCUMENT_NO
     , A.LINE_NO    , (CASE WHEN A.END_QTY < B.END_QTY THEN A.END_QTY ELSE B.END_QTY END)
                      - (CASE WHEN A.START_QTY > B.START_QTY THEN A.START_QTY ELSE B.START_QTY END)
FROM (
      SELECT T.LINE_NO
           , T.ITEM_CODE
           , T.LOT_NO
           , SUM(T.QTY) OVER (PARTITION BY T.ITEM_CODE, T.LOT_NO ORDER BY T.LINE_NO ROWS UNBOUNDED PRECEDING) - T.QTY AS START_QTY
           , SUM(T.QTY) OVER (PARTITION BY T.ITEM_CODE, T.LOT_NO ORDER BY T.LINE_NO ROWS UNBOUNDED PRECEDING) AS END_QTY
      FROM DOCUMENT_DETAIL T
      WHERE T.COMPANY_ID = @COMPANY_ID
        AND T.DOCUMENT_NO = @DOCUMENT_NO
     ) A
        INNER JOIN (
                    SELECT T.RECEIPT_NO
                         , T.RECEIPT_LINE
                         , T.RECEIPT_DT
                         , T.ITEM_CODE
                         , T.LOT_NO
                         , SUM(T.QTY - ISNULL(T1.QTY, 0)) OVER (PARTITION BY T.ITEM_CODE, T.LOT_NO
                                                                ORDER BY T.RECEIPT_DT, T.RECEIPT_NO, T.RECEIPT_LINE
                                                                ROWS UNBOUNDED PRECEDING) - (T.QTY - ISNULL(T1.QTY, 0)) AS START_QTY
                         , SUM(T.QTY - ISNULL(T1.QTY, 0)) OVER (PARTITION BY T.ITEM_CODE, T.LOT_NO
                                                                ORDER BY T.RECEIPT_DT, T.RECEIPT_NO, T.RECEIPT_LINE
                                                                ROWS UNBOUNDED PRECEDING) AS END_QTY
                    FROM STOCK_RECEIPT T
                            LEFT OUTER JOIN (
                                             SELECT T.RECEIPT_NO
                                                  , T.RECEIPT_LINE
                                                  , SUM(T.QTY) AS QTY
                                             FROM STOCK_ISSUE T
                                             WHERE T.COMPANY_ID = @COMPANY_ID
                                             GROUP BY T.RECEIPT_NO, T.RECEIPT_LINE
                                            ) T1
                                            ON T.RECEIPT_NO = T1.RECEIPT_NO
                                            AND T.RECEIPT_LINE = T1.RECEIPT_LINE
                    WHERE T.COMPANY_ID = @COMPANY_ID
                      AND T.QTY > ISNULL(T1.QTY, 0)
                   ) B
                   ON A.ITEM_CODE = B.ITEM_CODE
                   AND A.LOT_NO = B.LOT_NO
                   AND A.START_QTY < B.END_QTY
                   AND B.START_QTY < A.END_QTY

IF EXISTS (
           SELECT 1
           FROM DOCUMENT_DETAIL A
                   LEFT OUTER JOIN (
                                    SELECT T.LINE_NO
                                         , SUM(T.QTY) AS QTY
                                    FROM STOCK_ISSUE T
                                    WHERE T.COMPANY_ID = @COMPANY_ID
                                      AND T.DOCUMENT_NO = @DOCUMENT_NO
                                    GROUP BY T.LINE_NO
                                   ) B
                                   ON A.LINE_NO = B.LINE_NO
           WHERE A.COMPANY_ID = @COMPANY_ID
             AND A.DOCUMENT_NO = @DOCUMENT_NO
             AND A.QTY <> ISNULL(B.QTY, 0)
          )
BEGIN
    RAISERROR('The stock is not enough for the requested quantity.', 16, 1);
    RETURN;
END
```

재고가 모자라면 배분 합계가 요청보다 작아 뒤의 검증이 실패하고 호출부(`ExecSPTrn`)가 롤백한다. EDIT에서 다시 배분할 행만 쓰려면 A에 그 행의 업무 키 조건(이미 출고가 없는 행 등)을 더한다. 같은 키의 요청 2행, 재고 여러 행에 걸친 배분, 재고 부족, 다른 회사의 같은 LOT을 확인한다.

## Parsed rows and NEW

XML은 기존 처리 범위에서 한 번 파싱한다. 필요한 열·타입을 정의하고 파싱한 행을 INSERT SELECT에 직접 쓴다. 할당한 문서 핸들은 정상·예외 경로에서 해제한다. 정상 해제 후 핸들을 비워 뒤의 오류가 이중 해제를 유발하지 않게 한다.

```sql
INSERT INTO CONTACTS
(
       COMPANY_ID  , CUSTOMER_ID  , CONTACT_ID   , CONTACT_NAME
)
SELECT @COMPANY_ID , @CUSTOMER_ID , A.CONTACT_ID , A.CONTACT_NAME
FROM @TMP_CONTACT A
WHERE A.CHANGE_STATE = 'NEW'
```

기존 채번 범위·순서를 지킨다. 상세 순번은 [고정 규칙](#save-고정-규칙)의 파생 MAX + ROW_NUMBER로 매긴다. XML 행 인덱스는 영구 키의 근거가 될 수 없다. 생성한 상세 키가 뒤 단계에 필요하면 쓴 대상 행을 업무 키로 JOIN해 읽는다.

## Operation ownership

| 업무 | 분기 위치 |
| --- | --- |
| 신규 모드에만 필요한 검증·헤더·상세 쓰기 | 같은 신규 분기에서 실행 순서대로 처리 |
| 이름 변경에만 필요한 수정 | 해당 변경 분기 안에서 처리 |
| 두 모드가 같은 결과를 반환하거나 같은 해제를 수행 | 자료 의존성이 같은 공통 위치에서 한 번 실행 |

같은 모드를 준비·검증·쓰기마다 다시 검사하지 않는다. 기존 호출자가 요구하는 공통 XML 전처리·검증은 해당 범위에 둔다. 검증을 바꾸면 [검증 예시](#검증-예시)를 대조한다.

## MOD and DEL

한 고객의 선택된 연락처를 수정·삭제하는 경우다. 회사·고객·연락처가 전체 키다.

```sql
UPDATE A
SET CONTACT_NAME = B.CONTACT_NAME
  , MODIFIED_AT = GETDATE()
FROM CONTACTS A
        INNER JOIN @TMP_CONTACT B
                ON A.CONTACT_ID = B.CONTACT_ID
WHERE A.COMPANY_ID = @COMPANY_ID
  AND A.CUSTOMER_ID = @CUSTOMER_ID
  AND B.CHANGE_STATE = 'MOD'

DELETE A
FROM CONTACTS A
        INNER JOIN @TMP_CONTACT B
                ON A.CONTACT_ID = B.CONTACT_ID
WHERE A.COMPANY_ID = @COMPANY_ID
  AND A.CUSTOMER_ID = @CUSTOMER_ID
  AND B.CHANGE_STATE = 'DEL'
```

## Multiple-master-delete

여러 문서의 삭제 키를 받은 경우 선택한 전체 키 집합을 끝까지 유지한다. 삭제 가능 조건을 확인하고 연관 상세를 먼저, 헤더를 다음에 삭제한다.

```sql
DELETE A
FROM DOCUMENT_DETAIL A
        INNER JOIN @TMP_DOCUMENT B
                ON A.COMPANY_ID = B.COMPANY_ID
                AND A.DOCUMENT_NO = B.DOCUMENT_NO
WHERE A.COMPANY_ID = @COMPANY_ID
  AND B.CHANGE_STATE = 'DEL'
```

같은 키 조건으로 해당 헤더를 처리한다. 선택 2건, 미선택 1건, 다른 회사의 동일 번호로 대상·제외 결과를 확인한다.

## 재고 이동 (출고 + 입고를 함께 쓰는 저장)

자재를 한 창고에서 내보내고 다른 창고(출하대기 등)로 들이는 저장이다. 저장 한 번이 출고 테이블과 입고 테이블에 **짝이 되는 행**을 만든다. 수불장·재고 조회가 이 두 테이블을 읽으므로 짝이 어긋나면 재고가 틀어진다. 이름은 가상이다.

```sql
EXEC SP_SYSTEM_BA100T_KEYCODE @ORGDIV, 'BA100T', @OUTDT, @NEWSEQ OUTPUT;

INSERT INTO STOCK_OUT
(
       ORGDIV   , RECDT     , SEQ1     , SEQ2
     , ORDNUM   , ORDSEQ    , ITEMCD   , QTY
     , OUTDT    , REGDT     , REGEMPNO , STORAGE
)
SELECT @ORGDIV  , @OUTDT    , @NEWSEQ  , ROW_NUMBER() OVER (ORDER BY A.ORDNUM, A.ORDSEQ, A.ITEMCD)
     , A.ORDNUM , A.ORDSEQ  , A.ITEMCD , A.QTY
     , @OUTDT   , GETDATE() , @USERID  , (CASE WHEN B.REQLOCA = '3' THEN '3000' ELSE '1001' END)
FROM @TMP_DETAIL A
        LEFT OUTER JOIN (
                         SELECT T.ORDNUM
                              , T.ORDSEQ
                              , T.REQLOCA
                         FROM REQUEST_REV T
                                 INNER JOIN (
                                             SELECT T.ORDNUM
                                                  , T.ORDSEQ
                                                  , MAX(T.REVNO) AS MAXREVNO
                                             FROM REQUEST_REV T
                                             WHERE T.ORGDIV = @ORGDIV
                                             GROUP BY T.ORDNUM, T.ORDSEQ
                                            ) T1
                                            ON T.ORDNUM = T1.ORDNUM
                                            AND T.ORDSEQ = T1.ORDSEQ
                                            AND T.REVNO = T1.MAXREVNO
                         WHERE T.ORGDIV = @ORGDIV
                        ) B
                        ON A.ORDNUM = B.ORDNUM
                        AND A.ORDSEQ = B.ORDSEQ
WHERE A.CHK = 'Y';

INSERT INTO STOCK_IN
(
       ORGDIV   , RECDT     , SEQ1     , SEQ2
     , ORDNUM   , ORDSEQ    , ITEMCD   , QTY
     , INDT     , REGDT     , REGEMPNO , STORAGE
)
SELECT A.ORGDIV , A.RECDT   , A.SEQ1   , A.SEQ2
     , A.ORDNUM , A.ORDSEQ  , A.ITEMCD , A.QTY
     , A.OUTDT  , GETDATE() , @USERID  , (CASE WHEN B.LOCATION = '1' THEN '9999' ELSE '7777' END)
FROM STOCK_OUT A
        INNER JOIN ORDER_HEADER B
                ON A.ORGDIV = B.ORGDIV
                AND A.ORDNUM = B.ORDNUM
WHERE A.ORGDIV = @ORGDIV
  AND A.RECDT = @OUTDT
  AND A.SEQ1 = @NEWSEQ;
```

- **입고는 방금 쓴 출고 행을 읽어서 만든다.** 같은 스테이징에서 `ROW_NUMBER()`를 두 번 돌려 두 테이블에 따로 INSERT하면 순번이 서로 다르게 붙을 수 있다. 출고를 먼저 쓰고, 입고는 그 행을 업무 키(`RECDT`, `SEQ1`)로 읽어 같은 `SEQ2`를 쓴다.
- `ROW_NUMBER()`의 `ORDER BY`는 실제 업무 키로 쓴다. `ORDER BY @ORGDIV`처럼 모든 행이 같은 값이면 순서가 실행마다 달라진다.
- 창고 코드처럼 조건으로 정해지는 값은 `CASE`로 INSERT 안에서 정한다. 조건 값(요청 사업장 등)이 차수별로 여러 행이면 **최신 차수만** 남긴 파생(`MAX(REVNO)`)을 JOIN한다.
- 같은 파생 블록을 INSERT마다 복사하지 않는다. 뒤 단계는 앞에서 쓴 대상 행을 읽는다.
- 디버그용 `SELECT * FROM @TMP…`를 남기지 않는다. SAVE가 결과표를 돌려주면 화면이 엉뚱한 표를 읽는다.
- 대상 선별이 `TOP 1`이나 `DISTINCT`에 기대고 있으면 키가 중복된다는 뜻이다. 전체 키로 GROUP BY해서 한 행으로 만든다.

삭제는 두 테이블을 함께 지우고, 지우기 전에 **뒤 단계 실적을 깨지 않는지** 수량으로 검증한다.

```sql
IF EXISTS (
           SELECT 1
           FROM (
                 SELECT T1.CODE AS ORDNUM
                      , T1.SEQ1 AS ORDSEQ
                      , SUM(T.QTY) AS DELQTY
                 FROM @TMP_LIST T
                         CROSS APPLY DBO.RETURN_KEYCODE(T.ORDKEY) T1
                 WHERE T.GBN = 'DEL'
                 GROUP BY T1.CODE, T1.SEQ1
                ) A
                   INNER JOIN (
                               SELECT T.ORDNUM
                                    , T.ORDSEQ
                                    , SUM(T.QTY) AS INQTY
                               FROM STOCK_IN T
                               WHERE T.ORGDIV = @ORGDIV
                               GROUP BY T.ORDNUM, T.ORDSEQ
                              ) B
                              ON A.ORDNUM = B.ORDNUM
                              AND A.ORDSEQ = B.ORDSEQ
                   INNER JOIN (
                               SELECT T.ORDNUM
                                    , T.ORDSEQ
                                    , SUM(T.QTY) AS SALEQTY
                               FROM SALES_RESULT T
                               WHERE T.ORGDIV = @ORGDIV
                               GROUP BY T.ORDNUM, T.ORDSEQ
                              ) C
                              ON A.ORDNUM = C.ORDNUM
                              AND A.ORDSEQ = C.ORDSEQ
           WHERE B.INQTY - A.DELQTY < C.SALEQTY
          )
BEGIN
    RAISERROR('매출실적 수량보다 출고수량이 적어질 수 없습니다. 삭제 불가 합니다.', 16, 9);
    RETURN;
END
```

- 비교는 `남는 수량(기존 합계 - 삭제 수량) < 뒤 단계 실적 합계`다. 삭제 수량, 기존 합계, 실적 합계를 **각각 같은 키로 먼저 합산**한 뒤 JOIN한다. 합산 전에 JOIN하면 행이 곱해진다.
- 화면이 표시용 키(`20260129-1`)를 넘기면 `RETURN_KEYCODE`로 분해해서 구성 열로 JOIN한다.
- 마감 검증([kone.md](kone.md))은 삭제하려는 행의 **실제 출고일**로 한다. XML의 일자가 아니라 대상 테이블 행의 일자를 읽는다.
- 출고·입고 삭제는 같은 키 조건으로 두 번 쓴다. 한쪽만 지우는 경로가 없어야 한다.

# 검증 예시

Do not infer a new business validation from an example. Apply only the checks required by the actual operation, with its full keys, units and transaction behavior.

## 검증: Missing related row

Do not remove a valid IF EXISTS check because SELECT/WHERE subqueries are disfavored. IF EXISTS owns the control-flow check; JOIN supplies the related rows.

In this fictional schema PRODUCT_MASTER has a unique, non-null PRODUCT_CODE.

```sql
IF EXISTS (
           SELECT 1
           FROM @TMP_DETAIL A
                   LEFT OUTER JOIN PRODUCT_MASTER B
                                ON A.PRODUCT_CODE = B.PRODUCT_CODE
           WHERE B.PRODUCT_CODE IS NULL
             AND A.CHANGE_STATE <> 'DEL'
          )
BEGIN
    RAISERROR('An input product is not registered.', 16, 9)
    RETURN;
END
```

## 검증: Edited-quantity-proposal

Do not count the current document's persisted contribution twice during EDIT. Do not overlook repeated source keys in the proposed rows or change quantity units to make the comparison easier.

This fictional flow has already validated source receipt existence and units. STOCK_RECEIPT is unique by COMPANY_ID/RECEIPT_NO/RECEIPT_LINE, and each STOCK_ISSUE row consumes that receipt in the same unit. Quantities and document keys, including @DOCUMENT_NO, are non-null in this example. @TMP_PROPOSAL contains the current document's **complete final contribution** after the edit, including retained unchanged rows and excluding deleted rows. Repeated receipt keys in that proposal must be summed. For a target with nullable quantities, establish its actual NULL meaning before comparing; do not silently reinterpret NULL as zero or add an unrequested required-value rule.

```sql
IF EXISTS (
           SELECT 1
           FROM (
                 SELECT T.RECEIPT_NO
                      , T.RECEIPT_LINE
                      , SUM(T.QTY) AS QTY
                 FROM @TMP_PROPOSAL T
                 GROUP BY T.RECEIPT_NO, T.RECEIPT_LINE
                ) A
                   INNER JOIN STOCK_RECEIPT B
                           ON B.COMPANY_ID = @COMPANY_ID
                           AND A.RECEIPT_NO = B.RECEIPT_NO
                           AND A.RECEIPT_LINE = B.RECEIPT_LINE
                   LEFT OUTER JOIN (
                                    SELECT T.COMPANY_ID
                                         , T.RECEIPT_NO
                                         , T.RECEIPT_LINE
                                         , SUM(T.QTY) AS QTY
                                    FROM STOCK_ISSUE T
                                    WHERE T.COMPANY_ID = @COMPANY_ID
                                      AND T.DOCUMENT_NO <> @DOCUMENT_NO
                                    GROUP BY T.COMPANY_ID, T.RECEIPT_NO, T.RECEIPT_LINE
                                   ) C
                                   ON B.COMPANY_ID = C.COMPANY_ID
                                   AND B.RECEIPT_NO = C.RECEIPT_NO
                                   AND B.RECEIPT_LINE = C.RECEIPT_LINE
           WHERE A.QTY + ISNULL(C.QTY, 0) > B.QTY
          )
BEGIN
    RAISERROR('The proposed quantity exceeds the receipt quantity.', 16, 9)
    RETURN;
END
```

Do not apply this whole-document exclusion to a changed-rows-only XML batch: it would also discard the current document's retained persisted rows. Derive that caller's final contribution through its actual full-key/state flow before comparing.

Check equal-to-limit and over-limit proposals, duplicate source keys, retained/deleted rows, the same receipt in another company, and an EDIT with an existing current-document contribution. SQL shape alone does not establish unit or concurrency correctness.

# 호출부와의 계약

- 호출자의 모드 문자열, Added/Modified/Deleted 행 선별, XML TableName과 SAVE 분기·XML 경로(`/ROOT/<TableName>`)를 맞춘다.
- 선택한 마스터 키 전체를 XML에서 UPDATE/DELETE까지 유지한다. 편집 중 상세 삭제, 저장된 문서 삭제, 행별 인쇄와 저장 배치를 구분한다.
- 복합키는 구성 열 전부로 JOIN한다. 키 파싱은 기존 위치에 둔다.
- 채번은 실제 상위 키 범위 안에서 한다. 상세 순번은 INSERT 안에서 파생 MAX + ROW_NUMBER로 매긴다.
- 수량 검증은 전체 연결 키·같은 단위로 비교한다. EDIT에서 자기 문서 수량을 이중 집계하지 않는다.
- 연동을 주석 처리하라는 요청은 원래 본문을 남기고 실행만 막는다.
- 같은 모드의 결과표는 한 분기 안에서 호출자가 읽는 순서대로 반환한다.
