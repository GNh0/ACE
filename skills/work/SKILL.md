---
name: work
description: 언어와 무관한 개발 작업 방식. 요청을 지시 목록·변경 목록으로 나누기, 기능 단위 요청(새 화면+새 SP+관련 화면·SP), 참조와 작성 기준 구분, 요청 범위, _BAK 백업, 완료 보고, 작업 파일 정리, 교정 기록. SQL·C#·PB 개발 요청이면 언어 스킬과 함께 사용한다.
---

# Work method

Reply to the user in Korean. Open only the references a task table names, one per read (a combined dump gets truncated). Do the work and the self-checks yourself; don't delegate ACE skills. This skill runs the task; sql/csharp/pb and erp say how to write each object.

## Start

1. Lessons: read `references/lessons.md` of each ACE skill you use (this one: [lessons](references/lessons.md)) and the local record `~/.claude/ace/lessons/<skill>.md` (newer; same path on every host). Matching entries override rules; open `lessons-checked.md` ((c) entries) only when that checker item fails.
2. Intent: questions, reviews, "전달해줘", "직접 생성하지 말고" → answer only, no file or DB changes. Diagnosis → cause and fix first. Build, commit, document files only when asked.
3. Instruction list: split the user's message into items (placement, column/table/SP names, formulas, conditions) in their words; names spelled exactly as written. Follow Excel/image formulas and layouts as given; check that a given example result comes out.
4. Change list: new objects (screen ID, SP name), objects to modify (related screens/SPs), references (other projects' screens/SPs), data flow (screen → table → screen, key columns), objects to back up.
5. Feature-level request (new screen + new SP + related screens/SPs): [feature](references/feature.md).
6. Best host and model per task, without being asked: for the task (or each independent piece) pick the platform and model that fit it best (the [dispatch](../dispatch/SKILL.md) skill's host/model choice, `dispatch.py usage` for headroom); when that is not this host, hand it over through dispatch. Keep here only what needs this conversation's context (decisions a brief cannot carry) and pieces that would edit the same file as another. Say in one line what goes where before sending ("Codex(gpt-6.2-sol)에 맡깁니다: …"); review what comes back. User 2026-11-25: "그냥 어떤 작업에 더 좋은 모델이면 그냥 알아서 그 플랫폼 그 모델로 쓰는거아냐?".

## Reference vs target

A screen or SP from another project that the user names ("PROJECT_B_1 XD100100 참조만") is a reference for layout and behavior only. Code, Designer and SQL style follow same-role siblings **in the target project** (same module, same query/save pattern). Members, signatures, helpers and flags that exist only in the reference are used only if the target has them. No reference named: ask for one in the target project. Copying the reference verbatim was the most frequent C# correction (264 cases).

## Scope

- Change only what was asked.
- When the user corrects one spot, name the rule it broke, search every file/SP created or changed in this task for the same pattern, fix all, and list them (`같은 유형 N곳 수정: 파일:줄`). If the user says "전부", widen to earlier work (same session, SPs applied the same day).
- When a pattern is banned, don't replace it with an equivalent banned or unusual pattern (CTE → `#temp`); use the user's normal form (derived-table JOIN / `@table` variable) and run the skill's checker on the whole file.
- "Keep behavior": if a result may change, don't change it; if you must, put "원본과 달라지는 경우" at the top of the answer.
- Never break one rule for another; pick the safer one and state the conflict at the top.
- No LINQ, staging tables or builds unless very hard/slow without; say why.

## Backups

When the user asks: screen `<ID>_BAK` (.cs/.Designer.cs/.resx, csproj registration; the backup screen calls the backup SP), SP `sp_<ID>_<TYPE>_<YYYYMMDD>_BAK`, table `<TABLE>_<YYYYMMDD>_BAK`; then change the original name. Never invent another name. Never edit `_BAK`/`_bak` objects; leave them out of search results.

## Finish

- Diff original vs final: nothing unrequested.
- Map every instruction-list item to file:line (or why it is not done).
- Before reporting a change of SPs or screens, have it reviewed with fresh eyes: the `review` skill (Claude Code: the `ace-reviewer` agent). Fix real findings; list the rest.
- Report each completion claim separately: source checked / DB applied (hash) / built / UI verified. One does not imply another; what was not done is `미확인` or "하지 않음".

## Work files and cleanup

- Work files (drafts, copies, exports, tests, logs) go to a task folder in `%TEMP%`, never the source.
- **`.sql` files never go inside the solution folder**: use `SQL\<YYYYMMDD>\` in the `.sln` folder's parent (`…\고객사\SQL\20261120\`). Never use an `SQL` folder inside it; propose moving it. No commit. Unsure: ask.
- Write only the final deliverables to the source folder, and only to the path you were given.
- Stop your processes, never others'; remove your temp files (`git status`) except ones the next step needs (give their paths); report unknown files.

## Compound

After a correction, fix it and, without asking, add it to `~/.claude/ace/lessons/<skill>.md` of the layer owning the rule (work/sql/csharp/pb/erp; in-house framework/project rules → erp) and write `교정 기록에 추가: <제목>`. [compound.md](references/compound.md)
