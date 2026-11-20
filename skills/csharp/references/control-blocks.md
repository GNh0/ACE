# 컨트롤 속성 블록과 이벤트 연결

근호·KH 작성 SP를 부르는 화면 100개(C_KONE110_1, FrmDevBase 88개 + FrmPopBase 12개)의 Designer와 비하인드 코드를 집계한 결과다(2026-11-20). 컨트롤을 새로 추가할 때 아래 블록을 그대로 쓰고, 여기 없는 속성을 임의로 더하지 않는다.

## 원칙

- **화면 구성은 Designer에, 이벤트 연결은 비하인드 코드에 둔다.** 컨트롤 생성·배치·속성은 `*.Designer.cs`의 `InitializeComponent()`에 쓴다. 이벤트 구독(`+=`)은 `*.cs` 생성자에서 `InitializeComponent()` 다음에 이름 있는 핸들러로 한 번씩 쓴다. 집계에서도 구독의 약 90%가 비하인드 코드에 있었다.
- Designer에 이벤트 구독을 새로 쓰지 않는다. 기존 화면의 Designer에 이미 있는 구독은 요청 없이 옮기지 않는다.
- 글꼴·스킨·높이 값은 **같은 화면의 같은 종류 컨트롤**에서 가져온다. 아래 값은 C_KONE110_1 기준이며 다른 프로젝트는 다를 수 있다.

## 컨트롤 선택

**프로젝트에 UserControl(`u_…`)이 있으면 그것을 쓰고, 없을 때만 DevExpress가 지원하는 표준 컨트롤을 쓴다.** `System.Windows.Forms`의 기본 컨트롤(`TextBox`, `Label`, `Button`, `DataGridView`)은 쓰지 않는다.

| 용도 | 쓰는 컨트롤 | 기반 DevExpress 컨트롤 | 100개 화면의 개수 |
| --- | --- | --- | --- |
| 라벨 | `u_Label` | `LabelControl` | 1,020 |
| 한 줄 입력 | `u_TextEdit` | `TextEdit` | 471 (표준 `TextEdit` 3) |
| 코드 선택 콤보 | `u_LookUpEdit` | `LookUpEdit` | 347 |
| 날짜 | `u_DateEdit` | `DateEdit` | 241 |
| 숫자 | `u_SpinEdit` | `SpinEdit` | 199 |
| 찾기 버튼이 달린 입력 | `u_ButtonEdit` | `ButtonEdit` | 59 |
| 버튼 | `u_ButtonControl` | `SimpleButton` | 138 (표준 `SimpleButton` 8) |
| 체크 | `u_CheckEdit` | `CheckEdit` | 85 |
| 라디오 묶음 | `u_RadioButton` | `RadioGroup` | 77 |
| 여러 줄 입력 | `u_MemoEdit` | `MemoEdit` | 50 |
| 제목 있는 묶음 | `u_GroupControl` | `GroupControl` | 333 (표준 `GroupControl` 14) |
| 패널 | `u_Panel`, 스크롤이 필요하면 `u_ScrollPanel` | `PanelControl`, `XtraScrollableControl` | 285, 9 |
| 그리드 | `u_GridControl` + `u_GridView` | `GridControl`, `GridView` | 262, 273 (표준 `GridView` 25) |
| 탭 | `u_TabControl` + `XtraTabPage` | `XtraTabControl` | 52 |
| 그림 | `u_PictureEdit` | `PictureEdit` | |
| 그리드 안 콤보 | `u_GridLookUpEdit` | `GridLookUpEdit` | |

UserControl이 없어서 표준 DevExpress 컨트롤을 그대로 쓰는 것:

