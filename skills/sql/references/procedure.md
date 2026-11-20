# 프로시저 골격

실제 근호·KH 작성 SP에서 뽑은 공통 골격이다. 테이블·열 이름은 가상이다. 실제 인자·타입·XML 경로는 대상 호출부와 스키마에서 가져온다.

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

## 저장(SAVE) SP 앞부분

```sql
-- =============================================
-- AUTHOR:      {작성자명}
-- CREATE DATE: {첫작성일}
-- DESCRIPTION: {프로그램명} 처리
-- =============================================
CREATE PROCEDURE [dbo].[sp_XX000100_SAVE]
      @WORKTYPE VARCHAR(20)
    , @ORGDIV   VARCHAR(2)
    , @USERID   VARCHAR(20)
    , @USERIP   VARCHAR(50)
    , @XML      VARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;

    EXEC SP_XML_LOG_SAVE @@PROCID, @WORKTYPE, @USERID, @XML;

    DECLARE @DOC_ID INT;

    DECLARE @TMP_DETAIL TABLE
    (
          GBN     VARCHAR(3)
        , DOCNUM  VARCHAR(20)
        , SEQ     INT
        , ITEMCD  VARCHAR(20)
        , QTY     NUMERIC(18, 4)
    );

    EXEC SP_XML_PREPAREDOCUMENT @DOC_ID OUTPUT, @XML;

    INSERT INTO @TMP_DETAIL
    (
           GBN      , DOCNUM   , SEQ
         , ITEMCD   , QTY
    )
    SELECT A.GBN    , A.DOCNUM , A.SEQ
         , A.ITEMCD , A.QTY
    FROM OPENXML(@DOC_ID, '/ROOT/DOC_DETAIL', 1)
    WITH
    (
          GBN     VARCHAR(3)
        , DOCNUM  VARCHAR(20)
        , SEQ     INT
        , ITEMCD  VARCHAR(20)
        , QTY     NUMERIC(18, 4)
    ) A;

    EXEC SP_XML_REMOVEDOCUMENT @DOC_ID;

    -- 이후: 검증(IF EXISTS … RAISERROR … RETURN) → WORKTYPE 분기 → 쓰기
    -- 형태는 save.md의 SAVE 고정 규칙을 따른다.
END;
```

- `@WORKTYPE`은 C#의 `m_Editmode.ToString().ToUpper()` 값이다. 화면이 실제로 보내는 값(NEW, EDIT, UPDATE, DELETE 등)을 호출부에서 확인한다.
- XML 경로 `/ROOT/<이름>`의 `<이름>`은 C#에서 `dt.TableName`에 넣은 값이다. 행 상태는 `GBN` 속성(NEW·MOD·DEL)으로 온다.
- `SP_XML_LOG_SAVE` 호출은 대상 프로젝트의 기존 SAVE에 있으면 같은 위치에 둔다.
- 테이블 변수와 `OPENXML … WITH`의 열 목록·타입은 같은 순서로 맞춘다. 타입은 실제 테이블 스키마에서 가져온다.
- 테이블 변수는 XML 파싱 결과를 담는 데만 쓴다.
- 검증 실패는 `RAISERROR('메시지', 16, 1); RETURN;`으로 끝낸다. C#의 `ExecSPTrn`이 예외를 받아 롤백한다.

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
