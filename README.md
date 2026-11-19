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
- `references/lessons.md`: **교정 기록(Compound)**. 사용자가 교정한 실수를 `실수 → 규칙`으로 쌓고, 다음 작업 전에 먼저 읽습니다.
- 자체 점검의 **시나리오 표(EDD)**: 정상 사례와 제외·경계 사례를 양쪽 다 확인해야 완료로 봅니다.

별도 서브에이전트, 훅, Python 체커는 두지 않습니다. 메인 에이전트가 스킬을 직접 읽고 작업과 자체 점검까지 수행합니다.

## 규칙 고치기

규칙은 `SKILL.md`나 `references/*.md` 한 곳에만 씁니다. 같은 규칙을 여러 파일에 중복해서 적지 않습니다. 예외로 "작업 파일과 정리"는 각 스킬이 혼자서도 완결되도록 세 SKILL.md에 같은 내용을 둡니다. 고칠 때는 셋을 함께 고칩니다. 교정은 우선 `lessons.md`에 추가하고, 일반 규칙으로 굳어지면 해당 reference로 옮깁니다.

## 설치

```
/plugin marketplace add GNh0/ACE
/plugin install ace@gnho-labs
```