| 용도 | 쓰는 컨트롤 |
| --- | --- |
| 그리드 열 | `GridColumn`, 밴드형은 `BandedGridColumn` + `GridBand` |
| 그리드 셀 편집기 | `RepositoryItemLookUpEdit`(693), `RepositoryItemSpinEdit`(227), `RepositoryItemButtonEdit`(102), `RepositoryItemCheckEdit`(74), `RepositoryItemDateEdit`(25), `RepositoryItemMemoEdit`(10) |
| 영역 크기 조절 | `SplitterControl`(118), `SplitContainerControl`(6) |
| 트리 | `TreeList` + `TreeListColumn` |
| 차트 | `ChartControl` |

- 그리드 셀의 콤보는 `u_rpsLookUpEdit`(44)보다 표준 `RepositoryItemLookUpEdit`(693)를 훨씬 많이 쓴다. 같은 화면의 기존 Repository와 같은 종류를 쓴다.
- UserControl은 생성자와 초기화에서 기본값(높이, 글꼴, 정렬, Enter 이동 등)을 이미 잡고 있다. 아래 속성 블록은 Designer가 그 기본값을 직렬화한 결과다. 기본값을 덮어쓰는 속성을 더하지 않는다.
- 다른 프로젝트에서는 그 프로젝트에 어떤 `u_…` 컨트롤이 있는지 먼저 확인한다. 없는 컨트롤은 표준 DevExpress 컨트롤로 대신하고, 그 사실을 답변에 적는다.

## 이름 접두어

| 컨트롤 | 접두어 | 예 |
| --- | --- | --- |
| `u_Label` | `lbl` | `lblITEMCD` |
| `u_TextEdit` | `txt` | `txtITEMNM` |
| `u_LookUpEdit` | `cbo` | `cboPRODMAN` |
| `u_DateEdit` | `ymd` | `ymdFRDT`, `ymdTODT` |
| `u_SpinEdit` | `spin` | `spinQTY` |
| `u_ButtonEdit`, `u_ButtonControl` | `btn` | `btnCUSTCD`, `btnADD` |
| `u_CheckEdit` | `chk` | `chkUSEYN` |
| `u_RadioButton` | `rad` | `radALL` |
| `u_MemoEdit` | `memo` | `memoREMARK` |
| `u_GroupControl` | `grp` | `grpMaster` |
| `u_Panel` | `pn` | `pnMaster` |
| `u_GridControl` / `u_GridView` | `grd` / `gvw` | `grdList` / `gvwList` |
| `GridColumn` | `col<그리드역할>_<필드>` | `colList_ITEMCD` |
| `RepositoryItemLookUpEdit` | `rpscbo` | `rpscboPERSON` |
| `RepositoryItemButtonEdit` | `rpsbtn` | `rpsbtnITEMCD` |
| `RepositoryItemCheckEdit` | `rpschk` | `rpschkCHK` |
| `RepositoryItemSpinEdit` | `rpsSpin` | `rpsSpinQTY` |

Designer가 붙인 기본 이름(`u_Label17`, `repositoryItemSpinEdit1`, `gridColumn3`)은 새로 만드는 컨트롤에 쓰지 않는다.

## 이벤트 연결

폼 이벤트는 생성자에서 이 순서로 구독한다. 화면에 필요한 것만 쓴다.

```csharp
public XX000100()
{
    InitializeComponent();
    this.Load += XX000100_Load;
    this.Shown += XX000100_Shown;
    this.SearchCommand += XX000100_SearchCommand;
    this.NewCommand += XX000100_NewCommand;
    this.EditCommand += XX000100_EditCommand;
    this.SaveCommand += XX000100_SaveCommand;
    this.ClearCommand += XX000100_ClearCommand;
    this.DeleteCommand += XX000100_DeleteCommand;
    this.PrintCommand += XX000100_PrintCommand;

    gvwList.FocusedRowChanged += GvwList_FocusedRowChanged;
    gvwList.CellValueChanged += GvwList_CellValueChanged;
    btnADD.Click += BtnADD_Click;
    rpsbtnITEMCD.ButtonClick += RpsbtnITEMCD_ButtonClick;
}
```

