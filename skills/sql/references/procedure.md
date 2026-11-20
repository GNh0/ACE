# Procedure skeleton: header, SELECT SP, CASE

Taken from real SPs by 근호/KH. Table and column names are fictional; take real arguments, types and XML paths from the caller and schema. SAVE skeleton: [procedure-save.md](procedure-save.md).

## Procedure header

A new SP uses this header. Author: the one name you confirmed with the user. Date: first creation date. Description: program name + `처리` (SAVE) or `조회` (SELECT). Change an existing SP's author/creation date only when the user asks.

```sql
-- =============================================
-- AUTHOR:      {작성자명}
-- CREATE DATE: {첫작성일}
-- DESCRIPTION: {프로그램명} 처리OR조회
-- =============================================
```

## SELECT SP

```sql
CREATE PROCEDURE [dbo].[sp_XX000100_SELECT]
      @WORKTYPE VARCHAR(20) = NULL
    , @ORGDIV   VARCHAR(2)  = NULL
    , @FRDT     VARCHAR(8)  = NULL
    , @TODT     VARCHAR(8)  = NULL
    , @DOCNUM   VARCHAR(20) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @WORKTYPE = 'LIST'
    BEGIN
        SELECT 'N' AS CHK
             , A.DOCNUM
             , B.ITEMNM
        FROM DOC_HEADER A
                LEFT OUTER JOIN ITEM_MASTER B
                             ON A.ITEMCD = B.ITEMCD
        WHERE A.ORGDIV = @ORGDIV
          AND A.DOCDT BETWEEN @FRDT AND @TODT
        ORDER BY A.DOCDT DESC, A.DOCNUM;
    END
    ELSE IF @WORKTYPE = 'DETAIL'
    BEGIN
        SELECT A.SEQ
             , A.ITEMCD
             , A.QTY
        FROM DOC_DETAIL A
        WHERE A.ORGDIV = @ORGDIV
          AND A.DOCNUM = @DOCNUM
        ORDER BY A.SEQ;
    END
END;
```

- One argument per line, leading commas; align the start of name, type and default. SELECT arguments default to `= NULL`.
- `@WORKTYPE` values are the member names of the C# screen's `enum SelectType` (`_selectType.ToString()`).
- One `IF … ELSE IF` branch per mode. A mode with several result sets keeps them in one branch in the order C# reads them.
- A list that needs a check column has `'N' AS CHK` as the first column.

## Screen arguments and output

- Keep the existing template and call contract: `@WORKTYPE`/`@ORGDIV` of screen SPs, NULL defaults of optional arguments.
- Match length, Unicode, precision, scale and NULL from the real schema → arguments/XML/staging → result → caller.
- Display digits belong to the screen. Convert calculation types only when the consumer needs it. Check the widened type SUM returns.
- Compare binding names, returned columns and SP arguments one by one with the C# caller.
- Server save time follows the existing GETDATE() style.

## CASE

Short: one line. Long: align WHEN/ELSE/END one column after CASE. Wrap the whole CASE in parentheses.

```sql
UPDATE A
SET A.PLANTIME = (CASE WHEN A.QTY = 0 THEN A.PLANTIME
                       ELSE ROUND(A.PLANTIME / A.QTY, 0) * B.PLANQTY
                  END)
  , A.QTY = B.PLANQTY
FROM DOC_HEADER A
        INNER JOIN @TMP_DETAIL B
                ON A.DOCNUM = B.DOCNUM
WHERE A.ORGDIV = @ORGDIV
```

```sql
SELECT B.ITEMNM + (CASE WHEN B.SPEC IS NULL OR B.SPEC = '' THEN '' ELSE ' ' + B.SPEC END) AS ITEMNM
```
