---
name: dispatch
description: 개발 작업을 서로 겹치지 않는 조각으로 나눠 Claude Code·Codex·Antigravity 구독 CLI에 맡기고, 남은 사용량과 작업 종류로 호스트·모델·추론 등급을 고르고, 돌아온 diff를 ACE review·검사기로 확인한 뒤 조각별 호스트·모델·추론·토큰·결과 표로 보고한다. "나눠서 시켜줘", "코덱스한테 맡겨"라고 할 때뿐 아니라, 말하지 않아도 작업(또는 조각)에 더 잘 맞는 플랫폼·모델이 지금 호스트가 아닐 때 사용한다. 이 대화의 맥락이 꼭 필요한 일과 같은 파일을 고치는 조각만 지금 호스트에 남긴다. 어느 호스트에서 실행해도 나머지 두 호스트에 맡긴다.
---

# ACE dispatch

The agent running this skill is the **orchestrator** (Claude Code, Codex or Antigravity). It splits the task, hands pieces to the *other* hosts through their subscription CLIs, then reviews and reports. All calls go through one script, so the flow is the same on every host:

`python -B <ACE>/skills/dispatch/scripts/dispatch.py <usage|run|ledger|whoami>` (`<ACE>` = this plugin's folder; standard-library Python).

## 1. Read usage

`dispatch.py whoami` → the orchestrator's host. `dispatch.py usage` → used % and reset per window: Claude 5-hour/weekly, Codex weekly (+ `config.toml` model/effort), Antigravity Gemini and Claude/GPT groups. `unknown` = could not be read; `cached <time>` = the last good read (live read failed). It can take minutes (agy.exe starts slowly under antivirus scans): run it once per task, in the background. No credentials are read.

## 2. Split

Follow [work](../work/SKILL.md) for the instruction list. Each piece gets:
- `files`: an explicit file scope (paths or globs inside `dir`). **No two pieces edit the same file**: the script refuses overlapping scopes. Read-only pieces set `read_only: true` and need no scope.
- a self-contained prompt: goal, files, the rules to follow (name the ACE skills, such as `ace:sql`, and the reference files), the done criteria. The worker never sees this conversation.
- `needs_db: true` only when it must read a DB. DB MCP servers stay off otherwise. Writes to live DBs are never part of a piece.

Keep a piece here (no dispatch) when it is a few tool calls, needs the conversation's context, or touches the files another piece edits.

## 3. Choose host, model, effort

Pick by kind first, then headroom (the host with the most remaining % in the window that resets last). When the best fit is the orchestrator's own host, do that piece here without dispatching (a run on the own host only when the user asks: `"allow_self": true`):

| Piece | First choice | Then |
| --- | --- | --- |
| Big multi-file feature, refactor, migration (many `.cs`/`.sql`) | Codex `gpt-6.2-sol`, effort `high` (`xhigh` for hard logic) | Claude `claude-opus-5-5` high |
| ACE rule maintenance, analysis, review, SP with the user's style rules | Claude `claude-opus-5-5` (effort `high`) | Codex |
| Read-only batch (list, find, summarise, count) | Antigravity `gemini-4-hydrogen-medium` | Claude `claude-haiku-5-5`, Codex effort `low` |
| Self-contained edit piece (one area, clear spec) | Codex effort `medium` | Claude `claude-sonnet-5-5` |
| Second opinion on a design, planning (read-only) | Antigravity `gemini-4-carbon-high` | `claude-opus-5-5-high` there, or the other host |

**Antigravity takes read-only pieces only**: its base instructions cannot be replaced from the CLI (rule files and ACP only append), and the user does not want a platform's own default harness editing their code; the script refuses an Antigravity edit piece.

Antigravity uses Gemini 4 by default: Carbon is its planner (Antigravity's own Orchestrator plans with Carbon High), Hydrogen its executor (it executes with Hydrogen High). The Gemini group shares one quota, used in proportion to token cost. `gemini-3.8-flash-*` only when that group is above ~85 % used or the user asks for it.

Move a piece off a host whose window is above ~85 % used or `unknown`. Antigravity has no live-DB guard hook: `needs_db` pieces go to Codex or Claude. Model names: `agy models` lists Antigravity's. Codex's default is the `config.toml` value, which the script reads and never writes.

## 4. Run

Write `plan.json` next to the work (format in the script header): `{"task", "decisions", "cwd", "pieces": [{"id", "host", "model", "effort", "dir", "files", "read_only", "needs_db", "timeout", "prompt" | "prompt_file", "resume"}]}`.

- **`decisions`**: write it every time: what the user asked and decided in this conversation that the pieces depend on (names, rules, corrections, what not to touch), in a few lines. The worker never sees this conversation.
- The script adds a **context block** to every new brief: `decisions`, the orchestrator's memory to read (Claude `~/.claude/projects/<key>/memory/MEMORY.md`; Codex `~/.codex/memories/memory_summary.md`, `AGENTS.md` inlined), the ACE state file of `cwd` inlined (≤ 3000 chars), the orchestrator's transcript path (search only), and this ACE folder (the worker reads the orchestrator's ACE version, not its own install).
- **Base instructions**: Codex runs with `model_instructions_file` = `base/codex.md` (replaces Codex's default instructions: read before editing, scoped minimal changes, verify, report faithfully, no destructive actions, DB guard, Korean, ACE skills; tools and sandbox stay Codex's). Claude keeps its default prompt plus `--append-system-prompt` `base/claude-append.md`, never `--system-prompt`.
- **Follow-ups** on a piece set `"resume": "<its session id>"` (from `result.json`): the worker continues its own session (`codex exec resume`, `claude --resume`, `agy --conversation`) and the context block is not repeated.
1. `dispatch.py run plan.json --dry-run`: validates (hosts exist, scopes don't overlap, no self host, an editing piece has a scope) and prints the commands.
2. `dispatch.py run plan.json --out <folder>` **in the background**; pieces run in parallel, headless, in their `dir` (exact commands in the script header). Don't poll.
3. Per piece: `prompt.md`, `raw.jsonl` (trace), `final.md`, `diff.patch`, `result.json` (status, changed files, outside scope, tokens, duration, worker session id); `summary.md` per run; one line per piece in `~/.claude/ace/dispatch/ledger.jsonl`.
4. **The log is the record**: exec/print runs do not appear in the Codex app's (or the other hosts') chat lists. Each run writes `~/.claude/ace/dispatch/<yyyymmdd-hhmm>-<task>.md`: request, host/model/effort, final answer, changed files, check, session id and how to reopen it (`codex resume <id> -C <dir>`, `claude --resume <id>`, `agy --conversation <id>`). For project work `dir` is the project folder itself, never a temp copy.

## 5. Check every returned diff

A piece is accepted only after it passes, whatever its final message claims:
- `status` is `done`. `timeout`/`error` → rerun smaller or do it here. `scope-violation` → the files outside scope are reverted or explained before anything else.
- Read `diff.patch` whole. Run the [review](../review/SKILL.md) skill on the changed files (fresh-eyes review; Claude Code can use the `ace-reviewer` agent), plus the checkers: `check_sql.py` for `.sql`, `check_designer.py` for `.cs`, with `--original` from the snapshot (the `a/` side of the diff).
- SQL that must run: the execution evidence of [sql verify](../sql/references/verify.md) is the orchestrator's job, never the worker's word.
- Conflicts between pieces (one renamed what another calls) → fix here.

Record each piece's check status with `dispatch.py review <out> <id> "통과" | "수정 후 통과" | "반려 (이유)"` (rewrites the summary and the log).

## 6. Report (Korean)

| 조각 | 호스트 / 모델 / 추론 | 결과 | 변경 파일 | 토큰 | 검사 | 세션 |
| --- | --- | --- | --- | --- | --- | --- |
| id: one-line job | codex / gpt-6.2-sol / high | done 312s | `A.cs`, `B.sql` | 48,120 (in 40,002 / out 8,118) | 통과 (check_sql PASS 31/31) | `codex resume <id>` |

Then the log path, the usage after the run (`dispatch.py usage`), what was redone here and why, and what is not verified. `dispatch.py ledger` shows past pieces (time, task, host, model, effort, tokens, result).

Lessons: [references/lessons.md](references/lessons.md) (override the rules above).

## Self-check

- [ ] usage read; no host above ~85 % or `unknown` given a big piece
- [ ] scopes disjoint; dry run passed; no live-DB write in any prompt; `decisions` written; Antigravity read-only
- [ ] every diff read, reviewed and checked (`ACE-CHECK` lines pasted), out-of-scope changes handled
- [ ] report table with host / model / effort / tokens / check status