- 핸들러 이름은 `<컨트롤 이름 첫 글자 대문자>_<이벤트>`다(`gvwList` → `GvwList_FocusedRowChanged`). 폼 이벤트는 `<화면ID>_<이벤트>`다.
- 람다나 익명 메서드로 구독하지 않는다. 이름 있는 메서드를 쓴다.
- 같은 이벤트를 두 번 구독하지 않는다. Designer와 생성자 양쪽에 있는지 확인한다.

컨트롤별로 실제 쓰는 이벤트(괄호는 100개 화면의 구독 횟수):

| 컨트롤 | 이벤트 | 용도 |
| --- | --- | --- |
| `u_GridView` | `FocusedRowChanged` (68) | 선택 행의 상세 조회 |
| | `CellValueChanged` (26) | 셀 값이 바뀔 때 다른 셀 계산 |
| | `ShowingEditor` (17) | 조건에 따라 셀 편집 막기(`e.Cancel = true`) |
| | `DoubleClick` (11) | 행 더블클릭으로 선택·이동 |
| `u_ButtonControl` | `Click` (105) | 버튼 동작 |
| `RepositoryItemButtonEdit` | `ButtonClick` (51) | 그리드 셀의 찾기 팝업 |
| `u_ButtonEdit` | `ButtonClick` (39) | 입력란의 찾기 팝업 |
| `u_SpinEdit` | `EditValueChanged` (32) | 합계·금액 다시 계산 |
| `u_LookUpEdit` | `EditValueChanged` (24) | 선택에 따라 다른 컨트롤 갱신 |
| `u_TabControl` | `SelectedPageChanged` (25) | 탭 전환 시 조회·보호 |
| `u_DateEdit` | `EditValueChanged` (15) | 일자 변경 시 재계산 |
| `u_GroupControl` | `CustomButtonClick` (17) | 그룹 머리글의 추가·삭제 버튼 |

값이 바뀔 때의 처리는 `EditValueChanged`를 쓴다. `TextChanged`, `Leave`, `Validating`으로 같은 일을 하지 않는다.

## Designer 속성 블록

`<…>`만 바꾸고 나머지는 그대로 쓴다. `Location`, `Size`의 폭, `TabIndex`는 배치에 맞춘다. 한 줄 입력 컨트롤과 라벨의 높이는 **25**이고 `MaximumSize`·`MinimumSize`의 높이도 25다.

### u_Label

```csharp
this.lbl<FIELD>.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
this.lbl<FIELD>.Appearance.Options.UseFont = true;
this.lbl<FIELD>.Appearance.Options.UseTextOptions = true;
this.lbl<FIELD>.Appearance.TextOptions.HAlignment = DevExpress.Utils.HorzAlignment.Far;
this.lbl<FIELD>.Appearance.TextOptions.VAlignment = DevExpress.Utils.VertAlignment.Center;
this.lbl<FIELD>.AutoSizeMode = DevExpress.XtraEditors.LabelAutoSizeMode.None;
this.lbl<FIELD>.Location = new System.Drawing.Point(<X>, <Y>);
this.lbl<FIELD>.LookAndFeel.SkinName = "The Bezier";
this.lbl<FIELD>.LookAndFeel.UseDefaultLookAndFeel = false;
this.lbl<FIELD>.Margin = new System.Windows.Forms.Padding(1, 2, 1, 2);
this.lbl<FIELD>.MaximumSize = new System.Drawing.Size(74897, 25);
this.lbl<FIELD>.MinimumSize = new System.Drawing.Size(0, 25);
this.lbl<FIELD>.Name = "lbl<FIELD>";
this.lbl<FIELD>.Size = new System.Drawing.Size(<W>, 25);
this.lbl<FIELD>.TabIndex = <N>;
this.lbl<FIELD>.Text = "<캡션>";
this.lbl<FIELD>.UseMnemonic = false;
```

라벨은 오른쪽 정렬(`Far`), 세로 가운데, `AutoSizeMode.None`이다.

### u_TextEdit

