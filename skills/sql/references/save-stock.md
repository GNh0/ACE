# Allocation and quantity limits

Names are fictional. Stock moves (issue + receipt pairs): erp [domain-erp.md](../../erp/references/domain-erp.md).

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

Then an `IF EXISTS` raises `RAISERROR('The stock is not enough for the requested quantity.', 16, 1); RETURN;` when a detail's `QTY` differs from its allocated sum (STOCK_ISSUE summed by LINE_NO, LEFT OUTER JOIN, `ISNULL(…, 0)`). Short stock makes the sum smaller, the check fails and `SaveTrn` rolls back. To reallocate only some rows in EDIT, add those rows' business-key condition to A (e.g. rows without issues yet). Test 2 request rows with the same key, allocation across several stock rows, short stock, the same LOT in another company.

## Validation: edited-quantity proposal

Do not count the current document's persisted contribution twice during EDIT. Do not overlook repeated source keys in the proposal or change quantity units to make the comparison easier. Here @TMP_PROPOSAL holds the current document's **complete final contribution** after the edit (retained rows included, deleted rows excluded); repeated receipt keys are summed. Units and receipt existence are already validated; quantities and keys are non-null. For nullable quantities, establish the actual NULL meaning first; do not silently treat NULL as zero or add an unrequested required-value rule.

Shape: A = @TMP_PROPOSAL summed by receipt key (`AS PROPQTY`), INNER JOIN STOCK_RECEIPT B on `B.COMPANY_ID = @COMPANY_ID` and the receipt key, LEFT OUTER JOIN C = STOCK_ISSUE of **other documents only**, summed by receipt key:

```sql
                   LEFT OUTER JOIN (
                                    SELECT T.RECEIPT_NO
                                         , T.RECEIPT_LINE
                                         , SUM(T.QTY) AS ISSUEQTY
                                    FROM STOCK_ISSUE T
                                    WHERE T.COMPANY_ID = @COMPANY_ID
                                      AND T.DOCUMENT_NO <> @DOCUMENT_NO
                                    GROUP BY T.RECEIPT_NO, T.RECEIPT_LINE
                                   ) C
                                   ON B.RECEIPT_NO = C.RECEIPT_NO
                                   AND B.RECEIPT_LINE = C.RECEIPT_LINE
           -- 이번 제안수량 + 다른 문서 출고수량 > 입고수량
           WHERE A.PROPQTY + ISNULL(C.ISSUEQTY, 0) > B.QTY
```

then `RAISERROR('The proposed quantity exceeds the receipt quantity.', 16, 1) RETURN;`.

Do not apply this whole-document exclusion to a changed-rows-only XML batch: it would discard the document's retained rows. Derive that caller's final contribution through its full-key/state flow first. Check equal-to-limit and over-limit, duplicate source keys, retained/deleted rows, the same receipt in another company, and EDIT with an existing contribution. SQL shape alone does not prove unit or concurrency correctness.
