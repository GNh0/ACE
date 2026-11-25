---
name: pb
description: PowerBuilder PBL·DataWindow·이벤트를 분석하거나 WinForms/DevExpress와 SQL Server로 이관한다. PB·PBL·데이터윈도우 분석, PBL 내보내기, C# 이관·전환 요청에 사용한다.
---

# PB analysis and migration

Follow the [work](../work/SKILL.md) skill (Korean replies, lessons, reference vs target, scope, finish, cleanup, Compound). Open only the references below, one per read.

## Start

1. Read [lessons](references/lessons.md) and the local `pb.md` record.
2. First read the exact PBL/object, ancestor classes, linked DataWindows, real events, SQL and report links. With only exported files, speak only within them; never claim to have analyzed PBLs you did not read.
3. Writing C#: also the **csharp skill**; SQL: the **sql skill**; framework-based target: the **erp skill**. Layout and behavior come from the PB screen, writing style from target-project siblings.

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

## Self-check

1. **Source↔result mapping**: where each event, DW, SQL and field went, with **source (PB export file:line) and result (file:line)**; missing ones `미확인`. Analysis only: link targets instead of results. Only items touching the change. [verify](references/verify.md)
2. **Rules**: the rules above, lessons, and the self-checks of the csharp/sql skills used, including running their checkers yourself. New C#: the csharp contract table.
3. **Scenario table**:

| Kind | Cases | Evidence |
| --- | --- | --- |
| Normal | Rows/states PB queried or saved behave the same in C#/SP | 실행 / 정적 대조 / 미확인 |
| Exclusion/edge | Rows PB protected/excluded, NULL retrieve args, empty result, partial composite-key mismatch, deleted rows | same |

Separate statically checked scope, run results and unconfirmed screen/DB behavior. Remove export temp folders when done.
