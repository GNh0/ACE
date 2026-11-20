# ACE

A Claude Code plugin that makes SQL Server procedures, WinForms/DevExpress screens and PowerBuilder migrations follow the user's own way of working.

## Skills

| Skill | For |
| --- | --- |
| `sql` | Writing, cleaning up and reviewing queries, SELECT SPs and SAVE SPs |
| `csharp` | WinForms/DevExpress screens, Designer, grids, reports |
| `pb` | PBL export, DataWindow analysis, migration to C#/SQL |

Every skill has the same shape:

- `SKILL.md`: how to read (open only the needed reference, one at a time — a combined dump gets truncated), what to do first, always-keep rules, the self-check before finishing. Kept under 5,000 characters so it is read whole.
- `references/`: the full rules and example code, split by task so a typical task reads SKILL.md, lessons and at most three references.
- `references/verify*.md`: **verification (EDD)** — how to build the evidence for the final scenario table.
  - `sql`: run when possible. On a dev DB, SELECTs compare the old and new query with the same arguments; SAVEs run new/round-trip/mixed edit/failed validation/delete inside a transaction and roll everything back. Production or unknown DB: don't run, write the reason.
  - `csharp`: compare screen calls with the SP contract (arguments, `@WORKTYPE`, XML TableName, row states, result order, FieldName) with file and line numbers.
  - `pb`: a source (PB) ↔ result mapping list with file:line on both sides.
- `references/compound.md` and `lessons.md`: **corrections (Compound)** in two steps.
  - Local record: on a correction the model writes to `~/.claude/ace/lessons/<skill>.md` without asking. Plugin updates don't erase it; the next session reads it.
  - Promotion: when the user says "교정 기록 정리해줘", local entries move into this repository's `lessons.md`, settled rules go to their reference, and a new version is released.
  - At start a skill reads both the plugin `lessons.md` and the local record; the local one wins.

There are no subagents: the main agent reads the skill, does the work and the self-check. Some rules are not kept from documents alone (models differ in how well they follow layout and prohibition rules, and filled tables with static guesses instead of runs). **When a rule exists but is not followed, it becomes a mechanical check instead of more prose.** So there are small scripts and one hook:

| File | Does | Does not |
| --- | --- | --- |
| `skills/sql/scripts/check_sql.py` | Checks the layout and prohibition rules that can be judged reliably (transactions, lock hints, 120 chars, INSERT grid, uppercase …) and prints failing line numbers and `ACE-CHECK: PASS/FAIL n/m` | Business comments, unrequested validation, EDIT handling — judgement calls stay in SKILL.md |
| `skills/sql/scripts/make_rollback_test.py` | Drafts a rollback test batch from the SP definition (arguments, XML path, `WITH` columns, WORKTYPE, target tables) | Never runs it; source data and keys stay `-- TODO:` |
| `skills/csharp/scripts/check_designer.py` | `*.Designer.cs`: label alignment, default sizes and "shrunk to one width", overlap, height 25, prefixes and default names, `grd/gvw/col` naming, required block lines, column appearance, `rpsSpin`/`rpscbo` on numeric/code columns, footer count, `+=` in `InitializeComponent`; with `--original`, changed properties of existing controls as `[확인]`. Other `.cs`: added `CloseEditor`/`UpdateCurrentRow`, `P_*` flags, `FilterInfo`, forced focus, `MinWidth`, `grp….Text`, `MessageBox`, lambda subscriptions, brace-less ifs. Default sizes come from the project's `KoneLib.Control` source | Choices that need the screen (a grid's role, whether a size comes from the named reference) are reported as `[확인]` |
| `hooks/ace_stop_check.py` (Stop, SubagentStop) | `sql`: blocks once if an SP was written or applied with neither execution evidence (rollback test, `EXCEPT` comparison) nor `실행 검증: 하지 않음 - <이유>`, or if the SP file fails `check_sql.py`. `csharp`: blocks once if a written `.cs` fails `check_designer.py` (the original comes from the transcript, so only this request's changes count) | Never injects reminder text; prints nothing when fine; never blocks twice for the same stop (`stop_hook_active`); a hook error never blocks work |

Turn the hook off with `ACE_HOOK=off`. **Hooks run only in Claude Code.** In other hosts (Codex and others) nothing runs automatically, so each SKILL.md contains the exact checker command and the `ACE-CHECK` line the model must paste. The older KH plugin grew a large checker and a hook that injected text every turn, and work turned into fighting the hook; so there is one hook, and each script is a single standard-library Python file (`check_designer.py` is the largest, about 460 lines, because it covers Designer and code-behind).

## Changing rules

Write a rule in one place only (`SKILL.md` or one `references/*.md`). Exception: "Work files and cleanup" is identical in the three SKILL.md files so each skill stands alone, and `compound.md` is identical in the three skills except the skill name and paths; change them together. Corrections go to the local record first, move into `lessons.md` on promotion, and become reference rules once settled. Procedure: each skill's `references/compound.md`.

## Install

```
/plugin marketplace add GNh0/ACE
/plugin install ace@gnho-labs
```
