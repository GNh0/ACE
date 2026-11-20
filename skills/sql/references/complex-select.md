# 복잡한 조회

BOM 전개, 월별 피벗처럼 구조가 복잡한 조회의 형태다. 실제 근호·KH 작성 SP(BOM역전개, 공정불량율)에서 뽑았고 이름은 가상이다. 수불장·재고 조회는 아직 기준 SP를 받지 못해 여기 없다.

복잡한 조회일수록 먼저 **결과 한 행이 무엇인지**(품목 1개? 품목×월? 문서×공정?)를 적고, 각 파생 테이블이 그 단위를 지키는지 확인한다. 파생 하나가 행을 늘리면 뒤의 합계가 전부 틀어진다.

## BOM 전개·역전개

```sql
SELECT B.PARENTID
     , B.ID
     , B.ITEMCD
     , C.ITEMNM
     , B.UNITQTY
FROM (
      SELECT T.PRNTITEMCD
      FROM BOM_DETAIL T
              INNER JOIN (
                          SELECT T.PRNTITEMCD
                               , MAX(T.RVNO) AS MAXRVNO
                          FROM BOM_REVISION T
                          GROUP BY T.PRNTITEMCD
                         ) T1
                         ON T.PRNTITEMCD = T1.PRNTITEMCD
                         AND T.RVNO = T1.MAXRVNO
      WHERE T.CHLDITEMCD = @ITEMCD
      GROUP BY T.PRNTITEMCD
     ) A
        CROSS APPLY DBO.ITEMBOMTREE(A.PRNTITEMCD) B
        LEFT OUTER JOIN ITEM_MASTER C
                     ON B.ITEMCD = C.ITEMCD
ORDER BY B.PARENTID, B.SORTKEY;
```

- 계층 전개는 재귀 CTE를 새로 쓰지 않고 프로젝트의 **기존 테이블 함수**(`ITEMBOMTREE` 등)를 `CROSS APPLY`로 부른다. 함수의 실제 반환 열과 정렬 키를 정의에서 확인한다.
- **최신 리비전만** 쓴다: 리비전 테이블을 품목별 `MAX(RVNO)`로 GROUP BY한 파생을 JOIN한다. 이 조건을 빼먹으면 과거 리비전 자식까지 섞여 나온다.
- 역전개(자식 → 부모)는 먼저 시작 품목을 자식으로 가진 부모 목록을 파생 A로 만들고, 그 부모들을 전개한다.
- 트리 그리드에 바인딩하는 결과는 부모 키·자기 키·정렬 키(`PARENTID`, `ID`, `SORTKEY`) 열을 그대로 돌려준다. 화면의 TreeList가 이 열 이름을 쓴다.
- 소요량은 단위 수량을 계층마다 곱한 값이다. 함수가 누적 수량을 주는지, 단계별 수량만 주는지 확인하고 중복 곱셈을 피한다.

## 월별 피벗

행은 구분(생산수량·불량수량·불량율), 열은 월(01~12, TOTAL)인 결과다.

