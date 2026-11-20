# Source↔result mapping (EDD)

Migration results are hard to run, so compare with a **source (PB) ↔ result mapping list** carrying evidence (file:line) on both sides. Having a list is not verification; only items whose lines you found and copied are confirmed.

## Mapping list

| Source (PB file:line) | Result (file:line) | State | Note |
| --- | --- | --- | --- |
| `w_….srw:120` `ue_retrieve` → `dw_list.Retrieve(ls_fr, ls_to)` | `XX000100.cs:210` `CallSelectProcedure(SelectType.LIST)` | moved | 2 args → `@FRDT`, `@TODT` |
| `d_detail.srd:40` update properties (table, key columns, updatable columns) | `sp_XX000100_SAVE.sql:257-269` MOD UPDATE | moved | all 3 key columns JOINed |
| `d_detail.srd:12` compute `qty * unp` | `sp_XX000100_SELECT.sql:52` `A.QTY * A.UNP AS AMT` | changed | calculation moved screen → SP |
| `w_….srw:300` `itemchanged` amount recalculation | none | **미확인** | target event not found |

- State is one of `moved` (same behavior), `changed` (place/method differs; reason in note), `dropped` (deliberately excluded; reason required), `미확인` (not found).
- Source line numbers come from ORCA exports (`.srw`, `.srd`, `.sru` …, [orca.md](orca.md)) or export files from the user. With only a PBL, export first.
- Result lines are C# files, Designer, `.sql` files or DB definitions. For SP definition line numbers follow csharp skill `references/verify-evidence.md#sp-line-numbers`.
- Include the easy-to-miss items one by one: retrieve args, DW SQL, update properties (table, keys, updatable columns), compute columns, protect/taborder (edit protection), events (`itemchanged`, `itemfocuschanged`, `updatestart`, `clicked`), embedded SQL, numbering, output (report bands, groups), values exchanged with other windows (`OpenWithParm`, `Message.PowerObjectParm`/`StringParm`).
- Names decided at run time (dynamic `DataObject` assignment) stay `미확인`; do not guess.
- Items with many columns (DW columns ↔ grid columns) are counted (`17/17 moved`); name only the mismatches with lines.

## Scope

- Full migration: fill the list for the whole screen. Partial move or fix: only items touching **changed events, DWs, SQL**; one line `out of scope` for the rest.
- Analysis only: only objects the question touches (one window, its DataWindows, windows it calls directly). Unread ancestors and global functions stay `미확인`.

## Analysis only

When only describing PB behavior, write the **link target** (where that line leads in the same PB source) instead of the result. State is `확인` (both lines found) or `미확인`.

| Source (PB file:line) | Link target (PB file:line) | State | Note |
| --- | --- | --- | --- |
| `w_xx_pop.srw:200` `dw_list.Retrieve(gs_orgdiv, ls_cust, ls_fr, ls_to, ls_loc, ls_no)` | `d_xx_list.srd:67` `arguments=` 6 | 확인 | same order and count. SQL `:24-66` |
| `d_xx_list.srd:80` `chk` `tabsequence=10` | other columns `tabsequence=32766` (tab order 0 in export) | 확인 | only `chk` is editable |
| `w_xx_pop.srw:49` `ids_x = Message.PowerObjectParm` | caller `xx_main.sru:1035` `OpenWithParm(w_xx_pop, ids_x)` | 확인 | same DW as popup `dw_list`, so `RowsCopy` columns match |
| `w_xx_pop.srw:2` `from w_popup_base` | no ancestor export | 미확인 | `call super::` behavior |

Search order and terms:

1. In windows/user objects (`.srw`/`.sru`), find the DW from `dataobject =` and the ancestor from `from …`.
2. In the same file find `Retrieve(`, `Update(`, `SetItem(`, `GetItem`, `OpenWithParm(`, `Message.`, `RowsCopy(`, embedded SQL (`SELECT`/`UPDATE`/`INSERT`/`DELETE` … `;`).
3. In the DW (`.srd`) find `retrieve=`, `arguments=`, `update=`/`updatewhere=`/`key=yes`, `column=(type=` (result columns), `compute(` (expressions), `tabsequence=`, `protect=`, `dddw.name=`.
4. For values exchanged with other windows, find the caller's line too and write both.

## Related checks

- New or changed C#: fill the csharp skill's `references/verify.md` contract table (screen ↔ SP).
- New or changed SP with a dev DB allowed: SELECT comparison and rollback test per sql skill `references/verify.md` and `references/verify-save.md`. With results from the same arguments as PB you may write "same"; never claim equal values, row counts or performance without results.
