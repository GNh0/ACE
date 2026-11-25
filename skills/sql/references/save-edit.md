# EDIT saves, numbering, edited quantities

Examples are fictional contracts. Skeleton: [sp-save.md](../../erp/references/sp-save.md#save-sp-header--detail).

## Row states in EDIT

- Split details by `GBN`: `DEL` deletes, **only `MOD` UPDATEs**, only `NEW` INSERTs. In EDIT never delete all details and re-insert them, even if the existing SP does.
- Unchanged rows (`UNC`) are not touched and get no modifier stamp.
- Values copied from the header into details (date, customer, currency, rate) are aligned across all details in their own UPDATE, and a detail whose copied value actually changes gets the modifier stamp too (`MODDT`, `MODEMPNO`, `MODIP`): limit that UPDATE to rows where a copied value differs (`ISNULL(A.INDT, '') <> ISNULL(B.INDT, '') OR …`), so a header change that leaves the details as they were (a remark) stamps nothing (user, 2026-11-24).
- `MOD` rows are UPDATEd in every target table (including the paired issue table). Delete/re-insert and numbering are only for `NEW` rows.
- Call the numbering `EXEC` only in NEW mode or when there are `NEW` rows.
- When inserting paired rows into two tables, number both by the same sort key (check it is unique first).

## Same row unit for SELECT and SAVE

Check that "one detail row the save writes" and "one row the DETAIL query returns" are the same unit. Query → save unchanged → query again must keep quantity and amount. An aggregate that keeps one of several different values (`MAX(unit price)`) when merging means the unit is wrong.

## Parsed rows and NEW

Parse the XML once, in the existing scope. Define the needed columns/types and use the parsed rows directly in INSERT SELECT. Release the document handle on normal and error paths; clear it after the normal release so a later error cannot release it twice.

```sql
INSERT INTO CONTACTS
(
       COMPANY_ID  , CUSTOMER_ID  , CONTACT_ID   , CONTACT_NAME
)
SELECT @COMPANY_ID , @CUSTOMER_ID , A.CONTACT_ID , A.CONTACT_NAME
FROM @TMP_CONTACT A
WHERE A.CHANGE_STATE = 'NEW'
```

Keep the existing numbering range and order. Detail sequences use the derived MAX + ROW_NUMBER of the [fixed rules](save.md#save-fixed-rules). An XML row index is never the basis of a permanent key. If a later step needs a generated key, JOIN the written rows by business key.

## MOD and DEL

Company, customer and contact form the full key.

```sql
UPDATE A
SET CONTACT_NAME = B.CONTACT_NAME
  , MODIFIED_AT = GETDATE()
FROM CONTACTS A
        INNER JOIN @TMP_CONTACT B
                ON A.CONTACT_ID = B.CONTACT_ID
WHERE A.COMPANY_ID = @COMPANY_ID
  AND A.CUSTOMER_ID = @CUSTOMER_ID
  AND B.CHANGE_STATE = 'MOD'

DELETE A
FROM CONTACTS A
        INNER JOIN @TMP_CONTACT B
                ON A.CONTACT_ID = B.CONTACT_ID
WHERE A.COMPANY_ID = @COMPANY_ID
  AND A.CUSTOMER_ID = @CUSTOMER_ID
  AND B.CHANGE_STATE = 'DEL'
```

## Multiple-master-delete

With delete keys for several documents, keep the full selected key set to the end. Check that deletion is allowed, delete related details first, then headers with the same key condition.

```sql
DELETE A
FROM DOCUMENT_DETAIL A
        INNER JOIN @TMP_DOCUMENT B
                ON A.COMPANY_ID = B.COMPANY_ID
                AND A.DOCUMENT_NO = B.DOCUMENT_NO
WHERE A.COMPANY_ID = @COMPANY_ID
  AND B.CHANGE_STATE = 'DEL'
```

Check with 2 selected, 1 unselected, and the same number in another company.
