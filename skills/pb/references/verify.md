# 원본↔결과 대조 (EDD)

이관 결과는 실행해 보기 어렵다. 그래서 **원본(PB)↔결과 매핑 목록**에 양쪽 근거(파일·줄)를 붙여 대조한다. 목록이 있다는 것만으로는 검증이 아니다. 줄을 찾아 옮겨 적은 항목만 확인된 것이다.

## 매핑 목록

| 원본 (PB 파일:줄) | 결과 (파일:줄) | 상태 | 비고 |
| --- | --- | --- | --- |
| `w_….srw:120` `ue_retrieve` → `dw_list.Retrieve(ls_fr, ls_to)` | `XX000100.cs:210` `CallSelectProcedure(SelectType.LIST)` | 옮김 | 인자 2개 → `@FRDT`, `@TODT` |
| `d_list.srd:5` retrieve SQL | `sp_XX000100_SELECT.sql:23-46` LIST 분기 | 옮김 | |
| `d_detail.srd:40` update 속성(테이블·키 열·수정 가능 열) | `sp_XX000100_SAVE.sql:257-269` MOD UPDATE | 옮김 | 키 열 3개 전부 JOIN |
| `d_detail.srd:12` compute `qty * unp` | `sp_XX000100_SELECT.sql:52` `A.QTY * A.UNP AS AMT` | 바꿈 | 계산 위치가 화면 → SP |
| `w_….srw:300` `itemchanged` 금액 재계산 | 없음 | **미확인** | 대상 이벤트를 찾지 못함 |

- 상태는 `옮김`(같은 동작), `바꿈`(위치·방식이 달라짐, 이유를 비고에), `뺌`(의도적으로 제외, 이유 필수), `미확인`(찾지 못함) 중 하나다.
- 원본 쪽 줄 번호는 ORCA로 내보낸 파일(`.srw`, `.srd`, `.sru` 등, [orca.md](orca.md))이나 사용자가 준 내보내기 파일에서 가져온다. 내보내기 없이 PBL만 있으면 먼저 내보낸다.
- 결과 쪽은 C# 파일, Designer, `.sql` 파일 또는 DB 정의의 줄이다. SP 정의의 줄 번호를 얻는 법은 csharp 스킬 `references/verify.md`의 "SP 쪽 줄 번호 얻기"를 따른다.
- 빠뜨리기 쉬운 것을 하나씩 넣는다: retrieve 인자, DW SQL, update 속성(테이블·키·수정 가능 열), compute 열, protect·taborder(편집 보호), 이벤트(`itemchanged`, `itemfocuschanged`, `updatestart`, `clicked`), embedded SQL, 채번, 출력(보고서 밴드·그룹), 다른 창과 주고받는 값(`OpenWithParm`, `Message.PowerObjectParm`·`StringParm`).
- 동적 `DataObject` 대입처럼 이름이 실행 때 정해지는 것은 `미확인`으로 두고 추측하지 않는다.
- 열이 많은 항목(DW 열 ↔ 그리드 열 등)은 `17/17 옮김`처럼 개수로 적고, 어긋난 것만 이름과 줄을 적는다.

## 채울 범위

- 이관 전체면 위 목록을 화면 전체에 채운다. 일부만 옮기거나 고쳤으면 **바꾼 이벤트·DW·SQL에 닿는 항목만** 채우고, 나머지는 `범위 밖`으로 한 줄 적는다.
- 분석만이면 질문에 닿는 객체(윈도우 1개와 거기서 쓰는 DataWindow, 직접 부르는 창)까지만 채운다. 읽지 않은 조상·전역 함수는 `미확인`으로 남긴다.

## 분석만 할 때

C#으로 옮기지 않고 PB 동작만 정리할 때는 "결과" 칸 대신 **연결 대상**(같은 PB 소스 안에서 그 줄이 닿는 곳)을 적는다. 상태는 `확인`(양쪽 줄을 찾음) 또는 `미확인`이다.

| 원본 (PB 파일:줄) | 연결 대상 (PB 파일:줄) | 상태 | 비고 |
| --- | --- | --- | --- |
| `w_xx_pop.srw:200` `dw_list.Retrieve(gs_orgdiv, ls_cust, ls_fr, ls_to, ls_loc, ls_no)` | `d_xx_list.srd:67` `arguments=` 6개 | 확인 | 순서·개수 같음. SQL `:24-66` |
| `d_xx_list.srd` `update=` 없음 | - | 확인 | 읽기 전용 DW(저장 없음) |
| `d_xx_list.srd:80` `chk` `tabsequence=10` | 나머지 열 `tabsequence=32766`(내보내기에서 탭 순서 0) | 확인 | 편집 가능한 열은 `chk`뿐 |
| `w_xx_pop.srw:49` `ids_x = Message.PowerObjectParm` | 호출자 `xx_main.sru:1035` `OpenWithParm(w_xx_pop, ids_x)`, `:55` `ids_x.DataObject = 'd_xx_list'` | 확인 | 팝업 `dw_list`와 같은 DW라 `RowsCopy`(`w_xx_pop.srw:126`) 대상과 열이 맞음 |
| 호출자 `xx_main.sru:1132` `GetItemNumber(1, "compute_2")` | `d_xx_list.srd:102` footer `sum(compute_9 for all)` | 확인 | 팝업에서 체크한 행만 복사되므로 합계도 체크 행 기준 |
| `w_xx_pop.srw:2` `from w_popup_base` | 조상 객체 내보내기 없음 | 미확인 | `call super::` 동작, `dw_list`·`dw_c` 기본 이벤트 |
| `w_xx_pop.srw:231` `f_Get_CustNm(data)` | 전역 함수 내보내기 없음 | 미확인 | |

찾는 순서와 검색어:

1. 윈도우·사용자 객체(`.srw`·`.sru`)에서 `dataobject =`로 쓰는 DW를 정하고 `from …`으로 조상을 적는다.
2. 같은 파일에서 `Retrieve(`, `Update(`, `SetItem(`, `GetItem`, `OpenWithParm(`, `Message.`, `RowsCopy(`, embedded SQL(`SELECT`·`UPDATE`·`INSERT`·`DELETE` … `;`)을 찾는다.
3. DW(`.srd`)에서 `retrieve=`, `arguments=`, `update=`·`updatewhere=`·`key=yes`, `column=(type=`(결과 열 정의), `compute(`(식), `tabsequence=`, `protect=`, `dddw.name=`을 찾는다.
4. 다른 창과 주고받는 값은 호출자 쪽 줄도 찾아 양쪽을 적는다.

## 함께 하는 대조

- C#을 만들거나 고쳤으면 csharp 스킬의 `references/verify.md` 계약 대조표(화면 ↔ SP)를 채운다.
- SP를 만들거나 고쳤고 개발 DB에서 실행해도 되면 sql 스킬의 `references/verify.md`대로 조회 비교·롤백 테스트를 한다. PB와 같은 인자로 돌린 결과가 있으면 "같다"고 쓸 수 있다. 결과 없이 값·행 수·성능이 같다고 쓰지 않는다.
