"""Antigravity PreToolUse entry: runs the live-DB guard and the SP apply gate and returns ONE decision.

  python -B hooks/ace_ag_pretool.py

One hook gives the host one decision for both checks (deny if either check denies). Output: {"decision": "deny",
"reason": ...} or {"decision": "ask"} (the host's normal permission flow; {} would deny, "allow" would skip
approval). ACE_HOOK=off and any error of its own give "ask".
"""
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import ace_antigravity  # noqa: E402


def main():
    reason = None
    try:
        event = json.loads(sys.stdin.buffer.read().decode('utf-8-sig', 'replace') or '{}')
        if isinstance(event, dict) and os.environ.get('ACE_HOOK', '').strip().lower() != 'off':
            import ace_db_guard
            import ace_apply_gate
            name, text, last, _ = ace_antigravity.ag_pre(event)
            reason = ace_db_guard.decide({'tool_name': name, 'tool_input': text, '_last_user': last})
            if not reason:
                reason = ace_apply_gate.decide_antigravity(event)
    except Exception:
        reason = None
    sys.stdout.write(ace_antigravity.ag_answer(reason))


if __name__ == '__main__':
    main()
