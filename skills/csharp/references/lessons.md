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
