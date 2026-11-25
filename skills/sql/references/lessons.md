# SQL lessons

Matching entries override rules; format: [compound.md](../../work/references/compound.md). (c) = enforced by `check_sql.py`, body in [lessons-checked.md](lessons-checked.md).

---

## Layout

- (c) [All identifiers uppercase (v3.6.3)](lessons-checked.md#all-identifiers-uppercase-v363)
- (c) [Long INSERT values go at the line end (v3.6.8)](lessons-checked.md#long-insert-values-go-at-the-line-end-v368)
- (c) [Clauses are left-aligned (2026-11-20)](lessons-checked.md#clauses-are-left-aligned-2026-11-20)
- (c) [Do not break the INSERT grid into one-cell lines (2026-11-20, PROJECT_A XM100500)](lessons-checked.md#do-not-break-the-insert-grid-into-one-cell-lines-2026-11-20-project_a-xm100500)

### Aliases by business role (v3.6.2)
- Mistake: chose aliases by JOIN order or the table name's first letter.
- Rule: same-business tables take the base letter plus a number; only a new business takes the next letter. [style-alias.md](style-alias.md#alias-roles)

### Key conditions get a business comment (2026-11-20)
- Mistake: wrote quantity/exclusion conditions without a comment, or with a comment that just repeated column names.
- Rule: comment directly above in business terms with the same operator, and name derived aggregates `OUTQTY`/`INQTY`. [style-insert.md](style-insert.md#condition-comments)

### Also format the untouched original parts (2026-11-20, three-model test)
- Mistake: all three models kept the original's one-line `INSERT INTO @T (…)`, multi-column table variable lines, 120+ lines and `SET XACT_ABORT ON`.
- Rule: when the task changes logic, bring the whole SP to the rules. [style.md](style.md#formatting-untouched-parts)

## SELECT

- (c) [No CTE, no #temp tables (2026-11-20, PROJECT_A XQ500100)](lessons-checked.md#no-cte-no-temp-tables-2026-11-20-project_a-xq500100)
- (c) [Banning one pattern made the model swap to another (2026-11-20, PROJECT_A XQ500100)](lessons-checked.md#banning-one-pattern-made-the-model-swap-to-another-2026-11-20-project_a-xq500100)
- (c) [EXISTS/IN subquery → JOIN (v3.6.4)](lessons-checked.md#existsin-subquery--join-v364)

## SAVE structure

- (c) [No lock hints (repeated since before 2026-11-20)](lessons-checked.md#no-lock-hints-repeated-since-before-2026-11-20)

### Fix SAVE fixed-rule violations even in the original (v3.6.5)
- Mistake: kept count variables, several COMMITs and early RETURNs because the original had them.
- Rule: when changing SAVE logic apply the fixed rules; in format-only work just report locations. [save.md](save.md#save-fixed-rules)

### Minimize @variables (v3.6.6)
- Mistake: created assign-once-read-once variables and variables copying header values.
- Rule: write the expression in place or JOIN the table variable / target rows. [save.md](save.md#save-fixed-rules)

### Set-based allocation (v3.6.7)
- Mistake: allocated row by row with WHILE/cursor/`SELECT TOP 1 @var` and copied the code into NEW and EDIT.
- Rule: one INSERT with a running-range JOIN; shared processing once. [save-stock.md](save-stock.md#allocation-insert)

### Same row unit for SELECT and SAVE (2026-11-20, PROJECT_A XM100500)
- Mistake: the save merged rows with `GROUP BY` but DETAIL returned child rows with the merged amount; re-saves multiplied it.
- Rule: check that one saved detail row and one DETAIL row are the same unit. [save-edit.md](save-edit.md#same-row-unit-for-select-and-save)

### EDIT works by row state (2026-11-20, PROJECT_A XM100500)
- Mistake: EDIT deleted and re-inserted all details, overwriting registrant/date and renumbering.
- Rule: split by `GBN`: DEL deletes, only MOD updates, only NEW inserts, number only when NEW rows exist. [save-edit.md](save-edit.md#row-states-in-edit)

### MOD rows also UPDATE the paired table (2026-11-20, three-model test)
- Mistake: updated `MOD` details but deleted/re-inserted their paired issue rows, renumbering them.
- Rule: `MOD` rows are UPDATEd in every target table. [save-edit.md](save-edit.md#row-states-in-edit)

### No unrequested validation (2026-11-20, three-model test)
- Mistake: added "duplicate selection" / "unregistered item" checks to keep sequence pairs or JOINs safe.
- Rule: make it work without new checks; propose needed ones in the answer. [save.md](save.md#unrequested-validation)

## Way of working

### Do not hide cases that change behavior (2026-11-20, three complex-SP test)
- Mistake: a set-based rewrite changed results for "delete then re-add" and "same key twice"; noted low in the report, change made anyway.
- Rule: if results can differ, do not make the change; if it must be made, say so at the top of the answer. [work SKILL.md](../../work/SKILL.md#scope)

### Filters in WHERE, not in INNER JOIN ON or HAVING (2026-11-24)
- Mistake: results used INNER JOIN with long ON condition lists and derived tables filtered by HAVING (partly because select.md prescribed INNER JOIN for EXISTS conversion); user: "INNER JOIN으로해서 안에 조건을 HAVING이나 아니면 JOIN에 AND 를 엄청 나열하는거같은데 … LEFT OUTER JOIN에 밖의 WHERE 절에 조건을 쓰는걸 더 선호".
- Rule: LEFT OUTER JOIN on join keys; filters and aggregate comparisons in the outer WHERE. [style.md](style.md#sql-layout)

### Empty checks: ISNULL(X, '') <> '', not NULLIF IS NOT NULL (2026-11-24)
- Mistake: conditions like `AND NULLIF(A.LOTNUM, '') IS NOT NULL`; user: "조회할때 빈값을 표시할땐 NULLIF 를 쓰지만 조건같은곳에 쓸땐 ISNULL(A.LOTNUM, '') <> '' 이런방식을 더 선호함".
- Rule: conditions use `ISNULL(X, '') <> ''` / `= ''`; NULLIF only for displayed columns. [style.md](style.md#sql-layout)
- Follow-up (same day): user: "IS NULL, IS NOT NULL 자체를 그렇게 선호하는편이 아니거든? 웬만하면 잘 안쓰는편이야" — the ISNULL form also replaces `IS (NOT) NULL`, including LEFT JOIN found/not-found tests.

### No column fallback with ISNULL (2026-11-24)
- Mistake: SELECTs like `ISNULL(B.INVUNIT, A.INVUNIT)` (also in Codex logs: "ISNULL(B.INVUNIT, A.INVUNIT)이딴식으로 하지말랬지"); user: "ISNULL로 다른컬럼 대체하는형태 별로 안좋아하고 … SELECT 문쓸때".
- Rule: one correct source per value; no ISNULL/COALESCE fallback to another column. [style.md](style.md#sql-layout)

### CONVERT before FORMAT (2026-11-24)
- Mistake: `FORMAT(x, '##0')` in key expressions where `CONVERT` was used elsewhere in the same SP (PROJECT_A `sp_XS100100_SELECT`); user: "convert가 속도가 더 빠른걸로알고있고 format형태는 앞에 고정적으로 몇자리 표현되거나 보여야할 포맷이 지정된 형태가 아닐경우는 Convert 우선사용".
- Rule: `CONVERT` by default; `FORMAT` only for fixed display formats. [style.md](style.md#sql-layout)

### Master tables: LEFT OUTER JOIN, existence only via IF EXISTS (2026-11-24, PROJECT_A XM100500)
- Mistake: SPs joined `MS020T`/`MS030T` with INNER JOIN (rows silently dropped when the master row is missing); user: "내가 품목이나 업체가 없으면 처리안되게 해달라고한적도 없는데 전부 INNER JOIN으로 처리됐거든? … 쟤네가 있어야하면 IF EXISTS 로 예외처리가 되게 해달라고 하는거지 저렇게 INNER JOIN을 걸필요가 없어".
- Rule: master tables LEFT OUTER JOIN; a required master row is an explicit IF EXISTS check, only when asked. [style.md](style.md#sql-layout)
- Follow-up (same day): "그 두개뿐만 아니라 INNER JOIN을 왜이렇게 쓰는지 잘 모르겠거든 필수테이블 연결아닌데도" — LEFT OUTER JOIN is the default for every non-required table; INNER only for the staging table in SAVE writes or user-stated required rows.

### CASE always has ELSE (2026-11-24, XM200150)
- Mistake: `(CASE WHEN C.PROCCD = '06' THEN A.CUSTLOTNUM END)`; user: "ELSE NULL이나 ELSE '' 같은거 가져다 팔아먹었네?".
- Rule: every CASE has ELSE. [style.md](style.md#sql-layout)

### Validations before writes (2026-11-24, XM200150)
- Mistake: quantity checks (`IF EXISTS … RAISERROR`) ran after the INSERT, relying on the caller's rollback; user: "IF EXISTS는 항상 최우선으로 먼저 처리하고 난뒤에 들어가야지 … 먼저 처리하고 이거 안맞네 하고 예외발생시킬거냐".
- Rule: every check runs before the first write; a post-save total is computed from existing rows not being changed + the staging rows. [save.md](save.md#save-fixed-rules)

### Style rules win in a cleanup (2026-11-24, ACE comply run 1)
- Mistake: asked to clean up a SELECT SP "우리 스타일로", Codex saw `[실패] 마스터 테이블(MS0xxT)은 LEFT OUTER JOIN` and kept the INNER JOINs, HAVING, FORMAT and the ISNULL fallback "to preserve rows" (all three prompt levels).
- Rule: in a cleanup or new SP the user's style rules win; change and list differing rows/values. [style.md](style.md#style-rules-win)

### Header change that changes details stamps the modifier (2026-11-24, PROJECT_A XM200150)
- Mistake: the header-to-detail sync UPDATE dropped `MODDT/MODEMPNO/MODIP` (ACE said "without a modifier stamp"), so details changed by a header edit kept no modifier. User: "만약 헤더가 수정되어서 상세의 값이 바뀌는게 있으면 같이 바뀌어야지?".
- Rule: stamp the modifier on details whose copied values change; rows left as they were are not touched. [save-edit.md](save-edit.md#row-states-in-edit)
