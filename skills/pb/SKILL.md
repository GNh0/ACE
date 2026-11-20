---
name: pb
description: PowerBuilder PBL·DataWindow·이벤트를 분석하거나 WinForms/DevExpress와 SQL Server로 이관한다. PB·PBL·데이터윈도우 분석, PBL 내보내기, C# 이관·전환 요청에 사용한다.
---

# PB analysis and migration

필요한 참조 문서만 하나씩 연다. 여러 문서를 한 번에 출력하지 않는다(잘린다).

Reply to the user in Korean. Follow it yourself, don't delegate.

## Start

1. Read [lessons](references/lessons.md) and `~/.claude/ace/lessons/pb.md` (newer); they override rules.
2. First read the exact PBL/object, ancestor classes, linked DataWindows, real events, SQL and report links. With only exported files, speak only within them; never claim to have analyzed PBLs you did not read.
3. Writing C#: also follow the **csharp skill**; SQL: the **sql skill**. For migrated code, take layout and behavior from the PB screen and writing style from sibling screens in the target project.

| Task | Read |
| --- | --- |
| Export source from a PBL | [orca](references/orca.md) |
| DataWindow/screen mapping, C# grid from a DW | [datawindow](references/datawindow.md) |
| SELECT/SAVE and C# call migration | [migration](references/migration.md) |
| Source↔result mapping (analysis or migration) | [verify](references/verify.md) |

## Always-keep rules

- Keep raw composite-key columns; build display keys separately; never fix component count or names. [datawindow](references/datawindow.md#datawindow-and-screen-mapping)
- Trace input, query, edit protection, save and output in real source; compare source and target. [migration](references/migration.md#result-check)
- A simple SELECT extraction needs no migration document or C# generation. [migration](references/migration.md#result-check)
- Prefer the target project's user controls and their init defaults; add no PB properties or familiar DevExpress options without evidence.

## Work files and cleanup

- Work files (drafts, copies, exports, tests, logs) go to a task folder in `%TEMP%`, never the source.
- **`.sql` files never go inside the solution folder**: use `SQL\<YYYYMMDD>\` in the `.sln` folder's parent (`…\고객사\SQL\20261120\`). Never use an `SQL` folder inside it; propose moving it. No commit. Unsure: ask.
- Write only the final deliverables to the source folder, and only to the path you were given.
- Leave processes and services you did not start alone.
- Temp files still needed for the next step may stay; give their paths in the answer.
- Stop your processes; remove your temp files (`git status`); report unknown files.

## Self-check

1. **Source↔result mapping**: where each event, DW, SQL and field went, with **source (PB export file:line) and result (file:line)**; missing ones `미확인`. Analysis only: link targets instead of results. Only items touching the change. [verify](references/verify.md)
2. **Rules**: the rules above, lessons, and the self-checks of the csharp/sql skills used. New C#: the csharp contract table (incl. `ExecSPTrn` vs `ExecSP`).
3. **Scenario table**:

| Kind | Cases | Evidence |
| --- | --- | --- |
| Normal | Rows/states PB queried or saved behave the same in C#/SP | 실행 / 정적 대조 / 미확인 |
| Exclusion/edge | Rows PB protected/excluded, NULL retrieve args, empty result, partial composite-key mismatch, deleted rows | same |

Separate statically checked scope, run results and unconfirmed screen/DB behavior.

4. Clean up (export temp folders included).

## Compound

After a correction, fix it and, without asking, add it to `~/.claude/ace/lessons/pb.md` and write `교정 기록에 추가: <제목>`. [compound.md](references/compound.md)
