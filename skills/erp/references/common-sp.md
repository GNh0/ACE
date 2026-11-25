# framework project common functions and SPs

Common objects that the user's SPs call in PROJECT_ DBs (PROJECT_C, PROJECT_B …). In other DBs first check the same name exists with the same arguments. Do not change the common objects themselves unless asked.

| Object | Kind | Used for |
| --- | --- | --- |
| `SP_LOG_XML` | SP | First executable statement of every SAVE |
| `SP_NEW_KEY` | SP | Document numbering |
| `F_SPLIT_KEY` | table function | Split a screen display key into the composite key |
| `F_IS_CLOSED` | scalar function | Year/month closing check |
| `F_FIND_USERNM` | scalar function | User name (existing SPs only; new code JOINs `MS095T`) |
| `F_CODE_NAME` | scalar function | Common-code name. Only in existing code; new code JOINs `MS011T` |

## SP_LOG_XML

Logs the XML a SAVE received. Put it right after `SET NOCOUNT ON`. Pass every XML argument.

```sql
EXEC SP_LOG_XML @@PROCID, @WORKTYPE, @USERID, @XML, @XMLDETAIL;
```

## SP_NEW_KEY

Returns the next sequence per base date as OUTPUT. Arguments: business unit, table kind, base date (YYYYMMDD), sequence (OUTPUT). EXEC arguments cannot be expressions, so base date and sequence are variables.

```sql
EXEC SP_NEW_KEY @ORGDIV, 'SY100T', @DOCDT, @NEWSEQ OUTPUT;

SET @DOCNUM = @DOCDT + '-' + CONVERT(VARCHAR(10), @NEWSEQ);
```

- The table kind value follows the existing SAVE of the same business.
- Only the header number comes from this SP. Detail sequences: derived MAX + `ROW_NUMBER()` inside each INSERT … SELECT (LEFT OUTER JOIN the MAX derived table, `ISNULL(D.MAXSEQ, 0) + ROW_NUMBER() OVER (ORDER BY A.SEQ)`; name the MAX column `MAX<col>` (`MAXSEQ`, `MAXSEQ2`); when one XML carries several parents, `ROW_NUMBER() OVER (PARTITION BY A.<parent key> ORDER BY A.SEQ)`). When two tables share the sequence, each INSERT computes it the same way with the same `ORDER BY A.SEQ`. Never precompute it with an `UPDATE` of the staging table; (checked) never `CROSS JOIN (SELECT MAX(…))` — the MAX comes from `LEFT OUTER JOIN (SELECT T.ORGDIV, T.PURNUM, MAX(T.PURSEQ2) AS MAXSEQ FROM XX110T T … GROUP BY T.ORGDIV, T.PURNUM) D`.
- Do not compute sequences on the screen and pass them.
- **Never UPDATE/INSERT the numbering table (`SY100T`) directly from an SP.** Numbers always come from this common SP. Do not bypass it to remove a loop.
- If one save needs several document numbers (a different number per row), use a small loop that runs only the numbering `EXEC`. This is the exception to "no row-by-row loops": the loop holds only the numbering call and the statement recording the number into staging; the real INSERT/UPDATE/DELETE run set-based outside it. Say in the answer why the loop stays.

## F_SPLIT_KEY

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
                            CROSS APPLY DBO.F_SPLIT_KEY(T.KEYCODE) T1
                   ) B
                   ON A.RECDT = B.CODE
                   AND A.SEQ1 = B.SEQ1
                   AND A.SEQ2 = B.SEQ2
WHERE A.ORGDIV = @ORGDIV
  AND B.GBN = 'DEL';
