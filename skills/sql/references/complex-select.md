# Complex SELECT

Shapes for structurally complex queries such as BOM expansion and monthly pivots, taken from the user's real SPs (BOM reverse expansion, process defect rate); names are fictional. Stock ledger / stock queries are not here yet (no reference SP received).

The more complex the query, the more you must first write **what one result row is** (one item? item × month? document × process?) and check each derived table keeps that unit. One derived table that multiplies rows breaks every later total.

## BOM expansion / reverse expansion

```sql
SELECT B.PARENTID
     , B.ID
     , B.ITEMCD
     , C.ITEMNM
FROM (
      SELECT T.PRNTITEMCD
      FROM BOM_DETAIL T
              INNER JOIN (
                          SELECT T.PRNTITEMCD
                               , MAX(T.RVNO) AS MAXRVNO
                          FROM BOM_REVISION T
                          GROUP BY T.PRNTITEMCD
                         ) T1
                         ON T.PRNTITEMCD = T1.PRNTITEMCD
                         AND T.RVNO = T1.MAXRVNO
      WHERE T.CHLDITEMCD = @ITEMCD
      GROUP BY T.PRNTITEMCD
     ) A
        CROSS APPLY DBO.ITEMBOMTREE(A.PRNTITEMCD) B
        LEFT OUTER JOIN ITEM_MASTER C
                     ON B.ITEMCD = C.ITEMCD
ORDER BY B.PARENTID, B.SORTKEY;
```

- For hierarchy expansion do not write a new recursive CTE; `CROSS APPLY` the project's **existing table function** (`ITEMBOMTREE` …). Check its real return columns and sort key in its definition.
- **Latest revision only**: JOIN a derived table grouping the revision table by item with `MAX(RVNO)`. Without it, children of old revisions appear.
- Reverse expansion (child → parent): first build the list of parents having the start item as child (derived A), then expand those parents.
- Results bound to a tree grid return parent key, own key and sort key (`PARENTID`, `ID`, `SORTKEY`) unchanged; the screen's TreeList uses these names.
- Required quantity is the unit quantity multiplied per level. Check whether the function returns cumulative or per-level quantity; avoid multiplying twice.

## Monthly pivot

Rows are kinds (production qty, defect qty, defect rate); columns are months (01–12, TOTAL).

```sql
SELECT P.GBCD
     , P.GBNM
     , P.[01] AS MON01
     , P.[TOTAL] AS TOTAL
FROM (
      SELECT A2.GBCD
           , A2.GBNM
           , A.MON
           , A2.VAL
      FROM (
            VALUES ('01'), ('02'), ('TOTAL')
           ) A(MON)
              LEFT OUTER JOIN (
                               SELECT (CASE WHEN GROUPING(T.MON) = 1 THEN 'TOTAL' ELSE T.MON END) AS MON
                                    , SUM(T.BADQTY) AS BADQTY
                                    , SUM(T.PRODQTY) AS PRODQTY
                               FROM (
                                     SELECT SUBSTRING(T.RECDT, 5, 2) AS MON
                                          , SUM(T.BADQTY) AS BADQTY
                                          , 0 AS PRODQTY
                                     FROM BAD_RESULT T
                                     WHERE T.ORGDIV = @ORGDIV
                                     GROUP BY SUBSTRING(T.RECDT, 5, 2)

                                     UNION ALL

                                     -- PROD_RESULT by month the same way: 0 AS BADQTY, SUM(T.QTY) AS PRODQTY
                                    ) T
                               GROUP BY ROLLUP(T.MON)
                              ) A1
                              ON A.MON = A1.MON
              CROSS APPLY (
                           VALUES ('A', '생산수량', A1.PRODQTY)
                                , ('B', '불량수량', A1.BADQTY)
                                , ('C', '불량율(%)', CONVERT(NUMERIC(18, 1), A1.BADQTY / NULLIF(A1.PRODQTY, 0) * 100.0))
                          ) A2(GBCD, GBNM, VAL)
     ) A
PIVOT (
       MAX(VAL)
       FOR MON IN ([01], [02], [TOTAL])
      ) P
ORDER BY P.GBCD;
```

