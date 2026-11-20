---
name: csharp
description: WinForms/DevExpress 화면, Designer, 그리드, 사용자 컨트롤, XtraReport를 실제 프로젝트 방식으로 작성·수정·검토한다. C# 화면·폼·그리드·컨트롤·Designer·보고서 수정 요청에 사용한다.
---

# C# screens

필요한 참조 문서만 하나씩 연다. 여러 문서를 한 번에 출력하지 않는다(잘린다).

Reply to the user in Korean. Don't delegate this skill.

## Start

1. Read [lessons](references/lessons.md) and `~/.claude/ace/lessons/csharp.md` (newer); they beat rules.
2. Another project's screen = layout/function reference only; style from same-role siblings in the **target** project (none named: ask).
3. Before editing read whole callers/callees, init and the original Designer.

| Task | Read |
| --- | --- |
| New list + detail screen | [screen-skeleton](references/screen-skeleton.md), [controls](references/controls.md), [grid](references/grid.md) |
| Add controls / columns | [controls](references/controls.md) / [grid](references/grid.md) |
| Save, delete, header + detail | [save-flow](references/save-flow.md), [behaviors](references/behaviors.md) |
| Event/method per behaviour; syntax, formats | [behaviors](references/behaviors.md); [coding-style](references/coding-style.md) |
| Screen ↔ SP contract table | [verify](references/verify.md), [verify-evidence](references/verify-evidence.md) |
| Migration; UserControls/timers; reports; C_KONE120 API | [designer](references/designer.md); [screen-behavior](references/screen-behavior.md); [reports](references/reports.md); [kone120](references/kone120.md) |

## Always-keep rules

(c) = `check_designer.py` checks it.

- Change only requested members; keep properties, events, user edits (width, order, Font, Visible). [coding-style](references/coding-style.md#priority-of-requirements)
- `u_…` first, DevExpress otherwise, never plain WinForms; keep their defaults. [controls](references/controls.md#choosing-a-control)
- (c) Default sizes, not one shrunk width; labels right-aligned; no overlap; height 25. [controls](references/controls.md#size-and-placement)
- (c) Whole Designer block, prefixes, no `u_Label17` names. [controls](references/controls.md#designer-blocks)
- (c) `grdList`/`gvwList`/`colList_…`; HTML defaults; no column `Font`/alignment/formats. [grid](references/grid.md)
- (c) Numeric columns `rpsSpin…`, code columns `rpscbo…`, footer count. [grid](references/grid.md#repository-editors)
- (c) Layout in the Designer; named `+=` handlers in the constructor. [screen-skeleton](references/screen-skeleton.md#constructor)
- (c) Braces on every `if`/`else`/loop. [coding-style](references/coding-style.md#syntax-and-naming)
- Command/value-change handlers check `m_Editmode` first. [behaviors](references/behaviors.md#inputs)
- (c) No new helpers, `MessageBox`, own DB, `CloseEditor`, `P_*`, `FilterInfo`. [behaviors](references/behaviors.md#not-used)
- New saves `ExecSPTrn`; `ExecSP` screens keep the SP transaction. [save-flow](references/save-flow.md#saving-rules)
- Screen + SP change: sql skill too; compare arguments (null defaults), TableName, row states, result order, FieldName. [verify](references/verify.md#contract-table)
- No LINQ, staging tables or builds unless very hard/slow without; say why.

## Work files and cleanup

- Work files (drafts, copies, tests, logs) go to a task folder in `%TEMP%`, never the source.
- **`.sql` files never go inside the solution folder**: use `SQL\<YYYYMMDD>\` in the `.sln` folder's parent (`…\고객사\SQL\20261120\`). Never use an `SQL` folder inside it; propose moving it. No commit. Unsure: ask.
- Write only the final deliverables to the source folder, and only to the path you were given.
- Leave processes and services you did not start alone.
- Temp files still needed for the next step may stay; give their paths in the answer.
- Stop your processes; remove your temp files (`git status`); report unknown ones.

## Self-check

1. Run on each written `.cs`, fix `[실패]`, rerun, paste the last line (`ACE-CHECK: PASS 13/13`), judge `[확인]`:

   ```
   python <스킬 폴더>/scripts/check_designer.py <X.Designer.cs> --original <원본 사본> --sibling <형제.Designer.cs>
   python <스킬 폴더>/scripts/check_designer.py <X.cs> --original <원본 사본>
   ```

   New file: no `--original`; `--project <솔루션 루트>` if not found.
2. Nothing unrequested vs original; written like the sibling; rules/lessons without (c): yes/no, file:line.
3. SP calls changed: contract table (file:line). [verify](references/verify.md)
4. Scenario table per changed query/save/state: normal; none/several selected, empty, deleted row (Original key), locked, failed save keeps edits, re-query/resize overwrite. Evidence: 실행 / 정적 대조(파일:줄) / 미확인.
5. Clean up.

## Compound

After a correction, fix it and without asking add it to `~/.claude/ace/lessons/csharp.md` and write `교정 기록에 추가: <제목>`. [compound.md](references/compound.md)
