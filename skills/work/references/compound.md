# Building up lessons (Compound)

The one procedure for every ACE skill. `<skill>` is the layer that owns the corrected rule: `work`, `sql`, `csharp`, `pb` or `erp` (a in-house framework/project rule goes to `erp` even when found while writing SQL or C#).

Corrections build up in two steps: the **local record**, which every session picks up at once, and **promotion** into the repository, only when the user asks.

## Two records

| Record | Location | When it changes |
| --- | --- | --- |
| Plugin record | `skills/<skill>/references/lessons.md` | Only on promotion. Never write into an installed plugin folder (`~/.claude/plugins/cache/…`, `~/.codex/plugins/cache/…`, Antigravity's plugin folder); updates overwrite it |
| Local record | `~/.claude/ace/lessons/<skill>.md` (Windows: `%USERPROFILE%\.claude\ace\lessons\<skill>.md`), the same file on Claude Code, Codex and Antigravity | Immediately on every correction. Plugin updates do not erase it |

## Reading at start

1. Read the plugin's `lessons.md` of each skill you use.
2. Read the local record `~/.claude/ace/lessons/<skill>.md`; skip if missing.
3. If they differ, **the local one is newer**; follow it.

Entries that apply to this task override the rules in SKILL.md and the references.

## Writing to the local record

### When

| Write | Do not write |
| --- | --- |
| The user corrected the result: said it is wrong, repeated an instruction, asked for another approach | Requirements for this task only (a specific column name, a one-off exception) |
| Verification (the skill's `verify*.md`) runs or comparisons failed or disagreed, because a rule was missing or wrong | My own guesses the user did not call wrong |

### How

1. Fix the result first, and the same pattern everywhere in this task's files ([work](../SKILL.md#scope)).
2. Look for the same content in the plugin lessons.md and the local file.
   - If found, edit that entry instead of adding one. For a plugin entry, write the edited version locally (same title, marked `플러그인 항목 수정`).
   - Otherwise append to the end of the local file.
3. Create the folder or file if missing. A new file starts with `# <Skill> local lessons` (`# SQL local lessons`, `# C# local lessons`, `# PB local lessons`, `# framework local lessons`, `# Work local lessons`).
4. Write it **without asking**. Tell the user in one line: `교정 기록에 추가: <제목>` (when edited: `교정 기록 수정: <제목>`).
5. If the user said in this conversation not to create or change files, do not write the local file. Show the entry in the answer and say it was not saved.

### Entry format

```
## <short title> (YYYY-MM-DD, <project/target>)
- Mistake: <what went wrong>
- Rule: <what to do from now on>
- Scope: all projects / <project> only
- Evidence: <gist of what the user said, or the failure/mismatch from verification>
```

Examples (one per skill; csharp and pb are fictional):

```
## Count deletions so 0 rows are visible (2026-11-20, PROJECT_A XM100500)
- Mistake: the rollback test counted deletions with GROUP BY, so the deleted document vanished from the result and "0" never showed.
- Rule: put the keys to check in VALUES and count with LEFT OUTER JOIN.
- Scope: all projects
- Evidence: in the execution check the delete scenario had no row for the test document
```

```
## Take the detail XML TableName from the SAVE path (2026-11-20, PROJECT_A XX000100)
- Mistake: set the detail DataTable's TableName to the grid name, which differed from the SAVE's `/ROOT/DOC_DETAIL`; details were not saved.
- Rule: read the SAVE SP's `OPENXML` path and use that name as is. Put both line numbers in the contract table.
- Scope: all projects
- Evidence: user: "상세가 안 들어간다"
```

```
## Put itemchanged calculations in the mapping list (2026-11-20, purchase order screen w_pur_order)
- Mistake: the amount recalculation in the DataWindow itemchanged event was not in the mapping list, so the C# screen lost it.
- Rule: list DW events (itemchanged, itemfocuschanged, updatestart) one by one in the source↔result mapping with the target location (file:line).
- Scope: all projects
- Evidence: user: "수량 바꾸면 금액이 안 바뀐다"
```

- Write rules that the next task can follow as is: "do / do not", not "be careful".
- Evidence carries the gist; quote the user only briefly.

## Promotion (into the repository)

### When

- When the user says "교정 기록 정리해줘" or "ACE에 반영해줘".
- When local entries exceed 10, only **propose** cleanup at the end of the answer. Do nothing until the user asks.

### One home per rule

The same rule written differently in several documents drifts apart when edited, so each document owns something different.

| Document | Owns |
| --- | --- |
| reference documents (layout, SAVE, … by topic) | The rule's home: full text, examples, exceptions |
| SKILL.md | Task order and documents to read, plus a one-line list of never-break rules, each naming the rule concretely and linking to its home |
| lessons.md | Mistake record: title, date, `Mistake:` line, `Rule:` line of one sentence plus home link |

Pick the layer by the rule, not by the file you were editing: language-independent work method → `work`; SQL Server / C# WinForms-DevExpress / PowerBuilder → `sql` / `csharp` / `pb`; in-house framework, business domain, one project → `erp` (`references/`; real names and project facts only in the local `~/.claude/ace/profile/`).

### Steps

1. Find the local path of the ACE repository (GNh0/ACE). Ask the user if unknown.
2. Move local entries under the matching topic heading of the repository's `skills/<skill>/references/lessons.md`. Check the local files of all skills.
3. Write or fix the rule's full content in its home (reference document) per the table above. Shorten the lessons.md `Rule:` to one sentence plus home link. A never-break rule also gets one line and a link in the SKILL.md list.
4. When a checker enforces an entry's rule, move its body to `references/lessons-checked.md` (same title, plus a `Check:` line naming the checker item) and leave a one-line `(c)` link with the full title in `lessons.md`.
5. Clean up duplicate and stale entries. If other documents link to a lessons.md title as an anchor, fix those links too.
6. When a rule or lesson is new or keeps being missed, add or extend a scenario in `comply/scenarios/` (fixture + task + checks) and run `python -B comply/run_comply.py <scenario>` on the hosts the user works in; a rule that fails under the neutral or competing prompt goes into a checker or hook, or gets a shorter SKILL.md line.
7. Bump the version in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json` and `.antigravity-plugin/plugin.json` (hosts cache by version) and commit.
8. Push to `main` and `release`, only when the user asked for the cleanup.
9. Update the installed plugin on each host the user works in (README "Install and update").
10. Delete the moved entries from the local file; keep the others.
11. In the answer list moved entries, rules raised into references, deleted entries and the new version.
