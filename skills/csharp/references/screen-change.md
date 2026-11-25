# Changing an existing screen

Connecting new functions and keeping integrations. framework save/delete flow: erp [save-flow.md](../../erp/references/save-flow.md).

## Connecting a function to an existing screen

Whole screen: follow Load/init → search → detail → edit lock → commands → re-query and focus. Local change: follow only the related events, permissions, toolbar and user buttons.

| Task | What to keep |
| --- | --- |
| New / edit | Reuse init and the existing schema; query an empty DETAIL only when a schema is needed. Edit keeps bound values and selects the existing mode/tab |
| Detail add / delete | NewRow → assign → Rows.Add; numbering stays with its owner; delete with the existing GridView API |
| Delete saved documents | Send all checked master keys as one XML batch. Distinguish focused row, display order and real selection |
| Save error | Keep existing confirmations, checks, messages and unsaved changes; re-query only on success |
| Dates, amounts | Check the real control and same-screen usage; keep type, precision and NULL from DB expression → DataColumn → editor/output |

- Save type and row selection: read the real caller and the same-role reference. Normal saves use the existing edit-mode API; only dedicated actions use a fixed mode; match the SP strings.
- Link checked keys, changed rows, TableName/XML, transaction and re-query on success. Use `Clone`/`ImportRow` for selected master keys when needed; check deleted rows' Original keys. Don't split a save batch because printing is per row.
- Connect display names and save codes to their own controls; a hidden USERID is read from its `EditValue`. Compare FieldName, XML and SP arguments by real names on both sides.
- Movement guards go before bypassing early returns; keep selection and detail; leave colour/enable to the existing protect routine. No new limits from a status column alone.
- Helpers, state flags, re-queries, extra checks or delete-and-reinsert only when existing handling cannot meet the requirement. Return a server `GETDATE()` save time only when the caller needs it.
- When the SP changes too, follow the sql skill and compare arguments, XML and result columns on both sides.

## Keeping original integrations as comments

- "Stop the integration": keep the original body and existing commented JOINs/filters; only block execution. Check call, fields, bindings and schema separately.
- Uploads: check real headers, types, dates and keys; iterate the DataTable the target's way. "Save valid rows, collect errors" applies to that upload.
- TY: query `RTRUSER` and edit `USER` are different. Feedback fixes look at declaration, init, assignment and use together and keep the user's later edits.
