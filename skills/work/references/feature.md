# Feature-level requests

One instruction often covers several objects: a new screen, a new SP and changes to related screens/SPs, e.g. "PROJECT_B_1 에서 XD100100 를 참조만 하고 이걸 XQ500100으로 … XS100500랑 XS200100 … 단조LOTNUM도 같이 저장". In the Codex logs the most frequent correction was a misunderstood business flow (406 cases), then missing DB application (92) and missed dependent screens/tables.

## Steps

1. **Change list first** ([SKILL.md](../SKILL.md#start) steps 3-4), in the user's order and words: new objects, objects to modify, references, data flow with key columns, objects to back up.
2. **Investigate source and DB before writing.** Read the real rows of the tables in the flow and the key links of the existing SPs; fill keys, units and process decisions in the change list from them.
3. **Impacted objects.** Search other SPs and screens that use the changed tables/columns (query, save and delete paths). Add each to "modify" or mark it "건드리지 않음". Example: deleting in XP500100 must also delete the XS210T rows that XP200100/XP200500 save.
4. **Ask only real decisions**: irreversible DDL, display choices the source cannot decide, business rules that split (when a receipt becomes possible, which C/T when an item has several). One or two short questions; never ask what the user already said, never guess instead of asking.
5. **Per object, apply the language skills**: screens csharp, SPs sql, plus erp on framework-based projects. Write each object's style basis (target-project sibling, [reference vs target](../SKILL.md#reference-vs-target)) in the change list.
6. **Verify the whole flow**: screen ↔ SP contract tables, and one rollback test across the flow (save on the earlier screen → appears in the later screen's query) per the sql skill's verification.
7. **Report** the change list as a table with each object's state: done / DB applied / not built / UI unverified ([Finish](../SKILL.md#finish)).