```csharp
this.txt<FIELD>._isPKValue = false;
this.txt<FIELD>.BindingField = "<FIELD>";
this.txt<FIELD>.EnterMoveNextControl = true;
this.txt<FIELD>.Location = new System.Drawing.Point(<X>, <Y>);
this.txt<FIELD>.Margin = new System.Windows.Forms.Padding(1, 2, 1, 2);
this.txt<FIELD>.MaximumSize = new System.Drawing.Size(74897, 25);
this.txt<FIELD>.MinimumSize = new System.Drawing.Size(0, 25);
this.txt<FIELD>.Name = "txt<FIELD>";
this.txt<FIELD>.Properties.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
this.txt<FIELD>.Properties.Appearance.Options.UseFont = true;
this.txt<FIELD>.Properties.AutoHeight = false;
this.txt<FIELD>.Properties.LookAndFeel.SkinName = "The Bezier";
this.txt<FIELD>.Properties.LookAndFeel.UseDefaultLookAndFeel = false;
this.txt<FIELD>.Size = new System.Drawing.Size(<W>, 25);
this.txt<FIELD>.TabIndex = <N>;
```

- `BindingField`는 조회 결과의 열 이름이다. `DataRowToPanel`·`MasterToDataTable`이 이 값으로 연결한다.
- `_isPKValue = true`는 키 값 컨트롤에만 준다(수정 모드에서 잠긴다).

### u_LookUpEdit

```csharp
this.cbo<FIELD>._isPKValue = false;
this.cbo<FIELD>.BindingField = "<FIELD>";
this.cbo<FIELD>.EnterMoveNextControl = true;
this.cbo<FIELD>.isUseCode = false;
this.cbo<FIELD>.Location = new System.Drawing.Point(<X>, <Y>);
this.cbo<FIELD>.MainCode = "<공통코드 구분>";
this.cbo<FIELD>.Margin = new System.Windows.Forms.Padding(1, 2, 1, 2);
this.cbo<FIELD>.MaximumSize = new System.Drawing.Size(74897, 25);
this.cbo<FIELD>.MinimumSize = new System.Drawing.Size(0, 25);
this.cbo<FIELD>.Name = "cbo<FIELD>";
this.cbo<FIELD>.Properties.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
this.cbo<FIELD>.Properties.Appearance.Options.UseFont = true;
this.cbo<FIELD>.Properties.AutoHeight = false;
this.cbo<FIELD>.Properties.Buttons.AddRange(new DevExpress.XtraEditors.Controls.EditorButton[] {
new DevExpress.XtraEditors.Controls.EditorButton(DevExpress.XtraEditors.Controls.ButtonPredefines.Combo)});
this.cbo<FIELD>.Properties.DisplayMember = "NAME";
this.cbo<FIELD>.Properties.LookAndFeel.SkinName = "The Bezier";
this.cbo<FIELD>.Properties.LookAndFeel.UseDefaultLookAndFeel = false;
this.cbo<FIELD>.Properties.NullText = "";
this.cbo<FIELD>.Properties.PopupWidth = 227;
this.cbo<FIELD>.Properties.TextEditStyle = DevExpress.XtraEditors.Controls.TextEditStyles.Standard;
this.cbo<FIELD>.Properties.ValueMember = "CODE";
this.cbo<FIELD>.Size = new System.Drawing.Size(<W>, 25);
this.cbo<FIELD>.TabIndex = <N>;
this.cbo<FIELD>.UseOrgdiv = false;
```

- 값·표시 멤버는 항상 `CODE` / `NAME`이다.
- `MainCode`에 공통코드 구분을 주면 컨트롤이 목록을 채운다. 사업장별 코드는 `UseOrgdiv = true`다. 코드로 채울 수 없는 목록은 비하인드 코드에서 `syCode.BindingCode` / `BindingorgdivCode`로 바인딩한다.

### u_DateEdit

