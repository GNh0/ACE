---
name: style
description: 프로젝트의 실제 코드(SP·화면)에서 사용자의 작성 스타일을 뽑아 ACE 규칙과 비교한다. "스타일 분석해줘", "이 프로젝트 패턴 파악해줘", "내가 만든 SP 기준으로 규칙 맞춰줘", 새 프로젝트·새 참조 DB를 기준으로 삼을 때 사용한다. 습관을 세어 규칙 후보를 만들고, 갈리는 것만 한 번에 하나씩 묻는다.
---

# Style analysis

Turns a reference codebase into ACE rules (ideas from ECC inherit-legacy-style, MIT). The user's words beat counts; counts beat guesses. Follow the [work](../work/SKILL.md) skill.

## Steps

1. **Pick the reference.** Ask which project/DB is the style reference and whose code counts (author header, e.g. `AUTHOR: <name>`; AI-generated code (an AI plugin tag) is excluded unless the user says otherwise). Newest code wins when old and new differ.
2. **List the objects.** SQL: `SELECT O.name, O.create_date, O.modify_date, LEN(M.definition) FROM sys.sql_modules M INNER JOIN sys.objects O ON O.object_id = M.object_id WHERE M.definition LIKE '%AUTHOR%<name>%'` (read-only; on a live DB only SELECT). Screens: the matching `<code>.cs`/`.Designer.cs` pairs; `skills/erp/scripts/map_project.py <solution>` for the framework names.
3. **Count.** Local SP files: `python <ACE>/skills/sql/scripts/mine_style.py <folder> [--author <name>]` (rule / dont / ask per habit). Definitions only in the DB: split them into batches by module (about 10–15 SAVE SPs, or 20–30 SELECT SPs, per batch) and give each batch to a subagent that reads them with SELECT `OBJECT_DEFINITION` and reports in four parts with counts and `name: excerpt` evidence: CONFIRMED (follows ACE), CONTRADICTS (ACE rule + what the code does), MISSING (recurring, not in ACE), INCONSISTENT (splits; newer form). One more subagent for screens. Subagents never write files or run changing SQL.
4. **Merge.** For each item decide: the user already decided it (keep the user's rule) · clear in the code (`rule`/`dont`) → write it · project-specific (mode names, call kinds) → local `~/.claude/ace/profile/projects/<PROJECT>.md` · a slip, not a style (debug SELECT, `MODIP = @USERID`) → a "don't" + checker item if cheap · split → ask.
5. **Ask the splits** with short options showing both forms and their counts, at most four per question round, in Korean. Apply each answer immediately.
6. **Write** each rule in its one home (work Compound "One home per rule"), add a checker item where a regex can tell it reliably (test it on the reference: original lines must not fail), add a comply scenario for rules that agents keep missing, bump the version, release.

## Report

Korean: what was counted (how many objects, whose), what changed in ACE (rules added/changed, checker items, project facts), what the user decided, what is still open.
