# Finding contract evidence

How to fill [verify.md](verify.md#contract-table). Start from the screen file and widen from the call line to the SP and the Designer.

## Search order

1. **Call line**: in the screen `.cs` find `GetDataSetFromSP(`, `ExecSPTrn(`, `ExecSP(`. Note the SP name and the `DbParameter` line range.
2. **Value sources**: where each argument's value comes from. Mark values that can be `null` (method arguments defaulting to `null`, `int?`, locals assigned only in some branches, `EditValue`).
3. **Mode**: every `enum SelectType` member and every line assigning `m_Editmode`. `DataEditMode` member names come from the target `FrmDevBase.cs` ([kone120.md](kone120.md)); with `GetEditModeWorkType()` its conversion is the value.
4. **Tables and columns**: `TableName =`, `DataTableToXml(`, `MasterToDataTable(`, `.DataSource =`, `Tables[`. Follow which query mode produced the saved table's schema (getters querying an empty key for the schema are common).
5. **Designer**: column prefixes don't prove membership; membership comes from `Columns.AddRange`.
   - membership and order: `^\s+this\.col\w+[,}]` (lines inside AddRange only)
   - fields: `\.FieldName = `, `\.BindingField = `, `\.Visible = true`, `\.Visible = false`
   - panel membership: `<panel>\.Controls\.Add\(`
   - expressions: `Expression = ` (FormatRule, unbound columns)
6. **SP definition**: read with line numbers (below) and note argument declarations, `IF @WORKTYPE`, `OPENXML`, `WITH`, `GBN`, and each branch's `SELECT` list.

## SP line numbers

- A `.sql` file: use its line numbers.
- Otherwise read the DB definition. Reading a definition is not running it; cite `DB 정의`. With line numbers (the `STRING_SPLIT` ordinal argument is unavailable on low compatibility levels):

```sql
WITH D AS (SELECT REPLACE(OBJECT_DEFINITION(OBJECT_ID('sp_XX000100_SAVE')), CHAR(13), '') + CHAR(10) AS T),
L AS (SELECT CAST(1 AS INT) AS LN, CAST(1 AS BIGINT) AS S, CAST(CHARINDEX(CHAR(10), T) AS BIGINT) AS E, T FROM D
      UNION ALL
      SELECT LN + 1, E + 1, CAST(CHARINDEX(CHAR(10), T, E + 1) AS BIGINT), T FROM L WHERE CHARINDEX(CHAR(10), T, E + 1) > 0)
SELECT LN, SUBSTRING(T, S, E - S) AS TXT FROM L OPTION (MAXRECURSION 0)
```

- These differ from SSMS "Modify" line numbers (SSMS prepends `SET` lines). A blank line before the definition is line 1.
- Old branches/arguments inside `/* */` match text searches too; never cite commented code.
- No DB and no file: the SP cells are `미확인`.

## Example

From two real screens (header panel + detail grid saved with `ExecSPTrn`; two XMLs saved with `ExecSP`), names changed, matching rows trimmed.

| # | Contract | Screen | SP | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Save call | `XX000200.cs:336` `ExecSP("sp_XX000200_SAVE"` | DB 정의 `:214-215` `BEGIN TRY`·`BEGIN TRANSACTION`, `:546` COMMIT, `:551` ROLLBACK | 일치 |
| 3 | Null arguments | `XX000100.cs:253` `string strXmlDetail = null;`, delete branch (254-265) never assigns → `:283` `@XML_DETAIL` | DB 정의 `:12` `@XML_DETAIL VARCHAR(MAX)` no default | **불일치(정적, 실행 미확인)**: "not supplied" on delete |
| 4 | `@WORKTYPE` | `XX000100.cs:278` `m_Editmode.ToString()`, `FrmDevBase.cs:108-114` DEFAULT·EDIT·NEW·DELETE; no mode check in the save handler → DEFAULT possible | DB 정의 `:70` `NOT IN ('NEW', 'EDIT', 'DELETE')` → RAISERROR | 일치 (SP rejects DEFAULT) |
| 7 | XML columns | detail schema = `sp_XX000200_SELECT` DETAIL `:71-102` | `sp_XX000200_SAVE` `:131-153` `WITH` 23 columns | **불일치 20/23**: `SPEC1` (`:137`), `SPEC2` (`:138`) missing → NULL; `:370-371` MOD UPDATE overwrites both with NULL |
| 9 | Grid columns | `XX000200.Designer.cs` 13 visible columns | DETAIL `:71-102` | 13/13 일치; 5 hidden columns not in the result, no effect |
| 12 | Key after save | `XX000100.cs:287` `strFindKey = parmOutput.Value` → `:121` `GetGridRowIndex(…, "DOCNUM", strFindKey)` | `:529` `SET @OUTPUT = @DOCNUM` (NEW·EDIT only) | 일치 (delete → NULL → empty string) |

Rows 2, 5, 6, 8, 10, 11 matched and were left out here. Real answers never leave rows out: write `범위 밖` or counts.
