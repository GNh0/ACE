-- =============================================
-- AUTHOR:      테스트
-- CREATE DATE: 2026.11.24
-- DESCRIPTION: 발주 상세 추가 저장(점검용)
-- =============================================
CREATE PROCEDURE [dbo].[sp_TEST300_SAVE]
      @WORKTYPE   VARCHAR(20)
    , @ORGDIV     VARCHAR(2)
    , @USERID     VARCHAR(50)
    , @USERIP     VARCHAR(100)
    , @PURNUM     VARCHAR(20)
    , @XML_XX110T VARCHAR(MAX)
    , @OUTPUT     VARCHAR(20)  OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @DOC_ID  INT
          , @MAXSEQ  INT
          , @I       INT = 1
          , @CNT     INT

    DECLARE @TMPXX110T TABLE
    (
          SEQ      INT IDENTITY(1, 1)
        , GBN      VARCHAR(3)
        , PURSEQ2  NUMERIC(5, 0)
        , ITEMCD   VARCHAR(20)
        , QTY      NUMERIC(18, 4)
    )

    EXEC SP_XML_PREPAREDOCUMENT @DOC_ID OUTPUT, @XML_XX110T

    INSERT INTO @TMPXX110T
    (
           GBN , PURSEQ2, ITEMCD, QTY
    )
    SELECT GBN , PURSEQ2, ITEMCD, QTY
    FROM OPENXML (@DOC_ID, '/ROOT/XX110T', 1)
    WITH
    (
          GBN      VARCHAR(3)
        , PURSEQ2  NUMERIC(5, 0)
        , ITEMCD   VARCHAR(20)
        , QTY      NUMERIC(18, 4)
    )

    EXEC SP_XML_REMOVEDOCUMENT @DOC_ID

    SELECT @MAXSEQ = ISNULL(MAX(PURSEQ2), 0)
    FROM XX110T
    WHERE ORGDIV = @ORGDIV
      AND PURNUM = @PURNUM

    SELECT @CNT = COUNT(*) FROM @TMPXX110T

    WHILE @I <= @CNT
    BEGIN
        UPDATE @TMPXX110T
        SET PURSEQ2 = @MAXSEQ + @I
        WHERE SEQ = @I
          AND GBN = 'NEW'

        SET @I = @I + 1
    END

    INSERT INTO XX110T
    (
           ORGDIV , PURNUM , PURSEQ2, ITEMCD
         , QTY    , REGDT  , REGEMPNO, REGIP
    )
    SELECT @ORGDIV, @PURNUM, A.PURSEQ2, A.ITEMCD
         , A.QTY  , GETDATE(), @USERID, @USERIP
    FROM @TMPXX110T A
    WHERE A.GBN = 'NEW'

    SET @OUTPUT = @PURNUM
END
