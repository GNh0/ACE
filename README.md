# ACE

A plugin for Claude Code, Codex and Google Antigravity that makes SQL Server procedures, WinForms/DevExpress screens and PowerBuilder migrations follow the user's own way of working.

## Layers

Rules are split by level so that a task loads only the layers that apply and every rule has one obvious home:

```
work      language-independent work method (instruction/change lists, scope, backups, reporting, cleanup, Compound)
  │
sql       SQL Server language layer          csharp    C# + WinForms/DevExpress platform layer      pb   PowerBuilder analysis/migration
  │                                             │
  └──────────────┬──────────────────────────────┘
erp      business-system layer: framework roles (base form, controls, save call, numbering, closing, keys) mapped per project
  ├─ profile   references/profile.md (roles; example names are made up)
  ├─ domain    references/domain-erp.md (MES / smart factory files added when real rules exist)
  └─ local     ~/.claude/ace/profile/ (real names: profile.md, profile.json, designer.json, projects/<PROJECT>.md; never committed)
```

A lower layer only adds; it links to the rule above instead of repeating it. Rules that hold for every language (Korean replies, lessons, scope, "keep behavior", rule conflicts, LINQ/builds, finish, cleanup, Compound) live only in `work`. Any project can use `erp`: the rules name roles, and a new project maps them to its own names first (`references/profile.md`, then a small `projects/<PROJECT>.md`). Framework-specific checker items fire only when the code uses the profile's names.

| Skill | For |
| --- | --- |
| `work` | Every development task: request breakdown, feature-level requests (new screen + SP + related objects), reference vs target, scope, `_BAK` backups, completion claims, work files, Compound procedure |
| `sql` | Writing, cleaning up and reviewing queries, SELECT SPs and SAVE SPs |
| `csharp` | WinForms/DevExpress screens, Designer, grids, reports, the generic screen ↔ SP contract table |
| `pb` | PBL export, DataWindow analysis, migration to C#/SQL |
| `erp` | Business-system screens and SPs (ERP, MES, smart factory): framework roles and the per-project profile, screen ↔ SP contract rows, rollback-test XML, domain flows, project facts |

## Which skills load

| Task | Skills (SKILL.md, then the references their task table names) |
| --- | --- |
| SQL cleanup (format only), framework project or not | work, sql (style, style-insert) — no erp |
| Change a framework SAVE SP | work, sql (save, save-edit), erp (save-call; common-sp for numbering) |
| New framework list + detail screen with SP (feature-level) | work (feature), then per object: csharp + erp (screen-skeleton, controls, grid), sql + erp (sp-skeleton / sp-save) |
| Add a grid column | work, csharp (grid), erp if framework-based |
| PB screen analysis | work, pb (orca, verify) |
| Non-framework C# WinForms task | work, csharp |

Every skill has the same shape:

- `SKILL.md`: what to do first, the task table of references, always-keep rules, the self-check. Kept under 5,000 characters so it is read whole; open only the references the table names, one per read (a combined dump gets truncated).
- `references/`: the full rules and example code, split by task (each under 8 KB).
- `references/verify*.md`: **verification (EDD)** — how to build the evidence for the final scenario table.
  - `sql`: run when possible. On a dev DB, SELECTs compare the old and new query with the same arguments; SAVEs run new/round-trip/mixed edit/failed validation/delete inside a transaction and roll everything back. Production or unknown DB: don't run, write the reason.
  - `csharp`: compare screen calls with the SP contract (arguments, mode values, serialized table name, row states, result order, FieldName) with file and line numbers; framework strings in `erp/references/contract.md`.
  - `pb`: a source (PB) ↔ result mapping list with file:line on both sides.
