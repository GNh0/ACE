# Finding contract evidence

How to fill [verify.md](verify.md#contract-table). Start from the screen file and widen from the call line to the SP and the Designer. framework call and serializer names, and a worked example: [erp contract.md](../../erp/references/contract.md).

## Search order

1. **Call line**: in the screen `.cs` find the DB calls (`SqlCommand`/`ExecuteNonQuery`/`Fill`, or the project's wrapper). Note the SP name and the parameter line range.
2. **Value sources**: where each argument's value comes from. Mark values that can be `null` (method arguments defaulting to `null`, `int?`, locals assigned only in some branches, `EditValue`).
3. **Mode**: every enum member the screen can pass and every line assigning the edit mode; follow any conversion method to the sent string.
4. **Tables and columns**: `TableName =`, the serializer call, panel → table copies, `.DataSource =`, `Tables[`. Follow which query mode produced the saved table's schema (getters querying an empty key for the schema are common).
5. **Designer**: column prefixes don't prove membership; membership comes from `Columns.AddRange`.
   - membership and order: `^\s+this\.col\w+[,}]` (lines inside AddRange only)
   - fields: `\.FieldName = `, the panel binding property, `\.Visible = true`, `\.Visible = false`
   - panel membership: `<panel>\.Controls\.Add\(`
   - expressions: `Expression = ` (FormatRule, unbound columns)
6. **SP definition**: read with line numbers (below) and note argument declarations, mode branches, the parse path, parsed columns, state branches, and each branch's `SELECT` list.

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