```csharp
this.ymd<FIELD>._isPKValue = false;
this.ymd<FIELD>.EditValue = null;
this.ymd<FIELD>.EnterMoveNextControl = true;
this.ymd<FIELD>.Location = new System.Drawing.Point(<X>, <Y>);
this.ymd<FIELD>.Margin = new System.Windows.Forms.Padding(2, 3, 2, 3);
this.ymd<FIELD>.MaximumSize = new System.Drawing.Size(57343, 25);
this.ymd<FIELD>.MinimumSize = new System.Drawing.Size(0, 25);
this.ymd<FIELD>.Name = "ymd<FIELD>";
this.ymd<FIELD>.Properties.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
this.ymd<FIELD>.Properties.Appearance.Options.UseFont = true;
this.ymd<FIELD>.Properties.Appearance.Options.UseTextOptions = true;
this.ymd<FIELD>.Properties.Appearance.TextOptions.HAlignment = DevExpress.Utils.HorzAlignment.Center;
this.ymd<FIELD>.Properties.AutoHeight = false;
this.ymd<FIELD>.Properties.Buttons.AddRange(new DevExpress.XtraEditors.Controls.EditorButton[] {
new DevExpress.XtraEditors.Controls.EditorButton(DevExpress.XtraEditors.Controls.ButtonPredefines.Combo)});
this.ymd<FIELD>.Properties.CalendarTimeProperties.Buttons.AddRange(new DevExpress.XtraEditors.Controls.EditorButton[] {
new DevExpress.XtraEditors.Controls.EditorButton(DevExpress.XtraEditors.Controls.ButtonPredefines.Combo)});
this.ymd<FIELD>.Properties.LookAndFeel.SkinName = "The Bezier";
this.ymd<FIELD>.Properties.LookAndFeel.UseDefaultLookAndFeel = false;
this.ymd<FIELD>.Properties.Mask.MaskType = DevExpress.XtraEditors.Mask.MaskType.DateTimeAdvancingCaret;
this.ymd<FIELD>.Size = new System.Drawing.Size(105, 25);
this.ymd<FIELD>.TabIndex = <N>;
```

날짜는 가운데 정렬이고 두 `Buttons.AddRange`를 모두 둔다. 초기값은 비하인드 코드의 Load에서 `SetToDay(n)`으로 준다.

### u_SpinEdit

```csharp
this.spin<FIELD>._isAllowBlank = true;
this.spin<FIELD>._isPecentType = false;
this.spin<FIELD>._isPKValue = false;
this.spin<FIELD>.BindingField = "<FIELD>";
this.spin<FIELD>.EnterMoveNextControl = true;
this.spin<FIELD>.isEnterBlock = true;
this.spin<FIELD>.Location = new System.Drawing.Point(<X>, <Y>);
this.spin<FIELD>.Margin = new System.Windows.Forms.Padding(1, 2, 1, 2);
this.spin<FIELD>.MaximumSize = new System.Drawing.Size(74897, 25);
this.spin<FIELD>.MinimumSize = new System.Drawing.Size(0, 25);
this.spin<FIELD>.Name = "spin<FIELD>";
this.spin<FIELD>.Properties.AllowMouseWheel = false;
this.spin<FIELD>.Properties.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
this.spin<FIELD>.Properties.Appearance.Options.UseFont = true;
this.spin<FIELD>.Properties.AutoHeight = false;
this.spin<FIELD>.Properties.Buttons.AddRange(new DevExpress.XtraEditors.Controls.EditorButton[] {
new DevExpress.XtraEditors.Controls.EditorButton(DevExpress.XtraEditors.Controls.ButtonPredefines.Combo)});
this.spin<FIELD>.Properties.DisplayFormat.FormatType = DevExpress.Utils.FormatType.Numeric;
this.spin<FIELD>.Properties.EditFormat.FormatType = DevExpress.Utils.FormatType.Numeric;
this.spin<FIELD>.Properties.LookAndFeel.SkinName = "The Bezier";
this.spin<FIELD>.Properties.LookAndFeel.UseDefaultLookAndFeel = false;
this.spin<FIELD>.Size = new System.Drawing.Size(<W>, 25);
this.spin<FIELD>.TabIndex = <N>;
```

