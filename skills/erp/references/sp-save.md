# Procedure skeleton: SAVE

Table and column names are fictional. Header comment: [sp-skeleton.md](sp-skeleton.md#procedure-header). The rules live in [save.md](../../sql/references/save.md).

## SAVE SP: header + detail

Saves one header and several details together. For a single-table save keep one side.

```sql
CREATE PROCEDURE [dbo].[sp_XX000100_SAVE]
      @WORKTYPE  VARCHAR(20)
    , @ORGDIV    VARCHAR(2)
    , @USERID    VARCHAR(20)
    , @USERIP    VARCHAR(50)
    , @XML       VARCHAR(MAX)
    , @XMLDETAIL VARCHAR(MAX) = NULL
    , @OUTPUT    VARCHAR(20) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    EXEC SP_LOG_XML @@PROCID, @WORKTYPE, @USERID, @XML, @XMLDETAIL;

    IF (ISNULL(@XML, '') = '') RETURN;

    SET @OUTPUT = '';

    DECLARE @DOC_ID INT;
    DECLARE @DOCDT  VARCHAR(8);
    DECLARE @NEWSEQ INT;
    DECLARE @DOCNUM VARCHAR(20);

    DECLARE @TMPXX100T TABLE
    (
          GBN     VARCHAR(3)
        , DOCNUM  VARCHAR(20)
        , DOCDT   VARCHAR(8)
        , CUSTCD  VARCHAR(8)
    );

    -- @TMPXX110T: same form (GBN, DOCNUM, SEQ, ITEMCD, QTY)

    EXEC SP_XML_PREPAREDOCUMENT @DOC_ID OUTPUT, @XML;

    INSERT INTO @TMPXX100T
    SELECT *
    FROM OPENXML(@DOC_ID, '/ROOT/XX100T', 1)
    WITH
    (
          GBN     VARCHAR(3)
        , DOCNUM  VARCHAR(20)
        , DOCDT   VARCHAR(8)
        , CUSTCD  VARCHAR(8)
    );

    EXEC SP_XML_REMOVEDOCUMENT @DOC_ID;

    IF ISNULL(@XMLDETAIL, '') <> ''
    BEGIN
        -- parse '/ROOT/XX110T' into @TMPXX110T the same way
    END

    -- checks for every mode (closing etc., common-sp.md F_IS_CLOSED)
    IF EXISTS (
               SELECT 1
               FROM @TMPXX100T A
               WHERE DBO.F_IS_CLOSED(@ORGDIV, 'MA', '2', LEFT(A.DOCDT, 6), '1') = 'Y'
              )
    BEGIN
        RAISERROR('월 마감이 완료되었습니다. 년/월마감 프로그램에서 월마감 해제 후 처리 가능합니다.', 16, 9);
        RETURN;
    END

    IF @WORKTYPE = 'DELETE'
    BEGIN
        -- DELETE-only checks (later documents exist → RAISERROR … RETURN)

        DELETE A
        FROM XX110T A
                INNER JOIN @TMPXX100T B
                        ON A.DOCNUM = B.DOCNUM
        WHERE A.ORGDIV = @ORGDIV;

        -- XX100T deleted the same way
    END
    ELSE IF @WORKTYPE IN ('NEW', 'EDIT')
    BEGIN
        -- NEW/EDIT checks (unregistered item etc., rows with GBN <> 'DEL')

        IF @WORKTYPE = 'NEW'
        BEGIN
            SELECT @DOCDT = A.DOCDT
            FROM @TMPXX100T A;

            EXEC SP_NEW_KEY @ORGDIV, 'XX100T', @DOCDT, @NEWSEQ OUTPUT;

            SET @DOCNUM = @DOCDT + '-' + CONVERT(VARCHAR(10), @NEWSEQ);

            -- XX100T INSERT from @TMPXX100T (REGDT = GETDATE(), REGEMPNO = @USERID, REGIP = @USERIP)
        END
        ELSE IF @WORKTYPE = 'EDIT'
        BEGIN
            SELECT @DOCNUM = A.DOCNUM
            FROM @TMPXX100T A;

            -- header UPDATE; detail GBN = 'DEL' DELETE

            UPDATE A
            SET A.ITEMCD = B.ITEMCD
              , A.QTY = B.QTY
              , A.MODDT = GETDATE()
              , A.MODEMPNO = @USERID
              , A.MODIP = @USERIP
            FROM XX110T A
                    INNER JOIN @TMPXX110T B
                            ON A.DOCNUM = B.DOCNUM
                            AND A.SEQ = B.SEQ
            WHERE A.ORGDIV = @ORGDIV
              AND B.GBN = 'MOD';
        END

        INSERT INTO XX110T
        (
               ORGDIV    , DOCNUM   , SEQ
             , ITEMCD    , QTY      , REGDT
             , REGEMPNO  , REGIP
        )
        SELECT @ORGDIV   , @DOCNUM  , ISNULL(B.MAXSEQ, 0) + ROW_NUMBER() OVER (ORDER BY A.SEQ)
             , A.ITEMCD  , A.QTY    , GETDATE()
             , @USERID   , @USERIP
        FROM @TMPXX110T A
                LEFT OUTER JOIN (
                                 SELECT T.ORGDIV
                                      , T.DOCNUM
                                      , MAX(T.SEQ) AS MAXSEQ
                                 FROM XX110T T
                                 WHERE T.ORGDIV = @ORGDIV
                                   AND T.DOCNUM = @DOCNUM
                                 GROUP BY T.ORGDIV, T.DOCNUM
                                ) B
                                ON B.ORGDIV = @ORGDIV
                                AND B.DOCNUM = @DOCNUM
        WHERE A.GBN = 'NEW';

        SET @OUTPUT = @DOCNUM;
    END
END;
```

Order:

1. **Log → empty check → XML parsing**: call `SP_LOG_XML` first (every XML argument), then (optional) `IF (ISNULL(@XML, '') = '') RETURN;`, then parse header and detail XML into table variables named after their target table (`@TMPMA200T`, `@TMPMA210T`). Detail XML may be missing, so parse it inside `IF ISNULL(@XMLDETAIL, '') <> ''`. (The early return is optional: with or without it is fine, user 2026-11-24.)
2. **Shared checks**: checks for every mode (closing etc.) once, before the branches, as `IF EXISTS … RAISERROR … RETURN`.
3. **Mode branches**: `DELETE` and `NEW/EDIT` via `IF … ELSE IF`. Mode-specific checks go inside their branch.
4. **DELETE**: details first, header last.
5. **NEW**: numbering → build document number → header INSERT.
6. **EDIT**: header UPDATE → detail `DEL` delete → detail `MOD` update.
7. **Detail NEW INSERT is shared by NEW and EDIT**, so it comes once after both. Sequence: derived MAX + `ROW_NUMBER()`.
8. **@OUTPUT**: the key the screen re-queries after saving.

Keep in mind:

- `@WORKTYPE` is what the screen sends (`m_EditState.ToString().ToUpper()`), and it differs by screen (list screens may send `EDIT` for new and `UPDATE` for edit). **Check the real value in the caller and name the branches to match.**
- `<name>` in the XML path `/ROOT/<name>` is the C# `dt.TableName`. Row state comes in the `GBN` attribute (NEW/MOD/DEL).
- Staging: `INSERT INTO @TMP<TABLE> SELECT * FROM OPENXML(…) WITH (…)` is the user's usual form; an explicit column list is equally fine (user 2026-11-24: "어차피 저장되는데 크게 문제 없고"), never a finding; the table variable and the `WITH` list have the same columns in the same order, types from the real schema. List columns explicitly (`INSERT (…) SELECT A.…`) only when the staging table differs from the XML (extra IDENTITY `SEQ`, computed or renamed columns).
- Variables: only `@DOC_ID`, `@DOCDT`/`@NEWSEQ` (numbering arguments), `@DOCNUM` (number used by several statements). Other header values: JOIN `@TMPXX100T`.
- No transaction code: this is the form for an `SaveTrn` caller. For `SaveNoTrn` see [save-call.md](save-call.md#transactions).
- Arguments the screen may pass as `null`, like `@XMLDETAIL`, get `= NULL`. [save-call.md](save-call.md#arguments-the-screen-may-pass-as-null)
- Common functions (`F_IS_CLOSED`, `F_SPLIT_KEY`, numbering SP): [common-sp.md](common-sp.md).
- Errors: business checks `RAISERROR('…', 16, 1); RETURN;`, the closing checks (`F_IS_CLOSED`) `16, 9`. Messages are polite Korean sentences, usually ending `확인 후 진행바랍니다.` / `~할 수 없습니다.` (PROJECT_B: 16,1 in every business check of 30+ SAVEs; 16,9 only on closing messages.)
- Never leave a debug `SELECT * FROM @TMP…` or a preview `SELECT` in a SAVE: the screen reads the wrong result set. Audit columns: `MODIP = @USERIP` (never `@USERID`).
- Mode names follow the project's `EditMode` (PROJECT_B: `EDIT` = new, `UPDATE` = modify, order EDIT → UPDATE → DELETE; see the project file). The skeleton's NEW/EDIT is one project's naming.
