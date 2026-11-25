# C# and SELECT/SAVE migration

## Mapping

- Move PB retrieve/update paths to C# parameters/XML, SP result sets, numbering, NEW/MOD/DEL and check locations. If both SELECT and SAVE are requested, finish both.
- Do not delete original checks or replace them with a bulk overwrite in C#.
- Compare each call's parameter names and required flags with the real SP definition. Leave computed parameter names `미확인`. Check OUTPUT direction, return value and XML content separately.
- Generated or cleaned SQL follows the sql skill. Do not add DB-only SQL files as C# project items.

## Finding SQL in PB source

- Distinguish DataWindow retrieve SQL (the quoted value), PowerScript embedded SQL, and SQL built from string pieces. For built SQL check the real assembly order.
- Do not guess dynamic `DataObject` assignments; leave them unresolved.

## Result check

- For a detailed plan, link screens, events, DWs, DB, fields, I/O, save order, open questions and implementation order so someone else can continue. A simple SELECT extraction needs neither this document nor C# generation.
- Trace input, query, edit protection, save and output in real source. Compare query, edit protection, new/edit/delete, XML, SP, re-query/restore and output between source and target. Write missing events, fields and indirect calls as `미확인`.
- Claims that values, row counts, query counts or performance are equal need a real comparison under the same conditions.