`FormatType = Numeric`까지가 기본이다. `FormatString`(`N0` 등)은 약 30%의 컨트롤에만 있었다. 사용자가 표시 형식을 요청했을 때만 넣는다.

### u_CheckEdit

```csharp
this.chk<FIELD>._isAllowBlank = true;
this.chk<FIELD>._isPKValue = false;
this.chk<FIELD>.BindingField = "<FIELD>";
this.chk<FIELD>.Name = "chk<FIELD>";
this.chk<FIELD>.Properties.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
this.chk<FIELD>.Properties.Appearance.Options.UseFont = true;
this.chk<FIELD>.Properties.Caption = "<캡션>";
this.chk<FIELD>.Properties.LookAndFeel.SkinName = "The Bezier";
this.chk<FIELD>.Properties.LookAndFeel.UseDefaultLookAndFeel = false;
this.chk<FIELD>.Properties.NullStyle = DevExpress.XtraEditors.Controls.StyleIndeterminate.Unchecked;
this.chk<FIELD>.Properties.ValueChecked = "Y";
this.chk<FIELD>.Properties.ValueUnchecked = "N";
this.chk<FIELD>.Size = new System.Drawing.Size(<W>, 20);
```

체크 값은 항상 문자열 `"Y"` / `"N"`이다. `true`/`false`나 `1`/`0`을 쓰지 않는다. 높이는 20이다.

### 그리드 (u_GridControl, u_GridView)

```csharp
this.grd<Role>.Dock = System.Windows.Forms.DockStyle.Fill;
this.grd<Role>.EmbeddedNavigator.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
this.grd<Role>.EmbeddedNavigator.Appearance.Options.UseFont = true;
this.grd<Role>.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
this.grd<Role>.isShowRowNumber = true;
this.grd<Role>.MainView = this.gvw<Role>;
this.grd<Role>.Name = "grd<Role>";
this.grd<Role>.RepositoryItems.AddRange(new DevExpress.XtraEditors.Repository.RepositoryItem[] {
this.rpscbo<FIELD>,
this.rpsSpin<FIELD>});
this.grd<Role>.ViewCollection.AddRange(new DevExpress.XtraGrid.Views.Base.BaseView[] {
this.gvw<Role>});
this.grd<Role>.XmlTabelName = null;

this.gvw<Role>.Appearance.HeaderPanel.Options.UseTextOptions = true;
this.gvw<Role>.Appearance.HeaderPanel.TextOptions.HAlignment = DevExpress.Utils.HorzAlignment.Center;
this.gvw<Role>.Columns.AddRange(new DevExpress.XtraGrid.Columns.GridColumn[] {
this.col<Role>_<FIELD1>,
this.col<Role>_<FIELD2>});
this.gvw<Role>.GridControl = this.grd<Role>;
this.gvw<Role>.HorzScrollStep = 3;
this.gvw<Role>.Name = "gvw<Role>";
this.gvw<Role>.OptionsView.ColumnAutoWidth = false;
this.gvw<Role>.OptionsView.EnableAppearanceEvenRow = true;
this.gvw<Role>.OptionsView.ShowAutoFilterRow = true;
this.gvw<Role>.OptionsView.ShowFooter = true;
this.gvw<Role>.OptionsView.ShowGroupPanel = false;
```

- `ShowGroupPanel = false`는 모든 뷰(100%)에 있다. 나머지 네 `OptionsView` 값은 뷰의 64~86%에 있었고 값은 항상 같았다. [grid.md](grid.md)의 기본값과 같다.
- 체크박스로 여러 행을 고르는 목록은 `OptionsSelection.MultiSelect = true`와 `MultiSelectMode = CheckBoxRowSelect`를 더한다(뷰의 30%).
- Repository는 선언·생성·`RepositoryItems.AddRange` 등록·열의 `ColumnEdit` 연결 네 곳이 모두 있어야 한다.

### GridColumn