```sql
SELECT P.GBCD
     , P.GBNM
     , P.[01] AS MON01
     , P.[02] AS MON02
     , P.[03] AS MON03
     , P.[TOTAL] AS TOTAL
FROM (
      SELECT A2.GBCD
           , A2.GBNM
           , A.MON
           , A2.VAL
      FROM (
            VALUES ('01'), ('02'), ('03'), ('TOTAL')
           ) A(MON)
              LEFT OUTER JOIN (
                               SELECT (CASE WHEN GROUPING(T.MON) = 1 THEN 'TOTAL' ELSE T.MON END) AS MON
                                    , SUM(T.BADQTY) AS BADQTY
                                    , SUM(T.PRODQTY) AS PRODQTY
                               FROM (
                                     SELECT SUBSTRING(T.RECDT, 5, 2) AS MON
                                          , SUM(T.BADQTY) AS BADQTY
                                          , 0 AS PRODQTY
                                     FROM BAD_RESULT T
                                     WHERE T.ORGDIV = @ORGDIV
                                       AND T.RECDT BETWEEN @FRDT AND @TODT
                                     GROUP BY SUBSTRING(T.RECDT, 5, 2)

                                     UNION ALL

                                     SELECT SUBSTRING(T.INDT, 5, 2) AS MON
                                          , 0 AS BADQTY
                                          , SUM(T.QTY) AS PRODQTY
                                     FROM PROD_RESULT T
                                     WHERE T.ORGDIV = @ORGDIV
                                       AND T.INDT BETWEEN @FRDT AND @TODT
                                     GROUP BY SUBSTRING(T.INDT, 5, 2)
                                    ) T
                               GROUP BY ROLLUP(T.MON)
                              ) A1
                              ON A.MON = A1.MON
              CROSS APPLY (
                           VALUES ('A', '생산수량', A1.PRODQTY)
                                , ('B', '불량수량', A1.BADQTY)
                                , ('C', '불량율(%)', CONVERT(NUMERIC(18, 1), A1.BADQTY / NULLIF(A1.PRODQTY, 0) * 100.0))
                          ) A2(GBCD, GBNM, VAL)
     ) A
PIVOT (
       MAX(VAL)
       FOR MON IN ([01], [02], [03], [TOTAL])
      ) P
ORDER BY P.GBCD;
```

안쪽에서 바깥 순서로 읽는다.

1. **원천별 월 집계를 UNION ALL**: 원천이 다른 값(불량, 생산)은 같은 열 구조로 맞추고 자기 값이 아닌 열은 0으로 둔다. 원천끼리 JOIN하지 않는다(행이 곱해진다).
2. **`GROUP BY ROLLUP`으로 합계 행**을 만들고, `GROUPING()`으로 합계 행의 월 값을 `'TOTAL'`로 바꾼다.
3. **월 목록은 `VALUES` 파생** `A(MON)`으로 만들고 집계를 LEFT OUTER JOIN한다. 자료가 없는 월도 열이 나온다.
4. **`CROSS APPLY (VALUES …)`로 한 월을 여러 행으로 펼친다**(생산수량 행, 불량수량 행, 불량율 행). 구분 코드(`GBCD`)가 정렬 키다.
5. **PIVOT**: `MAX(VAL) FOR MON IN (…)`. 바깥 SELECT에서 `P.[01] AS MON01`처럼 화면 FieldName에 맞는 열 이름을 붙인다.

지킬 점:

- **비율은 합계끼리 나눈다.** TOTAL 열의 불량율은 월별 불량율의 합이나 평균이 아니라 `불량 합계 / 생산 합계`다. 위 구조는 ROLLUP 행에서 다시 계산하므로 맞다.
- 분모는 `NULLIF(…, 0)`으로 0 나눗셈을 막는다. 결과가 NULL일 때 0으로 바꿀지는 사용자 요청이 있을 때만 정한다.
- 차트용 결과가 따로 필요하면 PIVOT 전 형태(구분, 월, 값)를 같은 분기에서 두 번째 결과표로 돌려준다. 화면이 읽는 순서와 맞춘다.
- 월이 고정 12개면 정적 PIVOT을 쓴다. 열이 실행 때 정해지는 경우에만 동적 SQL을 쓰고 이유를 밝힌다.

## 검색 조건 인자

화면의 검색 구분 콤보(`@TYPE`)와 검색어(`@TEXT`)를 받는 조회는 조건이 비었을 때 전체가 나오게 쓴다.

```sql
WHERE A.ORGDIV = @ORGDIV
  AND (ISNULL(@TYPE, '') = ''
       OR ISNULL(@TEXT, '') = ''
       OR (@TYPE = 'ITEM' AND (A.ITEMCD LIKE '%' + @TEXT + '%' OR B.ITEMNM LIKE '%' + @TEXT + '%'))
       OR (@TYPE = 'INSIZ' AND A.SPEC LIKE '%' + @TEXT + '%'))
```

`@TYPE` 값은 화면 콤보의 실제 코드와 맞춘다.
