# 프로시저 골격

실제 근호·KH 작성 SP 중 복잡한 것(검증 여러 개, 채번, 헤더+상세 저장)을 기준으로 뽑은 골격이다. 테이블·열 이름은 가상이다. 실제 인자·타입·XML 경로는 대상 호출부와 스키마에서 가져온다.

## 조회(SELECT) SP

```sql
-- =============================================
-- AUTHOR:      {작성자명}
-- CREATE DATE: {첫작성일}
-- DESCRIPTION: {프로그램명} 조회
-- =============================================
CREATE PROCEDURE [dbo].[sp_XX000100_SELECT]
      @WORKTYPE VARCHAR(20) = NULL
    , @ORGDIV   VARCHAR(2)  = NULL
    , @FRDT     VARCHAR(8)  = NULL
    , @TODT     VARCHAR(8)  = NULL
    , @DOCNUM   VARCHAR(20) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @WORKTYPE = 'LIST'
    BEGIN
        SELECT 'N' AS CHK
             , A.ORGDIV
             , A.DOCNUM
             , A.ITEMCD
             , B.ITEMNM
             , ISNULL(C.PRODQTY, 0) AS PRODQTY
        FROM DOC_HEADER A
                LEFT OUTER JOIN ITEM_MASTER B
                             ON A.ITEMCD = B.ITEMCD
                LEFT OUTER JOIN (
                                 SELECT T.ORGDIV
                                      , T.DOCNUM
                                      , SUM(T.PRODQTY) AS PRODQTY
                                 FROM DOC_RESULT T
                                 WHERE T.ORGDIV = @ORGDIV
                                 GROUP BY T.ORGDIV, T.DOCNUM
                                ) C
                                ON A.ORGDIV = C.ORGDIV
                                AND A.DOCNUM = C.DOCNUM
        WHERE A.ORGDIV = @ORGDIV
          AND A.DOCDT BETWEEN @FRDT AND @TODT
        ORDER BY A.DOCDT DESC, A.DOCNUM;
    END
    ELSE IF @WORKTYPE = 'DETAIL'
    BEGIN
        SELECT A.SEQ
             , A.ITEMCD
             , A.QTY
        FROM DOC_DETAIL A
        WHERE A.ORGDIV = @ORGDIV
          AND A.DOCNUM = @DOCNUM
        ORDER BY A.SEQ;
    END
END;
```

- 인자는 한 줄에 하나, 선행 쉼표. 이름·타입·기본값의 시작 열을 맞춘다. 조회 인자는 `= NULL` 기본값을 둔다.
- `@WORKTYPE` 값은 C# 화면의 `enum SelectType` 멤버 이름과 같다(`_selectType.ToString()`으로 넘어온다).
- 모드마다 `IF … ELSE IF` 분기 하나. 한 모드가 여러 결과표를 돌려주면 같은 분기 안에 C#이 읽는 순서대로 둔다.
- 체크 열이 필요한 목록은 `'N' AS CHK`를 첫 열로 둔다.

## 저장(SAVE) SP — 헤더 + 상세

헤더 한 건과 상세 여러 행을 함께 저장하는 형태다. 단일 테이블 저장은 여기서 헤더나 상세 한쪽만 남기면 된다.

