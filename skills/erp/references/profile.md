# Framework profile: roles and names

The rules in this layer are written for **roles** (base form, save call, numbering SP …). The concrete names in the other references (`FrmBase`, `ux` controls, `SaveTrn`, `SY100T` …) are a **made-up example profile** (`ExampleLib`); they never exist in a real project. The real names live only on the user's machine in `<profile>` (`~/.claude/ace/profile`, or `$ACE_PROFILE_DIR`): `profile.md` (this role table with real names), `profile.json` and `designer.json` (read by the checkers; formats in [data](../data/)) and `projects/<PROJECT>.md` (project-only facts). The repository never holds real project, DB, table, screen, framework or person names.

## Before the first task in a project

1. Read `<profile>/profile.md` and `<profile>/projects/<PROJECT>.md`. If they exist, use their names and translate every example name in the references through them.
2. Otherwise run `python <ACE>/skills/erp/scripts/map_project.py <solution folder> --name <PROJECT>` (counts base form, edit-mode enum, control prefix, DB calls, XML helper, messages, code binding, SP prefix, modules; PROJECT_B_1: 983 files in ~9 s), check the top file of each row, read one saving screen with its SAVE SP, and write the role table below with that project's names to `<profile>/profile.md` (and `profile.json` for the checkers), project-only facts to `<profile>/projects/<PROJECT>.md`. Mark a role `없음` when the project has no such thing; rules for that role then do not apply.
3. Write the mapping in the answer before the first change ("프로필: 기본 폼 = …, 저장 호출 = …"). Never write an example-profile name into real code.

## Roles

| Role | Example profile (`ExampleLib`, made up) | How to find it in a project |
| --- | --- | --- |
| Base form class | `FrmBase` (`: FrmBase`) | the class every screen inherits |
| Edit-mode enum and variable | `EditMode` / `m_EditState` (values per project: `<profile>/projects/`) | the enum the toolbar commands set |
| Toolbar commands | `RunCommand(Cmd.Search)`, `SearchCommand`/`NewCommand`/`SaveCommand` … | the base form's command dispatch |
| Control library | `ux` controls (`uxLabel`, `uxTextEdit`, `uxLookUpEdit`, `uxGridControl`, `uxGridView` …); sizes in `<profile>/designer.json` ([format](../data/designer.example.json)) | the namespace most Designer fields use |
| Screen helper | `ui` (`RowToPanel`, `PanelToTable`, `GridRowIndex`, `ProtectControls`) | the helper object the base form exposes |
| Code binding | `code.Bind` / `BindByOrg` | how combos are filled from the code table |
| DB client and save calls | `db.SaveTrn` (caller owns the transaction) / `SaveNoTrn` (no transaction) | the base form's DB object; which call wraps a transaction |
| Grid → XML | `TableToXml(dt)` with row state attribute `GBN` (NEW/MOD/DEL) | how a screen sends rows to a SAVE SP |
| Messages | `Msg`, `MsgWarn`, `MsgYesNo`, `MsgError` | the base form's message methods |
| SP log | `SP_LOG_XML @@PROCID, @WORKTYPE, @USERID, @XML…` | first statement of existing SAVE SPs |
| Header numbering | `SP_NEW_KEY` (never write `SY100T`) | how existing SAVEs get a new header number |
| Closing check | `DBO.F_IS_CLOSED` + the four standard messages | the check before stock-changing writes |
| Key split | `DBO.F_SPLIT_KEY(@KEYCODE)` → `CODE`, `SEQ1`, `SEQ2` | how SPs split a combined screen key |
| Code table / user table | `MS011T` (`MAINCD`, `SUBCD`, `SUBNM`, `USEYN`) / `MS095T` (`USERID`, `USERNM`) | where code names and user names live |
| Master tables | `MS0xxT` (`MS020T` customers, `MS030T` items …) | the item/customer/master tables |

## Checkers

- `check_designer.py` applies the control-library items (sizes, blocks, prefixes, grid roles) only to control types listed in `data/designer.json`; a Designer without those types skips them.
- `check_sql.py` items tied to the profile fire only when the SQL uses those names (`SY100T` writes, `MS0xxT` joins, `SP_NEW_KEY` loops). `--caller` means "the caller owns the transaction" (`SaveTrn`), "no transaction" (`SaveNoTrn`) or `unknown`; pass the mapped call of the project.
- For another profile, add its control defaults as a new `data/designer.<profile>.json` only when the user starts working in that project often.
