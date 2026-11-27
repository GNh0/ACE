---
name: credit
description: 조직 API 크레딧(Anthropic API 키)이 등록돼 있으면 작업을 `claude -p`(API 키)로 실행해 크레딧에서 차감하고, 키가 없거나 소진되면 구독으로 처리한다. 스킬·훅·플러그인(ACE)·CLAUDE.md·메모리는 그대로 적용된다. 키가 없으면 아무것도 하지 않으므로 누구나 설치해도 된다. 여러 조각으로 나뉘는 일은 dispatch가 같은 크레딧을 쓴다. ACE 힌트가 크레딧을 쓸 수 있다고 알릴 때, "크레딧 먼저 써", "API 크레딧으로" 할 때 사용한다.
---

# ACE credit

Spend an organization's API credit before the subscription. The orchestrator (this session) stays on the
subscription; only work sent through `scripts/credit_run.py run` (or a dispatch piece billed to the credit) is
billed to the key. So: keep orchestration short, send the real work.

Script: `python -B <ACE>/skills/credit/scripts/credit_run.py <status|setup|run|ledger>` (`<ACE>` = this plugin's
folder). Local settings, never in the repository: `~/.claude/ace/credit.json` — `anthropic_key_var` (default
`ANTHROPIC_CREDIT_KEY`), `openai_vault` (dispatch's Codex API key, see [dispatch](../dispatch/SKILL.md)), `models`
(the user's model per kind of work), `notes` (account facts such as a promo's end date). Read it when present.
`ACE_CREDIT=off` turns the credit off.

## Every request

1. `status`. Read `route`:
   - `here (this is a credit-first child run …)` → you are the child: do the work yourself, never call `run`.
   - `credit` → step 2.
   - `subscription (no usable key: run setup)` → offer **Key setup** below once per session only when the user asked
     for the credit; otherwise do the work here on the subscription without mentioning it.
   - `subscription (credit exhausted)` → do the work here; say "크레딧 소진(재시도: <retry_credit_after>)" once.
2. Decide what goes out. Work that needs this conversation's context, a live-DB change the user must approve, or a
   quick answer (a question, one read, a handful of tool calls) stays here. Work that splits into pieces on
   different files, or has a piece Codex or Antigravity fits better, goes to [dispatch](../dispatch/SKILL.md) (its
   Claude pieces bill to this credit with `"billing": "auto"`). Everything else is one brief here.
3. Write the brief to a file in the scratchpad: the user's request in their words, what was decided here, the files
   and folders, what done looks like, the rules that apply (ACE skills load by themselves in the child; name the ones
   to use), and "report in the user's language: what changed, files, verification". The child does not see this
   conversation, so the brief must stand alone.
4. `run --brief <file> --cwd <project folder> --model <model>` (add `--plan` for read-only analysis; `--add-dir
   <folder>` for every folder outside `--cwd` the child must read or write, and this plugin's folder when it runs
   checkers). Long tasks: run in the background. Model: `models` in `credit.json` when set; otherwise any edit →
   `opus`, finding files or a simple check → `haiku`, a check that needs reading or judgment → `sonnet`.
5. Read the JSON: `route`, `result.result` (the child's report), `result.cost_usd`. Check the changed files or diff
   yourself before saying it is done (the child's report is not proof). End with one line `처리: 크레딧 $<cost>` or
   `처리: 구독(<reason>)`.
6. `route: credit, failed` (another error) → read `error`, fix the brief or do it here; it was not re-run.

## Key setup (no key, or `key: invalid`)

The agent never creates, sees, types or stores the key. Creating a key and pasting it are the user's actions.

1. Ask once: "크레딧을 쓰려면 Console API 키가 필요합니다. 발급 페이지를 열까요?" On yes: `setup --open`.
2. Tell the user: choose the organization that holds the credit, Create Key, copy it, then run in their own
   terminal (hidden input, saved to the user environment variable):

   ```powershell
   powershell -ExecutionPolicy Bypass -File "<ACE>\skills\credit\scripts\register_key.ps1"
   ```

   Not on Windows: put the variable in their shell profile themselves.
3. When they say it is done, `status` → `key: valid` → continue with step 2. Never ask the user to paste the key into
   the chat; if they do, tell them to revoke it in the Console and register a new one.

## Notes

- There is no balance lookup: the first credit run answered "credit balance is too low" marks the credit exhausted;
  the same brief re-runs on the subscription, and the credit is tried again after 24 h.
- With the key, claude.ai connectors are off in the child; local MCP servers and ACE hooks still load.
- The child runs with a clean environment (no desktop-app proxy or session variables) in `acceptEdits` mode, so ACE
  hooks such as the live-DB guard still apply there. It never re-dispatches (`CREDIT_FIRST_CHILD`, `ACE_DISPATCH_CHILD`).
- `ledger` shows runs and cost per mode (the subscription cost is only the API-equivalent estimate).
