# framework lessons

in-house framework, domain and project mistakes. Matching entries override rules; format: [compound.md](../../work/references/compound.md). (c) = enforced by `check_sql.py` / `check_designer.py`, body in [lessons-checked.md](lessons-checked.md).

## SP common objects

- (c) [Do not bypass the common numbering SP to remove a loop (2026-11-20, PROJECT_A XP000100)](lessons-checked.md#do-not-bypass-the-common-numbering-sp-to-remove-a-loop-2026-11-20-project_a-xp000100)

### Common-code names by JOIN, user names by function (2026-11-20)
- Mistake: fetched common-code names with the `F_CODE_NAME` function too.
- Rule: common-code names JOIN `MS011T`; user names use `F_FIND_USERNM` only in the outermost SELECT, JOIN in bulk queries. [common-sp.md](common-sp.md#name-lookup)

## Save call

### No transaction code in SAVE SPs (2026-11-20)
- Mistake: put `BEGIN TRANSACTION`/`COMMIT`/`ROLLBACK`/`TRY/CATCH` or `@STARTTRANCOUNT` in a SAVE SP, or in the screen.
- Rule: new saves use `SaveTrn` and the SP has no transaction code; check the next entry first. [save-call.md](save-call.md#transactions), [save-flow.md](save-flow.md#saving-rules)

### Keep the SP transaction for SaveNoTrn saves (2026-11-20, PROJECT_A XS200100)
- Mistake: removed the transaction from `sp_XS200100_SAVE`, whose screen uses `SaveNoTrn`; it was the only protection.
- Rule: find the call line before removing; with `SaveNoTrn` or when you cannot ask, keep it. [save-call.md](save-call.md#transactions)

### XML arguments the screen passes as null get a default (2026-11-20, PROJECT_A XM100500)
- Mistake: `@XML_XX110T` had no default; the screen sends `null` on delete (`XM100500.cs:253`), so delete failed "not supplied"; the test always passed it.
- Rule: give `= NULL` and omit the argument in the rollback test like the screen. [save-call.md](save-call.md#arguments-the-screen-may-pass-as-null), [verify-save.md](../../sql/references/verify-save.md#must-keep)

## Screens

- (c) [Default size and right-aligned labels (2026-11-20, XQ500100)](lessons-checked.md#default-size-and-right-aligned-labels-2026-11-20-xq500100)
- (c) [Write the whole property block (2026-11-20, XQ500100)](lessons-checked.md#write-the-whole-property-block-2026-11-20-xq500100)

### No invented flags or signatures (2026-11-20, XQ500100)
- Mistake: invented `isBindingList` and `QuerySP(…, DataRow dr = null)`.
- Rule: sibling's `isFlagRowChanged`, `string` key arguments. [screen-skeleton.md](screen-skeleton.md#rules-in-this-skeleton)

### Combined key must match the screen's composition (2026-11-24, eval S2)
- Mistake: a rewritten `sp_XM200100_SELECT` built `PURKEY` as `PURNUM-PURSEQ1` (2 parts) where the screen checks duplicates per detail (`PURNUM-PURSEQ1-PURSEQ2`), blocking a second item of the same order. User: "PURKEY,KEYCODE 형태로 PURNUM,PURSEQ,PURSEQ2 같은거 따로 조회 + 합친거같이 조회하는형태는 보통 쓰는편이 맞아".
- Rule: keep returning parts + combined key; build it with the screen's/siblings' exact parts and order. [keys.md](keys.md)
- Screen side (user, same day): "C#에서 PURNUM,PURSEQ,PURSEQ2 각각 따로 그리드에 컬럼은 만들어두는데 숨겨두는처리를 하고 그 값을 보여주는형태임" — part columns exist hidden, the combined key is the shown column.
- Survey and naming (2026-11-24): user: "PURNUM,ORDNUM,RECDT 등 그 패턴을 정확하게 파악해"; surveyed 183 user SPs and 456 Designer files; user chose the current-code naming (`KEYCODE` own key, `<FAMILY>NUMS` referenced). [keys.md](keys.md)

### Sequences inside the INSERT, not a staging UPDATE (2026-11-24, XM100500)
- Mistake: to share PURSEQ2 between XS210T and XX110T I added `UPDATE @TMPXX110T SET PURSEQ2 = …` before the INSERTs; user: "장난치니?? 이건 INSERT 문에서 JOIN하는 방식 그대로 쓰는거 맞는데?".
- Rule: compute detail sequences in each INSERT … SELECT with the MAX derived JOIN + ROW_NUMBER (same ORDER BY); no staging UPDATE. [common-sp.md](common-sp.md#sp_new_key)

### User names by MS095T JOIN (2026-11-24, PROJECT_B analysis)
- Mistake: ACE told agents to use `DBO.F_FIND_USERNM` for user names, while the newest PROJECT_B SPs JOIN MS095T and the JOIN measured ~14x faster on 580k rows.
- Rule: user names JOIN `MS095T` once per name; user: "JOIN 기본으로". [common-sp.md](common-sp.md#name-lookup)
