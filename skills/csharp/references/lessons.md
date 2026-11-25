# C# lessons

Matching entries override rules; format: [compound.md](../../work/references/compound.md). (c) = enforced by `check_designer.py`, body in [lessons-checked.md](lessons-checked.md).

## Designer and grids

- (c) [Grid names follow the screen role (2026-11-20, XQ500100)](lessons-checked.md#grid-names-follow-the-screen-role-2026-11-20-xq500100)
- (c) [Repository editors by default (2026-11-20, XQ500100; count rule revised 2026-11-24)](lessons-checked.md#repository-editors-by-default-2026-11-20-xq500100-count-rule-revised-2026-11-24)
- (c) [Footer count: record grids yes, aggregate grids no; first non-editable column, `건` (2026-11-24)](lessons-checked.md#footer-count-record-grids-yes-aggregate-grids-no-first-non-editable-column-건-2026-11-24)
- (c) [No font on grid columns; centre every header (2026-11-20)](lessons-checked.md#no-font-on-grid-columns-centre-every-header-2026-11-20)

### Grid defaults only from the HTML output (2026-09-08)
- Mistake: added cell alignment, DisplayFormat, EditMask, view-wide Editable=false from other screens.
- Rule: only the `DataWindowToXml.html` output plus the user's footer/repository habits. [grid.md](grid.md)

### Checking a SpinEdit connection is not a format request
- Mistake: answered "SpinEdit이 연결되지 않은 것 같다" with DisplayFormat/EditMask.
- Rule: check declaration, construction, registration, `ColumnEdit`; formats only on request. [screen-behavior.md](screen-behavior.md#grid-connections-and-overwrite-paths)

## Code-behind

- (c) [Braces when the body is on the next line (2026-11-20, revised 2026-11-24)](lessons-checked.md#braces-when-the-body-is-on-the-next-line-2026-11-20-revised-2026-11-24)
- (c) [No editor commits, permission flags or string filters (2026-11-20)](lessons-checked.md#no-editor-commits-permission-flags-or-string-filters-2026-11-20)

## Way of working

### Open references one at a time (2026-11-20)
- Mistake: printed SKILL.md and all references at once; cut at ~44,570 tokens, label rules unseen.
- Rule: only the task table's documents, one per read. [work SKILL.md](../../work/SKILL.md)
