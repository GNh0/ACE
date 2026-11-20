# C# 교정 기록

사용자가 교정한 실수의 기록이다. 작업 전에 읽고, 해당하면 다른 규칙보다 우선한다. 로컬 기록과 함께 읽는 법, 항목 형식, 승격 절차는 [compound.md](compound.md)에 있다.

각 항목의 `규칙:`은 한 문장과 규칙의 자리로 가는 링크다. 전체 내용·예시·예외는 링크한 문서에 있다.

더 이상 맞지 않는 항목은 지운다. 항목 제목은 다른 문서가 앵커로 가리킬 수 있으므로 바꾸면 링크도 함께 고친다.

---

## 그리드 기본값은 HTML 생성 결과만 (2026-09-08)
- 실수: 다른 화면이나 DevExpress 예시의 옵션(셀 정렬, DisplayFormat, EditMask, 뷰 전체 Editable=false)을 새 그리드에 함께 넣었다.
- 규칙: 사용자의 `DataWindowToXml.html` 생성 결과에 있는 속성만 쓴다. [grid.md](grid.md)

## SpinEdit 연결 확인 요청 ≠ 표시 형식 요청
- 실수: "SpinEdit이 연결되지 않은 것 같다"는 말에 DisplayFormat/EditMask를 추가했다.
- 규칙: 선언·생성·RepositoryItems 등록·ColumnEdit 연결을 확인하고, 형식 속성은 따로 요청할 때만 넣는다. [screen-behavior.md](screen-behavior.md#grid-connections-and-overwrite-paths)

## 한 줄 if도 항상 중괄호 (2026-11-20)
- 실수: 기존 화면을 따라 `if (...) return;`처럼 중괄호 없이 썼다.
- 규칙: if·else·반복문은 한 줄이어도 중괄호를 쓴다. [coding-style.md](coding-style.md#syntax-and-naming)

## 저장 트랜잭션은 ExecSPTrn이 맡는다 (2026-11-20)
- 실수: 화면이나 SP에 트랜잭션·롤백 코드를 따로 넣었다.
- 규칙: 새 저장은 `dbClient.ExecSPTrn`으로 부르고 화면에 트랜잭션 코드를 쓰지 않는다. 기존 `ExecSP` 저장의 SP 트랜잭션은 빼지 않는다. [screen-skeleton.md](screen-skeleton.md#이-골격에서-지킬-점)

## 그리드 열에 글꼴을 지정하지 않는다 (2026-11-20)
- 실수: 새 그리드 열의 셀·머리글 Appearance에 `Font = Tahoma 9pt`를 넣었다.
- 규칙: 열은 셀과 머리글의 `Options.UseFont = true`만 켜고 글꼴은 지정하지 않는다. [grid.md](grid.md#appearance), 속성 블록은 [control-blocks.md](control-blocks.md#gridcolumn)
