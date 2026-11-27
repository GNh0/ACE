---
name: dbhub
description: DB(MSSQL) MCP 목록과 연결에 관한 모든 요청을 맡는다. 공용 허브 하나로 Claude Code·Codex·Antigravity가 같은 목록을 쓰게 하고, 등록·수정(주소·계정·비밀번호)·이름 변경·삭제·켜기/끄기·운영 DB 보호 지정·연결 점검·허브 재시작을 한다. 허브가 없으면(클라이언트마다 npx mssql-mcp를 띄우는 예전 방식이거나 새 PC) 기존 설정의 연결을 옮겨 허브를 먼저 구축한다. "DB 등록할거야", "DB 목록 보여줘", "어떤 DB 붙어 있어?", "비번 바뀌었어", "이 DB 빼줘/잠깐 꺼줘", "이름 바꿔줘", "운영 DB로 막아줘", "DB 연결 안 돼", "MCP가 느려/프로세스 많아", "새 PC에 DB MCP 세팅"에 사용한다. SQL 작성·SP 작업 자체에는 쓰지 않는다(sql 스킬).
---

# ACE dbhub

One local MCP hub (`127.0.0.1:<port>`, default 8765) serves every MSSQL connection to every client and session:
one process instead of one `npx mssql-mcp` per connection per session. Clients see `mssql_<NAME>` servers with the
same tools as mssql-mcp 3.0.0, so the ACE live-DB guard (`~/.claude/ace/config.json` `protected_db`, matched on the
server name) keeps working on all three hosts.

Script: `python -B <ACE>/skills/dbhub/scripts/dbhub.py <command>` (`<ACE>` = this plugin's folder). Runtime, never
in the repository: `$ACE_DBHUB_DIR` or `~/.claude/ace/dbhub` — `connections.json` (the only place passwords live,
owner-only), `hub.log`, `backup/` (every client config is backed up before a change).

## Every request

1. `status`. It says whether the hub is installed, running, and whether legacy per-client entries remain.
2. Not installed, or legacy entries remain → `install` first (tell the user in one line: "허브 구조가 아니라 먼저
   구축한다"). It needs Node.js 20+ and npm; it moves every legacy connection (Claude `~/.claude.json`, Codex
   `config.toml`, Antigravity `~/.gemini/config/mcp_config.json`) into `connections.json`, installs mssql-mcp
   3.0.0 once, starts the hub, checks each connection, rewrites the three clients to the hub URLs (other MCP
   servers untouched) and, on Windows, registers the logon task `ace-dbhub`. `--from <connections.json>` imports
   another hub's list; `--no-autostart` skips the task.
3. Then the request:

| Request | Command |
| --- | --- |
| 등록 | See **Registering** below |
| 목록 ("뭐 붙어 있어?") | `list` — 켬/끔, 운영 보호, 서버/DB, 계정, 옵션 (no passwords) |
| 수정 ("비번 바뀌었어", "주소 바뀜") | `set NAME --password-prompt` / `--server …` / `--port …` / `--database …` / `--user …` / `--encrypt on\|off` / `--legacy-tls on\|off` — only the given fields change; the password follows **Registering**'s two ways |
| 이름 변경 | `rename OLD NEW` (also renames it in `protected_db`; Codex per-tool approvals of the old name are dropped — say so) |
| 잠깐 빼기/다시 넣기 | `disable NAME …` / `enable NAME …` — kept in `connections.json`, left out of the clients (fewer tools in every session) |
| 운영 DB 보호 | `protect NAME …` / `unprotect NAME …` (ACE live-DB guard list). Confirm before `unprotect` |
| 삭제 | `remove NAME` (confirm first; backed up) |
| 점검 | `check [NAME …] [--fix]` — runs `SELECT DB_NAME()` through the hub; failures are diagnosed (step 4) |
| 원인 ("왜 안 돼?") | `diagnose NAME … [--fix]` |
| 직접 고친 뒤 | edit `connections.json`, then `sync` (`--dry` to preview). The hub reloads the file by itself |
| 허브 | `start` / `stop` / `restart`; log `hub.log`; status `http://127.0.0.1:<port>/status` |

4. A connection that fails (`check`, `add`, `set`, or "DB 연결 안 돼"): `diagnose NAME` runs automatically after a
   failed `check`/`add`/`set`; run it yourself otherwise. It checks, in order: the address resolves (DNS) → the port
   answers within 5 s (timeout = VPN/firewall/server down; refused = wrong port or SQL Server not on TCP) → the
   server's login error number (18456 wrong user/password, 18452 SQL logins off, 18470 disabled, 18486 locked,
   18487/18488 password expired/must change) → login works on `master` but not the DB (wrong DB name or no
   permission; it lists the DBs the account can open and the closest names) → encrypt off / legacy TLS / trust
   certificate. Relay its **원인** and **고치기** lines to the user as they are; apply the fix only when it is a
   setting (`diagnose --fix`, `check --fix` and `add` do), never guess a password or DB name — ask.
5. Finish: after `install`, `add`, `remove` or `sync`, tell the user that open Claude/Codex/Antigravity sessions must
   restart to load the list. Name the connection as the user will see it (`mssql_<NAME>`). When a new connection is
   a live DB, ask whether to add it to `protected_db`.

## Registering

When the user says they want to register a DB ("등록할거야", "DB 하나 붙여줘") without the details, ask once, in one
message, for what is missing: 이름 (as it will appear: `mssql_<이름>`), 서버 주소, 포트 (기본 1433), DB 이름, 계정,
and how to give the password:

- **터미널에서 직접 (권장)**: give the user the full command with `--password-prompt` to run themselves (in Claude
  Code: `! python -B "<ACE>/skills/dbhub/scripts/dbhub.py" add <이름> --server … --database … --user …
  --password-prompt`). The password is typed into a hidden prompt and never enters the conversation. Then run
  `check <이름>` and report.
- **채팅으로**: the user pastes it; run `add … --password-stdin` with the password piped on stdin (never on the
  command line, never repeated back), and say once that it stays in this conversation's history.

`add` tests the connection (trying encrypt off / legacy TLS on failure), syncs the three clients and reports.
Options when the user knows them: `--port`, `--no-encrypt`, `--no-trust-cert`, `--legacy-tls`, `--force` (replace).
Ask whether it is a live DB; if yes, offer to add `<이름>` to `protected_db` in `~/.claude/ace/config.json`.

## Rules

- Never print, log or commit a password. `connections.json` stays in the runtime folder only.
- NAME: letters, digits, `_`. Keep the user's existing names (the installer keeps Claude/Codex names without the
  `mssql_` prefix) — habits, `protected_db` entries and lessons refer to them.
- Do not hand-edit the `mssql_*` entries in the client configs; `sync` regenerates them from `connections.json`.
- Hooks: every host's SessionStart runs `ensure`, which starts the hub when it is installed but down, and restarts it
  when a plugin update changed the hub code. It never installs anything.
- Undo: copy the files in `backup/` back to their places and `stop`.
