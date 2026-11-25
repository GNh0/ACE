# PBL export (ORCA)

Use the bundled `scripts/Export-PBL.ps1` and `scripts/PblExporter.exe` (x86 helper). No PblScripter install is needed, but the PowerBuilder ORCA runtime (PB 7.0 / 10.5 / 12.5) must be installed on this PC.

## Run

Point the output folder at a temp work folder outside the source project. Use an absolute skill folder path.

```powershell
# object list (printed to the console, but without -OutputDirectory it stops with exit code 17)
powershell -ExecutionPolicy Bypass -File "<skill>\scripts\Export-PBL.ps1" -Version 125 -PblPath "C:\project\app.pbl" -Action list -OutputDirectory "<temp>\pbl-export"

# export everything: -Action exportall ; one object: -Action export -ObjectName "d_employee"
```

- Unknown version: try `-Action list` with `125` → `105` → `70`. If the runtime is not in the standard path, pass `-OrcaDllPath`, `-RuntimePath`. A PB 7 PBL really gave a SySAM license error on `125`, `Bad library` on `105`, and listed on `70`; those two errors mean "try the next version".
- With the version that lists, export only the needed objects with `-Action export`. For one screen, the window (or user object) and the DataWindows it uses via `dataobject` are enough.
- If existing exports have unknown origin (which PBL, when), export the same object again and compare before using them as evidence. If equal, use the existing files' line numbers.
- Export does not change the PBL, but if a copy of the PBL exists use the copy. The output folder must be outside the source folder.
- A PBL header of 0600 does not prove PB 6; you found a runtime that reads it, not the authoring version.

## Success

- Exit code 0 with `Session open failed`, `Bad library`, SySAM/license errors or empty output is **failure**.
- Exit code 0 with no new output file is **unconfirmed**.
- On failure continue with export files or pasted source from the user, and state the missing evidence.
- For analysis only, delete the temp output folder after reading the needed source. Keep exports requested as deliverables.
