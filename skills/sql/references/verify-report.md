# Scenario table, applied check, evidence

## Scenario table

Fill it for every changed SELECT/SAVE path. One side matching is not done.

| Kind | Cases to check | Evidence |
| --- | --- | --- |
| Normal | Rows that must be included/updated | 실행 결과(숫자) / 정적 대조(실행 못 한 이유) / 미확인 |
| Round trip | Query → save unchanged → query: quantity, amount, sequence unchanged (same row unit for SELECT and SAVE) | same |
| Exclusion/edge | Completed previous/current process rows, the document's own quantity in EDIT, partial composite-key mismatch, unrequested WORKTYPE branches, NULL/empty/0, several rows / no selection | same |

Give the reason for any cell that does not apply. Do not run on production or an unknown DB. If you could not run, write the line `실행 검증: 하지 않음 - <이유>` in the answer exactly.

## Applied check (hash)

If you applied the SP, confirm the DB definition equals the `.sql` file by hash, not by eye.

- SQL Server stores the definition as `CREATE PROCEDURE …` even when applied with ALTER. On the file side, replace the first `ALTER PROC` with `CREATE PROC`.
- The trailing newline differs by tool (one LF after `END`, or LF and CRLF). On both sides remove CR and trim leading/trailing spaces, tabs and LF.
- `HASHBYTES` hashes `NVARCHAR` as UTF-16LE bytes, so encode the file as UTF-16LE for SHA-256. The file BOM is dropped on read.

```sql
SELECT A.NAME
     , CONVERT(VARCHAR(64), HASHBYTES('SHA2_256', TRIM(CHAR(32) + CHAR(9) + CHAR(10)
                                                       FROM REPLACE(B.DEFINITION, CHAR(13), ''))), 2) AS DBHASH
FROM SYS.OBJECTS A
        INNER JOIN SYS.SQL_MODULES B
                ON A.OBJECT_ID = B.OBJECT_ID
WHERE A.NAME = 'sp_XX000100_SAVE';
```

```powershell
$t = [System.IO.File]::ReadAllText('<path>\sp_XX000100_SAVE.sql').Replace("`r", "")
$t = [regex]::Replace($t, '^(\s*(?:--[^\n]*\n\s*)*)ALTER(\s+PROC)', '${1}CREATE${2}', 'IgnoreCase')
$t = $t.Trim(" `t`n".ToCharArray())
$sha = [System.Security.Cryptography.SHA256]::Create()
($sha.ComputeHash([System.Text.Encoding]::Unicode.GetBytes($t)) | ForEach-Object { $_.ToString('X2') }) -join ''
```

`TRIM(chars FROM …)` needs SQL Server 2017+. On older versions fetch the definition and hash it in PowerShell the same way. Write "applied" only when both hashes match.

## Evidence format

| Evidence | How |
| --- | --- |
| 실행 결과 | Before/after numbers, e.g. `실행 결과: 수량 18 → 18, 금액 180,000 유지, 순번 1, 불출 20260101-1-1 유지` |
| 정적 대조 | With the reason it was not run (`운영 DB라 실행 안 함`, `대상 데이터 없음`) |
| 미확인 | Why it could not be confirmed |

Example (made-up values): `sp_XX100500_SAVE` with the rollback template, all rolled back:

| Kind | Case | Evidence |
| --- | --- | --- |
| Normal | NEW, 3 details | 실행 결과: 발주 상세 3행(수량 5·4·3, 금액 50,000·40,000·30,000), 불출 3행 순번 1·2·3 짝 일치, 등록자 ACETEST |
| Round trip | 20260101-1 saved twice as queried | 실행 결과: 수량 18 → 18, 금액 180,000 유지, 순번 1, 불출 20260101-1-1 유지, 등록자·등록일 유지 |
| Mixed edit | MOD·DEL·UNC·NEW one each | 실행 결과: MOD 수량 5 → 6·수정자 ACETEST2, DEL 행은 상세·불출 모두 삭제, UNC 수정자 없음, NEW 순번 4·새 불출번호, 등록일 유지 |
| Failed check | 999 over receipt qty 12 | 실행 결과: "발주 수량이 재고 수량을 초과합니다", XACT_STATE 1, 상세 합계 11·3행 전후 같음 |
| Delete | Test document | 실행 결과: 테스트 문서 0건, 20260101-1은 헤더·상세·불출 1건씩 유지 |
| After rollback | All counts | 실행 결과: XX100T(PURDIV 2) 1 → 1, XX210T(XX100500) 1 → 1, SP_LOG 100 → 100, `@@TRANCOUNT` 0 |
