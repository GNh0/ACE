# Alias roles

General SQL layout: [style.md](style.md).

## Alias roles

Before changing aliases in a general cleanup, write `alias | table | business role | link key` for each table. Aliases follow this role, not JOIN order or the table name's first letter. One rule for every table (FROM, plain JOIN, derived JOIN). The main FROM target comes first, so it is always **A**.

- **Same business as a table that already has a letter → that letter plus a number**: helper tables adding standard/setting/approval values to its rows, a header's detail, derived tables splitting the same source by condition. A's → A1, A2; B's → B1, B2; the same for any letter.
- **New business → next letter** (B, C, D…) in order of appearance, even if it joins on an earlier table's key.
- A same-business table appearing before its base still takes the business letter. Do not change JOIN order.

| Original | Alias | Basis |
| --- | --- | --- |
| `XP110T` process plan | `A` | main target |
| `XP100T` standard time | `A1` | A's process/item standard (same business), not `B` |
| `XS100T` order header | `B` | new business |
| `MS011T` process name code | `C` | new business |
| `XS110T` order detail | `B1` | B's detail, B family regardless of C before it |
| `XP210T` result total (PARTCD <> 'Y') | `D` | new business |
| `XP210T` result total (PARTCD = 'Y') | `D1` | same source as D by condition |
| `SY905T` drawing file | `E` | new business |

Judge "same business" from the table description, real link keys and used columns. If evidence is thin, write `미확인` and the reason in the role table and ask the user. In the answer, list original → new alias with the role basis.

```sql
SELECT A.GONUM
     , A1.STDTIME
     , B.HULLNO
     , B1.ITEMNM
     , C.SUBNM3
FROM XP110T A
        LEFT OUTER JOIN XP100T A1
                     ON A.ORGDIV = A1.ORGDIV
                     AND A.PROCCD = A1.PROCCD
        LEFT OUTER JOIN XS100T B
                     ON A.ORGDIV = B.ORGDIV
                     AND A.ORDNUM = B.ORDNUM
        LEFT OUTER JOIN MS011T C
                     ON A.PROCCD = C.SUBCD
        LEFT OUTER JOIN XS110T B1
                     ON A.ORGDIV = B1.ORGDIV
                     AND A.ORDSEQ = B1.ORDSEQ
```
