---
name: csharp
description: WinForms/DevExpress 화면, Designer, 그리드, 사용자 컨트롤, XtraReport를 실제 프로젝트 방식으로 작성·수정·검토한다. C# 화면·폼·그리드·컨트롤·Designer·보고서 수정 요청에 사용한다.
---

# C# screens

Follow the [work](../work/SKILL.md) skill (Korean replies, lessons, reference vs target, scope, finish, cleanup, Compound). Open only the references below, one per read. framework-based project (ExampleLib / FrmBase / PROJECT_*): also the [erp](../erp/SKILL.md) skill.

## Start

1. Read [lessons](references/lessons.md) and the local `csharp.md` record.
2. Before editing read whole callers/callees, init and the original Designer.

| Task | Read |
| --- | --- |
| New screen / add controls | [designer](references/designer.md), [grid](references/grid.md); framework skeleton, `ux` controls: erp skill |
| Add columns | [grid](references/grid.md) |
| Connect a function to an existing screen | [screen-change](references/screen-change.md); framework save/delete, events: erp skill |
| Syntax, events, formats, not-used APIs | [coding-style](references/coding-style.md) |
| Screen ↔ SP contract table | [verify](references/verify.md), [verify-evidence](references/verify-evidence.md); framework rows: erp skill |
| Migration; UserControls/timers; reports | [designer](references/designer.md); [screen-behavior](references/screen-behavior.md); [reports](references/reports.md) |

## Always-keep rules

(c) = `check_designer.py` checks it.

- Change only requested members; keep properties, events, user edits (width, order, Font, Visible). [coding-style](references/coding-style.md#priority-of-requirements)
- Project UserControl first, DevExpress otherwise, never plain WinForms. [designer](references/designer.md#choosing-a-control)
- (c) No Designer default names (`uxLabel17`, `gridColumn3`) on new controls. [designer](references/designer.md#names)
- (c) `grdList`/`gvwList`/`colList_…`; HTML defaults; no column `Font`/alignment/formats. [grid](references/grid.md)
- (c) Numeric columns `rpsSpin…`, code columns `rpscbo…`. [grid](references/grid.md#repository-editors)
- (c) Row count on record grids, none on statistics/aggregate grids; on the first non-editable column, `…건`. [grid](references/grid.md#footer)
- (c) Layout in the Designer; named `+=` handlers in the constructor. [coding-style](references/coding-style.md#event-subscriptions)
- (c) Braces on every `if`/`else`/loop. [coding-style](references/coding-style.md#syntax-and-naming)
- (c) No new helpers, `MessageBox`, own DB, `CloseEditor`, `P_*`, `FilterInfo`. [coding-style](references/coding-style.md#not-used)
- Screen + SP change: sql skill too; compare arguments (null defaults), TableName, row states, result order, FieldName. [verify](references/verify.md#contract-table)

## Self-check

Run the checker yourself every time; a host hook may not run.

1. Run on each written `.cs`, fix `[실패]`, rerun, paste the last line (`ACE-CHECK: PASS 13/13`), judge `[확인]`:

   ```
   python <스킬 폴더>/scripts/check_designer.py <X.Designer.cs> --original <원본 사본> --sibling <형제.Designer.cs>
   python <스킬 폴더>/scripts/check_designer.py <X.cs> --original <원본 사본>
   ```

   New file: no `--original`; `--project <솔루션 루트>` if not found.
2. Written like the sibling; rules/lessons without (c): yes/no, file:line.
3. SP calls changed: contract table (file:line). [verify](references/verify.md)
4. Scenario table per changed query/save/state: normal; none/several selected, empty, deleted row (Original key), locked, failed save keeps edits, re-query/resize overwrite. Evidence: 실행 / 정적 대조(파일:줄) / 미확인.
