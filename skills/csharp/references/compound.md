# Building up lessons (Compound)

> This file exists identically in the sql, csharp and pb skills, because each skill folder must be self-contained when installed. Keep the three copies in sync; only the skill name and paths differ.

Corrections build up in two steps: the **local record**, which every session picks up at once, and **promotion** into the repository, only when the user asks.

## Two records

| Record | Location | When it changes |
| --- | --- | --- |
| Plugin record | this skill's [lessons.md](lessons.md) | Only on promotion. Never write into the installed plugin folder (`~/.claude/plugins/cache/…`); updates overwrite it |
| Local record | `~/.claude/ace/lessons/csharp.md` (Windows: `%USERPROFILE%\.claude\ace\lessons\csharp.md`) | Immediately on every correction. Plugin updates do not erase it |

## Reading at start

1. Read the plugin's [lessons.md](lessons.md).
2. Read the local record `~/.claude/ace/lessons/csharp.md`; skip if missing.
3. If they differ, **the local one is newer**; follow it.

Entries that apply to this task override the rules in SKILL.md and the references.

## Writing to the local record

### When

| Write | Do not write |
| --- | --- |
| The user corrected the result: said it is wrong, repeated an instruction, asked for another approach | Requirements for this task only (a specific column name, a one-off exception) |
| Verification ([verify.md](verify.md)) runs or comparisons failed or disagreed, because a rule was missing or wrong | My own guesses the user did not call wrong |

### How

1. Fix the result first.
2. Look for the same content in the plugin lessons.md and the local file.
   - If found, edit that entry instead of adding one. For a plugin entry, write the edited version locally (same title, marked `플러그인 항목 수정`).
   - Otherwise append to the end of the local file.
3. Create the folder or file if missing. A new file starts with `# C# local lessons`.
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
## Count deletions so 0 rows are visible (2026-11-20, C_KONE120 MA100500)
- Mistake: the rollback test counted deletions with GROUP BY, so the deleted document vanished from the result and "0" never showed.
- Rule: put the keys to check in VALUES and count with LEFT OUTER JOIN.
- Scope: all projects
- Evidence: in the execution check the delete scenario had no row for the test document
```

```
## Take the detail XML TableName from the SAVE path (2026-11-20, C_KONE120 XX000100)
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

### Steps

1. Find the local path of the ACE repository (GNh0/ACE). Ask the user if unknown.
2. Move local entries under the matching topic heading of the repository's `skills/csharp/references/lessons.md`. Also check local files of the other skills.
3. Write or fix the rule's full content in its home (reference document) per the table above. Shorten the lessons.md `Rule:` to one sentence plus home link. A never-break rule also gets one line and a link in the SKILL.md list.
4. Clean up duplicate and stale entries. If other documents link to a lessons.md title as an anchor, fix those links too.
5. Bump the version in `.claude-plugin/plugin.json` and `marketplace.json` and commit.
6. Push to `main` and `release`, only when the user asked for the cleanup.
7. Update the installed plugin (`/plugin marketplace update gnho-labs`, then update the plugin).
8. Delete the moved entries from the local file; keep the others.
9. In the answer list moved entries, rules raised into references, deleted entries and the new version.
