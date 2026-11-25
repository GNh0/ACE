# INSERT grid and condition comments

## INSERT column grid

INSERT columns and SELECT/VALUES values match in order, line groups and real start column. The column and value with the same position start at the same place; each cell is padded to the longer of its column and value. **A long value (30+ characters: expression, CASE, ROW_NUMBER…) is the last item on its line; the next column starts on the next line.** The INSERT column list breaks at the same place. Never put a long value alone on a line, and never push other lines' columns dozens of spaces to fit one long value. `check_sql.py` checks one-line column lists, one-cell lines and 20+ space gaps.

```sql
    INSERT INTO TARGET
    (
           ORGDIV   , DOCNO  , SEQ
         , ITEMCD   , QTY    , UNITWGT
         , TOTWGT
    )
    SELECT @ORGDIV  , @DOCNO , ISNULL(C.SEQ, 0) + ROW_NUMBER() OVER (ORDER BY A.SEQ)
         , A.ITEMCD , A.QTY  , A.UNITWGT
         , A.QTY * A.UNITWGT * (CASE WHEN A.WGTUNIT = 'G' THEN 0.001 ELSE 1 END)
    FROM SOURCE A
```

Not this (long value mid-line, other cells pushed apart):

```sql
    SELECT @ORGDIV , @DOCNO    , ISNULL(C.SEQ, 0) + ROW_NUMBER() OVER (ORDER BY A.SEQ) , A.ITEMCD
         , A.QTY   , A.UNITWGT , A.QTY * A.UNITWGT                                      , GETDATE()
```

- Do not put a long value alone on its own line, leaving a one-cell line (`, SEQ`) in the column list. Keep it at the end of a line with the items before it.
- If that exceeds 120 characters, do not split the value over two lines; make the expression shorter (e.g. a staging table variable with `SEQ INT IDENTITY(1, 1)` and `ROW_NUMBER() OVER (ORDER BY A.SEQ)`). Paired rows in two tables numbered by the same `A.SEQ` match. Do not remove an existing `SEQ IDENTITY` from the original SP.
- Remove gaps already widened by a long value by breaking lines as above. With multi-line expressions or comments, check each column/value's meaning and start column in the final text.

## Condition comments

Quantity/state comparisons, check conditions and key target-selection conditions get a one-line comment **directly above, saying what the condition means in business terms**. The reader must see **which quantity each term is**.

A comment alone is not enough: when both sides are `QTY`, the expression still does not show which is receipt and which is issue.

```sql
-- 쓰지 않는 형태: 양쪽 다 QTY라서 무슨 수량인지 알 수 없다
  -- 이전공정 입고수량 > 누적불출수량
  AND T.QTY > ISNULL(T1.QTY, 0)
```

So do both:

1. (checked) **Give aggregate columns in derived tables a name that says which quantity**: not `SUM(T.QTY) AS QTY` but `AS OUTQTY` (issue), `AS INQTY` (receipt), `AS PRODQTY` (production), `AS PURQTY` (purchase).
2. **Write the comment in the same order and with the same comparison operator as the expression**: left term's name on the left, right term's on the right.

```sql
FROM XM210T T
        LEFT OUTER JOIN (
                         SELECT T.ORGDIV
                              , T.INRECDT
                              , SUM(T.QTY) AS OUTQTY
                         FROM XS210T T
                         WHERE T.ORGDIV = @ORGDIV
                         GROUP BY T.ORGDIV, T.INRECDT
                        ) T1
                        ON T.ORGDIV = T1.ORGDIV
                        AND T.RECDT = T1.INRECDT
WHERE T.ORGDIV = @ORGDIV
  -- 이전공정 입고수량 > 누적불출수량
  AND T.QTY > ISNULL(T1.OUTQTY, 0)
```

- Base table columns (`T.QTY`, `B.QTY`) cannot be renamed, so the comment says which table's quantity they are; derived columns say it by name.
- (checked) If `QTY` appears twice in one comparison, rename the derived column.
- The comment has the **same indentation** as its condition, directly above it, never at the line end.
- A check block has the "pass condition" (`<=`) above the block and the "error condition" (`>`) on the deciding line, e.g. `-- 입고키별 이번 발주수량 + 기존 누적불출수량 <= 입고수량` above `IF EXISTS` and `-- 이번 발주수량 + 기존 누적불출수량 > 입고수량` above `WHERE A.PURQTY + ISNULL(C.OUTQTY, 0) > B.QTY`.
- No comment on simple key conditions (`A.ORGDIV = @ORGDIV`, JOIN key equality); only on comparisons, calculations and exclusions whose meaning is not obvious.
- In a multi-statement SAVE, put a one-line comment at each major step (`-- 발주 상세: 선택한 입고 LOT 행마다 1행`).
- Do not delete or rewrite existing comments. If you change a condition, update its comment.
- Output columns that reach the screen must match its FieldName, so this rule does not rename them; rename the inner derived columns.
