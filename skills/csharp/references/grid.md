# Grids

New grids: the `generateDevExpressXml` output of the user's `DataWindowToXml.html` (2026-09-08) plus the footer and repository habits below; no options from other screens or DevExpress samples. Existing screens: keep user edits, change only what is required. Not for reports. (c) = `check_designer.py`.

## Names

User screens (C_KONE120 92 grids, C_KONE110_1 224):

- (c) `grd<X>`/`gvw<X>` share the suffix (100% in C_KONE120); columns are `col<X>_<FIELD>` (1,544 of 1,737). Membership comes from `Columns.AddRange`, not the prefix.
- `<X>`: the list is **`List`**, its detail **`Detail`** (12 of 37 C_KONE120 screens use only these). Table-based screens use the table (`grdMA110T`/`colMA110T_PURNUM`; SA100500, MA200100, PR200600: 30 grids). Other grids take the reference screen's role word (`grdBad`, `grdLOT`, `grdItem`).
- (c) A one-grid screen named otherwise (`grdMaterial`) fails; an unknown role word in a multi-grid screen is `[확인]`.
- Repositories: `rpsSpin<FIELD>`, `rpscbo<FIELD>`, `rpsbtn<FIELD>`, `rpschk<FIELD>`; a second one for another grid adds the role (`rpsDetailSpinQTY`).

## Grid and view block

```csharp
this.grd<X>.Dock = System.Windows.Forms.DockStyle.Fill;
this.grd<X>.EmbeddedNavigator.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
this.grd<X>.EmbeddedNavigator.Appearance.Options.UseFont = true;
this.grd<X>.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
this.grd<X>.isShowRowNumber = true;
this.grd<X>.MainView = this.gvw<X>;
this.grd<X>.Name = "grd<X>";
this.grd<X>.RepositoryItems.AddRange(new DevExpress.XtraEditors.Repository.RepositoryItem[] {
this.rpsSpinQTY,
this.rpscboQTYUNIT});
this.grd<X>.ViewCollection.AddRange(new DevExpress.XtraGrid.Views.Base.BaseView[] {
this.gvw<X>});
this.grd<X>.XmlTabelName = null;

this.gvw<X>.Appearance.HeaderPanel.Options.UseTextOptions = true;
this.gvw<X>.Appearance.HeaderPanel.TextOptions.HAlignment = DevExpress.Utils.HorzAlignment.Center;
this.gvw<X>.Columns.AddRange(new DevExpress.XtraGrid.Columns.GridColumn[] {
this.col<X>_<FIELD1>,
this.col<X>_<FIELD2>});
this.gvw<X>.GridControl = this.grd<X>;
this.gvw<X>.HorzScrollStep = 3;
this.gvw<X>.Name = "gvw<X>";
this.gvw<X>.OptionsView.ColumnAutoWidth = false;
this.gvw<X>.OptionsView.EnableAppearanceEvenRow = true;
this.gvw<X>.OptionsView.ShowAutoFilterRow = true;
this.gvw<X>.OptionsView.ShowFooter = true;
this.gvw<X>.OptionsView.ShowGroupPanel = false;
```

- `ShowGroupPanel = false` is on every view; the other `OptionsView` lines on 64-86%, always these values. (c) `ShowFooter = true` on new views.
- Check-box multi-select lists add `OptionsSelection.MultiSelect = true` and `MultiSelectMode = CheckBoxRowSelect` (30% of views).
- Other Load Layout values stay at HTML defaults (`ShowViewCaption = false`, `FocusRectStyle = CellFocus`, live scrolling); XML `gridView1` becomes `gvw<X>`.

## Column block

