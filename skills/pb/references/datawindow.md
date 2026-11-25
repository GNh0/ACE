# DataWindow and screen mapping

Map PBL/object, base classes, linked DWs, retrieve arguments, SQL, column/compute, protect/taborder, update properties, and events. Reflect groups, panels, grids, captions, column order, and defaults from HTML-to-XML input in the actual layout.

For slide-based screen requirements, inspect the complete rendered slide before mapping columns, captions and editable fields. Separate embedded-image exports do not represent the full composite layout. Follow the csharp skill's designer.md and the latest user corrections.

Preserve raw composite-key components and create display keys separately. Derive component counts and business names from input; never hard-code the number of components or names like ORD/PUR/REC. Migrate read-only/editable states, list/detail connections, selection/focus, user permissions, and lookup/numeric/button Repositories using current C# patterns.

For reports, preserve H/D/F, group, band, and page order. Review shared paths for converting multiple reports to HTML while checking constructor side effects and render order. Check actual contracts for missing bands and empty values. Do not replace output behavior with simple HTML concatenation.

## C# grid generation from a DataWindow

When generating a C# grid from a DataWindow, use the csharp skill's grid.md defaults (from the user's `DataWindowToXml.html`). Use actual DataWindow captions, column order, widths and visibility. Do not assign a font to generated columns (they only set `UseFont = true`), and do not impose template display values on an existing screen; current Designer values take priority there.

Editing modes per column: read-only → `AllowEdit=false` + `ReadOnly=true`; action column (button Repository) → `ReadOnly=true` only; editable → neither. Do not add `OptionsBehavior` or EditMask/DisplayFormat when connecting a Spin Repository. If another grid on the same screen already has `rpsSpinQTY`, the detail grid uses `rpsSpinDetailQTY`; do not rename existing Repositories.
