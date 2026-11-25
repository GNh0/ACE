---
name: erp
description: 업무 시스템(ERP·MES·스마트팩토리) 화면과 SP를 만드는 규칙. 기본 폼·저장 호출·화면↔SP 계약·채번·마감·키·코드명 같은 역할별 규칙, 업무 흐름(재고 이동 등), 프로젝트별 사실(로컬 프로필 ~/.claude/ace/profile). 프레임워크 이름은 역할별 프로필로 매핑해서 어떤 프로젝트에서도 쓴다. 업무 화면·SP 작업이면 sql·csharp 스킬과 함께 사용한다. 서식만 정리하는 SQL 작업에는 쓰지 않는다.
---

# Business-system layer: framework roles, domain, projects

Layer below [sql](../sql/SKILL.md)/[csharp](../csharp/SKILL.md) (their self-checks still apply); it only adds. Follow the [work](../work/SKILL.md) skill. Open only the references below, one per read. **Not for format-only SQL tasks.**

## Start

1. Read [lessons](references/lessons.md) and the local `erp.md` record.
2. Map the framework: read the local profile `~/.claude/ace/profile/profile.md` and `projects/<PROJECT>.md` there; a project without one gets a role mapping first ([profile](references/profile.md)). Names in the references (`FrmBase`, `ux` controls, `SaveTrn`, `SP_NEW_KEY` …) are a made-up example profile: translate them through the local profile, never write them into real code.

| Task | Read |
| --- | --- |
| New SELECT SP, SP header | [sp-skeleton](references/sp-skeleton.md) |
| New SAVE SP | [sp-save](references/sp-save.md), [common-sp](references/common-sp.md) |
| Closing, numbering, display keys, names | [common-sp](references/common-sp.md) |
| SAVE transaction, null arguments | [save-call](references/save-call.md) |
| Screen ↔ SP contract table, rollback-test XML | [contract](references/contract.md) |
| New list + detail screen | [screen-skeleton](references/screen-skeleton.md), [controls](references/controls.md) |
| Add controls | [controls](references/controls.md) |
| Save, delete, header + detail | [save-flow](references/save-flow.md), [behaviors](references/behaviors.md) |
| Event/method per behaviour | [behaviors](references/behaviors.md) |
| Map a new project's framework (roles → names) | [profile](references/profile.md) |
| Current profile's binding/XML/DB calls (`RowToPanel`, `TableToXml`, `SaveTrn` …) | [framework](references/framework.md) |
| Stock moves (issue + receipt pairs) | [domain-erp](references/domain-erp.md) |
| Changing an existing SP or its parameters/result columns | [contract](references/contract.md#impact-before-changing-an-sp) |

## Always-keep rules

(c) = checked by `check_sql.py` / `check_designer.py`.

Names in parentheses are the current profile; use the mapped name of the project ([profile](references/profile.md)).

- Code names JOIN the code table (`MS011T`); user names JOIN the user table (`MS095T`), one per name; no new name function. [common-sp](references/common-sp.md#name-lookup)
- Composite keys: `NUM + '-' + CONVERT(VARCHAR(10), SEQ…)`; row's own key `KEYCODE`, referenced number `<FAMILY>NUMS`; parts returned too; split with the key-split function (`F_SPLIT_KEY`); grid shows the key, part columns hidden (no Visible line). [keys](references/keys.md)
- (c) Header numbers only via the numbering SP (`SP_NEW_KEY`), never by writing its table. [common-sp](references/common-sp.md#sp_new_key)
- Transaction follows the caller: when the save call owns the transaction (`SaveTrn`) the SP has none; a call without one (`SaveNoTrn`) or unknown keeps the SP transaction. [save-call](references/save-call.md#transactions), [save-flow](references/save-flow.md#saving-rules)
- Args the screen may send `null`: `= NULL`. [save-call](references/save-call.md#arguments-the-screen-may-pass-as-null)
- The project's control per role (`u_…`); keep their defaults. [controls](references/controls.md#choosing-a-control)
- (c) Sizes match the neighbouring controls, not one shrunk width; labels right-aligned; no overlap; height 25 unless asked. [controls](references/controls.md#size-and-placement)
- (c) Whole Designer block, prefixes. [controls](references/controls.md#designer-blocks)
- Command/value-change handlers check the edit mode (`m_EditState`) first. [behaviors](references/behaviors.md#inputs)

## Self-check

Run the sql/csharp checkers yourself (a host hook may not run); they cover profile items: `check_sql.py --caller trn|plain|unknown` from the real call (caller owns the transaction / does not / unknown), `check_designer.py` with the profile's control defaults (skipped for other control libraries).
