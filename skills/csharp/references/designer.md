# Designer migration and structural review

New controls, sizes and names: [controls.md](controls.md). Grids: [grid.md](grid.md).

## Migration with source preservation

- Keep the original C#, Designer and resx as comparison copies (in `%TEMP%`). When bringing an original screen over, copy its Designer and resx and apply only the requested renames, deletions and edits. Screenshots confirm target and scope.
- A rename touches declaration, `Name`, references, events and resx keys. A deletion covers field, construction, registration, events and resources. Replace parts only where the target API differs.
- Compare remaining controls' Font, Size, AutoHeight, alignment, buttons, masks, display properties and Visible with the original diff (`check_designer.py --original` lists them). Check indirect init and resources separately.

## Structural review

- Slides as requirements: read the whole rendered slide (text, shapes, tables, images) and the latest corrections; compare final captions, field order and editable columns. Extracts stay outside the source.
- Fields and static controls, columns and repositories are created, placed and set in a form Visual Studio Designer can read. Dynamic binding and business code go to code-behind; named handlers are wired once where the target subscribes.
- Check the right-side space for buttons, `TabIndex` and container order.
- Totals, counts and their positions, group footers, merging, EvenRow, and the real bindings of `colList_`/`colDetail_`/`col<TABLE>_` columns. Properties overwritten after query or resize follow [screen-behavior.md](screen-behavior.md#grid-connections-and-overwrite-paths).
- Check the referenced DevExpress version's API and csproj/resx registration. Replace unsupported properties with supported ones of the same behaviour. DB/Task shutdown cleanup goes into the existing close/cancel path without duplicating inherited or partial `Dispose`.

## Preserving control defaults

- Before overriding, read the real control's constructor, `InitializeComponent`, helpers and base class; separate event/culture/mode-dependent changes from fixed defaults. Formats, masks, Enter-move, colours and borders may change in callbacks.
- The screen owns names, placement, text, bindings and events. Override only what a requirement needs; keep existing serialization and user edits.
- Keep required `Buttons.AddRange` of editors and calendars, even buttons that shared init hides later. A RepositoryItem follows its own class's init path.
- A screen-only large font needs a basis: the user's existing setting, the same-role control, or the approved reference Designer.

## Existing grids

`--original` lists unrequested option changes. View-wide `Appearance.*` is not set by column defaults; for font/alignment changes trace control/base/shared init and layout loading (normal, focused, selected) and don't reset shared properties to silence a warning.
