# Controls: choice, size, naming, Designer blocks

From the user's screens in two reference projects (PROJECT_A, PROJECT_B_1), 2026-11-20. (c) = `check_designer.py`.

## Choosing a control

framework `u_…` control per role (the general rule is csharp [designer.md](../../csharp/references/designer.md#choosing-a-control)):

Label `uxLabel` · one-line text `uxTextEdit` · code combo `uxLookUpEdit` · date `uxDateEdit` · number `uxSpinEdit` · input with find button `uxButtonEdit` · button `uxButtonControl` · check `uxCheckEdit` · radio group `uxRadioButton` · multi-line `uxMemoEdit` · titled box `uxGroupControl` · panel `uxPanel` (scrolling `uxScrollPanel`) · grid `uxGridControl` + `uxGridView` · tabs `uxTabControl` + `XtraTabPage` · picture `uxPictureEdit` · combo in grid `uxGridLookUpEdit`. DevExpress as is: `GridColumn` (`BandedGridColumn` + `GridBand`), `RepositoryItem…` ([grid.md](../../csharp/references/grid.md#repository-editors)), `SplitterControl`, `TreeList`, `ChartControl`.

## Size and placement

Constructor defaults (`base.Size`, `ExampleSystemPlatform/ExampleLib.Control`, same in both projects): `uxLabel` 100×25 (`uxLabel.cs:33`), `uxDateEdit` 100×25 (`uxDateEdit.cs:65`; the block uses 105×25), `uxButtonControl` and `uxCheckEdit` 100×25 (`:20`, `:47`), `uxTextEdit`, `uxLookUpEdit`, `uxSpinEdit`, `uxButtonEdit`, `uxRadioButton`, `uxGridLookUpEdit` 150×25 (`uxTextEdit.cs:54`, `uxLookUpEdit.cs:95`, `uxSpinEdit.cs:64`, `uxButtonEdit.cs:45`, `uxRadioButton.cs:53`, `uxGridLookUpEdit.cs:53`).

- (c) A new control takes the size of the controls next to it: same row / same column of the same kind on that screen (user, 2026-11-24: "옆 컨트롤에 맞춤"; PROJECT_B labels are mostly 111–114 wide, inputs fit the layout). Pass the screen as `--sibling`. Default constructor size only when the screen has no control of that kind nearby.
- (c) **Never shrink a set of labels and inputs to one common width.** Each type keeps its own default.
- (c) `uxLabel`: right-aligned (`Far`), vertically centred, `AutoSizeMode.None` (constructor turns `Default` into Far/Center, `uxLabel.cs:27-29`). Keep explicit alignment of existing labels.
- Label and one-line input height 25, `MaximumSize`/`MinimumSize` heights 25 where the block has them, unless the user asked for another height (checker shows it as `[확인]`, never blocks). Font, skin, height: same kind of control on the same screen.
- (c) No two controls in one parent overlap; each input sits right of its label.

## Names

General naming (bound field, role, no default names): csharp [designer.md](../../csharp/references/designer.md#names).

`lbl` `uxLabel` · `txt` `uxTextEdit` · `cbo` `uxLookUpEdit` · `ymd` `uxDateEdit` (`ymdFRDT`/`ymdTODT`) · `spin` `uxSpinEdit` · `btn` `uxButtonEdit`/`uxButtonControl` · `chk` · `rad` · `memo` · `grp` · `pn` · `tab` · `splitter`/`split` · `treeList`. Grid, view, column and repository names: [grid.md](../../csharp/references/grid.md#names).

## Designer blocks

Change only `<…>`; add nothing that overrides constructor defaults (height, font, alignment, Enter-move). (c) No event `+=` in `InitializeComponent` ([coding-style.md](../../csharp/references/coding-style.md#event-subscriptions)).

### uxLabel

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
this.lbl<FIELD>.Size = new System.Drawing.Size(100, 25);
this.lbl<FIELD>.TabIndex = <N>;
this.lbl<FIELD>.Text = "<캡션>";
this.lbl<FIELD>.UseMnemonic = false;
```

### uxTextEdit (base of the input blocks)

```csharp
this.txt<FIELD>._isKey = false;
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
this.txt<FIELD>.Size = new System.Drawing.Size(150, 25);
this.txt<FIELD>.TabIndex = <N>;
```

`BindingField` = result column for `RowToPanel`/`PanelToTable`. `_isKey = true` only on key controls (locked in edit mode).

Other inputs = the text block plus (combo button = `Properties.Buttons.AddRange(…EditorButton(…ButtonPredefines.Combo)})`):

- `uxLookUpEdit`: (c) combo button; `isUseCode = false`, `MainCode = "<code group>"`, `UseOrgdiv = false`; `Properties.DisplayMember = "NAME"`, `ValueMember = "CODE"` (always), `NullText = ""`, `PopupWidth = 227`, `TextEditStyle = Standard`. `MainCode` fills the list (`UseOrgdiv = true` per site); other lists bind in code with `code.Bind`/`BindByOrg`.
- `uxDateEdit`: no `BindingField`; `EditValue = null`; `Margin(2, 3, 2, 3)`, `MaximumSize(57343, 25)`; `Properties.Appearance.Options.UseTextOptions = true` + `HAlignment = Center`; (c) combo button on `Properties` **and** `Properties.CalendarTimeProperties`; `Properties.Mask.MaskType = DateTimeAdvancingCaret`; `Size(105, 25)`. First value in Load: `SetToDay(n)`.
- `uxSpinEdit`: `_isAllowBlank = true`, `_isPecentType = false`, `isEnterBlock = true`; `Properties.AllowMouseWheel = false`; combo button; `DisplayFormat.FormatType`/`EditFormat.FormatType = Numeric`. `FormatString` (`N0` …) only on request.
- `uxButtonEdit`: (c) its button line.
- `uxCheckEdit`: `_isAllowBlank = true`, `Properties.Caption`, `NullStyle = Unchecked`, `ValueChecked = "Y"`, `ValueUnchecked = "N"` (strings, never `true`/`1`); no Location/Margin/Max/Min/AutoHeight; height 20.

## Containers

Inputs sit in `uxPanel` (`pn<Role>`, `BorderStyle = NoBorder`), titled groups in `uxGroupControl` (`grp<Role>`, `_isGrpEdit = false`), areas split by `SplitterControl`. Lock per container with `ui.ProtectControls(pn<Role>, true)`; per-control `ReadOnly`/`Enabled` only for one button or input toggled by state. Overriding defaults of existing controls: [designer.md](../../csharp/references/designer.md#preserving-control-defaults).
