# KONE project common functions and SPs

Common objects that 근호/KH SPs call in C_KONE DBs (C_KONE060, C_KONE110 …). In other DBs first check the same name exists with the same arguments. Do not change the common objects themselves unless asked.

| Object | Kind | Used for |
| --- | --- | --- |
| `SP_XML_LOG_SAVE` | SP | First executable statement of every SAVE |
| `SP_SYSTEM_BA100T_KEYCODE` | SP | Document numbering |
| `RETURN_KEYCODE` | table function | Split a screen display key into the composite key |
| `F_CHECK_CLOSE` | scalar function | Year/month closing check |
| `F_FIND_USERNM` | scalar function | User name |
| `F_BA011T_FIND_SUBNM` | scalar function | Common-code name. Only in existing code; new code JOINs `BA011T` |

## SP_XML_LOG_SAVE

Logs the XML a SAVE received. Put it right after `SET NOCOUNT ON`. Pass every XML argument.

```sql
EXEC SP_XML_LOG_SAVE @@PROCID, @WORKTYPE, @USERID, @XML, @XMLDETAIL;
```

## SP_SYSTEM_BA100T_KEYCODE

Returns the next sequence per base date as OUTPUT. Arguments: business unit, table kind, base date (YYYYMMDD), sequence (OUTPUT). EXEC arguments cannot be expressions, so base date and sequence are variables.

```sql
EXEC SP_SYSTEM_BA100T_KEYCODE @ORGDIV, 'BA100T', @DOCDT, @NEWSEQ OUTPUT;

SET @DOCNUM = @DOCDT + '-' + CONVERT(VARCHAR(10), @NEWSEQ);
```

- The table kind value follows the existing SAVE of the same business.
- Only the header number comes from this SP. Detail sequences: derived MAX + `ROW_NUMBER()` inside the INSERT.
- Do not compute sequences on the screen and pass them.
- **Never UPDATE/INSERT the numbering table (`BA100T`) directly from an SP.** Numbers always come from this common SP. Do not bypass it to remove a loop.
- If one save needs several document numbers (a different number per row), use a small loop that runs only the numbering `EXEC`. This is the exception to "no row-by-row loops": the loop holds only the numbering call and the statement recording the number into staging; the real INSERT/UPDATE/DELETE run set-based outside it. Say in the answer why the loop stays.

## RETURN_KEYCODE

Splits one display key like `20260129-1-11` from the screen into `CODE`, `SEQ1`, `SEQ2`. With one hyphen, `SEQ2` is NULL.

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

- Never compare keys by concatenating strings (`A.RECDT + '-' + CONVERT(…) = B.KEYCODE`). Split and JOIN on all components.

## F_CHECK_CLOSE

`F_CHECK_CLOSE(@ORGDIV, module, period kind, period, '1')` returns the closing state.

- Module: business module code such as `'MA'` (materials). Follow the existing SAVE of the same business.
- Period kind: `'1'` year closing (period `LEFT(date, 4)`), `'2'` month closing (period `LEFT(date, 6)`).
- Returns `''` no closing info, `'Y'` closed, anything else = may proceed.

A SAVE affecting stock checks these four in order before writing, with the same messages and `16, 9` as existing SAVEs:

| Call | Result | Message |
| --- | --- | --- |
| `F_CHECK_CLOSE(@ORGDIV, 'MA', '1', LEFT(A.OUTDT, 4), '1')` | `''` | `년마감 정보가 없습니다. 년/월마감 프로그램에서 년마감 정보를 생성한 후 처리 가능합니다.` |
| same | `'Y'` | `년 마감이 완료되었습니다. 년/월마감 프로그램에서 년마감 해제 후 처리 가능합니다.` |
| `F_CHECK_CLOSE(@ORGDIV, 'MA', '2', LEFT(A.OUTDT, 6), '1')` | `''` | `월마감 정보가 없습니다. 년/월마감 프로그램에서 월마감 정보를 생성한 후 처리 가능합니다.` |
| same | `'Y'` | `월 마감이 완료되었습니다. 년/월마감 프로그램에서 월마감 해제 후 처리 가능합니다.` |

Each is one block of this form:

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
```

- The checked date is the date the stock movement is booked on (receipt date, issue date …). For edits, check whether the date before and after the change can differ.

## Name lookup

User name by function, common-code name by JOIN:

| Name | Method |
| --- | --- |
| User name (registrant, modifier, person in charge …) | **Function** `DBO.F_FIND_USERNM(user ID)` |
| Common-code name (process name, kind name …) | **JOIN** `BA011T`. Do not newly use `F_BA011T_FIND_SUBNM` |

```sql
SELECT A.DOCNUM
     , B.SUBNM AS PROCNM
     , DBO.F_FIND_USERNM(A.REGEMPNO) AS REGEMPNM
FROM DOC_HEADER A
        LEFT OUTER JOIN BA011T B
                     ON B.MAINCD = 'PR001'
                     AND A.PROCCD = B.SUBCD
WHERE A.ORGDIV = @ORGDIV
```

- LEFT OUTER JOIN `BA011T` on `MAINCD = 'code kind'` and the code value. PK is `(MAINCD, SUBCD)`, so rows do not multiply. Several code kinds: one JOIN per kind with separate aliases (`B`, `B1`).
- User names appear several times per query (registrant, modifier). A JOIN per name repeats the same table, so the **final result shown on screen** uses the function.
- **The function is slower than a JOIN.** Use it only in the **outermost SELECT list**, on final result rows (usually thousands to tens of thousands). Never inside derived tables scanning large tables, before aggregation, or in WHERE/GROUP BY/ORDER BY. Queries returning or aggregating hundreds of thousands of rows (stock ledger, status totals) JOIN user names too.
- When JOINing user names check row counts. `BA095T`'s PK is `(USERID, PRSNNUM)`; `USERID` is unique today but the PK does not guarantee it.
- Also JOIN when other user-table columns are needed or the business unit (`ORGDIV`) must match; `F_FIND_USERNM` searches by user ID only.
- Do not swap existing function calls and JOINs unless asked.

Measured (C_KONE110, SQL Server 2019, 2026-11-20, one name over all ~580k receipt rows): JOIN ~0.08 s; function (inlined, default) ~1.1 s; two functions (registrant + modifier) ~2.3 s vs two JOINs ~0.09 s; function with inlining off ~13.7 s. For 1,000 rows both took 0.2–0.3 s. On servers without inlining (2017 or older, or `SYS.SQL_MODULES.IS_INLINEABLE = 0`) the function is far slower, so JOIN is the default there.
