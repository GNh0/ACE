# C# 교정 기록

사용자가 교정한 실수와 그 뒤로 지킬 규칙이다. 작업 전에 읽고, 해당하면 다른 규칙보다 우선한다.

항목 형식:

```
## <짧은 제목> (YYYY-MM-DD)
- 실수: <무엇을 잘못했나>
- 규칙: <앞으로 어떻게 하나>
```

새 항목은 맨 아래에 추가한다. 더 이상 맞지 않는 항목은 지운다.

---

## 그리드 기본값은 HTML 생성 결과만 (2026-09-08)
- 실수: 다른 화면이나 DevExpress 예시의 옵션(셀 정렬, DisplayFormat, EditMask, 뷰 전체 Editable=false)을 새 그리드에 함께 넣었다.
- 규칙: 사용자의 `DataWindowToXml.html` 생성 결과에 있는 속성만 쓴다. [grid.md](grid.md)

## SpinEdit 연결 확인 요청 ≠ 표시 형식 요청
- 실수: "SpinEdit이 연결되지 않은 것 같다"는 말에 DisplayFormat/EditMask를 추가했다.
- 규칙: 선언·생성·RepositoryItems 등록·ColumnEdit 연결을 확인한다. 형식 속성은 사용자가 따로 요청할 때만. [screen-behavior.md](screen-behavior.md)

## 한 줄 if도 항상 중괄호 (2026-11-20)
- 실수: 기존 화면을 따라 `if (...) return;`처럼 중괄호 없이 썼다.
- 규칙: if·else·반복문은 한 줄이어도 중괄호를 쓴다. [coding-style.md](coding-style.md)

## 저장 트랜잭션은 ExecSPTrn이 맡는다 (2026-11-20)
- 실수: 화면이나 SP에 트랜잭션·롤백 코드를 따로 넣었다.
- 규칙: 저장은 `dbClient.ExecSPTrn`으로 부르고, 화면과 SP에는 트랜잭션 코드를 쓰지 않는다. [screen-skeleton.md](screen-skeleton.md)

## 그리드 열에 글꼴을 지정하지 않는다 (2026-11-20)
- 실수: 새 그리드 열의 셀·머리글 Appearance에 `Font = Tahoma 9pt`를 넣었다.
- 규칙: 열은 셀과 머리글의 `Options.UseFont = true`만 켜고 글꼴은 지정하지 않는다. 머리글은 가로·세로 가운데 정렬이 기본이다. [control-blocks.md](control-blocks.md#gridcolumn)
