-- =============================================
-- AUTHOR:      테스트
-- CREATE DATE: 2026.11.24
-- DESCRIPTION: 외주입고 저장(점검용)
-- =============================================
CREATE PROCEDURE [dbo].[sp_TEST100_SAVE]
      @WORKTYPE   VARCHAR(20)
    , @ORGDIV     VARCHAR(2)
    , @USERID     VARCHAR(50)
    , @USERIP     VARCHAR(100)
    , @XML_XM210T VARCHAR(MAX)
    , @OUTPUT     VARCHAR(20)  OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @DOC_ID INT
          , @RECDT  VARCHAR(8) = CONVERT(VARCHAR(8), GETDATE(), 112)
          , @SEQ1   INT

    DECLARE @TMPMA210T TABLE
    (
          SEQ        INT IDENTITY(1, 1)
        , GBN        VARCHAR(3)
        , PURNUM     VARCHAR(20)
        , PURSEQ2    NUMERIC(5, 0)
        , ITEMCD     VARCHAR(20)
        , QTY        NUMERIC(18, 4)
        , CUSTLOTNUM VARCHAR(200)
    )

    EXEC SP_XML_PREPAREDOCUMENT @DOC_ID OUTPUT, @XML_XM210T

    INSERT INTO @TMPMA210T
    (
           GBN    , PURNUM , PURSEQ2, ITEMCD
         , QTY    , CUSTLOTNUM
    )
    SELECT GBN    , PURNUM , PURSEQ2, ITEMCD
         , QTY    , CUSTLOTNUM
    FROM OPENXML (@DOC_ID, '/ROOT/XM210T', 1)
    WITH
    (
          GBN        VARCHAR(3)
        , PURNUM     VARCHAR(20)
        , PURSEQ2    NUMERIC(5, 0)
        , ITEMCD     VARCHAR(20)
        , QTY        NUMERIC(18, 4)
        , CUSTLOTNUM VARCHAR(200)
    )

    EXEC SP_XML_REMOVEDOCUMENT @DOC_ID

    IF @WORKTYPE = 'NEW'
    BEGIN
        EXEC SP_NEW_KEY @ORGDIV, 'SY100T', @RECDT, @SEQ1 OUTPUT

        INSERT INTO XM210T
        (
               ORGDIV  , RECDT   , SEQ1    , SEQ2
             , PURNUM  , PURSEQ2 , ITEMCD  , ITEMNM
             , QTY     , PROCCD  , HEATLOTNUM
             , REGDT   , REGEMPNO, REGIP
        )
        SELECT @ORGDIV , @RECDT  , @SEQ1   , ROW_NUMBER() OVER (ORDER BY A.SEQ)
             , A.PURNUM, A.PURSEQ2, A.ITEMCD, B.ITEMNM
             , A.QTY   , C.PROCCD, (CASE WHEN C.PROCCD = '06' THEN A.CUSTLOTNUM END)
             , GETDATE(), @USERID, @USERIP
        FROM @TMPMA210T A
                INNER JOIN MS020T B
                        ON B.ORGDIV = @ORGDIV
                        AND A.ITEMCD = B.ITEMCD
                INNER JOIN XX110T C
                        ON C.ORGDIV = @ORGDIV
                        AND A.PURNUM = C.PURNUM
                        AND A.PURSEQ2 = C.PURSEQ2
        WHERE A.GBN = 'NEW'

        IF EXISTS (
                   SELECT 1
                   FROM XM210T A
                           INNER JOIN XX110T B
                                   ON A.ORGDIV = B.ORGDIV
                                   AND A.PURNUM = B.PURNUM
                                   AND A.PURSEQ2 = B.PURSEQ2
                   WHERE A.ORGDIV = @ORGDIV
                   GROUP BY B.PURNUM, B.PURSEQ2, B.QTY
                   HAVING SUM(A.QTY) > B.QTY
                  )
        BEGIN
            RAISERROR('발주수량을 초과하여 입고할 수 없습니다.', 16, 1);
            RETURN;
        END
    END

    SET @OUTPUT = @RECDT + '-' + CONVERT(VARCHAR(10), @SEQ1)
END
