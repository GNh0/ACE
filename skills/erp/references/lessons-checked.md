# framework lessons enforced by the checkers

Bodies of the (c) entries indexed in [lessons.md](lessons.md). Open this file only when `check_sql.py` / `check_designer.py` fails one of these items or when promoting lessons. Titles are anchors.

## SP common objects

### Do not bypass the common numbering SP to remove a loop (2026-11-20, PROJECT_A XP000100)
- Mistake: to drop a numbering cursor, wrote `SY100T` directly with `ROW_NUMBER()`; no other SP does.
- Rule: number only through the common SP; keep a small loop around just the numbering call. [common-sp.md](common-sp.md#sp_new_key), conflicts: [work SKILL.md](../../work/SKILL.md#scope)
- Check: `check_sql.py` `채번 테이블(SY100T) 직접 쓰기 없음` (`# framework`)

## Screens

### Default size and right-aligned labels (2026-11-20, XQ500100)
- Mistake: labels overlapped inputs, were not right-aligned; labels, dates and LOT input shrunk to one width ("기본크기, 오른쪽정렬맞춤").
- Rule: default sizes, `Far`/`Center` labels, no overlap. [controls.md](controls.md#size-and-placement)
- Check: `check_designer.py` sizes, label alignment, overlap

### Write the whole property block (2026-11-20, XQ500100)
- Mistake: added `ymdFRDT`/`txtLOTNUM` with constructor defaults only ("크기,속성 다지키라고").
- Rule: copy the Designer block line for line. [controls.md](controls.md#designer-blocks)
- Check: `check_designer.py` required block lines