Read from inside out:

1. **UNION ALL per-source monthly totals**: values from different sources (defects, production) get the same column layout, with 0 for the other source's column. Do not JOIN the sources (rows multiply).
2. **`GROUP BY ROLLUP`** makes the total row; `GROUPING()` turns its month into `'TOTAL'`.
3. **Month list as a `VALUES` derived table** `A(MON)`, LEFT OUTER JOIN the totals, so months without data still get columns.
4. **`CROSS APPLY (VALUES …)`** spreads one month into several rows (production, defects, rate). The kind code (`GBCD`) is the sort key.
5. **PIVOT** `MAX(VAL) FOR MON IN (…)`. The outer SELECT names columns for the screen FieldName (`P.[01] AS MON01`).

Keep in mind:

- **Divide totals by totals.** The TOTAL defect rate is `total defects / total production`, not a sum or average of monthly rates. This structure recomputes it on the ROLLUP row, so it is right.
- Guard the denominator with `NULLIF(…, 0)`. Replace a NULL result with 0 only on user request.
- If a chart needs a separate result, return the pre-PIVOT shape (kind, month, value) as a second result set in the same branch, in the order the screen reads.
- With a fixed 12 months use static PIVOT. Dynamic SQL only when columns are decided at run time, and say why.

## Search condition arguments

A query taking the screen's search-type combo (`@TYPE`) and search text (`@TEXT`) returns everything when the condition is empty.

```sql
WHERE A.ORGDIV = @ORGDIV
  AND ((ISNULL(@TYPE, '') = '' OR ISNULL(@TEXT, '') = '' AND 1 = 1)
       OR (ISNULL(@TYPE, '') = 'ITEM' AND (ISNULL(A.ITEMCD, '') LIKE '%' + ISNULL(@TEXT, '') + '%'
                                            OR ISNULL(B.ITEMNM, '') LIKE '%' + ISNULL(@TEXT, '') + '%'))
       OR (ISNULL(@TYPE, '') = 'INSIZ' AND ISNULL(F.CNT, 0) >= 1))
```

Match `@TYPE` values to the combo's real codes (`cboSelectType.MainCode` = the screen ID in MS011T); the screen passes `@TYPE`/`@TEXT` last. This is the PROJECT_B form (25 of 34 SELECT SPs): both the column and `@TEXT` wrapped in ISNULL.

- Searching detail rows from a header list: a derived table filters the detail table by `@TYPE`/`@TEXT`, groups by the header key with `COUNT(T.ORGDIV) AS CNT`, LEFT OUTER JOINs on the header key, and the combo tests `ISNULL(F.CNT, 0) >= 1` (XD000700, XS100100, XS200100, XS800100). This replaces `EXISTS`.
- Optional prefix filters: `AND A.X LIKE ISNULL(@X, '') + '%'` (30 uses in 11 SPs); not `@X = '' OR A.X = @X`.
- Date-type switch: `AND ((@DTGB = 'A' AND A.ORDDT BETWEEN @FRDT AND @TODT) OR (@DTGB = 'B' AND A.DLVDT BETWEEN @FRDT AND @TODT))` (9 SPs); the screen fills `cboDTGB` with CODE/NAME rows.
- Display dates: `TRY_CONVERT(DATE, NULLIF(A.X, ''), 112) AS X` (every SELECT created after 2026-06-15; older `CONVERT(DATE, A.X)`).
- Attachments: a SY905T derived table grouped by DATNUM giving `COUNT(T.DATNUM) AS ATTCNT` (and `STRING_AGG(T.REALNM, ', ')` for names).
- Done marks: `(CASE WHEN ISNULL(G.INDT, '') <> '' THEN '○' ELSE '' END) AS PRODFINYN`.