```csharp
this.col<X>_<FIELD>.AppearanceCell.Options.UseFont = true;
this.col<X>_<FIELD>.AppearanceHeader.Options.UseFont = true;
this.col<X>_<FIELD>.AppearanceHeader.Options.UseTextOptions = true;
this.col<X>_<FIELD>.AppearanceHeader.TextOptions.HAlignment = DevExpress.Utils.HorzAlignment.Center;
this.col<X>_<FIELD>.AppearanceHeader.TextOptions.VAlignment = DevExpress.Utils.VertAlignment.Center;
this.col<X>_<FIELD>.Caption = "<캡션>";
this.col<X>_<FIELD>.FieldName = "<FIELD>";
this.col<X>_<FIELD>.Name = "col<X>_<FIELD>";
this.col<X>_<FIELD>.OptionsColumn.AllowEdit = false;
this.col<X>_<FIELD>.OptionsColumn.ReadOnly = true;
this.col<X>_<FIELD>.Visible = true;
this.col<X>_<FIELD>.VisibleIndex = <N>;
```

- (c) Appearance: only these five lines. **No column `Font`** (inherits the grid's; HTML `Tahoma, 9pt` lives only in layout XML). No cell `TextOptions`, not even for numbers or dates. Headers centred both ways, `TreeListColumn` too.
- Columns in source order with its captions, FieldName, widths, visibility.
- Editing: display only (72%) = `AllowEdit = false` + `ReadOnly = true`; button works but value locked = only `ReadOnly = true`; editable = neither line (not `true`/`false`). Decide by repository type, events and request, not button name. Never view-wide `OptionsBehavior.Editable`/`ReadOnly` for column rules.

## Repository editors

Default on every new grid:

- (c) Numeric columns (`…QTY`, `…AMT`, `…UNP`, `…WGT`: 879 of 885) get `ColumnEdit = this.rpsSpin<FIELD>`; one `rpsSpinQTY` may serve several columns. A `HH:mm` time string stays text: decide by returned type.
- (c) Code columns shown as names (`…UNIT`, `…ACNT`, `…STS`: 161 of 175; `…DIV`/`…EMP`/`…MAN` 70-77% → `[확인]`) get `rpscbo<FIELD>`, bound in Load: `syCode.BindingCode("BA015", rpscboQTYUNIT)` / `BindingorgdivCode`.
- (c) Four places each: declaration, construction, the grid's `RepositoryItems.AddRange`, a column's `ColumnEdit`.

```csharp
this.rpsSpinQTY.AutoHeight = false;
this.rpsSpinQTY.Buttons.AddRange(new DevExpress.XtraEditors.Controls.EditorButton[] {
new DevExpress.XtraEditors.Controls.EditorButton(DevExpress.XtraEditors.Controls.ButtonPredefines.Combo)});
this.rpsSpinQTY.Name = "rpsSpinQTY";
```

- `rpscbo…` adds `NullText = ""`. `rpschk…`: `AutoHeight`, `Name`, `NullStyle = Unchecked`, `ValueChecked = "Y"`, `ValueUnchecked = "N"`, no buttons. `rpsbtn…`: its button; handler `ButtonClick`. Cell combos: `RepositoryItemLookUpEdit` (693) over `u_rpsLookUpEdit` (44), as the screen has.
- **No `DisplayFormat`, `FormatType`/`FormatString`, `Mask.EditMask` (`N0`/`N2`) by default** (11 of 278 user spin repositories). A date column doesn't justify `yyyy-MM-dd`; don't strip a DateEdit's required mask. Formats only when the requested behaviour needs them, with the reason.

## Footer

- (c) The first visible column carries the count (131 of 193 views; its own field in 173):

```csharp
this.col<X>_<FIELD>.Summary.AddRange(new DevExpress.XtraGrid.GridSummaryItem[] {
new DevExpress.XtraGrid.GridColumnSummaryItem(DevExpress.Data.SummaryItemType.Count, "<FIELD>", "{0:#,##0}건")});
```

  Missing: `[실패]` if a `--sibling` grid has one, else `[확인]` (61% of views).
- Quantities/amounts usually `Sum` (QTY 69%, AMT 85%): `"{0:#,##0.##}"` / `"{0:#,##0}"`, as the sibling; unit prices none. Summary formats never justify column formats ([coding-style.md](coding-style.md#numeric-display-formats)).
