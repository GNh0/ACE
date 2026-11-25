# Work lessons

Matching entries override rules; format: [compound.md](compound.md).

---

### SQL files go in the solution's parent folder (2026-11-20, PROJECT_A XM100500)
- Mistake: saved the SP under `SQL\date\` inside the solution, then moved it wrongly twice more.
- Rule: write `.sql` files to `SQL\<YYYYMMDD>\` under the parent of the `.sln` folder; ask when unsure. [SKILL.md](../SKILL.md#work-files-and-cleanup)

### The reference is for layout and function only (2026-11-20)
- Mistake: copied another project's screen verbatim ("진짜 복사해서 쳐 가져오셨네요").
- Rule: style from same-role siblings of the target. [SKILL.md](../SKILL.md#reference-vs-target)

### ACE not used on its own (2026-11-25, PROJECT_A XM200150 label)
- Mistake: a Claude session changed `XM200150.cs` and `XM200150_LABEL_RPT.*` for three turns without any ACE skill, then loaded only the csharp SKILL.md (no lessons, no reports.md) and never the erp skill. User: "XM200150 라벨 출력 수정 채팅에서는 스킬 알아서 안쓴거같은데".
- Rule: SQL/C# edits load the language skill (+ erp for framework screens/SPs) and read its lessons and the task-table document before the first edit.
- Check: Stop hook `doc_reasons` (no ACE skill on .sql/.cs edits; skill loaded but no rule document opened before the first write; framework screen without erp), block once.

### Dispatch only on explicit words (2026-11-25)
- Mistake: the dispatch skill triggered only on phrases like "나눠서 시켜줘"; work never pointed to it, so multi-object and batch tasks ran on one host.
- Rule (revised the same day): work Start step 6 — each task goes to the platform/model that fits it best, no count or usage thresholds; only context-bound pieces and same-file pieces stay here. [SKILL.md](../SKILL.md#start)

### No real data in the public repository (2026-11-25)
- Mistake: README listed the real project files, framework names and a live DB connection name although the user had said not to; the rest of the repository also carried real project, DB, table, screen, framework and person names as examples. User: "README에 저렇게 넣지말라고했는데 실제 프로젝트명을 왜넣었지", "GITHUB 예시같은곳에 실제 사용하는 데이터들의 예시를 왜 넣어두냐고".
- Rule: everything in the repository (README, SKILL.md, references, lessons, scripts, comply fixtures) uses the made-up example profile (`ExampleLib`, `FrmBase`, `ux` controls, `SY100T`, `XX100100`, `PROJECT_A`, `PROD_ERP`). Real names live only in the local `~/.claude/ace/profile/` (profile.md, profile.json, designer.json, projects/). Before every commit `python -B scripts/check_public.py` must pass (installed as the clone's pre-commit hook). [erp profile](../../erp/references/profile.md)
