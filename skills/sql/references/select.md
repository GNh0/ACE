# SELECT patterns

## SELECT contract

| Changing part | Form |
| --- | --- |
| Display names, business eligibility | Rows that must stay without a description: LEFT OUTER JOIN. Required eligibility rows: INNER JOIN. If a key has several rows, check the returned unit before JOINing |
| Detail totals per header | GROUP BY the detail on the full header key first, then JOIN (like the derived JOIN in [style.md](style.md#derived-join-and-union-examples)). Do not replace missing totals with 0 without the user's instruction |
| Excluding processed rows | LEFT OUTER JOIN the processing table on the full key, then `IS NULL` on a non-null key |
| Only rows that exist (WHERE EXISTS / IN subquery) | [EXISTS → JOIN](#exists--join): JOIN a derived table grouped by the link key; one row per key, so rows do not multiply |
| Several results in one mode | SELECTs in one branch in the caller's result order. Keep shared processing and other modes' conditions in their original scope |

Names below are fictional.

## Lookup and eligibility

Approved orders only, keeping approved orders without a customer description. At most one approval per company/order.

```sql
SELECT A.ORDER_NO
     , B.CUSTOMER_NAME
     , A1.APPROVED_AT
FROM ORDER_HEADER A
        INNER JOIN ORDER_APPROVAL A1
                ON A.COMPANY_ID = A1.COMPANY_ID
                AND A.ORDER_NO = A1.ORDER_NO
                AND A1.APPROVAL_STATE = 'APPROVED'
        LEFT OUTER JOIN CUSTOMER_MASTER B
                     ON A.COMPANY_ID = B.COMPANY_ID
                     AND A.CUSTOMER_ID = B.CUSTOMER_ID
WHERE A.COMPANY_ID = @COMPANY_ID
  AND A.ORDER_DATE BETWEEN @FROM_DATE AND @TO_DATE
```

## Exclusion JOIN

Documents not yet posted. The processing key's document number is non-null.

```sql
SELECT A.DOCUMENT_NO
FROM DOCUMENT_HEADER A
        LEFT OUTER JOIN POSTED_DOCUMENT A1
                     ON A.COMPANY_ID = A1.COMPANY_ID
                     AND A.DOCUMENT_NO = A1.DOCUMENT_NO
WHERE A.COMPANY_ID = @COMPANY_ID
  AND A1.DOCUMENT_NO IS NULL
```

## EXISTS → JOIN

Convert EXISTS/IN subqueries in WHERE to JOINs, including existing ones, when asked to change or review. A "cleanup only" request does not change meaning: leave them and propose. SAVE's `IF EXISTS` checks are not WHERE subqueries and stay ([save.md](save.md#validation-missing-related-row)).

1. Equalities comparing with the outer row (`T.KEY = A.KEY`) are the link keys. Move the other conditions into the derived table's WHERE.
2. GROUP BY the link keys: one row per key, so INNER JOIN does not multiply outer rows. That is why the result equals EXISTS.
3. If the correlated condition has `OR` with different link keys per branch, make one derived table per branch, LEFT OUTER JOIN each, and combine in WHERE with `(B.key IS NOT NULL OR B1.key IS NOT NULL)`. Same source → same letter with numbers (B, B1).
4. A non-equality comparison with the outer row (`>=` …): include the compared value as a GROUP BY key or aggregate and compare in ON. Keep EXISTS only when that is impossible, and say why.
5. After converting, check against the original that every condition moved (none lost or duplicated).

```sql
SELECT A.ORDNUM
     , A.ITEMCD
FROM WORK_PLAN A
        LEFT OUTER JOIN (
                         SELECT T.ITEMCD
                         FROM WORK_RESULT T
                         WHERE T.PROCCD = '00'
                           AND T.FINYN = 'Y'
                         GROUP BY T.ITEMCD
                        ) B
                        ON A.ITEMCD = B.ITEMCD
        LEFT OUTER JOIN (
                         SELECT T.ORDNUM
                              , T.ITEMCD
                         FROM WORK_RESULT T
                         WHERE T.FINYN = 'Y'
                         GROUP BY T.ORDNUM, T.ITEMCD
                        ) B1
                        ON A.ORDNUM = B1.ORDNUM
                        AND A.ITEMCD = B1.ITEMCD
WHERE (B.ITEMCD IS NOT NULL OR B1.ITEMCD IS NOT NULL)
```

The original was `EXISTS (SELECT 1 FROM WORK_RESULT T WHERE T.ITEMCD = A.ITEMCD AND T.FINYN = 'Y' AND (T.PROCCD = '00' OR T.ORDNUM = A.ORDNUM))`. Without `OR`, INNER JOIN one derived table.

## One branch with multiple results

This caller reads 1 result set for LIST and 2 (header, detail) for DETAIL, in that order.

```sql
IF @WORKTYPE = 'LIST'
BEGIN
    SELECT A.ORDER_NO
    FROM ORDER_HEADER A
    WHERE A.COMPANY_ID = @COMPANY_ID
END
ELSE IF @WORKTYPE = 'DETAIL'
BEGIN
    SELECT A.ORDER_NO
    FROM ORDER_HEADER A
    WHERE A.COMPANY_ID = @COMPANY_ID
      AND A.ORDER_NO = @ORDER_NO

    SELECT A.LINE_NO
         , A.QTY
    FROM ORDER_DETAIL A
    WHERE A.COMPANY_ID = @COMPANY_ID
      AND A.ORDER_NO = @ORDER_NO
    ORDER BY A.LINE_NO
END
```