- `references/lessons.md` in each skill and the one procedure `skills/work/references/compound.md`: **corrections (Compound)** in two steps.
  - Local record: on a correction the model writes to `~/.claude/ace/lessons/<skill>.md` (the layer that owns the rule) without asking. The same file is used on every host; plugin updates don't erase it.
  - Promotion: when the user says "교정 기록 정리해줘", local entries move into the owning skill's `lessons.md`, settled rules go to their reference, and a new version is released.
  - Lessons whose rule a checker enforces are marked `(c)`: `lessons.md` keeps a one-line link, the body lives in `references/lessons-checked.md`, opened only when that check fails or during promotion.

There are no subagents: the main agent reads the skills, does the work and the self-check. Some rules are not kept from documents alone (models differ in how well they follow layout and prohibition rules, and filled tables with static guesses instead of runs). **When a rule exists but is not followed, it becomes a mechanical check instead of more prose.** So there are small scripts and one hook:

| File | Does | Does not |
| --- | --- | --- |
| `skills/sql/scripts/check_sql.py` | Checks the layout and prohibition rules that can be judged reliably (transactions, lock hints, 120 chars, INSERT grid, uppercase, one SELECT column per line, `DBO.` on tables, CTE/`#temp` …; `CONCAT(`/`N'…'` as `[확인]`) and prints failing line numbers and `ACE-CHECK: PASS/FAIL n/m`. framework-specific items (`SY100T`, numbering loop, `--caller trn/SaveNoTrn`) are marked `# framework` | Business comments, unrequested validation, EDIT handling — judgement calls stay in SKILL.md |
| `skills/sql/scripts/make_rollback_test.py` | Drafts a rollback test batch from the SP definition (arguments, XML path, `WITH` columns, WORKTYPE, target tables) | Never runs it; source data and keys stay `-- TODO:` |
| `skills/csharp/scripts/check_designer.py` | `*.Designer.cs`: label alignment, default sizes and "shrunk to one width", overlap, height 25, prefixes and default names, `grd/gvw/col` naming, required block lines, column appearance, `rpsSpin`/`rpscbo` on numeric/code columns, footer count (missing: `[실패]` when the reference grid has one, else `[확인]`, ignored for statistics/aggregate grids; an added count must sit on the first non-editable column and end in `건`), `+=` in `InitializeComponent`; with `--original`, changed properties of existing controls as `[확인]`. Other `.cs`: added `CloseEditor`/`UpdateCurrentRow`, `P_*` flags, `FilterInfo`, forced focus, `MinWidth`, `grp….Text`, `MessageBox`, lambda subscriptions. Profile values (control prefix, default sizes, block lines, grid role names) come from `skills/erp/data/designer.json`; the project's own control sources (files starting with the profile prefix) win for sizes; a Designer without those control types skips these items | Choices that need the screen (a grid's role, whether a size comes from the named reference) are reported as `[확인]` |
| `hooks/ace_stop_check.py` + host adapters `hooks/ace_hosts.py` (Claude Code, Codex), `hooks/ace_antigravity.py` (Stop, SubagentStop) | When `sql` (or `erp`) was used in the session: blocks once if this turn wrote or applied an SP with neither execution evidence (rollback test, `EXCEPT` comparison) nor `실행 검증: 하지 않음 - <이유>`, or if the SP file fails `check_sql.py`. When `csharp` (or `erp`) was used: blocks once if a `.cs` written in this turn fails `check_designer.py` (against the turn's original when it can be rebuilt) | Never injects reminder text; prints nothing when fine; never blocks twice for the same stop; a hook error never blocks work |

The hook reads each host's own record:

| Host | Hook file | What it reads |
| --- | --- | --- |
| Claude Code | `hooks/hooks.json` (`--host claude`) | the session transcript: `Skill`/`Read` of an ACE skill, `Write`/`Edit`/`MultiEdit`, `mssql` tools; the original from `toolUseResult.originalFile` |
| Codex | `hooks/codex-hooks.json` (`--host codex`), named by `.codex-plugin/plugin.json` | the rollout file (`.jsonl` or `.jsonl.zst`) since the turn's `task_started`: ACE skill paths in any tool input, `apply_patch` blocks (also inside `exec` code), `.sql`/`.cs` files named in a PowerShell write and changed during the turn, `mssql` calls inside `exec`; the original is rebuilt by undoing the turn's patches |
| Antigravity | root `hooks.json` (`--host antigravity`) | `PostToolUse` events (`read_file`, `write_file` (`Path`, `Content`), `edit_file` (`Path`, `Target`, `Replacement`), the older `view_file`/`write_to_file`/`replace_file_content`/`multi_replace_file_content`, `run_command`, tools named `*sql*`) kept per conversation in `%TEMP%\ace-hook\`; judged at `Stop` with `fullyIdle` and the normal end `terminationReason: NO_TOOL_CALL`, never again while `continuationActive`. It asks once (`decision: continue`) and then lets the turn end; each `Stop` also writes the work-state file. `hooks/ace_ag_context.py`: `SessionStart` injects that file, `PreInvocation` injects the correction reminder once per request and the connect-first hint after a SQL tool failed with no connection (`injectSteps` system messages). `PreToolUse` (`run_command`, tools named `*sql*`) runs `hooks/ace_ag_pretool.py`: the live-DB guard (the event's `lastUserInput` is the user's message) and the SP apply gate in one hook, answering `deny` or `ask` (`{}` is read as deny and `allow` would skip the user's approval; JSON is ASCII-escaped because the host reads UTF-8). Checked with `agy -p` 2026-11-26 on `run_command`; Antigravity's MCP tool-name format is matched by pattern but not yet seen |

Turn the hook off with `ACE_HOOK=off`. A host may not run plugin hooks (not trusted yet, Python missing, older host), so **every SKILL.md self-check tells the model to run the checker itself** and paste the `ACE-CHECK` line. The older KH plugin grew a large checker and a hook that injected text every turn, and work turned into fighting the hook; so there is one hook, and each script is standard-library Python.

## Changing rules

Write a rule in one place only (`SKILL.md` or one `references/*.md`) in the layer it belongs to; other layers link to it. "Work files and cleanup" and the Compound procedure live only in the `work` skill. Corrections go to the local record first, move into `lessons.md` on promotion, and become reference rules once settled. Procedure: `skills/work/references/compound.md`.

- Profile items in the checkers: `check_sql.py` lines marked `# 프레임워크:` (`SY100T`, numbering loop, `--caller`); `check_designer.py` values in the local `designer.json` (control sizes, block lines, grid roles); formats in `skills/erp/data/*.example.json`. Without a local profile these items are skipped.
- New domain (MES, smart factory): `skills/erp/references/domain-<name>.md` when its first real rule is promoted, plus a row in the erp task table. New framework project: `~/.claude/ace/profile/projects/<PROJECT>.md` with project-only facts (local, not in the repo).

## Measuring compliance (comply)

`comply/run_comply.py` runs real user-style tasks headless on Claude Code (`claude -p`) and Codex (`codex exec`) in a temp copy of each scenario's fixtures, at three prompt levels (supportive, neutral, competing), grades the files with `check_sql` items, regexes and functions, and writes `report.md` with the rules that fail without a reminder. DB MCP servers are off during runs. Scenarios: `comply/scenarios/<id>/scenario.json` + fixture files; add one per lesson that keeps being missed. `--dry-run` prints the prompts; `--grade-only <out>` re-grades a run.

## Dispatching work to other hosts (dispatch)

The `dispatch` skill lets the host you are working in (the orchestrator: Claude Code, Codex or Antigravity) split a task into pieces with disjoint file scopes and hand them to the *other* two hosts through their subscription CLIs, then review every returned diff before accepting it. Everything goes through `skills/dispatch/scripts/dispatch.py` (standard library), so the flow is the same on every host.

| Command | Does |
| --- | --- |
| `dispatch.py usage` | Remaining usage per host, read-only: Claude `claude -p "/usage"` (5-hour, weekly), Codex the last `rate_limits` event in the newest `~/.codex/sessions/<y>/<m>/<d>/*.jsonl` plus `model`/`model_reasoning_effort` from `~/.codex/config.toml` (never written), Antigravity `agy -p "/usage" --output-format json` (Gemini and Claude/GPT groups). The two `/usage` calls are local commands (no model turn). Unreadable → the last good read from `~/.claude/ace/dispatch/usage-<host>.json` marked `cached <time>`, else `unknown` with the reason. No credential file is opened |
| `dispatch.py run plan.json [--dry-run]` | Validates the plan (hosts found, editing pieces have a scope, no two pieces edit the same file, the orchestrator's own host only with `allow_self`, no `needs_db` piece on Antigravity) and runs the pieces in parallel |
| `dispatch.py ledger` | Past pieces from `~/.claude/ace/dispatch/ledger.jsonl`: time, task, host, model, effort, result, changed files, tokens, duration |
| `dispatch.py whoami` | The orchestrator's host (from the environment; `ACE_DISPATCH_SELF` overrides) |
| `dispatch.py review <out> <id> "<status>"` | Records the orchestrator's check result for a piece and rewrites the summary and the log |
| `dispatch.py collect <out> <id> --final-file <report>` | Finishes a `"via": "orca"` piece after its Orca worker's `worker_done`: diff against the before-snapshot, scope check, result and log (`--failed <reason>` when the worker failed) |

How each piece runs (in its `dir`, prompt framed with its scope and "no DB writes, no commits"). `agy.exe` is ~240 MB and an antivirus scan can hold each start for minutes, so every Antigravity call gets `ACE_AGY_START` (default 240) extra seconds; a Defender exclusion for that file (the user's decision) removes the wait:

| Host | Command | Read-only piece | Tokens from |
| --- | --- | --- | --- |
| Codex | `codex exec --json --skip-git-repo-check -s workspace-write -C <dir> -c model_instructions_file='<ACE>/skills/dispatch/base/codex.md' -m <model> -c model_reasoning_effort=… -c mcp_servers={} -` (prompt on stdin; a follow-up uses `codex exec resume … <id> -`), the CLI bundled with the Codex app first (`C:\Program Files\WindowsApps\OpenAI.Codex_*\app\resources\codex.exe`; the standalone CLI fails on the app's `config.toml`) | `-s read-only` | `turn.completed` |
| Claude Code | `claude -p --output-format stream-json --verbose --permission-mode acceptEdits --add-dir <dir> --add-dir <ACE> --append-system-prompt <base/claude-append.md> --model … --effort … --strict-mcp-config` (prompt on stdin; the parent app's session variables are dropped; the orchestrator's memory folder is added read-able; a follow-up adds `--resume <id>`) | `--permission-mode plan`, Read/Glob/Grep only | `result` (`usage`, `modelUsage`) |
| Antigravity | read-only pieces only: `agy -p <prompt> --output-format json --mode plan --model … --effort … --print-timeout …` (`%LOCALAPPDATA%\agy\bin\agy.exe`, the personal subscription account: Vertex/Cloud variables are dropped for the run; a follow-up adds `--conversation <id>`) | `--mode plan` | `usage` in the JSON result |

**Workers run under ACE's instructions, not each platform's default harness.** Codex's default instructions are replaced by `skills/dispatch/base/codex.md` (`-c model_instructions_file`: read before editing, scoped minimal changes, verify, report faithfully, no destructive actions, live-DB guard, Korean, the ACE work skill and the named skills; tools and sandbox stay Codex's; the rollout's `session_meta.base_instructions` shows the file). Claude keeps its own default system prompt; `--append-system-prompt` adds only `base/claude-append.md` (Korean, the ACE folder, the context block), never `--system-prompt`. Antigravity's base instructions cannot be replaced from the CLI (`GEMINI.md`/`AGENTS.md` rules and ACP `systemPrompt.append` only add to it), so the script refuses an Antigravity edit piece.

**Conversation context.** Every new brief gets a context block: the plan's `decisions` (written by the orchestrator), the orchestrator's memory to read (Claude `~/.claude/projects/<key>/memory/MEMORY.md` and its files; Codex `~/.codex/memories/memory_summary.md`, with `~/.codex/AGENTS.md` inlined so `~/.codex` itself is never opened to a worker), the ACE state file `~/.claude/ace/state/<key>.md` of the orchestrator's folder inlined (≤ 3000 chars), the orchestrator's transcript path (search only), and the orchestrator's ACE folder so the worker reads the same ACE version. A follow-up on a piece sets `"resume": "<session id>"` and continues the worker's own session instead of starting fresh.

Per piece the run folder holds `prompt.md`, `raw.jsonl` (trace), `final.md`, `diff.patch` (before/after snapshot of `dir`), `result.json` (status `done`/`error`/`timeout`/`scope-violation`, changed files, files outside scope, tokens, duration, the worker's session id); `summary.md` is the run's table. Exec/print runs are saved by each host (Codex: `~/.codex/sessions`, `originator: codex_exec`) but are **not listed in the hosts' app chat lists**, so every run also writes a readable log, `log.md`, copied to `~/.claude/ace/dispatch/<yyyymmdd-hhmm>-<task>.md`: per piece the request, host/model/effort, final answer, changed files, check result, session id and how to reopen it (`codex resume <id> -C <dir>`, `claude --resume <id>`, `agy --conversation <id>`). For project work a piece's `dir` is the project folder itself (Codex `-C`), not a temp copy. Every CLI call (pieces and usage reads) runs inside a Windows job object that kills the worker's whole process tree when it ends or times out: `agy` starts its MCP servers (node + cmd per server) and leaves them running after it exits or is killed, which leaked ~3 GB per run before. DB MCP servers are off unless a piece sets `needs_db`. Workers read the orchestrator's ACE folder named in the brief, but their hooks come from **their own host's** installed ACE copy (Codex hooks only when trusted; Antigravity has the Stop check but no live-DB guard), so keep all three hosts on the same ACE version, and the orchestrator re-runs the review and checkers itself before accepting a diff.

## API credit (credit)

Optional and inert without a key, so ACE is safe to install for anyone. `skills/credit/scripts/credit_run.py` runs a brief with `claude -p` on an Anthropic API key read from an environment variable (default `ANTHROPIC_CREDIT_KEY`, registered by the user with `register_key.ps1`; hidden input, never printed or written by ACE), and falls back to the subscription when no key is set or the API answers "credit balance is too low" (marked for 24 h). While a key is usable, `hooks/ace_hints.py` adds one line on each prompt routing real work to `credit` or `dispatch`; it is silent otherwise, inside workers, and with `ACE_CREDIT=off`.

`dispatch` uses the same credit per piece (`"billing": "auto|credit|sub"`): Claude pieces on the Anthropic key; Codex pieces on an OpenAI API key passed only as that run's `CODEX_API_KEY` (source: a DPAPI vault named in the local config; API first, but a subscription whose weekly window resets within 48 h with more than 40 % left is used first); Antigravity always on its subscription. All personal settings live outside the repository in `~/.claude/ace/credit.json` (`anthropic_key_var`, `openai_vault`, `models`, `notes`); state and ledgers in `~/.claude/ace/credit/` and `~/.claude/ace/dispatch/`. Every run file is scrubbed of key-shaped strings, and worker environments never inherit API keys.

## Hooks

| Hook | Event | Does |
| --- | --- | --- |
| `hooks/ace_db_guard.py` | PreToolUse (MSSQL tools, shell) | Refuses data/object changes on DBs listed in `~/.claude/ace/config.json` (`{"protected_db": ["<MCP server name>"]}`); passes when the user's latest message names that DB (or 운영/live) with a change verb. @table/#temp writes are fine |
| `hooks/ace_apply_gate.py` | PreToolUse | Stops the first CREATE/ALTER of a real SP in a turn unless its DB hash was read first or the batch has a hash guard; a second attempt passes |
| `hooks/ace_hints.py` | UserPromptSubmit, PostToolUse | A correction-like message → reminder to record the lesson; an MSSQL "No active database connection" → connect first |
| `hooks/ace_state.py` | PreCompact, SessionStart | Saves recent user requests, files written, SPs applied and last DB hashes to `~/.claude/ace/state/<folder>.md` before compaction; restores it at session start (≤ 3 days) |
| `hooks/ace_stop_check.py` | Stop, SubagentStop | Execution evidence and checker failures, see above; .sql/.cs edited without an ACE skill, with a skill but no rule document opened before the first edit, or a framework screen without erp → block once |

Tools and helper skills:

- `review` skill + `agents/ace-reviewer.md`: fresh-eyes review of SP/screen changes (silent failures, screen ↔ SP contract, rules), find-only.
- `style` skill: turns a reference codebase into rules (counts, subagent batches, ask the splits); `skills/sql/scripts/mine_style.py` counts SQL habits.
- `comply` skill: runs `comply/run_comply.py` and acts on the report.
- `dispatch` skill + `skills/dispatch/scripts/dispatch.py`, `usage.py`: split a task across Claude Code, Codex and Antigravity by remaining usage and task kind, review returned diffs, report host/model/effort/tokens (see above).
- `skills/sql/scripts/make_compare_test.py`: old vs new SP comparison batch (temp proc, rollback, SAME/DIFF).
- `skills/erp/scripts/map_project.py`: drafts the framework profile of an unfamiliar solution.

comply, the apply gate, style mining, the SP impact step, the reviewer, the compare batch, project mapping, the live-DB guard, hints and state save take ideas from [everything-claude-code](https://github.com/affaan-m/everything-claude-code) (skill-comply, gateguard, inherit-legacy-style, change-impact, csharp/database-reviewer, silent-failure-hunter, module-regression, codebase-onboarding, hookify, config-protection, continuous-learning, mcp-health-check, pre-compact/session-start; MIT).

## Install and update

Hosts cache a plugin by its version, so **every release bumps the version** in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `.codex-plugin/plugin.json` and `.antigravity-plugin/plugin.json`; without a bump a host keeps the old copy. Releases are published on the `release` branch. Every commit runs `python -B scripts/check_public.py --staged` (the clone's pre-commit hook): it refuses the real names of the user's local profile (`~/.claude/ace/profile/`), so examples stay on the made-up `ExampleLib` profile.

**Claude Code**

```
/plugin marketplace add GNh0/ACE
/plugin install ace@gnho-labs
```

Update: `/plugin marketplace update gnho-labs`, then update the plugin in `/plugin`. From a shell: `claude plugin marketplace add GNh0/ACE`, `claude plugin install ace@gnho-labs`, `claude plugin marketplace update gnho-labs`.

**Codex** (marketplace `.agents/plugins/marketplace.json`, plugin `.codex-plugin/plugin.json`)

```
codex plugin marketplace add GNh0/ACE
codex plugin marketplace upgrade gnho-labs
```

Then enable `ace@gnho-labs` in the plugin list. Codex asks once to trust a new or changed hook (`hooks/codex-hooks.json`); until it is trusted the hook does not run and only the self-check applies. Installed copies live in `~/.codex/plugins/cache/gnho-labs/ace/<version>`.

**Antigravity** (`.antigravity-plugin/plugin.json`, root `hooks.json`)

Install the repository as a plugin from the Antigravity plugin settings; the host starts hooks with the plugin root as working directory (`python -B hooks/ace_stop_check.py --host antigravity <Event>`, `python -B hooks/ace_ag_pretool.py`). Where the `agy` CLI exists, check the folder before installing with `agy plugin validate --json <ACE folder>`. Update by installing the new version.
