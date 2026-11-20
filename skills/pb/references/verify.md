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
- 결과 쪽은 C# 파일, Designer, `.sql` 파일 또는 DB 정의의 줄이다. SP 정의는 읽어서 작업용 임시 폴더에 저장한 파일의 줄을 쓴다.
- 빠뜨리기 쉬운 것을 하나씩 넣는다: retrieve 인자, DW SQL, update 속성(테이블·키·수정 가능 열), compute 열, protect·taborder(편집 보호), 이벤트(`itemchanged`, `itemfocuschanged`, `updatestart`, `clicked`), embedded SQL, 채번, 출력(보고서 밴드·그룹).
- 동적 `DataObject` 대입처럼 이름이 실행 때 정해지는 것은 `미확인`으로 두고 추측하지 않는다.

## 함께 하는 대조

- C#을 만들거나 고쳤으면 csharp 스킬의 `references/verify.md` 계약 대조표(화면 ↔ SP)를 채운다.
- SP를 만들거나 고쳤고 개발 DB에서 실행해도 되면 sql 스킬의 `references/verify.md`대로 조회 비교·롤백 테스트를 한다. PB와 같은 인자로 돌린 결과가 있으면 "같다"고 쓸 수 있다. 결과 없이 값·행 수·성능이 같다고 쓰지 않는다.
