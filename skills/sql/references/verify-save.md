# SAVE SP rollback test

First check [verify.md](verify.md#1-is-it-safe-to-run) that the DB may be used.

## Draft

Do not hand-fit the template per SP. Generate a draft and fill only the `-- TODO:` lines.

1. Put the target SP definition in a file (the edited `.sql`, or the definition read from the DB).
2. Make the draft; output goes to a task folder under `%TEMP%`:

   ```
   python <skill folder>/scripts/make_rollback_test.py <SP definition.sql> --out <task folder>\<SP>_test.sql
   ```

3. The draft has argument declarations, one `FOR XML RAW` SELECT per XML (all `WITH` columns), count snapshots of target tables, an EXEC block per `@WORKTYPE`, rollback and post-rollback checks; its top comment lists the extracted arguments, XML paths, WORKTYPEs and tables. First check the extraction matches the SP.
4. Fill the `-- TODO:` lines: argument values, XML source tables and keys, value snapshots. If a `WITH` column is not in the source table (e.g. a paired table's key), change only the `FROM` to a derived table and keep the SELECT list. Build scenarios like mixed edit or failed check by copying a WORKTYPE block, following [Must keep](#must-keep).
5. Before running, run the filled XML source SELECTs alone (no transaction) to see rows come back. Name-resolution errors (missing table/column) are not caught by `CATCH` and cut the batch with the transaction open; if so, run `IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;` on the same connection.
6. Run. A leftover `<원천>` is a syntax error (nothing runs); a leftover `WHERE 1 = 0` gives a "… 행이 없다" `ERROR` row and full rollback. For blocks sending empty XML on purpose (detail on delete), delete that `IF … IS NULL` line.

## Shape

`@RESULT` table variable + before counts → XML from real data → `BEGIN TRANSACTION`, inside `BEGIN TRY` per scenario: `EXEC` + snapshot `INSERT INTO @RESULT` → `BEGIN CATCH` records message and line → `IF @@TRANCOUNT > @TRANCOUNT ROLLBACK TRANSACTION` → record after counts and `@@TRANCOUNT` = 0 → `SELECT * FROM @RESULT`.

Table variables are not rolled back, so snapshots collected in them survive. Some DB tools return only the first result set, so return **one `@RESULT` at the end**.

## Must keep

| Rule | Why |
| --- | --- |
| Build XML with `FOR XML RAW('<TableName>'), ROOT('ROOT')`; TableName is what the screen puts in `dt.TableName` | The SP's `OPENXML` path is `/ROOT/<TableName>` |
| Put row state directly: `'NEW' AS GBN` | The screen's `DataTableToXml` adds a `GBN` attribute per row |
| With Korean text, prefix `<?xml version="1.0" encoding="euc-kr"?>` | The SP takes XML as `VARCHAR`; without it `SP_XML_PREPAREDOCUMENT` fails with "텍스트 내용에 잘못된 문자가 있습니다". The screen adds the same declaration |
| Date columns as `CONVERT(VARCHAR(8), col, 112)` | The screen sends DateTime as `yyyyMMdd` (`yyyy-MM-dd HH:mm:ss` with time). `FOR XML` writes `2026-11-19`, truncated in `VARCHAR(8)` |
| No `SET XACT_ABORT ON` in the test batch | One expected error would kill the transaction and stop later scenarios |
| Wrap scenarios that must fail in their own inner `BEGIN TRY / BEGIN CATCH` | `RAISERROR … 16` does not kill the transaction (`XACT_STATE() = 1`); keep it from reaching the outer TRY |
| Registrant `'ACETEST'`, modifier a different value like `'ACETEST2'` | Snapshots show which save stamped registrant/modifier |
| Round-trip XML comes from the SELECT SP result via `INSERT INTO @DETAIL EXEC …` | It must equal what the screen really sends back |
| Count snapshots: key list in `VALUES`, counted with `LEFT OUTER JOIN` | `GROUP BY` counts drop 0-row keys, so "deleted" is invisible |
| Call the SP exactly as the screen does. If the screen omits an argument or leaves it `null` in a mode (detail XML on delete…), omit it in that mode's test | ADO.NET does not send `null` arguments; a test that always passes them misses "not supplied" errors ([save-tran.md](save-tran.md#arguments-the-screen-may-pass-as-null)) |

Check `DataTableToXml` serialization (NULL columns omitted, `GBN`/`NUM` attributes per row, DateTime format) once in the target project's `DataUtil.cs`. `FOR XML RAW` also omits NULL columns.

Common SPs' writes (`SP_XML_LOG_SAVE` log, `SP_SYSTEM_BA100T_KEYCODE` sequence) are in the same transaction and roll back too. In a failed-check scenario the log is written before the failure, so judge "nothing written" by **business tables**.

## Required scenarios

| Scenario | Check |
| --- | --- |
| NEW | Header, detail and paired-table rows are right; sequence pairs (detail seq ↔ paired seq) match. At least 2 detail rows |
| Round trip | Save exactly what was queried → quantity, amount, sequence, number unchanged; unchanged again after saving once more |
| Mixed edit | One each of `MOD`, `DEL`, `NEW`, `UNC` in one save → only `MOD` changes value and modifier, `UNC` unchanged, registrant/registration date kept; `DEL` also gone from the paired table; `NEW` gets the next sequence |
| Failed check | Over-limit value etc. shows the blocking message and nothing is written to business tables |
| Delete | Only the target document is deleted; others stay |
| After rollback | Counts and values equal the before state, `@@TRANCOUNT` is 0 |

Leave scenarios you cannot verify (no matching data…) as `미확인` with the reason. Do not infer them from numbers of scenarios you ran.

## Template

Fictional: the [procedure-save.md](procedure-save.md) skeleton. Take real arguments, XML paths and columns from the target SP (`OBJECT_DEFINITION`). Only parts beyond the generated draft are shown.

```sql
SET NOCOUNT ON;

DECLARE @TRANCOUNT INT = @@TRANCOUNT;
-- arguments and @RESULT (STEP INT IDENTITY(1, 1), SCENARIO, TBL, QTY, MSG …) as generated

BEGIN TRANSACTION;

BEGIN TRY
    -- 1~3. NEW / round trip / mixed edit: generated blocks, XML built per Must keep

    -- 4. failed check: must raise, so wrap it in an inner TRY
    BEGIN TRY
        EXEC SP_XX000100_SAVE @WORKTYPE = 'EDIT', @ORGDIV = @ORGDIV, @USERID = 'ACETEST2', @USERIP = 'ACE'
                            , @XML = @XML, @XMLDETAIL = @XMLDETAIL, @OUTPUT = @OUTPUT OUTPUT;

        INSERT INTO @RESULT (SCENARIO, MSG) VALUES ('4.FAIL', '차단되지 않음');
    END TRY
    BEGIN CATCH
        INSERT INTO @RESULT (SCENARIO, MSG)
        VALUES ('4.FAIL', ERROR_MESSAGE() + ' / XACT_STATE = ' + CONVERT(VARCHAR(2), XACT_STATE()));
    END CATCH

    -- 5. delete: count per key so 0 rows stay visible
    INSERT INTO @RESULT (SCENARIO, TBL, QTY)
    SELECT '5.DELETE', K.TBL, COUNT(B.DOCNUM) + COUNT(C.DOCNUM)
    FROM (
          VALUES ('DOC_HEADER', @DOCNUM), ('DOC_DETAIL', @DOCNUM)
         ) K(TBL, DOCNUM)
            LEFT OUTER JOIN DOC_HEADER B
                         ON K.TBL = 'DOC_HEADER'
                         AND K.DOCNUM = B.DOCNUM
            LEFT OUTER JOIN DOC_DETAIL C
                         ON K.TBL = 'DOC_DETAIL'
                         AND K.DOCNUM = C.DOCNUM
    GROUP BY K.TBL;
END TRY
-- outer CATCH (ERROR row with ERROR_LINE()), rollback, after counts, final SELECT: as generated
```

- Pass `@XMLDETAIL = '<ROOT/>'` on delete only if the screen sends empty XML; if it leaves it `null`, omit it.
- Scenarios reuse the document created earlier (NEW → mixed edit → failed check → delete). If an early step fails, the `ERROR` row shows the line and later scenarios do not run; they are `미확인`.
- Pick sources for new details (stock, earlier receipts) by first running the SELECT SP's candidate branch for real keys with remainders; quantities stay within the remainder.
- Choose failing values by reading the target SP's check. Hitting another check first does not confirm the intended block; compare the message with the target check's message.
- After the test, count once more outside the transaction and compare with the before counts.
