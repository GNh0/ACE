# Execution verification (EDD)

Filling the scenario table is not verification. SAVE SPs with perfect static review have still failed when actually run. **If you can run it, running is the default; static review is only for when you cannot.**

## 1. Is it safe to run

| Target DB | Do |
| --- | --- |
| The user called it a dev DB, or allowed test runs on it in this task | Verify by running |
| Production, or unknown | Do not run. Static review only, evidence `미확인`. Ask the user to run |

- Verification is a **read query**, or runs **inside a transaction that is fully rolled back**. Leave no data.
- During a rollback test the transaction locks target and numbering tables. Others use the same DB: keep it to one short batch and never leave a transaction open into the next call.
- To run an SP not yet applied:
  - With permission to apply to the dev DB, ALTER it and then test.
  - Otherwise create `CREATE PROCEDURE #sp_XX000100_SAVE` (session temp procedure). Do not create new permanent objects.
  - `CREATE PROCEDURE` must be the first statement of its batch, so create and run in separate calls. A temp procedure is visible only to its session: check both calls have the same `@@SPID`.
  - Inside a temp procedure `OBJECT_NAME(@@PROCID)` is NULL, so `SP_XML_LOG_SAVE` logs an empty SP name. It is rolled back, so fine.
- For a new SELECT branch, do not apply; run the branch's SELECT ad hoc with variable declarations.

## 2. SELECT SP comparison

Run the original and the new query **with the same arguments** and compare count and content, for each `@WORKTYPE` branch.

- Choose arguments that return rows in real data. **Never call two 0-row results equal**; change arguments.
- Compare content with `EXCEPT` in both directions; one direction misses extra new rows.
- `ORDER BY` is not caught by result comparison; compare the statements.
- Receive the original with `INSERT INTO @OLD EXEC original_sp …`. Run the new branch's SELECT as `INSERT INTO @NEW SELECT …`.
- Get table variable columns/types by passing the branch SELECT to `SYS.DM_EXEC_DESCRIBE_FIRST_RESULT_SET`. Passing the whole SP (`…_FOR_OBJECT`) fails because branches differ.
- If the original uses `INSERT … EXEC` internally or one branch returns several result sets, `INSERT … EXEC` cannot receive it; run the original branch ad hoc too.

```sql
SELECT COLUMN_ORDINAL
     , NAME
     , SYSTEM_TYPE_NAME
FROM SYS.DM_EXEC_DESCRIBE_FIRST_RESULT_SET(@SQL, N'@ORGDIV VARCHAR(2), @FRDT VARCHAR(8), @TODT VARCHAR(8)', 0)
ORDER BY COLUMN_ORDINAL;
```

Comparison frame:

```sql
SET NOCOUNT ON;

DECLARE @ORGDIV VARCHAR(2) = '01';
DECLARE @FRDT   VARCHAR(8) = '20261101';
DECLARE @TODT   VARCHAR(8) = '20261130';

DECLARE @OLD TABLE
(
      DOCNUM  VARCHAR(20)
    , QTY     NUMERIC(38, 4)
);

DECLARE @NEW TABLE ( … same columns … );

INSERT INTO @OLD
EXEC SP_XX000100_SELECT @WORKTYPE = 'LIST', @ORGDIV = @ORGDIV, @FRDT = @FRDT, @TODT = @TODT;

-- paste the new LIST branch SELECT unchanged (leave out ORDER BY, compare it separately)
INSERT INTO @NEW
SELECT …;

SELECT 'LIST' AS WORKTYPE
     , (SELECT COUNT(*) FROM @OLD) AS OLDCNT
     , (SELECT COUNT(*) FROM @NEW) AS NEWCNT
     , (SELECT COUNT(*) FROM (SELECT * FROM @OLD EXCEPT SELECT * FROM @NEW) T) AS OLDONLY
     , (SELECT COUNT(*) FROM (SELECT * FROM @NEW EXCEPT SELECT * FROM @OLD) T) AS NEWONLY;
```

Equal when `OLDCNT = NEWCNT > 0` and `OLDONLY = NEWONLY = 0`. Otherwise show the `EXCEPT` rows to see which column differs.

## 3. SAVE SP: rollback test

[verify-save.md](verify-save.md): draft with `scripts/make_rollback_test.py`, must-keep rules, required scenarios.

## 4. Applied check and 5. Report

[verify-report.md](verify-report.md): hash check after applying, scenario table, evidence format.