```sql
-- =============================================
-- AUTHOR:      {작성자명}
-- CREATE DATE: {첫작성일}
-- DESCRIPTION: {프로그램명} 처리
-- =============================================
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
        , REMARK  VARCHAR(500)
    );

    DECLARE @TMP_DETAIL TABLE
    (
          GBN     VARCHAR(3)
        , DOCNUM  VARCHAR(20)
        , SEQ     INT
        , ITEMCD  VARCHAR(20)
        , QTY     NUMERIC(18, 4)
        , REMARK  VARCHAR(500)
    );

    EXEC SP_XML_PREPAREDOCUMENT @DOC_ID OUTPUT, @XML;

    INSERT INTO @TMP_HEADER
    (
           GBN      , DOCNUM   , DOCDT
         , CUSTCD   , REMARK
    )
    SELECT A.GBN    , A.DOCNUM , A.DOCDT
         , A.CUSTCD , A.REMARK
    FROM OPENXML(@DOC_ID, '/ROOT/DOC_HEADER', 1)
    WITH
    (
          GBN     VARCHAR(3)
        , DOCNUM  VARCHAR(20)
        , DOCDT   VARCHAR(8)
        , CUSTCD  VARCHAR(8)
        , REMARK  VARCHAR(500)
    ) A;

    EXEC SP_XML_REMOVEDOCUMENT @DOC_ID;

    IF ISNULL(@XMLDETAIL, '') <> ''
    BEGIN
        EXEC SP_XML_PREPAREDOCUMENT @DOC_ID OUTPUT, @XMLDETAIL;

        INSERT INTO @TMP_DETAIL
        (
               GBN      , DOCNUM   , SEQ
             , ITEMCD   , QTY      , REMARK
        )
        SELECT A.GBN    , A.DOCNUM , A.SEQ
             , A.ITEMCD , A.QTY    , A.REMARK
        FROM OPENXML(@DOC_ID, '/ROOT/DOC_DETAIL', 1)
        WITH
        (
              GBN     VARCHAR(3)
            , DOCNUM  VARCHAR(20)
            , SEQ     INT
            , ITEMCD  VARCHAR(20)
            , QTY     NUMERIC(18, 4)
            , REMARK  VARCHAR(500)
        ) A;

        EXEC SP_XML_REMOVEDOCUMENT @DOC_ID;
    END

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
        IF EXISTS (
                   SELECT 1
                   FROM @TMP_HEADER A
                           INNER JOIN NEXT_DOC B
                                   ON B.ORGDIV = @ORGDIV
                                   AND A.DOCNUM = B.DOCNUM
                  )
        BEGIN
            RAISERROR('후속 자료가 존재합니다. 삭제 후 처리 가능합니다.', 16, 1);
            RETURN;
        END

        DELETE A
        FROM DOC_DETAIL A
                INNER JOIN @TMP_HEADER B
                        ON A.DOCNUM = B.DOCNUM
        WHERE A.ORGDIV = @ORGDIV;

        DELETE A
        FROM DOC_HEADER A
                INNER JOIN @TMP_HEADER B
                        ON A.DOCNUM = B.DOCNUM
        WHERE A.ORGDIV = @ORGDIV;
    END
    ELSE IF @WORKTYPE IN ('NEW', 'EDIT')
    BEGIN
        IF EXISTS (
                   SELECT 1
                   FROM @TMP_DETAIL A
                           LEFT OUTER JOIN ITEM_MASTER B
                                        ON A.ITEMCD = B.ITEMCD
                   WHERE A.GBN <> 'DEL'
                     AND B.ITEMCD IS NULL
                  )
        BEGIN
            RAISERROR('등록되지 않은 품목이 있습니다.', 16, 1);
            RETURN;
        END

        IF @WORKTYPE = 'NEW'
        BEGIN
            SELECT @DOCDT = A.DOCDT
            FROM @TMP_HEADER A;

            EXEC SP_SYSTEM_BA100T_KEYCODE @ORGDIV, 'DOC_HEADER', @DOCDT, @NEWSEQ OUTPUT;

            SET @DOCNUM = @DOCDT + '-' + CONVERT(VARCHAR(10), @NEWSEQ);

            INSERT INTO DOC_HEADER
            (
                   ORGDIV   , DOCNUM   , DOCDT
                 , CUSTCD   , REMARK   , REGDT
                 , REGEMPNO , REGIP
            )
            SELECT @ORGDIV  , @DOCNUM  , A.DOCDT
                 , A.CUSTCD , A.REMARK , GETDATE()
                 , @USERID  , @USERIP
            FROM @TMP_HEADER A;
        END
        ELSE IF @WORKTYPE = 'EDIT'
        BEGIN
            SELECT @DOCNUM = A.DOCNUM
            FROM @TMP_HEADER A;

            UPDATE A
            SET A.CUSTCD = B.CUSTCD
              , A.REMARK = B.REMARK
              , A.MODDT = GETDATE()
              , A.MODEMPNO = @USERID
              , A.MODIP = @USERIP
            FROM DOC_HEADER A
                    INNER JOIN @TMP_HEADER B
                            ON A.DOCNUM = B.DOCNUM
            WHERE A.ORGDIV = @ORGDIV;

            DELETE A
            FROM DOC_DETAIL A
                    INNER JOIN @TMP_DETAIL B
                            ON A.DOCNUM = B.DOCNUM
                            AND A.SEQ = B.SEQ
            WHERE A.ORGDIV = @ORGDIV
              AND B.GBN = 'DEL';

            UPDATE A
            SET A.ITEMCD = B.ITEMCD
              , A.QTY = B.QTY
              , A.REMARK = B.REMARK
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
             , ITEMCD    , QTY      , REMARK
             , REGDT     , REGEMPNO , REGIP
        )
        SELECT @ORGDIV   , @DOCNUM  , ISNULL(B.MAXSEQ, 0) + ROW_NUMBER() OVER (ORDER BY A.SEQ)
             , A.ITEMCD  , A.QTY    , A.REMARK
             , GETDATE() , @USERID  , @USERIP
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

순서와 이유:

1. **로그 → XML 파싱**: `SP_XML_LOG_SAVE`를 먼저 부르고, 헤더·상세 XML을 각각 테이블 변수에 담는다. 상세 XML은 없을 수 있으므로 `IF ISNULL(@XMLDETAIL, '') <> ''` 안에서 파싱한다.
2. **공통 검증**: 모든 모드에 해당하는 검증(마감 등)을 분기 앞에 한 번 둔다. `IF EXISTS … RAISERROR … RETURN` 형태다.
3. **모드 분기**: `DELETE`와 `NEW/EDIT`를 `IF … ELSE IF`로 나눈다. 모드별 검증은 그 분기 안에 둔다.
4. **삭제**: 상세 먼저, 헤더 나중.
5. **NEW**: 채번(`SP_SYSTEM_BA100T_KEYCODE`) → 문서번호 조립 → 헤더 INSERT.
6. **EDIT**: 헤더 UPDATE → 상세 `DEL` 삭제 → 상세 `MOD` 수정.
7. **상세 NEW INSERT는 NEW·EDIT 공통**이라 두 분기 뒤에 한 번만 둔다. 순번은 파생 MAX + `ROW_NUMBER()`로 INSERT 안에서 매긴다.
8. **@OUTPUT**: 화면이 저장 후 다시 조회할 키를 돌려준다.

지킬 점:

- `@WORKTYPE` 값은 화면이 보내는 `m_Editmode.ToString().ToUpper()`다. 화면마다 다르다(목록형 화면은 신규 등록이 `EDIT`, 수정이 `UPDATE`인 경우가 있다). **호출부에서 실제 값을 확인하고 분기 이름을 맞춘다.**
- XML 경로 `/ROOT/<이름>`의 `<이름>`은 C#에서 `dt.TableName`에 넣은 값이다. 행 상태는 `GBN` 속성(NEW·MOD·DEL)으로 온다.
- 테이블 변수와 `OPENXML … WITH`의 열 목록·타입은 같은 순서로 맞춘다. 타입은 실제 테이블 스키마에서 가져온다. `INSERT … SELECT *`로 줄이지 않는다.
- 변수는 `@DOC_ID`(XML 핸들), `@DOCDT`·`@NEWSEQ`(채번 EXEC 인자), `@DOCNUM`(여러 문장에서 쓰는 생성 번호)만 둔다. 그 밖의 헤더 값은 `@TMP_HEADER`를 JOIN해서 읽는다.
- 트랜잭션 코드는 없다. 호출부가 `ExecSPTrn`일 때의 형태다. 호출부가 `ExecSP`이면 [save.md](save.md#트랜잭션)를 따른다.
- `@XMLDETAIL`처럼 화면이 `null`로 넘길 수 있는 인자는 `= NULL` 기본값을 둔다. [save.md](save.md#화면이-null로-넘길-수-있는-인자)
- 프로젝트 공통 함수(`F_CHECK_CLOSE`, `RETURN_KEYCODE`, 채번 SP)의 인자와 쓰는 법은 [kone.md](kone.md)에 있다.

## CASE

짧으면 한 줄, 길면 WHEN/ELSE/END를 CASE 다음 칸에 맞춘다. 전체를 괄호로 감싼다.

```sql
UPDATE A
SET A.PLANTIME = (CASE WHEN A.QTY = 0 THEN A.PLANTIME
                       ELSE ROUND(A.PLANTIME / A.QTY, 0) * B.PLANQTY
                  END)
  , A.QTY = B.PLANQTY
  , A.MODDT = GETDATE()
  , A.MODEMPNO = @USERID
FROM DOC_HEADER A
        INNER JOIN @TMP_DETAIL B
                ON A.DOCNUM = B.DOCNUM
WHERE A.ORGDIV = @ORGDIV
```

```sql
SELECT B.ITEMNM + (CASE WHEN B.SPEC IS NULL OR B.SPEC = '' THEN '' ELSE ' ' + B.SPEC END) AS ITEMNM
```
