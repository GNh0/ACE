---
name: comply
description: 에이전트가 ACE 규칙을 실제로 지키는지 잰다. Claude·Codex에 사용자 말투의 과제를 세 가지 지시 강도로 시키고 결과 파일을 채점해서, 리마인드 없이 깨지는 규칙을 보고한다. "ACE 규칙 잘 지키나 재 봐줘", "comply 돌려줘", 규칙을 바꾼 뒤 확인할 때 사용한다.
---

# Comply measurement

Runs `comply/run_comply.py` of the ACE plugin (ideas from ECC skill-comply, MIT). Each scenario in `comply/scenarios/<id>/` is a fixture SP/screen + a task written the way the user writes it + checks (check_sql items, regexes, functions, trace patterns).

## Steps

1. Find the ACE folder (the plugin root that holds `comply/`). Python and the host CLIs are needed: Claude (`claude -p`, signed in) and/or Codex (`codex exec`).
2. Dry run first to show the prompts: `python -B <ACE>/comply/run_comply.py --dry-run [scenario ...]`.
3. Run in the background (each run takes minutes): `python -B <ACE>/comply/run_comply.py [scenario ...] --host claude|codex|both --out <folder>`. DB MCP servers are off during runs; work happens in a temp copy.
4. Read `<folder>/report.md`. A row `not run` (login, host error) is not a score: say so and how to fix it.
5. For each rule failing without a reminder (neutral/competing prompts): read the agent's output file and final message to find why (a rule conflict, a missing line in SKILL.md, a checker gap), fix the cause in ACE, re-run that scenario, and compare.
6. Grading changes only: `--grade-only <folder>` re-grades an earlier run without running agents.

## Adding a scenario

One scenario per lesson that keeps being missed: `scenario.json` with `id`, `lesson`, `skills`, `task` (the user's words, no hints that contradict ACE rules), `caller`, `checks`; and the fixture files. Test the checks first: they must fail on the untouched fixture and pass on a correct rewrite.

## Report

Korean table per scenario × host × level (passed/total, failed rules), what was fixed in ACE, before/after scores.