```csharp
this.col<Role>_<FIELD>.AppearanceCell.Options.UseFont = true;
this.col<Role>_<FIELD>.AppearanceHeader.Options.UseFont = true;
this.col<Role>_<FIELD>.AppearanceHeader.Options.UseTextOptions = true;
this.col<Role>_<FIELD>.AppearanceHeader.TextOptions.HAlignment = DevExpress.Utils.HorzAlignment.Center;
this.col<Role>_<FIELD>.AppearanceHeader.TextOptions.VAlignment = DevExpress.Utils.VertAlignment.Center;
this.col<Role>_<FIELD>.Caption = "<캡션>";
this.col<Role>_<FIELD>.FieldName = "<FIELD>";
this.col<Role>_<FIELD>.Name = "col<Role>_<FIELD>";
this.col<Role>_<FIELD>.OptionsColumn.AllowEdit = false;
this.col<Role>_<FIELD>.OptionsColumn.ReadOnly = true;
this.col<Role>_<FIELD>.Visible = true;
this.col<Role>_<FIELD>.VisibleIndex = <N>;
```

- 열 글꼴(`Font` 줄 없음, 그리드에서 물려받음)과 머리글·셀 정렬 기본값은 [grid.md](grid.md#appearance)를 따른다. 셀 정렬(`AppearanceCell.TextOptions`)은 집계에서 열의 27%에만 있었다.
- 조회만 하는 열은 `AllowEdit = false`와 `ReadOnly = true`를 함께 쓴다(열의 72%). 편집하는 열은 두 줄을 모두 뺀다.
- 편집기가 필요한 열은 `this.col<Role>_<FIELD>.ColumnEdit = this.rps…;`를 더한다.

### Repository

```csharp
this.rpscbo<FIELD>.AutoHeight = false;
this.rpscbo<FIELD>.Buttons.AddRange(new DevExpress.XtraEditors.Controls.EditorButton[] {
new DevExpress.XtraEditors.Controls.EditorButton(DevExpress.XtraEditors.Controls.ButtonPredefines.Combo)});
this.rpscbo<FIELD>.Name = "rpscbo<FIELD>";
this.rpscbo<FIELD>.NullText = "";

this.rpsSpin<FIELD>.AutoHeight = false;
this.rpsSpin<FIELD>.Buttons.AddRange(new DevExpress.XtraEditors.Controls.EditorButton[] {
new DevExpress.XtraEditors.Controls.EditorButton(DevExpress.XtraEditors.Controls.ButtonPredefines.Combo)});
this.rpsSpin<FIELD>.Name = "rpsSpin<FIELD>";

this.rpschk<FIELD>.AutoHeight = false;
this.rpschk<FIELD>.Name = "rpschk<FIELD>";
this.rpschk<FIELD>.NullStyle = DevExpress.XtraEditors.Controls.StyleIndeterminate.Unchecked;
this.rpschk<FIELD>.ValueChecked = "Y";
this.rpschk<FIELD>.ValueUnchecked = "N";
```

- 모든 Repository에 `AutoHeight = false`가 있다.
- Lookup Repository의 목록은 비하인드 코드의 Load에서 `syCode.BindingCode("코드구분", rpscbo<FIELD>)`로 채운다.
- Spin Repository에는 `EditMask`·`DisplayFormat`을 기본으로 넣지 않는다.

## 컨테이너

- 입력 영역은 `u_Panel`(`pn<Role>`, `BorderStyle = NoBorder`) 안에 라벨과 입력 컨트롤을 놓는다. 묶음에 제목이 필요하면 `u_GroupControl`(`grp<Role>`, `_isGrpEdit = false`)을 쓴다.
- 영역 사이 크기 조절은 `SplitterControl`을 쓴다.
- 편집 잠금은 컨테이너 단위로 `devFnc.Usr_ControlsProtect(pn<Role>, true)`를 부른다. 컨트롤마다 `ReadOnly`를 직접 바꾸는 것은 그 화면만의 예외일 때만 쓴다.
