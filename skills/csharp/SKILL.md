---
name: csharp
description: WinForms/DevExpress 화면, Designer, 그리드, 사용자 컨트롤, XtraReport를 실제 프로젝트 방식으로 작성·수정·검토한다. C# 화면·폼·그리드·컨트롤·Designer·보고서 수정 요청에 사용한다.
---

# C# 화면 작성·수정

이 스킬은 메인 에이전트가 직접 따른다. 별도 에이전트에 넘기지 않는다.

## 시작 전에

1. 교정 기록을 읽는다. 플러그인의 [lessons.md](references/lessons.md)와 로컬 기록 `~/.claude/ace/lessons/csharp.md`(없으면 넘어간다) 둘 다다. 둘이 다르면 로컬이 최신이다. 이번 작업에 해당하는 항목은 아래 규칙보다 우선한다. [compound.md](references/compound.md)
2. **비교 프로그램**을 정한다. 사용자가 지정한 비교 프로젝트에서 같은 역할의 실제 화면을 찾는다. 지정이 없으면 물어본다. 작성 방식은 비교 프로그램, 동작은 대상 프로젝트의 실제 호출부·컨트롤·라이브러리가 기준이다.
3. 바꾸는 부분에 맞는 문서만 읽는다.

| 바꾸는 부분 | 볼 문서 |
| --- | --- |
| 화면을 새로 만들기, 조회·저장 메서드 형태 | [screen-skeleton.md](references/screen-skeleton.md) |
| 어떤 동작에 어떤 이벤트·공통 메서드를 쓰는지 | [behaviors.md](references/behaviors.md) |
| 컨트롤을 Designer에 추가(속성 블록), 이벤트 연결 위치, 이름 접두어 | [control-blocks.md](references/control-blocks.md) |
| 메서드·이벤트·문법 | [coding-style.md](references/coding-style.md) |
| 컨트롤·Repository·이름 | [controls.md](references/controls.md) |
| Designer 배치·이관 | [designer.md](references/designer.md) |
| 그리드 열·뷰 속성 | [grid.md](references/grid.md) |
| 조회·저장·삭제 흐름 | [data-flow.md](references/data-flow.md) |
| 여러 UserControl·주기 재조회·그리드 재바인딩 | [screen-behavior.md](references/screen-behavior.md) |
| 출력·미리보기·인쇄 | [reports.md](references/reports.md) |
| C_KONE120 바인딩·XML·코드 콤보 | [kone120.md](references/kone120.md) |

4. 고치기 전에 실제 호출자와 피호출자의 **메서드 전체**, 생성자·초기화, 원본 Designer를 읽는다.

## 항상 지키는 규칙

