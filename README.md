# ACE

SQL Server 프로시저, WinForms/DevExpress 화면, PowerBuilder 이관을 사용자 방식대로 작업하게 하는 Claude Code 플러그인입니다.

## 구성

| 스킬 | 용도 |
| --- | --- |
| `sql` | 쿼리·조회 SP·저장 SP 작성, 정리, 검토 |
| `csharp` | WinForms/DevExpress 화면, Designer, 그리드, 보고서 |
| `pb` | PBL 내보내기, DataWindow 분석, C#/SQL 이관 |

각 스킬은 같은 틀을 씁니다.

- `SKILL.md`: 시작 전에 할 일, 항상 지키는 규칙, 끝내기 전 자체 점검
- `references/`: 규칙의 자세한 형태와 예시 코드
- `references/verify.md`: **검증(EDD)**. 끝내기 전 시나리오 표의 근거를 만드는 법입니다.
  - `sql`: 실행할 수 있으면 실행이 기본입니다. 개발 DB에서 조회는 원본과 새 조회문을 같은 인자로 비교하고, 저장은 트랜잭션 안에서 신규·왕복·혼합 수정·검증 실패·삭제를 돌린 뒤 전부 롤백합니다. 운영 DB이거나 모르면 실행하지 않고 이유를 적습니다.
  - `csharp`: 화면 호출 ↔ SP 계약(인자, `@WORKTYPE`, XML TableName, 행 상태, 결과표 순서, FieldName)을 파일·줄 번호로 대조합니다.
  - `pb`: 원본(PB)↔결과 매핑 목록에 양쪽 파일·줄 번호를 붙입니다.
- `references/compound.md`와 `lessons.md`: **교정 기록(Compound)**. 두 단계로 쌓습니다.
  - 로컬 기록: 교정을 받으면 묻지 않고 `~/.claude/ace/lessons/<스킬>.md`에 적습니다. 플러그인 업데이트에 지워지지 않고 다음 세션부터 바로 읽힙니다.
  - 승격: 사용자가 "교정 기록 정리해줘"라고 하면 로컬 항목을 이 저장소의 `lessons.md`로 옮기고, 굳어진 규칙은 해당 reference로 올린 뒤 버전을 올려 배포합니다.
  - 스킬은 시작할 때 플러그인 `lessons.md`와 로컬 기록을 둘 다 읽고, 다르면 로컬을 따릅니다.

별도 서브에이전트, 훅, Python 체커는 두지 않습니다. 메인 에이전트가 스킬을 직접 읽고 작업과 자체 점검까지 수행합니다.

## 규칙 고치기

규칙은 `SKILL.md`나 `references/*.md` 한 곳에만 씁니다. 같은 규칙을 여러 파일에 중복해서 적지 않습니다. 예외로 "작업 파일과 정리"는 각 스킬이 혼자서도 완결되도록 세 SKILL.md에 같은 내용을 둡니다. 고칠 때는 셋을 함께 고칩니다. `compound.md`도 스킬 이름과 예시만 다르고 세 스킬에 같은 내용으로 두므로 함께 고칩니다. 교정은 먼저 로컬 기록에 쌓이고, 승격할 때 `lessons.md`로 옮긴 뒤 일반 규칙으로 굳어지면 해당 reference로 옮깁니다. 절차는 각 스킬의 `references/compound.md`에 있습니다.

## 설치

```
/plugin marketplace add GNh0/ACE
/plugin install ace@gnho-labs
```
