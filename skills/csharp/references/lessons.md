# C# lessons

Corrected mistakes; a matching entry overrides other rules. Format and promotion: [compound.md](compound.md). `Rule:` links to the rule's home. Titles are anchors. (c) = caught by `check_designer.py`.

## Designer and grids

### Default size and right-aligned labels (2026-11-20, QC500100)
- Mistake: labels overlapped inputs, were not right-aligned; labels, dates and LOT input shrunk to one width ("기본크기, 오른쪽정렬맞춤").
- Rule: (c) default sizes, `Far`/`Center` labels, no overlap. [controls.md](controls.md#size-and-placement)

### Write the whole property block (2026-11-20, QC500100)
- Mistake: added `ymdFRDT`/`txtLOTNUM` with constructor defaults only ("크기,속성 다지키라고").
- Rule: (c) copy the Designer block line for line. [controls.md](controls.md#designer-blocks)

### Grid names follow the screen role (2026-11-20, QC500100)
- Mistake: named the only list `grdMaterial`/`gvwMaterial` ("그리드 컨트롤네이밍 … 안지키네?").
- Rule: (c) `grdList`/`gvwList`/`colList_<FIELD>`. [grid.md](grid.md#names)

### Repository editors and footer count by default (2026-11-20, QC500100)
- Mistake: no `rpsSpin` on quantities, no `rpscbo` on units, no footer count ("SpinEdit,LookupEdit 푸터에 건수도 빼먹는데").
- Rule: (c) `rpsSpin…`, `rpscbo…` bound in Load, `ShowFooter` + `{0:#,##0}건`. [grid.md](grid.md#repository-editors)

### Grid defaults only from the HTML output (2026-09-08)
- Mistake: added cell alignment, DisplayFormat, EditMask, view-wide Editable=false from other screens.
- Rule: only the `DataWindowToXml.html` output plus the user's footer/repository habits. [grid.md](grid.md)

### No font on grid columns; centre every header (2026-11-20)
- Mistake: put `Tahoma 9pt` on columns; left TreeList headers unaligned ("헤더 정렬도 쳐 안지키네").
- Rule: (c) only `Options.UseFont = true`; header H/V centre, tree lists too. [grid.md](grid.md#column-block)

### Checking a SpinEdit connection is not a format request
- Mistake: answered "SpinEdit이 연결되지 않은 것 같다" with DisplayFormat/EditMask.
- Rule: check declaration, construction, registration, `ColumnEdit`; formats only on request. [screen-behavior.md](screen-behavior.md#grid-connections-and-overwrite-paths)

## Code-behind

### Braces even on one-line ifs (2026-11-20)
- Mistake: copied `if (...) return;` from the existing screen.
- Rule: (c) braces always. [coding-style.md](coding-style.md#syntax-and-naming)

### ExecSPTrn owns the save transaction (2026-11-20)
- Mistake: added transaction code to the screen or SP.
- Rule: new saves `ExecSPTrn`; keep the SP transaction of `ExecSP` saves. [save-flow.md](save-flow.md#saving-rules)

### No editor commits, permission flags or string filters (2026-11-20)
- Mistake: added `CloseEditor()`/`UpdateCurrentRow()`, `P_Add = false`, `ColumnFilterInfo`, forced focus ("넣지마라니깐").
- Rule: (c) none unless the sibling has them. [behaviors.md](behaviors.md#not-used)

### No invented flags or signatures (2026-11-20, QC500100)
- Mistake: invented `isBindingList` and `CallSelectProcedure(…, DataRow dr = null)`.
- Rule: sibling's `isFlagRowChanged`, `string` key arguments. [screen-skeleton.md](screen-skeleton.md#rules-in-this-skeleton)

## Way of working

### The reference is for layout and function only (2026-11-20)
- Mistake: copied another project's screen verbatim ("진짜 복사해서 쳐 가져오셨네요").
- Rule: style from same-role siblings of the target. [coding-style.md](coding-style.md#priority-of-requirements)

### Open references one at a time (2026-11-20)
- Mistake: printed SKILL.md and all references at once; cut at ~44,570 tokens, label rules unseen.
- Rule: only the task table's documents, one per read. [SKILL.md](../SKILL.md)
