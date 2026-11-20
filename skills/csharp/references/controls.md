# Controls: choice, size, naming, Designer blocks

From the user's screens (SVN author JKH), C_KONE120 and C_KONE110_1, 2026-11-20. (c) = `check_designer.py`.

## Choosing a control

**Use the project's UserControl (`u_…`) when one exists; otherwise the DevExpress control. Never plain WinForms (`TextBox`, `Label`, `Button`, `DataGridView`).** In another project first list which `u_…` exist and say which ones you replaced.

Label `u_Label` · one-line text `u_TextEdit` · code combo `u_LookUpEdit` · date `u_DateEdit` · number `u_SpinEdit` · input with find button `u_ButtonEdit` · button `u_ButtonControl` · check `u_CheckEdit` · radio group `u_RadioButton` · multi-line `u_MemoEdit` · titled box `u_GroupControl` · panel `u_Panel` (scrolling `u_ScrollPanel`) · grid `u_GridControl` + `u_GridView` · tabs `u_TabControl` + `XtraTabPage` · picture `u_PictureEdit` · combo in grid `u_GridLookUpEdit`. DevExpress as is: `GridColumn` (`BandedGridColumn` + `GridBand`), `RepositoryItem…` ([grid.md](grid.md#repository-editors)), `SplitterControl`, `TreeList`, `ChartControl`.

## Size and placement

Constructor defaults (`base.Size`, `KonesystemPlatform/KoneLib.Control`, same in both projects): `u_Label` 100×25 (`u_Label.cs:33`), `u_DateEdit` 100×25 (`u_DateEdit.cs:65`; the block uses 105×25), `u_ButtonControl` and `u_CheckEdit` 100×25 (`:20`, `:47`), `u_TextEdit`, `u_LookUpEdit`, `u_SpinEdit`, `u_ButtonEdit`, `u_RadioButton`, `u_GridLookUpEdit` 150×25 (`u_TextEdit.cs:54`, `u_LookUpEdit.cs:95`, `u_SpinEdit.cs:64`, `u_ButtonEdit.cs:45`, `u_RadioButton.cs:53`, `u_GridLookUpEdit.cs:53`).

- (c) A new control keeps its default size. Another size only when the screen the user named (or the same-role sibling) uses it for that role; pass that file as `--sibling`. Widen only for long content.
- (c) **Never shrink a set of labels and inputs to one common width.** Each type keeps its own default.
- (c) `u_Label`: right-aligned (`Far`), vertically centred, `AutoSizeMode.None` (constructor turns `Default` into Far/Center, `u_Label.cs:27-29`). Keep explicit alignment of existing labels.
- (c) Label and one-line input height 25, `MaximumSize`/`MinimumSize` heights 25 where the block has them. Font, skin, height: same kind of control on the same screen.
- (c) No two controls in one parent overlap; each input sits right of its label.

## Names

`lbl` `u_Label` · `txt` `u_TextEdit` · `cbo` `u_LookUpEdit` · `ymd` `u_DateEdit` (`ymdFRDT`/`ymdTODT`) · `spin` `u_SpinEdit` · `btn` `u_ButtonEdit`/`u_ButtonControl` · `chk` · `rad` · `memo` · `grp` · `pn` · `tab` · `splitter`/`split` · `treeList`. Grid, view, column and repository names: [grid.md](grid.md#names). Inputs by bound field (`txtITEMNM`), containers by screen role (`pnMaster`). (c) No Designer default names (`u_Label17`, `gridColumn3`, `repositoryItemSpinEdit1`) on new controls. Rename only when asked ([designer.md](designer.md)).

## Designer blocks

Change only `<…>`; add nothing that overrides constructor defaults (height, font, alignment, Enter-move). (c) No event `+=` in `InitializeComponent` ([screen-skeleton.md](screen-skeleton.md#constructor)).

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
this.lbl<FIELD>.Size = new System.Drawing.Size(100, 25);
this.lbl<FIELD>.TabIndex = <N>;
this.lbl<FIELD>.Text = "<캡션>";
this.lbl<FIELD>.UseMnemonic = false;
```

### u_TextEdit (base of the input blocks)

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
this.txt<FIELD>.Size = new System.Drawing.Size(150, 25);
this.txt<FIELD>.TabIndex = <N>;
```

`BindingField` = result column for `DataRowToPanel`/`MasterToDataTable`. `_isPKValue = true` only on key controls (locked in edit mode).

Other inputs = the text block plus (combo button = `Properties.Buttons.AddRange(…EditorButton(…ButtonPredefines.Combo)})`):

- `u_LookUpEdit`: (c) combo button; `isUseCode = false`, `MainCode = "<code group>"`, `UseOrgdiv = false`; `Properties.DisplayMember = "NAME"`, `ValueMember = "CODE"` (always), `NullText = ""`, `PopupWidth = 227`, `TextEditStyle = Standard`. `MainCode` fills the list (`UseOrgdiv = true` per site); other lists bind in code with `syCode.BindingCode`/`BindingorgdivCode`.
- `u_DateEdit`: no `BindingField`; `EditValue = null`; `Margin(2, 3, 2, 3)`, `MaximumSize(57343, 25)`; `Properties.Appearance.Options.UseTextOptions = true` + `HAlignment = Center`; (c) combo button on `Properties` **and** `Properties.CalendarTimeProperties`; `Properties.Mask.MaskType = DateTimeAdvancingCaret`; `Size(105, 25)`. First value in Load: `SetToDay(n)`.
- `u_SpinEdit`: `_isAllowBlank = true`, `_isPecentType = false`, `isEnterBlock = true`; `Properties.AllowMouseWheel = false`; combo button; `DisplayFormat.FormatType`/`EditFormat.FormatType = Numeric`. `FormatString` (`N0` …) only on request.
- `u_ButtonEdit`: (c) its button line.
- `u_CheckEdit`: `_isAllowBlank = true`, `Properties.Caption`, `NullStyle = Unchecked`, `ValueChecked = "Y"`, `ValueUnchecked = "N"` (strings, never `true`/`1`); no Location/Margin/Max/Min/AutoHeight; height 20.

## Containers

Inputs sit in `u_Panel` (`pn<Role>`, `BorderStyle = NoBorder`), titled groups in `u_GroupControl` (`grp<Role>`, `_isGrpEdit = false`), areas split by `SplitterControl`. Lock per container with `devFnc.Usr_ControlsProtect(pn<Role>, true)`; per-control `ReadOnly`/`Enabled` only for one button or input toggled by state. Overriding defaults of existing controls: [designer.md](designer.md#preserving-control-defaults).
