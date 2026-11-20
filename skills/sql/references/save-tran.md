# Transactions and null arguments

## Transactions

**The caller decides** where the transaction lives. Before changing the SP, find the line in the screen code that calls it. Transaction code means `BEGIN TRANSACTION`, `COMMIT`, `ROLLBACK`, `BEGIN TRY/CATCH`, `THROW`, `SET XACT_ABORT ON`, `@STARTTRANCOUNT`.

| Caller | Transaction in the SP |
| --- | --- |
| `dbClient.ExecSPTrn("sp_…_SAVE", …)` | None. Remove it if the original has it |
| `dbClient.ExecSP("sp_…_SAVE", …)` | **Do not remove.** Keep the original `BEGIN TRY / BEGIN TRANSACTION / COMMIT / CATCH ROLLBACK` |
| Another SP or external system, or caller not found | Do not remove; ask the user. If you cannot ask, **do not remove** |

- A failed check is always `RAISERROR('message', 16, 1); RETURN;`.
- `ExecSPTrn` opens a transaction before the call, commits on success and rolls back on an exception. A `ROLLBACK` inside the SP then also ends the outer transaction and raises error 266 (transaction count mismatch).
- `ExecSP` has no transaction. Removing the SP's transaction leaves earlier writes behind when a write fails midway (truncation, NOT NULL, deadlock…). Moving checks before the writes does not remove this risk.
- When you find a save called with `ExecSP`, write the caller location (file, line) and propose switching the call to `ExecSPTrn` and then removing the SP's transaction. Change neither the screen nor the SP until the user agrees.
- One project mixes both (C_KONE120: 17 of 141 save calls use `ExecSP`). Do not assume from another screen.

## Arguments the screen may pass as null

If the screen may pass an XML or optional argument as `null`, declare it with `= NULL`. Check in the caller whether each mode fills it (e.g. a screen that leaves the detail XML `null` on delete).

- ADO.NET does not send arguments whose value is `null`. Without a default the save fails with "expects parameter '@…', which was not supplied". Screen side: csharp skill `references/kone120.md` row "Null argument" and `references/verify.md` contract table row 3.
- A default is all it takes: `SP_XML_PREPAREDOCUMENT` accepts NULL and `OPENXML` returns 0 rows.
- The rollback test also omits that argument, like the screen. [verify-save.md](verify-save.md#must-keep)
