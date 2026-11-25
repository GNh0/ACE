# Composite document keys

Surveyed 2026-11-24 from the user's own code: 99 SPs in PROJECT_B (newest style), 84 in PROJECT_A, 456 Designer files in PROJECT_B_1 / PROJECT_A. Follow this; when an existing screen depends on a different name or form, keep the screen's.

## Families

| Family | Header key | Detail key |
| --- | --- | --- |
| Receipts/issues/results `XM200T/XM210T`, `XS200T/XS210T`, `XP210T` | `RECDT-SEQ1` | `RECDT-SEQ1-SEQ2` |
| Purchase order `XX100T/XX110T` | `PURNUM-PURSEQ1` (PROJECT_A: `PURNUM` is already `PURDT-seq`) | `PURNUM-PURSEQ1-PURSEQ2` (PROJECT_A: `PURNUM-PURSEQ2`) |
| Sales order `XS100T/XS110T` | `ORDNUM` | `ORDNUM-ORDSEQ` (some 3 parts) |
| Request/shipping `XM090T`, `XS150T/XS160T` | `REQNUM` | `REQNUM-REQSEQ` |

Check the target project's tables (`<profile>/projects/`): the same family can differ per project.

## Build (SELECT)

```sql
     , A.RECDT + '-' + CONVERT(VARCHAR(10), A.SEQ1) AS PRODNUM
     , A.RECDT + '-' + CONVERT(VARCHAR(10), A.SEQ1) + '-' + CONVERT(VARCHAR(10), A.SEQ2) AS KEYCODE
```

- Separator `'-'` only, `CONVERT(VARCHAR(10), …)` for numbers, no spaces. No `CAST`, `FORMAT`, `CONCAT`, zero padding (padding is only for numbering), no length-less `CONVERT(VARCHAR, …)`.
- Return the parts as columns too; the screen needs them.
- A detail-level key has all detail parts, never fewer. Use the same parts and order as the screen's comparisons (`strPURs.Contains(PURKEY)`) and the sibling SPs that output the same column.
- An optional referenced number is wrapped only when it can be empty: `(CASE WHEN ISNULL(A.ORDNUM, '') = '' THEN '' ELSE A.ORDNUM + '-' + CONVERT(VARCHAR(10), A.ORDSEQ) END) AS ORDNUMS`. The row's own key is not wrapped.
- `'|'` joins only non-document grouping keys (`A.CUSTCD + '|' + A.AMTUNIT AS KEYCODE`). Never join two parts without a separator.
- A SAVE returns the key to refocus through `@OUTPUT`, built with the same expression.

## Names

- The row's own key is `KEYCODE` (header list: header parts; detail list: all detail parts).
- A referenced document's number is `<FAMILY>NUMS`: `ORDNUMS`, `PURNUMS`, `REQNUMS`. With the row's own key it becomes `KEYCODE` + `<FAMILY>NUMS`.
- Header and detail keys in one result: name the header one by its family (`PRODNUM` = `RECDT-SEQ1`) and the detail one `KEYCODE`.
- Keep names an existing screen depends on (`GridRowIndex`, `Contains` duplicate checks on `PURKEY`/`ORDKEY`/`PORKEY`/`REQKEY`, `@KEYCODE` passing). New code doesn't introduce `<FAMILY>KEY` names.
- Never output the same expression under two names (`PORKEY` and `ORDNUMS` both).

## Split (SP arguments and stored composite columns)

```sql
        CROSS APPLY DBO.F_SPLIT_KEY(@KEYCODE) K
WHERE A.RECDT = K.CODE
  AND A.SEQ1 = K.SEQ1
  AND A.SEQ2 = K.SEQ2
```

- `F_SPLIT_KEY` returns `CODE`, `SEQ1`, `SEQ2` (at most 3 parts; SEQ parts must be numbers, else NULL; no `'-'` → `CODE` is NULL). Join on every part the key has.
- A 1-part key compares directly: `A.ORDNUM = @KEYCODE`.
- Several keys in one argument: `FROM DBO.SPLITTABLENVARCHAR(@KEYCODE, '|') T CROSS APPLY DBO.F_SPLIT_KEY(T.VALUE) T1`.
- Stored composite columns (`PRODNUM`, `REFKEYCODE`, `REQNUM`) are split the same way, then joined on parts.
- Never `LEFT`/`CHARINDEX`/`SUBSTRING` to split, never join on a concatenation (`T.PRODNUM = T1.CODE + '-' + …`), never compare an argument to a concatenation (`@KEYCODE = A.CUSTCD + '|' + A.AMTUNIT`).

## Grid

```csharp
this.colMA200T_KEYCODE.Caption = "입고번호";
this.colMA200T_KEYCODE.FieldName = "KEYCODE";
this.colMA200T_KEYCODE.Visible = true;
this.colMA200T_KEYCODE.VisibleIndex = 1;
// part columns: in the view, no Visible / VisibleIndex lines, Caption = FieldName
this.colMA200T_RECDT.Caption = "RECDT";
this.colMA200T_RECDT.FieldName = "RECDT";
```

- The combined key is the visible column with a business caption (입고번호, 발주번호, 수주번호, 관리번호). The part columns exist in the view but are hidden by having no `Visible`/`VisibleIndex` lines (not `Visible = false`), caption = field name. 92 of 190 grids; most others are deliberate (key used only as a hidden row id, or a line number shown).
- A detail line number (`SEQ2`, `PURSEQ2`) may be visible with caption "순번".
- Column names `col<grid>_<FIELD>`.

## Screen code

```csharp
grdMA210T.DataSource = QuerySP(SelectType.DETAIL, dr?["KEYCODE"].ToString()).Tables[0];
, new DbParameter("@KEYCODE", strKeycode)
strFindDetailKey = Convert.ToString(parmOutput.Value);
int irow = ui.GridRowIndex(grdDetail, "KEYCODE", strFindDetailKey);
```

- Pass the focused row's `dr["KEYCODE"]` to `@KEYCODE`; after save refocus with `ui.GridRowIndex(grd, "KEYCODE", strFindKey)` using `@OUTPUT`.
- When copying a row to another grid, copy the parts and the combined key together.
- Don't split keys in C# (`Split('-')`); the SP splits with `F_SPLIT_KEY`.
