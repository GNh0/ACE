# SQL 서식

## SQL layout

- 별칭은 [별칭 역할](#별칭-역할) 순서로 정한다. 파생 쿼리 내부는 T 계열을 쓴다. 테이블명·MAINCD만으로 E/F를 정하지 않는다. “정렬만/별칭 그대로”는 원래 별칭을 보존한다.
- 리터럴·주석 밖의 SQL은 **모두 대문자**로 쓴다. 키워드·함수뿐 아니라 테이블·열·별칭·출력 열 이름(`AS` 뒤)·사용자 함수·프로시저·변수 이름도 포함한다(예: `DBO.F_BA011T_FIND_SUBNM`). 출력 열 이름이나 개체 이름의 대소문자가 바뀐다는 이유로 원래 표기를 남기지 않는다. 문자열 리터럴, 주석, `[...]`·`"..."`로 감싼 식별자 안의 표기만 원문을 유지한다.
- FROM·WHERE·GROUP BY·ORDER BY는 SELECT와 같은 열에서 시작한다(왼쪽 맞춤). WHERE의 AND·OR는 두 칸 들인다. 키워드 끝을 맞추는 오른쪽 맞춤(`  FROM`, ` WHERE`)은 쓰지 않는다.
- 한 줄은 100자 안쪽을 권장하고 120자를 넘기지 않는다. SELECT 목록은 한 줄에 하나가 기본이다. 짧고 단순한 GROUP BY·ORDER BY 항목은 한 줄에 모은다.
- JOIN은 FROM보다 8칸 들인다. LEFT·RIGHT·FULL JOIN에는 `OUTER`를 꼭 쓴다.
- CTE(`WITH … AS`)는 없으면 구현이 어려울 때만 쓴다. 기본은 파생 테이블 JOIN이다.
- 같은 NUMERIC/DECIMAL 타입으로 CONVERT를 두 번 감싸지 않는다.
- 선행 쉼표 표기를 따른다. SELECT 목록, UPDATE SET, SP 인자 순서와 기본값을 맞춘다. 별칭 AS와 출력 열 AS를 구별한다.
- 일반 JOIN의 ON과 그 조건의 AND는 JOIN의 I 열에 맞춘다. 파생 FROM/JOIN은 여는 괄호와 닫는 괄호를 맞추고 안쪽 절은 한 칸 더 들인다. 파생 JOIN의 ON·AND·OR는 여는 괄호 열에 둔다. 중첩·UNION은 각 괄호를 기준으로 한다.
- EXISTS 괄호는 같은 열, 내부 SQL은 다음 줄에서 한 칸 더 들인다. 짧은 GROUP BY·ORDER BY는 한 줄, CASE는 [procedure.md의 CASE 예시](procedure.md#case)와 맞춘다. BETWEEN의 AND는 해당 식 안에 둔다.
- INSERT 열과 SELECT/VALUES 값은 순서·줄 그룹·실제 시작 열을 대응시킨다. 같은 순번의 열과 값은 같은 시작 위치에 두고, 각 칸은 그 칸의 열·값 중 긴 쪽에 맞춰 공백을 둔다. **30자 이상인 긴 값(식·CASE·ROW_NUMBER 등)이 그 줄의 마지막 항목이 아니면, 그 값부터 다음 줄로 넘긴다.** INSERT 열 목록도 같은 위치에서 줄을 넘긴다. 긴 값 하나에 맞추려고 다른 줄의 열을 수십 칸씩 띄우지 않는다([INSERT 열 대응 예시](#insert-열-대응)). UPDATE SET은 세로 목록으로 쓴다.
- JOIN 종류·순서·조건, 출력 타입·필드, 리터럴·한글·기존 주석을 보존한다. 주석 처리 요청은 원문을 남긴다. 필요한 JOIN·IF EXISTS·업무 함수와 상수는 실제 의미를 지킨다.
- JOIN으로 변경할 때는 전체 키·NULL·중복·집계 단위, 함수 원본·실행 의미를 확인한다. 다중 결과는 각 결과의 기간·필터·집계 키·UNION·비율을 맞춘다.
- 요청이 UPDATE 하나면 해당 UPDATE FROM/CROSS APPLY를 완성한다. DB 변경은 지정한 연결·DB·키, 트랜잭션과 변경/제외 행을 확인한다. 중간 테이블은 없으면 구현이 어려울 때만 쓴다.

## 별칭 역할

일반 “정리”에서 별칭을 바꾸기 전에 테이블마다 `별칭 | 테이블 | 업무 역할 | 연결 키`를 먼저 적는다. 별칭은 JOIN 순서나 테이블명 첫 글자가 아니라 이 역할로 정한다.

모든 테이블(FROM·일반 JOIN·파생 JOIN)에 같은 규칙 하나를 적용한다. FROM의 주 대상은 처음 나오므로 항상 **A**다.

- **이미 글자를 받은 테이블과 같은 업무면 그 글자에 번호를 붙인다.** 그 테이블 행의 기준·표준·설정·승인 값을 더하는 보조 테이블, 헤더의 상세, 같은 원천을 조건만 달리 나눈 파생이 해당한다. A의 것이면 A1·A2, B의 것이면 B1·B2, C의 것이면 C1처럼 어느 글자에도 똑같이 적용한다.
- **새 업무면 다음 글자**(B, C, D…)를 처음 나오는 순서대로 쓴다. 앞 테이블의 키로 붙어도 업무가 다르면 새 글자다.
- 같은 업무 테이블이 기준 테이블보다 먼저 나와도 글자는 업무로 정한다. JOIN 순서는 바꾸지 않는다.

| 원래 | 별칭 | 근거 |
| --- | --- | --- |
| `PR110T` 공정계획 | `A` | 주 대상 |
| `PR100T` 표준시간 | `A1` | A의 공정·품목 표준값(같은 업무). `B`가 아니다 |
| `SA100T` 수주 헤더 | `B` | 새 업무 |
| `BA011T` 공정명 코드 | `C` | 새 업무 |
| `SA110T` 수주 상세 | `B1` | B의 상세(같은 업무). 먼저 나온 C와 무관하게 B 계열 |
| `PR210T` 실적 집계(PARTCD <> 'Y') | `D` | 새 업무 |
| `PR210T` 실적 집계(PARTCD = 'Y') | `D1` | D와 같은 원천의 조건별 집계(같은 업무) |
| `BA905T` 도면 파일 | `E` | 새 업무 |

업무가 같은지는 테이블 설명, 실제 연결 키, 사용하는 열로 판단한다. 근거가 부족하면 역할표에 `미확인`과 이유를 적고 사용자에게 확인한다. 답변에 원래→새 별칭과 역할 근거를 함께 적는다.

```sql
SELECT A.GONUM
     , A1.STDTIME
     , B.HULLNO
     , B1.ITEMNM
     , C.SUBNM3
     , D.PRODQTY
FROM PR110T A
        LEFT OUTER JOIN PR100T A1
                     ON A.ORGDIV = A1.ORGDIV
                     AND A.PROCCD = A1.PROCCD
                     AND A.ITEMCD = A1.ITEMCD
        LEFT OUTER JOIN SA100T B
                     ON A.ORGDIV = B.ORGDIV
                     AND A.ORDNUM = B.ORDNUM
        LEFT OUTER JOIN BA011T C
                     ON A.PROCCD = C.SUBCD
        LEFT OUTER JOIN SA110T B1
                     ON A.ORGDIV = B1.ORGDIV
                     AND A.ORDNUM = B1.ORDNUM
                     AND A.ORDSEQ = B1.ORDSEQ
        LEFT OUTER JOIN (
                         SELECT T.ORDNUM
                              , SUM(T.PRODQTY) AS PRODQTY
                         FROM PR210T T
                         GROUP BY T.ORDNUM
                        ) D
                        ON A.ORDNUM = D.ORDNUM
```

## JOIN 예시

```sql
SELECT A.ITEMCD
     , B.ITEMNM
FROM MA210T A
        LEFT OUTER JOIN BA030T B
                     ON A.ITEMCD = B.ITEMCD
WHERE A.ORGDIV = @ORGDIV
```

```sql
SELECT A.ORDERNO
     , B.QTY
FROM ORDERS A
        LEFT OUTER JOIN (
                         SELECT T.ORDERNO
                              , SUM(T.QTY) AS QTY
                         FROM WORK_LOG T
                         GROUP BY T.ORDERNO
                        ) B
                        ON A.ORDERNO = B.ORDERNO
                        AND A.QTY = B.QTY
```

파생 JOIN의 닫는 괄호, ON, AND는 여는 괄호와 같은 열이다. 실제 괄호 위치가 기준이다.

## 중첩·UNION 예시

```sql
    SELECT A.PERIOD
         , A.QTY
    FROM (
          SELECT T.PERIOD
               , SUM(T.QTY) AS QTY
          FROM (
                SELECT T.PERIOD, T.QTY
                FROM HISTORY T

                UNION ALL

                SELECT T.PERIOD, T.QTY
                FROM ORDERS T
               ) T
          GROUP BY T.PERIOD
         ) A
    ORDER BY A.PERIOD
```

## INSERT 열 대응

```sql
    INSERT INTO TARGET
    (
           ID  , VERY_LONG_FIELD , C       , D
         , E   , F               , G       , H
    )
    SELECT @ID , @A              , @COLUMN , @D
         , @E  , @F              , @G      , @H
    FROM SOURCE A
```

긴 값은 줄 끝에 둔다. 아래에서 `ISNULL(C.SEQ, 0) + ROW_NUMBER() …`는 그 줄의 마지막 항목이고, 다음 열 `ITEMCD`는 다음 줄에서 시작한다. 긴 값이 줄 중간에 오는 형태는 쓰지 않는다.

```sql
    INSERT INTO TARGET
    (
           ORGDIV   , DOCNO  , SEQ
         , ITEMCD   , QTY    , UNITWGT
         , TOTWGT
    )
    SELECT @ORGDIV  , @DOCNO , ISNULL(C.SEQ, 0) + ROW_NUMBER() OVER (ORDER BY A.SEQ)
         , A.ITEMCD , A.QTY  , A.UNITWGT
         , A.QTY * A.UNITWGT * (CASE WHEN A.WGTUNIT = 'G' THEN 0.001 ELSE 1 END)
    FROM SOURCE A
```

쓰지 않는 형태: 긴 값이 줄 중간에 있어서 다른 줄의 같은 칸이 수십 칸씩 벌어진다.

```sql
    SELECT @ORGDIV , @DOCNO    , ISNULL(C.SEQ, 0) + ROW_NUMBER() OVER (ORDER BY A.SEQ) , A.ITEMCD
         , A.QTY   , A.UNITWGT , A.QTY * A.UNITWGT                                      , GETDATE()
```

긴 값 때문에 이미 벌어진 간격은 위처럼 줄을 넘겨 없앤다. 여러 줄 표현·주석이 있으면 최종 문자열에서 열/값의 의미와 시작 열을 직접 확인한다.

## 조건 주석

수량·상태를 비교하는 조건, 검증의 판정 조건, 대상을 고르는 핵심 조건에는 **바로 윗줄에 그 조건이 업무로 무슨 뜻인지** 한 줄 주석을 단다. 컬럼 이름이 아니라 업무 용어와 비교 기호로 쓴다.

```sql
WHERE T.ORGDIV = @ORGDIV
  -- 이전공정 입고수량 > 누적불출수량
  AND T.QTY > ISNULL(T1.QTY, 0)
```

```sql
WHERE T.ORGDIV = @ORGDIV
  -- 이전공정 완료 또는 누적처리수량 >= 계획수량
  AND (T.FINYN = 'Y' OR ISNULL(T1.QTY, 0) >= T.QTY)
```

```sql
-- 입고키별 기존 불출수량 + 이번 발주수량 <= 입고수량
IF EXISTS (
           SELECT 1
           FROM @TMP_DETAIL A
                   INNER JOIN STOCK_IN B
                           ON A.INRECDT = B.RECDT
           -- 이번 발주수량 + 기존 누적불출수량 > 입고수량
           WHERE A.QTY + ISNULL(C.QTY, 0) > B.QTY
          )
```

- 주석은 설명하는 조건과 **같은 들여쓰기**로, 그 조건 바로 위에 둔다. 줄 끝에 붙이지 않는다.
- `수량A > 수량B`처럼 조건과 같은 방향의 비교 기호를 쓴다. 검증 블록은 위에 "통과 조건"(`<=`)을, 판정 줄에 "오류 조건"(`>`)을 적는다.
- 단순한 키 조건(`A.ORGDIV = @ORGDIV`, JOIN의 키 비교)에는 달지 않는다. 봐도 뜻이 바로 안 보이는 비교·계산·제외 조건에만 단다.
- 여러 문장이 이어지는 SAVE에서는 큰 단계마다 한 줄 주석으로 무엇을 하는지 적는다(`-- 발주 상세: 선택한 입고 LOT 행마다 1행`).
- 기존 주석은 지우거나 고쳐 쓰지 않는다. 조건을 바꿨으면 그 조건의 주석도 같이 맞춘다.

## 프로시저 헤더

새 SP는 아래 헤더를 쓴다. 작성자는 사용자에게 확인한 이름 한 명, 날짜는 최초 작성일, 설명은 프로그램명 뒤에 `처리`(SAVE) 또는 `조회`(SELECT)를 붙인다. 기존 SP의 작성자·최초 작성일은 사용자가 정정을 요청할 때만 바꾼다.

```sql
-- =============================================
-- AUTHOR:      {작성자명}
-- CREATE DATE: {첫작성일}
-- DESCRIPTION: {프로그램명} 처리OR조회
-- =============================================
```

## 화면 인자·출력

- 화면 SP의 `@WORKTYPE`·`@ORGDIV`와, 선택 인자의 NULL 기본값 등 기존 템플릿과 호출 약속을 지킨다.
- 실제 스키마 → 인자/XML/스테이징 → 결과 → 호출자까지 길이·Unicode·정밀도·스케일·NULL을 맞춘다.
- 화면에 필요한 표시 자릿수는 표시 계층(화면)에 둔다. 계산 타입 변환은 소비자가 요구할 때만 한다. SUM이 넓혀 반환하는 타입도 확인한다.
- 바인딩명·반환 열·SP 인자를 C# 호출부와 하나씩 대조한다.
- 서버 저장시각은 기존 GETDATE() 방식을 따른다.
