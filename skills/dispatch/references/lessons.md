# dispatch lessons

Matching entries override rules; format: [compound.md](../../work/references/compound.md).

### Workers run under ACE's instructions, not each platform's default harness; they get the conversation's context (2026-11-25)
- Mistake: workers ran with Codex's and Antigravity's default instructions and knew nothing of the orchestrator's conversation except the piece prompt. The user dislikes the other platforms' default instructions/harness and asked: "그렇게 고쳐줘 그리고 대화 기억같은건 방법이 없나?"
- Rule: Codex gets `base/codex.md` as `model_instructions_file` (Claude-Code-style working principles, Korean, ACE skills); Claude keeps its default prompt plus `--append-system-prompt` only; Antigravity, whose base cannot be replaced from the CLI, gets read-only pieces only. Every brief carries the context block (plan `decisions`, orchestrator memory paths, ACE state, transcript path, the orchestrator's ACE folder); follow-ups resume the worker's own session. [SKILL.md](../SKILL.md#4-run)
- Check: `dispatch.py` refuses an Antigravity edit piece; the Codex rollout's `session_meta.base_instructions` starts with `# ACE worker (Codex)`.
