# Save SP call contract: transactions and null arguments

How the framework screen's `db` call decides the SAVE SP's transaction and argument defaults.

## Transactions

**The caller decides** where the transaction lives. Before changing the SP, find the line in the screen code that calls it. Transaction code means `BEGIN TRANSACTION`, `COMMIT`, `ROLLBACK`, `BEGIN TRY/CATCH`, `THROW`, `SET XACT_ABORT ON`, `@STARTTRANCOUNT`.

| Caller | Transaction in the SP |
| --- | --- |
| `db.SaveTrn("sp_…_SAVE", …)` | None. Remove it if the original has it |
| `db.SaveNoTrn("sp_…_SAVE", …)` | **Do not remove.** Keep the original `BEGIN TRY / BEGIN TRANSACTION / COMMIT / CATCH ROLLBACK` |
| Another SP or external system, or caller not found | Do not remove; ask the user. If you cannot ask, **do not remove** |

- A failed check is always `RAISERROR('message', 16, 1); RETURN;` (closing checks: `16, 9`, [common-sp](common-sp.md)).
- `SaveTrn` opens a transaction before the call, commits on success and rolls back on an exception. A `ROLLBACK` inside the SP then also ends the outer transaction and raises error 266 (transaction count mismatch).
- `SaveNoTrn` has no transaction. Removing the SP's transaction leaves earlier writes behind when a write fails midway (truncation, NOT NULL, deadlock…). Moving checks before the writes does not remove this risk.
- When you find a save called with `SaveNoTrn`, write the caller location (file, line) and propose switching the call to `SaveTrn` and then removing the SP's transaction. Change neither the screen nor the SP until the user agrees.
- One project can mix both (see `<profile>/projects/<PROJECT>.md`). Do not assume from another screen.

## Arguments the screen may pass as null

If the screen may pass an XML or optional argument as `null`, declare it with `= NULL`. Check in the caller whether each mode fills it (e.g. a screen that leaves the detail XML `null` on delete).

- ADO.NET does not send arguments whose value is `null`. Without a default the save fails with "expects parameter '@…', which was not supplied". Screen side: [framework.md](framework.md#library-behaviour) row "Null argument" and csharp [verify.md](../../csharp/references/verify.md#contract-table) row 3.
- A default is all it takes: `SP_XML_PREPAREDOCUMENT` accepts NULL and `OPENXML` returns 0 rows.
- The rollback test also omits that argument, like the screen. sql [verify-save.md](../../sql/references/verify-save.md#must-keep), XML arguments: [contract.md](contract.md#rollback-test-xml)