- 요청한 멤버만 바꾼다. 기존 속성·이벤트·사용자 편집(폭, 순서, Font, Visible)은 보존한다.
- 라벨·한 줄 입력 높이는 같은 화면의 같은 역할 컨트롤과 맞춘다. 폰트·정렬·버튼은 실제 초기화 값을 유지한다.
- 그리드 새로 만들 때는 [grid.md](references/grid.md) 기본값만 쓴다. 셀 TextOptions, DisplayFormat, EditMask, 뷰 전체 Editable/ReadOnly를 임의로 추가하지 않는다.
- **프로젝트에 UserControl(`u_…`)이 있으면 그것을 쓰고, 없을 때만 DevExpress 표준 컨트롤을 쓴다.** WinForms 기본 컨트롤(`TextBox`, `Label`, `Button`, `DataGridView`)은 쓰지 않는다. 용도별 컨트롤은 [control-blocks.md](references/control-blocks.md#컨트롤-선택)에 있다.
- 사용자 컨트롤의 기본값을 덮어쓰지 않는다. 필요한 속성만 바꾼다.
- if·else·반복문은 한 줄이어도 **항상 중괄호**를 쓴다. 기존 화면에 중괄호 없는 한 줄 if가 있어도 새로 쓰는 코드는 중괄호를 쓴다.
- 저장은 `dbClient.ExecSPTrn`으로 부른다. 트랜잭션은 이 메서드가 맡으므로 화면이나 SP에 따로 만들지 않는다.
- **화면 구성은 Designer에, 이벤트 연결은 비하인드 코드에 둔다.** 컨트롤 생성·배치·속성은 `InitializeComponent()`에, 이벤트 구독(`+=`)은 생성자에서 `InitializeComponent()` 다음에 이름 있는 핸들러로 한 번씩 쓴다. Designer에 이벤트 구독을 새로 쓰지 않는다.
- 새 동작은 먼저 [behaviors.md](references/behaviors.md)에서 같은 동작의 이벤트와 공통 메서드를 찾아 쓴다. 새 헬퍼를 만들거나 `MessageBox.Show`, 직접 만든 DB 연결을 쓰지 않는다.
- 값 변경 핸들러(`EditValueChanged`, `CellValueChanged`)와 명령 핸들러는 첫 줄에서 `m_Editmode`를 확인한다.
- LINQ·중간 테이블·빌드는 기본적으로 쓰지 않는다. 없으면 구현이 어렵거나 성능 차이가 극단적일 때만 쓰고 이유를 말한다.
- 화면과 SP가 같이 바뀌면 sql 스킬도 따르고, SP 인자·XML TableName·행 상태·결과표 순서·바인딩 FieldName을 양쪽에서 하나씩 대조한다.

## 작업 파일과 정리

- **소스 프로젝트 폴더에 작업용 파일을 만들지 않는다.** 비교용 사본, 초안, 추출물, 테스트 스크립트, 실행 결과, 로그는 시스템 임시 폴더(`%TEMP%`) 아래 작업별 폴더에 둔다.
- 소스 폴더에는 사용자가 요청한 최종 결과물만 쓴다. 파일 위치를 지정받으면 그 경로에만 쓴다.
- **SP·쿼리 `.sql` 파일은 솔루션 폴더 안에 만들지 않는다.** `.sln`이 있는 폴더의 **상위 폴더**에 `SQL\<YYYYMMDD>\` 폴더를 두고 거기에 쓴다(예: 솔루션이 `…\고객사\C_KONE120\`이면 `…\고객사\SQL\20261120\sp_XX000100_SAVE.sql`). SP는 DB에 적용하고 이 파일은 날짜별 기록으로 남긴다. 솔루션 안에 `SQL` 폴더가 이미 있어도 거기에 쓰지 않고, 사용자에게 알리고 상위로 옮기자고 제안한다. 이 폴더는 형상관리 대상이 아니므로 `.sql` 파일의 커밋을 할 일로 적지 않는다.
- 작업 중 띄운 빌드, 앱 실행, DB 연결, 백그라운드 터미널·프로세스는 끝나면 종료한다. 사용자가 띄운 것이나 다른 작업이 같이 쓰는 서비스는 건드리지 않는다.
- 끝내기 전에 소스 폴더에 내가 만든 임시 파일이 남았는지 확인하고(git 저장소면 `git status`), 남았으면 지운다. 출처를 모르는 파일은 지우지 말고 보고한다.
- 다음 작업에 계속 필요한 임시 파일은 남기되, 경로를 답변에 적는다.

## 끝내기 전에 (자체 점검)

작성이 끝나면 별도 검토 에이전트 없이 직접 아래를 확인하고 결과를 답변에 넣는다.

1. **원본 대조**: 원본 .cs·Designer와 최종본을 비교해 요청하지 않은 속성 추가·변경·삭제가 없는지 본다.
2. **비교 프로그램 대조**: 같은 역할의 비교 화면과 작성 방식이 같은지 본다.
3. **규칙 대조**: 위 규칙과 교정 기록(플러그인·로컬) 항목을 하나씩 대조한다.
4. **계약 대조표**: SP를 부르는 코드를 만들거나 고쳤으면 화면 호출 ↔ SP 사이에서 저장 호출(`ExecSPTrn`/`ExecSP`), SP 인자 이름·순서, `@WORKTYPE` 값 ↔ SP 분기, XML TableName ↔ SP의 XML 경로, 행 상태 ↔ SP의 `GBN` 분기, 결과표 순서 ↔ `ds.Tables[n]`, 그리드 `FieldName`·`BindingField` ↔ 결과 열 이름을 **파일 경로와 줄 번호를 근거로** 대조해 표로 넣는다. 형태는 [verify.md](references/verify.md).
5. **시나리오 표**: 바꾼 조회·저장·화면 상태 전환마다 채운다.

| 구분 | 확인할 사례 | 근거 |
| --- | --- | --- |
| 정상 | 표시·활성·저장되어야 할 행과 상태 | 실행 / 정적 대조(파일:줄) / 미확인 |
| 제외·경계 | 선택 없음, 여러 행 선택, 빈 결과, 삭제 행(Original 키), 편집 보호 상태, 저장 실패 시 미저장 변경 유지, 재조회·리사이즈 후 덮어쓰기 | 실행 / 정적 대조(파일:줄) / 미확인 |

빌드 성공은 표시·바인딩·조회 시점을 증명하지 않는다. 정적 대조에는 근거가 된 파일과 줄을 적는다. 실행하지 못한 동작은 `미확인`으로 적는다.

마지막으로 [작업 파일과 정리](#작업-파일과-정리)대로 임시 파일과 띄운 프로세스를 정리했는지 확인한다.

## 교정을 받으면 (Compound)

사용자가 결과를 교정했거나(틀렸다고 지적, 같은 말을 다시 함, 방식을 바꾸라고 함) 계약 대조·실행에서 나온 어긋남의 원인이 규칙에 없거나 틀렸으면, 고친 뒤 **묻지 않고** 로컬 기록 `~/.claude/ace/lessons/csharp.md`에 항목을 추가하고 답변에 `교정 기록에 추가: <제목>` 한 줄로 알린다. 같은 내용이 이미 있으면 그 항목을 고친다. 이번 작업에만 해당하는 요구와 내 추측은 적지 않는다.

저장소(lessons.md·reference)로 옮기는 승격은 사용자가 "교정 기록 정리해줘 / ACE에 반영해줘"라고 할 때만 한다. 로컬 항목이 10개를 넘으면 정리를 제안만 한다. 형식과 절차는 [compound.md](references/compound.md).
