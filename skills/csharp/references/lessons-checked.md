# C# lessons enforced by check_designer.py

Bodies of the (c) entries indexed in [lessons.md](lessons.md). Open this file only when `check_designer.py` fails one of these items or when promoting lessons. Titles are anchors.

## Designer and grids

### Grid names follow the screen role (2026-11-20, XQ500100)
- Mistake: named the only list `grdMaterial`/`gvwMaterial` ("그리드 컨트롤네이밍 … 안지키네?").
- Rule: `grdList`/`gvwList`/`colList_<FIELD>`. [grid.md](grid.md#names)

### Repository editors by default (2026-11-20, XQ500100; count rule revised 2026-11-24)
- Mistake: no `rpsSpin` on quantities, no `rpscbo` on units, no footer count ("SpinEdit,LookupEdit 푸터에 건수도 빼먹는데").
- Rule: `rpsSpin…`, `rpscbo…` bound in Load; `ShowFooter`. The count only as in the next entry. [grid.md](grid.md#repository-editors)

### Footer count: record grids yes, aggregate grids no; first non-editable column, `건` (2026-11-24)
- Mistake: agents on every host put a `Count` footer with `개` on the editable item-code column of a work-order list ("품목코드에 개 적혀있는데 작업지시에 COUNT 로 건으로 바꿔라", "편집이 안되는 가장 앞에 있는 컬럼", "무조건 넣는게 아닌데", "보통 넣긴하는데 통계조회같은곳에는 사실 건수가 의미없잖아"). Cause: the old rule said "the first visible column carries the count" and the lesson above read as "always add one".
- Rule: usually a count on record/document grids; none on statistics/status/summary grids whose rows are aggregates, or when the reference grid has none; on the first column that cannot be edited (lowest VisibleIndex), never an editable or check-box column; text ends in `건`. [grid.md](grid.md#footer)
- Check: check_designer `그리드 건수 위치·표시` fails a count added on another column or without `건`; a missing count fails when a `--sibling` has one, else `[확인]` (ignored for aggregate grids).

### No font on grid columns; centre every header (2026-11-20)
- Mistake: put `Tahoma 9pt` on columns; left TreeList headers unaligned ("헤더 정렬도 쳐 안지키네").
- Rule: only `Options.UseFont = true`; header H/V centre, tree lists too. [grid.md](grid.md#column-block)

## Code-behind

### Braces when the body is on the next line (2026-11-20, revised 2026-11-24)
- Mistake (11-20): copied `if (...) return;` from the existing screen. Revised 11-24 after the PROJECT_B analysis (one-line guards in 29 of 30 screens); user: both forms allowed.
- Rule: braced and brace-less one-statement bodies are both fine; not checked. [coding-style.md](coding-style.md#syntax-and-naming)

### No editor commits, permission flags or string filters (2026-11-20)
- Mistake: added `CloseEditor()`/`UpdateCurrentRow()`, `P_Add = false`, `ColumnFilterInfo`, forced focus ("넣지마라니깐").
- Rule: none unless the sibling has them. [coding-style.md](coding-style.md#not-used)

### Height check only when the height changed (2026-11-24, PROJECT_A XP200500)
- Mistake: the hook blocked a requested width change of the QR input row because the whole `Size` line changed; the existing heights 66/72 were reported as violations (user: "내가 요청한건데 hook이 막은거같은데??").
- Rule: an existing control is judged on the height only when its height differs from the turn's original.
- Check: check_designer `라벨·한 줄 입력 높이 25` skips unchanged heights of existing controls and is only `[확인]` (user: "높이도 내가 요청한건데 잡으면 안되는거잖아"); it never blocks.
