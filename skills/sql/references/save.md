# SAVE fixed rules and validation

Examples are fictional contracts. Take real keys, types, state letters and XML paths from the target original and a working SAVE with the same role. Full skeleton: [sp-save.md](../../erp/references/sp-save.md).

## SAVE fixed rules

Apply these whenever you write a new SAVE or change a SAVE's logic, even if the user did not mention them. Fix the original too when it has another form. If you were asked only to format, do not change them; report their locations. Exception: lock hints are removed even in format-only work, and you list where. `check_sql.py` checks most of this table.

| Forbidden | Instead |
| --- | --- |
| Lock hints (including ones in the original or reference SP) | Read without hints. [Lock hints](#lock-hints) |
| `IF @WORKTYPE = 'DELETE' BEGIN … RETURN END` followed by the other modes without a condition | The IF/ELSE IF branches below |
| Transaction code in the SP (`BEGIN TRAN`, `COMMIT`, `ROLLBACK`, `TRY/CATCH`, `THROW`, `XACT_ABORT`, `@STARTTRANCOUNT`) | Decide from the caller first. [save-call.md](../../erp/references/save-call.md#transactions) |
| Count variables (`@NEWCOUNT`…), `IF @@ROWCOUNT <> @var`, `IF @CNT > 0` | `IF EXISTS` / `IF NOT EXISTS` before writing (full key, LEFT OUTER JOIN … `ISNULL(B.KEY, '') = ''`, duplicate key GROUP BY HAVING) |
| `SELECT @LASTSEQ = ISNULL(MAX(…), 0)` then `@LASTSEQ + RN`, or UPDATE a sequence into staging first | Inside the INSERT: `ISNULL(C.SEQ, 0) + ROW_NUMBER() OVER (…)` with a derived MAX JOIN. Later steps JOIN the written rows by business key |
| WHILE/cursor around writes, one row at a time (nested loops, `SELECT TOP 1 @var`, several loop variables) | JOIN/derived tables (running-total comparison) in one statement: [Allocation INSERT](save-stock.md#allocation-insert). Loop only when it cannot be set-based, and say why. Exception: when the common numbering SP must be called per row, only that call loops; writes stay set-based outside ([common-sp.md](../../erp/references/common-sp.md#sp_new_key)) |
| Copying the same detail INSERT / allocation / post-check into both NEW and EDIT | Once, after the mode-specific parts inside `ELSE IF @WORKTYPE IN ('NEW', 'EDIT')` |
| `OUTPUT INSERTED.… INTO @table` to collect keys and re-read | JOIN the written rows by business key |
| Variables assigned once and read once, never read, or copied from the header table variable | Write the expression in place, or JOIN the table variable / target rows |
| Storing intermediate results in a table variable / temp table and reading them back | JOIN/derived tables inside the final INSERT/UPDATE/DELETE. Table variables are only for XML parsing (`FROM OPENXML`) |

Keep only the `@variables` T-SQL requires:

| Kept variable | Why |
| --- | --- |
| `@DOC_ID` | OUTPUT handle of `SP_XML_PREPAREDOCUMENT` |
| `@NEWSEQ`, `@OUTSEQ` | OUTPUT arguments of the numbering SP |
| numbering base date such as `@PURDT` | EXEC arguments cannot be expressions or subqueries |
| document number such as `@PURNUM` | Created in NEW and used by several statements |

SAVEs written by the user outside the Codex output folder (`@REQNUM`/`@REQDT`/`@NEWSEQ` of `sp_XM000100_SAVE`, `@QCNUM` of `sp_XQ100100_SAVE`) are in this scope. Read other header values by JOINing `@TMP_HEADER`.

```sql
IF @WORKTYPE = 'DELETE'
BEGIN
    -- existence check → detail DELETE → header DELETE
END
ELSE IF @WORKTYPE IN ('NEW', 'EDIT')
BEGIN
    -- NEW/EDIT shared detail XML parsing and checks
    IF @WORKTYPE = 'NEW'
    BEGIN
        -- numbering → header INSERT
    END
    ELSE IF @WORKTYPE = 'EDIT'
    BEGIN
        -- MOD/DEL rows exist check, header UPDATE, detail MOD UPDATE / DEL DELETE
    END

    -- detail NEW INSERT (derived MAX + ROW_NUMBER) once, here
    SET @OUTPUT = @DOCUMENT_NO
END
```

A failed check ends inside its branch with `RAISERROR … RETURN` (`SaveTrn` rolls back). Do not recount rows after writing. Do not repeat the same mode condition for preparation, checks and writes. The same form in a reference SP is no reason to keep it.

## Lock hints

Never use lock hints (`UPDLOCK`, `HOLDLOCK`, …). Remove them even from the original or reference SP. Keep one only if the user asked for it in this task.

## Operation ownership

| Work | Where |
| --- | --- |
| Checks / header / detail writes needed only by NEW | In the NEW branch, in execution order |
| Changes needed only by a rename | Inside that branch |
| Two modes return the same result or do the same release | Once, at the shared place with the same data dependency |

Keep the shared XML preprocessing and checks an existing caller needs in their scope. When you change a check, compare with the validation examples below.

## Unrequested validation

Do not add validation the user did not ask for (`IF EXISTS … RAISERROR`), including "duplicate selection" or "unregistered item" checks meant to keep sequence pairs or JOINs safe. Write it so it works without them (e.g. number by the staging `SEQ`). If one seems needed, do not add it; propose it in the answer with the reason. Do not infer new business validation from an example: write only the checks the real operation needs, with its full keys, units and transaction behavior.

## Validation: missing related row

Do not remove a valid IF EXISTS check because SELECT/WHERE subqueries are disfavored. IF EXISTS owns the control-flow check; JOIN supplies the related rows. (PRODUCT_MASTER.PRODUCT_CODE is unique, non-null.)

```sql
IF EXISTS (
           SELECT 1
           FROM @TMP_DETAIL A
                   LEFT OUTER JOIN PRODUCT_MASTER B
                                ON A.PRODUCT_CODE = B.PRODUCT_CODE
           WHERE ISNULL(B.PRODUCT_CODE, '') = ''
             AND A.CHANGE_STATE <> 'DEL'
          )
BEGIN
    RAISERROR('An input product is not registered.', 16, 1)
    RETURN;
END
```

Quantity-limit checks: [save-stock.md](save-stock.md#validation-edited-quantity-proposal).

## Caller contract

- Match the caller's mode strings, Added/Modified/Deleted row selection, XML TableName with the SAVE branches and XML path (`/ROOT/<TableName>`).
- Keep the full selected master key set through UPDATE/DELETE. Distinguish deleting a detail while editing, deleting a saved document, per-row printing and save batches.
- JOIN composite keys on all component columns. Keep key parsing where it was.
- Number within the real parent-key range. Detail sequences: derived MAX + ROW_NUMBER inside the INSERT.
- Compare quantities on the full link key and the same unit. In EDIT do not count the document's own quantity twice.
- A request to comment out an integration keeps the original body and only stops it from running.
- Return a mode's result sets in one branch, in the order the caller reads them.
