# Allocation and stock moves

Names are fictional. Edited-quantity check: [save-edit.md](save-edit.md#validation-edited-quantity-proposal).

## Allocation INSERT

Allocate stock / earlier receipts to request rows in arrival order with one INSERT, no loop, no intermediate table. Build running start/end quantities per grouping key for the requests (A) and for stock with a remainder (B), and JOIN rows whose ranges overlap. Allocated quantity = `smaller end - larger start`. STOCK_RECEIPT is unique by COMPANY_ID/RECEIPT_NO/RECEIPT_LINE.

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
           , SUM(T.QTY) OVER (PARTITION BY T.ITEM_CODE, T.LOT_NO ORDER BY T.LINE_NO ROWS UNBOUNDED PRECEDING)
             - T.QTY AS START_QTY
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
                         -- START_QTY / END_QTY: same running SUM as A over the remainder
                         -- (T.QTY - ISNULL(T1.ISSUEQTY, 0)), ORDER BY T.RECEIPT_DT, T.RECEIPT_NO, T.RECEIPT_LINE
                    FROM STOCK_RECEIPT T
                            LEFT OUTER JOIN (
                                             SELECT T.RECEIPT_NO
                                                  , T.RECEIPT_LINE
                                                  , SUM(T.QTY) AS ISSUEQTY
                                             FROM STOCK_ISSUE T
                                             WHERE T.COMPANY_ID = @COMPANY_ID
                                             GROUP BY T.RECEIPT_NO, T.RECEIPT_LINE
                                            ) T1
                                            ON T.RECEIPT_NO = T1.RECEIPT_NO
                                            AND T.RECEIPT_LINE = T1.RECEIPT_LINE
                    WHERE T.COMPANY_ID = @COMPANY_ID
                      -- 입고수량 > 누적출고수량
                      AND T.QTY > ISNULL(T1.ISSUEQTY, 0)
                   ) B
                   ON A.ITEM_CODE = B.ITEM_CODE
                   AND A.LOT_NO = B.LOT_NO
                   AND A.START_QTY < B.END_QTY
                   AND B.START_QTY < A.END_QTY
```

Then an `IF EXISTS` raises `RAISERROR('The stock is not enough for the requested quantity.', 16, 1); RETURN;` when a detail's `QTY` differs from its allocated sum (STOCK_ISSUE summed by LINE_NO, LEFT OUTER JOIN, `ISNULL(…, 0)`). Short stock makes the sum smaller, the check fails and `ExecSPTrn` rolls back. To reallocate only some rows in EDIT, add those rows' business-key condition to A (e.g. rows without issues yet). Test 2 request rows with the same key, allocation across several stock rows, short stock, the same LOT in another company.

## Stock move (issue + receipt in one save)

One save writes **paired rows** into the issue and receipt tables. Stock ledgers read both, so a broken pair corrupts stock.

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
                         -- REQUEST_REV latest revision only: INNER JOIN its MAX(REVNO) per ORDNUM, ORDSEQ
                         -- (same shape as the MAX(RVNO) derived table in complex-select.md)
                        ) B
                        ON A.ORDNUM = B.ORDNUM
                        AND A.ORDSEQ = B.ORDSEQ
WHERE A.CHK = 'Y';

INSERT INTO STOCK_IN
(
       ORGDIV   , RECDT   , SEQ1   , SEQ2
     , STORAGE
)
SELECT A.ORGDIV , A.RECDT , A.SEQ1 , A.SEQ2
     , (CASE WHEN B.LOCATION = '1' THEN '9999' ELSE '7777' END)
FROM STOCK_OUT A
        INNER JOIN ORDER_HEADER B
                ON A.ORGDIV = B.ORGDIV
                AND A.ORDNUM = B.ORDNUM
WHERE A.ORGDIV = @ORGDIV
  AND A.RECDT = @OUTDT
  AND A.SEQ1 = @NEWSEQ;
```

- **Build the receipt from the issue rows just written**, read by business key (`RECDT`, `SEQ1`), so it gets the same `SEQ2`. Running `ROW_NUMBER()` twice over the same staging can number the two tables differently.
- `ROW_NUMBER()`'s `ORDER BY` uses real business keys. `ORDER BY @ORGDIV` (same value for all rows) gives a different order each run.
- Values decided by a condition (warehouse code) are set by `CASE` inside the INSERT. If the condition value has several revisions, JOIN a derived table keeping **only the latest** (`MAX(REVNO)`).
- Do not copy the same derived block into each INSERT; later steps read rows written earlier.
- Do not leave debug `SELECT * FROM @TMP…`: the screen would read the wrong result set.
- Target selection relying on `TOP 1` / `DISTINCT` means duplicated keys. GROUP BY the full key.

Delete both tables together with the same key condition (no path may delete only one). Before deleting, check by quantity that **later results stay valid**.

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
                               -- SALES_RESULT summed the same way: SUM(T.QTY) AS SALEQTY
                              ) C
                              ON A.ORDNUM = C.ORDNUM
                              AND A.ORDSEQ = C.ORDSEQ
           -- 기존 입고수량 - 삭제수량 < 매출실적수량
           WHERE B.INQTY - A.DELQTY < C.SALEQTY
          )
BEGIN
    RAISERROR('매출실적 수량보다 출고수량이 적어질 수 없습니다. 삭제 불가 합니다.', 16, 9);
    RETURN;
END
```

- Compare `remaining (existing total - deleted) < later results total`. Sum deleted, existing and result quantities **each by the same key first**, then JOIN. JOINing before summing multiplies rows.
- If the screen sends a display key (`20260129-1`), split it with `RETURN_KEYCODE` and JOIN on the components.
- The closing check ([kone.md](kone.md#f_check_close)) uses the **actual issue date** of the target table rows, not the XML date.
