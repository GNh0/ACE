# ERP domain: stock moves

Business-flow rules from framework ERP SAVEs (receipt/issue tables, stock ledgers). Generic SAVE rules: sql skill [save.md](../../sql/references/save.md); set-based allocation: [save-stock.md](../../sql/references/save-stock.md#allocation-insert). Names are fictional.

## Stock move (issue + receipt in one save)

One save writes **paired rows** into the issue and receipt tables. Stock ledgers read both, so a broken pair corrupts stock.

```sql
EXEC SP_NEW_KEY @ORGDIV, 'SY100T', @OUTDT, @NEWSEQ OUTPUT;

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
                         CROSS APPLY DBO.F_SPLIT_KEY(T.ORDKEY) T1
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
    RAISERROR('매출실적 수량보다 출고수량이 적어질 수 없습니다. 삭제 불가 합니다.', 16, 1);
    RETURN;
END
```

- Compare `remaining (existing total - deleted) < later results total`. Sum deleted, existing and result quantities **each by the same key first**, then JOIN. JOINing before summing multiplies rows.
- If the screen sends a display key (`20260129-1`), split it with `F_SPLIT_KEY` and JOIN on the components.
- The closing check ([common-sp.md](common-sp.md#f_is_closed)) uses the **actual issue date** of the target table rows, not the XML date.
