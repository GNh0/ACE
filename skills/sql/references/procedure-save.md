# Procedure skeleton: SAVE

Table and column names are fictional. Header comment: [procedure.md](procedure.md#procedure-header). The rules live in [save.md](save.md).

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

    EXEC SP_XML_LOG_SAVE @@PROCID, @WORKTYPE, @USERID, @XML, @XMLDETAIL;

    SET @OUTPUT = '';

    DECLARE @DOC_ID INT;
    DECLARE @DOCDT  VARCHAR(8);
    DECLARE @NEWSEQ INT;
    DECLARE @DOCNUM VARCHAR(20);

    DECLARE @TMP_HEADER TABLE
    (
          GBN     VARCHAR(3)
        , DOCNUM  VARCHAR(20)
        , DOCDT   VARCHAR(8)
        , CUSTCD  VARCHAR(8)
    );

    -- @TMP_DETAIL: same form (GBN, DOCNUM, SEQ, ITEMCD, QTY)

    EXEC SP_XML_PREPAREDOCUMENT @DOC_ID OUTPUT, @XML;

    INSERT INTO @TMP_HEADER
    (
           GBN    , DOCNUM   , DOCDT
         , CUSTCD
    )
    SELECT A.GBN  , A.DOCNUM , A.DOCDT
         , A.CUSTCD
    FROM OPENXML(@DOC_ID, '/ROOT/DOC_HEADER', 1)
    WITH
    (
          GBN     VARCHAR(3)
        , DOCNUM  VARCHAR(20)
        , DOCDT   VARCHAR(8)
        , CUSTCD  VARCHAR(8)
    ) A;

    EXEC SP_XML_REMOVEDOCUMENT @DOC_ID;

    IF ISNULL(@XMLDETAIL, '') <> ''
    BEGIN
        -- parse '/ROOT/DOC_DETAIL' into @TMP_DETAIL the same way
    END

    -- checks for every mode (closing etc., kone.md F_CHECK_CLOSE)
    IF EXISTS (
               SELECT 1
               FROM @TMP_HEADER A
               WHERE DBO.F_CHECK_CLOSE(@ORGDIV, 'MA', '2', LEFT(A.DOCDT, 6), '1') = 'Y'
              )
    BEGIN
        RAISERROR('월 마감이 완료되었습니다. 년/월마감 프로그램에서 월마감 해제 후 처리 가능합니다.', 16, 9);
        RETURN;
    END

    IF @WORKTYPE = 'DELETE'
    BEGIN
        -- DELETE-only checks (later documents exist → RAISERROR … RETURN)

        DELETE A
        FROM DOC_DETAIL A
                INNER JOIN @TMP_HEADER B
                        ON A.DOCNUM = B.DOCNUM
        WHERE A.ORGDIV = @ORGDIV;

        -- DOC_HEADER deleted the same way
    END
    ELSE IF @WORKTYPE IN ('NEW', 'EDIT')
    BEGIN
        -- NEW/EDIT checks (unregistered item etc., rows with GBN <> 'DEL')

        IF @WORKTYPE = 'NEW'
        BEGIN
            SELECT @DOCDT = A.DOCDT
            FROM @TMP_HEADER A;

            EXEC SP_SYSTEM_BA100T_KEYCODE @ORGDIV, 'DOC_HEADER', @DOCDT, @NEWSEQ OUTPUT;

            SET @DOCNUM = @DOCDT + '-' + CONVERT(VARCHAR(10), @NEWSEQ);

            -- DOC_HEADER INSERT from @TMP_HEADER (REGDT = GETDATE(), REGEMPNO = @USERID, REGIP = @USERIP)
        END
        ELSE IF @WORKTYPE = 'EDIT'
        BEGIN
            SELECT @DOCNUM = A.DOCNUM
            FROM @TMP_HEADER A;

            -- header UPDATE; detail GBN = 'DEL' DELETE

            UPDATE A
            SET A.ITEMCD = B.ITEMCD
              , A.QTY = B.QTY
              , A.MODDT = GETDATE()
              , A.MODEMPNO = @USERID
              , A.MODIP = @USERIP
            FROM DOC_DETAIL A
                    INNER JOIN @TMP_DETAIL B
                            ON A.DOCNUM = B.DOCNUM
                            AND A.SEQ = B.SEQ
            WHERE A.ORGDIV = @ORGDIV
              AND B.GBN = 'MOD';
        END

        INSERT INTO DOC_DETAIL
        (
               ORGDIV    , DOCNUM   , SEQ
             , ITEMCD    , QTY      , REGDT
             , REGEMPNO  , REGIP
        )
        SELECT @ORGDIV   , @DOCNUM  , ISNULL(B.MAXSEQ, 0) + ROW_NUMBER() OVER (ORDER BY A.SEQ)
             , A.ITEMCD  , A.QTY    , GETDATE()
             , @USERID   , @USERIP
        FROM @TMP_DETAIL A
                LEFT OUTER JOIN (
                                 SELECT T.ORGDIV
                                      , T.DOCNUM
                                      , MAX(T.SEQ) AS MAXSEQ
                                 FROM DOC_DETAIL T
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

1. **Log → XML parsing**: call `SP_XML_LOG_SAVE` first, then parse header and detail XML into table variables. Detail XML may be missing, so parse it inside `IF ISNULL(@XMLDETAIL, '') <> ''`.
2. **Shared checks**: checks for every mode (closing etc.) once, before the branches, as `IF EXISTS … RAISERROR … RETURN`.
3. **Mode branches**: `DELETE` and `NEW/EDIT` via `IF … ELSE IF`. Mode-specific checks go inside their branch.
4. **DELETE**: details first, header last.
5. **NEW**: numbering → build document number → header INSERT.
6. **EDIT**: header UPDATE → detail `DEL` delete → detail `MOD` update.
7. **Detail NEW INSERT is shared by NEW and EDIT**, so it comes once after both. Sequence: derived MAX + `ROW_NUMBER()`.
8. **@OUTPUT**: the key the screen re-queries after saving.

Keep in mind:

- `@WORKTYPE` is what the screen sends (`m_Editmode.ToString().ToUpper()`), and it differs by screen (list screens may send `EDIT` for new and `UPDATE` for edit). **Check the real value in the caller and name the branches to match.**
- `<name>` in the XML path `/ROOT/<name>` is the C# `dt.TableName`. Row state comes in the `GBN` attribute (NEW/MOD/DEL).
- Table variable and `OPENXML … WITH` column lists/types are in the same order, types from the real schema. Never shorten to `INSERT … SELECT *`.
- Variables: only `@DOC_ID`, `@DOCDT`/`@NEWSEQ` (numbering arguments), `@DOCNUM` (number used by several statements). Other header values: JOIN `@TMP_HEADER`.
- No transaction code: this is the form for an `ExecSPTrn` caller. For `ExecSP` see [save-tran.md](save-tran.md#transactions).
- Arguments the screen may pass as `null`, like `@XMLDETAIL`, get `= NULL`. [save-tran.md](save-tran.md#arguments-the-screen-may-pass-as-null)
- Common functions (`F_CHECK_CLOSE`, `RETURN_KEYCODE`, numbering SP): [kone.md](kone.md).
