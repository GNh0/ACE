# Illustrative SELECT/SAVE patterns

All schemas, identifiers, values and messages below are fictional. These examples express the user's preferred structures; they are not application code or deployable procedure templates. Derive actual types, keys, state strings and transaction ownership from the target and complete approved comparison procedures.

Read the sections matching the changed responsibilities, not every example. Each section pairs a specific misuse to avoid with the intended structure. Do not copy a fictional eligibility rule, state value or validation into an unrelated program.

| Responsibility | Example |
| --- | --- |
| Descriptive lookup versus required row eligibility | [SELECT: lookup and eligibility](select-patterns.md#lookup-and-eligibility) |
| One header row with detail totals | [SELECT: grouped detail JOIN](select-patterns.md#grouped-detail-join) |
| Exclude rows already processed | [SELECT: exclusion JOIN](select-patterns.md#exclusion-join) |
| Multiple ordered results for one mode | [SELECT: one branch with multiple results](select-patterns.md#one-branch-with-multiple-results) |
| XML parsing and NEW INSERT SELECT | [SAVE: parsed rows and NEW](save-patterns.md#parsed-rows-and-new) |
| Keep mode-owned preparation and writes together while preserving real shared phases | [SAVE: operation ownership](save-patterns.md#operation-ownership) |
| Modify/delete selected input rows | [SAVE: MOD and DEL](save-patterns.md#mod-and-del) |
| Delete several complete master documents | [SAVE: multiple-master-delete](save-patterns.md#multiple-master-delete) |
| Validate related-row existence | [Validation: missing related row](validation-patterns.md#missing-related-row) |
| Validate a complete edited quantity proposal | [Validation: edited-quantity-proposal](validation-patterns.md#edited-quantity-proposal) |

For nested FROM/UNION blocks and grouped INSERT/SELECT text-column alignment, use the existing [SQL layout examples](style.md); keep the query's actual keys and row grain separate from its whitespace layout.

Necessary numbering/output variables and staging updates that record generated keys remain valid when the real flow needs them. Do not judge necessity from variable count or ban every staging UPDATE.

Before applying a draft and after the final edit, compare the exact affected bodies with the matching examples and complete references. Include existing code the user asked to correct. A final edit reopens the affected comparison and audit.

## Standalone SELECT and SAVE skeletons

When no external reference procedure is available, use these structural skeletons for header framing, parameter layout, XML staging, and transaction handling (adapt all identifiers, types, and branches to the actual target contract; never call `_BAK` backup procedures or wrap already `NUMERIC(18, 4)` expressions in redundant `CONVERT(NUMERIC(18, 4), ...)`):

```sql
-- =============================================
-- AUTHOR:      근호
-- CREATE DATE: 2026-11-18
-- DESCRIPTION: 샘플프로그램 조회
-- =============================================
CREATE PROCEDURE [dbo].[sp_SAMPLE100_SELECT]
      @WORKTYPE VARCHAR(20)  = ''
    , @ORGDIV   VARCHAR(10)  = '01'
    , @FRDT     VARCHAR(8)   = NULL
    , @TODT     VARCHAR(8)   = NULL
    , @KEYCODE  VARCHAR(50)  = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @WORKTYPE = 'LIST'
    BEGIN
        SELECT A.ORGDIV
             , A.DOCNUM
             , B.ITEMNM
             , ISNULL(A1.QTY, 0) AS QTY
        FROM TB_HEADER A
                LEFT OUTER JOIN (
                                 SELECT T.ORGDIV, T.DOCNUM
                                      , SUM(ISNULL(T.QTY, 0)) AS QTY
                                 FROM TB_DETAIL T
                                 WHERE T.ORGDIV = @ORGDIV
                                 GROUP BY T.ORGDIV, T.DOCNUM
                                ) A1
                                ON A.ORGDIV = A1.ORGDIV
                                AND A.DOCNUM = A1.DOCNUM
                LEFT OUTER JOIN BA030T B
                             ON A.ITEMCD = B.ITEMCD
        WHERE A.ORGDIV = @ORGDIV
          AND A.DOCDT BETWEEN @FRDT AND @TODT
        ORDER BY A.DOCNUM DESC
    END
END
```

```sql
-- =============================================
-- AUTHOR:      근호
-- CREATE DATE: 2026-11-18
-- DESCRIPTION: 샘플프로그램 저장
-- =============================================
CREATE PROCEDURE [dbo].[sp_SAMPLE100_SAVE]
      @WORKTYPE   VARCHAR(20)   = ''
    , @ORGDIV     VARCHAR(10)   = '01'
    , @XML_DETAIL NVARCHAR(MAX) = NULL
    , @USERID     VARCHAR(30)   = ''
    , @USERIP     VARCHAR(50)   = ''
    , @OUTPUT     VARCHAR(100)  = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @DOC_ID INT = NULL

    BEGIN TRY
        EXEC sp_XML_LOG_SAVE @PGMID = 'SAMPLE100', @WORKTYPE = @WORKTYPE, @XML = @XML_DETAIL, @USERID = @USERID, @USERIP = @USERIP

        BEGIN TRAN

        IF @WORKTYPE = 'NEW'
        BEGIN
            -- Parse XML into @TMP staging table variable and apply set-based INSERT/UPDATE/DELETE
            SET @OUTPUT = @ORGDIV
        END

        IF @@TRANCOUNT > 0
            COMMIT TRAN
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0
            ROLLBACK TRAN

        IF @DOC_ID IS NOT NULL
            EXEC SP_XML_REMOVEDOCUMENT @DOC_ID

        DECLARE @ERRMSG NVARCHAR(4000) = ERROR_MESSAGE()
        RAISERROR(@ERRMSG, 16, 1)
    END CATCH
END
```