```

- Composite keys (how to build, name, split, show on the grid, use in code): [keys.md](keys.md). Never compare keys by concatenating strings; split and JOIN on all parts.

## F_IS_CLOSED

`F_IS_CLOSED(@ORGDIV, module, period kind, period, '1')` returns the closing state.

- Module: business module code such as `'MA'` (materials). Follow the existing SAVE of the same business.
- Period kind: `'1'` year closing (period `LEFT(date, 4)`), `'2'` month closing (period `LEFT(date, 6)`).
- Returns `''` no closing info, `'Y'` closed, anything else = may proceed.

A SAVE affecting stock checks these four in order before writing, with the same messages and `16, 9` as existing SAVEs (`16, 9` is only for these closing messages; business checks use `16, 1`):

| Call | Result | Message |
| --- | --- | --- |
| `F_IS_CLOSED(@ORGDIV, 'MA', '1', LEFT(A.OUTDT, 4), '1')` | `''` | `년마감 정보가 없습니다. 년/월마감 프로그램에서 년마감 정보를 생성한 후 처리 가능합니다.` |
| same | `'Y'` | `년 마감이 완료되었습니다. 년/월마감 프로그램에서 년마감 해제 후 처리 가능합니다.` |
| `F_IS_CLOSED(@ORGDIV, 'MA', '2', LEFT(A.OUTDT, 6), '1')` | `''` | `월마감 정보가 없습니다. 년/월마감 프로그램에서 월마감 정보를 생성한 후 처리 가능합니다.` |
| same | `'Y'` | `월 마감이 완료되었습니다. 년/월마감 프로그램에서 월마감 해제 후 처리 가능합니다.` |

Each is one block of this form:

```sql
IF EXISTS (
           SELECT 1
           FROM @TMP_DETAIL A
           WHERE DBO.F_IS_CLOSED(@ORGDIV, 'MA', '1', LEFT(A.OUTDT, 4), '1') = ''
          )
BEGIN
    RAISERROR('년마감 정보가 없습니다. 년/월마감 프로그램에서 년마감 정보를 생성한 후 처리 가능합니다.', 16, 9);
    RETURN;
END
```

- The checked date is the date the stock movement is booked on (receipt date, issue date …). For edits, check whether the date before and after the change can differ.

## Name lookup

User name and common-code name both by JOIN (user, 2026-11-24: "JOIN 기본으로"):

| Name | Method |
| --- | --- |
| User name (registrant, modifier, person in charge …) | **JOIN** `MS095T` once per name (`B1`, `B2`): `ON A.ORGDIV = B1.ORGDIV AND A.REGEMPNO = B1.USERID` → `B1.USERNM AS REGEMPNM`. Do not newly use `F_FIND_USERNM` |
| Common-code name (process name, kind name …) | **JOIN** `MS011T`. Do not newly use `F_CODE_NAME` |

```sql
SELECT A.DOCNUM
     , B.SUBNM AS PROCNM
     , B1.USERNM AS REGEMPNM
FROM DOC_HEADER A
        LEFT OUTER JOIN MS011T B
                     ON B.MAINCD = 'XP001'
                     AND A.PROCCD = B.SUBCD
        LEFT OUTER JOIN MS095T B1
                     ON A.ORGDIV = B1.ORGDIV
                     AND A.REGEMPNO = B1.USERID
WHERE A.ORGDIV = @ORGDIV
```

- LEFT OUTER JOIN `MS011T` on `MAINCD = 'code kind'` and the code value. PK is `(MAINCD, SUBCD)`, so rows do not multiply. Several code kinds: one JOIN per kind with separate aliases (`B`, `B1`).
- One `MS095T` JOIN per name (registrant `B1`, modifier `B2` …); PROJECT_B SPs from 2026-07 do this (7 SPs vs 2 with the function).
- Check row counts: `MS095T`'s PK is `(USERID, PRSNNUM)`; `USERID` is unique today but the PK does not guarantee it. Where duplicates are possible, JOIN a derived `SELECT T.ORGDIV, T.USERID, MAX(T.USERNM) AS USERNM FROM MS095T T GROUP BY T.ORGDIV, T.USERID` (XD600100).
- Do not swap existing function calls and JOINs unless asked.

Measured (PROJECT_B, SQL Server 2019, 2026-11-20, one name over all ~580k receipt rows): JOIN ~0.08 s; function (inlined, default) ~1.1 s; two functions (registrant + modifier) ~2.3 s vs two JOINs ~0.09 s; function with inlining off ~13.7 s. For 1,000 rows both took 0.2–0.3 s. On servers without inlining (2017 or older, or `SYS.SQL_MODULES.IS_INLINEABLE = 0`) the function is far slower, so JOIN is the default there.
