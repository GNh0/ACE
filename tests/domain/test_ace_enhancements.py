"""Regression tests for ACE enhancements across SQL, C#/Designer, cross-contract and Antigravity hooks."""
from pathlib import Path
import unittest

from src.csharp.checks import check_csharp
from src.maintenance.package_check import check_package
from src.pb.sql import check_sp_call
from src.runtime.hooks import ROOT, write_paths
from src.runtime.source_evidence import read_paths
from src.sql.checks import check_sql


class AceEnhancementTests(unittest.TestCase):
    def test_sql_trancount_and_expanded_description_suffixes(self):
        sql = """-- =============================================
-- AUTHOR:      근호
-- CREATE DATE: 2026-11-18
-- DESCRIPTION: 작업실적 등록
-- =============================================
CREATE PROCEDURE dbo.sp_TEST_SAVE
      @WORKTYPE VARCHAR(20) = ''
AS
BEGIN
    DECLARE @INIT_TRANCOUNT INT = @@TRANCOUNT;
    IF @INIT_TRANCOUNT = 0
    BEGIN
        BEGIN TRAN;
    END
    IF @INIT_TRANCOUNT = 0
    BEGIN
        COMMIT TRAN;
    END
END
"""
        result = check_sql(sql, require_procedure_header=True, procedure_author='근호')
        codes = [issue.code for issue in result.issues]
        self.assertNotIn('repeated_sibling_mode_guard', codes)
        self.assertNotIn('procedure_description_format', codes)

    def test_sql_sum_and_arithmetic_isnull_zero_exempted_while_business_fallback_flagged(self):
        sql = """SELECT SUM(ISNULL(A.QTY, 0)) AS TOTAL_QTY
     , A.STOCKQTY - ISNULL(B.OUTQTY, 0) AS REMAIN_QTY
     , ISNULL(NULLIF(A.PROCCD, ''), B.PROCCD) AS PROCCD
FROM MA210T A
        LEFT OUTER JOIN SA210T B
                     ON A.ITEMCD = B.ITEMCD
"""
        result = check_sql(sql)
        fallbacks = [issue for issue in result.issues if issue.code == 'value_fallback_review']
        self.assertEqual(1, len(fallbacks))
        self.assertEqual(3, fallbacks[0].line)

    def test_sql_backup_procedure_call_and_redundant_numeric_convert_detected(self):
        sql = """CREATE PROCEDURE dbo.sp_LIVE_SAVE
      @WORKTYPE VARCHAR(20) = ''
AS
BEGIN
    SELECT CONVERT(NUMERIC(18, 4), SUM(CONVERT(NUMERIC(18, 4), A.QTY))) AS QTY
    FROM MA210T A;

    EXEC dbo.sp_LEGACY_SAVE_BAK @WORKTYPE = @WORKTYPE;
END
"""
        result = check_sql(sql)
        codes = {issue.code: issue.severity for issue in result.issues}
        self.assertEqual('error', codes.get('backup_procedure_call'))
        self.assertEqual('warning', codes.get('redundant_numeric_convert_review'))

    def test_csharp_checkbox_multiselect_and_nested_row_panel_labels(self):
        control_src = """namespace KoneLib
{
    public class u_Label : DevExpress.XtraEditors.LabelControl
    {
        public u_Label()
        {
            this.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 10F);
            this.Appearance.Options.UseFont = true;
            this.Appearance.Options.UseTextOptions = true;
            this.Appearance.TextOptions.HAlignment = DevExpress.Utils.HorzAlignment.Far;
            this.Appearance.TextOptions.VAlignment = DevExpress.Utils.VertAlignment.Center;
            this.Size = new System.Drawing.Size(100, 25);
        }
    }
    public class u_TextEdit : DevExpress.XtraEditors.TextEdit
    {
        public u_TextEdit()
        {
            this.Size = new System.Drawing.Size(150, 25);
        }
    }
}
"""
        designer = """namespace Sample
{
    partial class SampleScreen
    {
        private KoneLib.u_GridControl grdList;
        private KoneLib.u_GridView gvwList;
        private KoneLib.u_Panel pnMaster;
        private KoneLib.u_Panel pnRow1;
        private KoneLib.u_Panel pnRow2;
        private KoneLib.u_Label lblITEM;
        private KoneLib.u_Label lblQTY;
        private KoneLib.u_TextEdit txtITEM;
        private KoneLib.u_TextEdit txtQTY;

        private void InitializeComponent()
        {
            this.grdList = new KoneLib.u_GridControl();
            this.gvwList = new KoneLib.u_GridView();
            this.pnMaster = new KoneLib.u_Panel();
            this.pnRow1 = new KoneLib.u_Panel();
            this.pnRow2 = new KoneLib.u_Panel();
            this.lblITEM = new KoneLib.u_Label();
            this.lblQTY = new KoneLib.u_Label();
            this.txtITEM = new KoneLib.u_TextEdit();
            this.txtQTY = new KoneLib.u_TextEdit();

            this.gvwList.GridControl = this.grdList;
            this.gvwList.Name = "gvwList";
            this.gvwList.OptionsSelection.MultiSelect = true;
            this.gvwList.OptionsSelection.MultiSelectMode = DevExpress.XtraGrid.Views.Grid.GridMultiSelectMode.CheckBoxRowSelect;
            this.gvwList.OptionsSelection.ShowCheckBoxSelectorInColumnHeader = DevExpress.Utils.DefaultBoolean.True;
            this.gvwList.OptionsSelection.CheckBoxSelectorColumnWidth = 30;
            this.gvwList.OptionsView.ColumnAutoWidth = false;
            this.gvwList.OptionsView.EnableAppearanceEvenRow = true;
            this.gvwList.OptionsView.ShowAutoFilterRow = true;
            this.gvwList.OptionsView.ShowFooter = true;
            this.gvwList.OptionsView.ShowGroupPanel = false;

            this.pnMaster.Controls.Add(this.pnRow1);
            this.pnMaster.Controls.Add(this.pnRow2);
            this.pnRow1.Controls.Add(this.txtITEM);
            this.pnRow1.Controls.Add(this.lblITEM);
            this.pnRow2.Controls.Add(this.txtQTY);
            this.pnRow2.Controls.Add(this.lblQTY);

            this.lblITEM.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 12F);
            this.lblITEM.Margin = new System.Windows.Forms.Padding(1, 2, 1, 2);
            this.lblITEM.MaximumSize = new System.Drawing.Size(65535, 65535);
            this.lblITEM.Size = new System.Drawing.Size(110, 44);

            this.lblQTY.Appearance.Font = new System.Drawing.Font("Pretendard GOV Variable", 12F);
            this.lblQTY.Margin = new System.Windows.Forms.Padding(1, 2, 1, 2);
            this.lblQTY.MaximumSize = new System.Drawing.Size(65535, 65535);
            this.lblQTY.Size = new System.Drawing.Size(110, 44);

            this.txtITEM.Size = new System.Drawing.Size(200, 44);
            this.txtQTY.Size = new System.Drawing.Size(200, 44);
        }
    }
}
"""
        code = """namespace Sample
{
    public partial class SampleScreen
    {
    }
}
"""
        result = check_csharp(code, designer=designer, control_sources=[control_src])
        codes = [issue.code for issue in result.issues]
        self.assertNotIn('grid_option_outside_baseline', codes)
        self.assertNotIn('label_font_mismatch', codes)
        self.assertNotIn('control_height_unverified', codes)
        self.assertNotIn('user_control_default_override', codes)

    def test_sp_call_cross_contract_worktype_and_xml_table_checks(self):
        sp_sql = """CREATE PROCEDURE dbo.sp_QC100110_SAVE
      @WORKTYPE VARCHAR(20) = ''
    , @ORGDIV VARCHAR(10) = '01'
    , @XML_QC100T NVARCHAR(MAX) = NULL
AS
BEGIN
    IF @WORKTYPE = 'NEW'
    BEGIN
        SELECT *
        FROM OPENXML(@DOC_ID, '/ROOT/QC100T', 1)
        WITH (ITEMCD VARCHAR(30)) A;
    END
    ELSE IF @WORKTYPE = 'DEL'
    BEGIN
        SELECT 1;
    END
END
"""
        bad_call = """string xml = DataUtil.DataTableToXml(dtList, "WRONG_TABLE");
dbClient.ExecSPTrn("sp_QC100110_SAVE"
                 , new DbParameter("@WORKTYPE", "RESULT")
                 , new DbParameter("@ORGDIV", "01")
                 , new DbParameter("@XML_QC100T", xml)
                  );
"""
        res = check_sp_call(bad_call, sp_sql)
        codes = [issue.code for issue in res.issues]
        self.assertIn('worktype_branch_missing_in_sql', codes)
        self.assertIn('xml_table_path_mismatch', codes)

        good_call = """string xml = DataUtil.DataTableToXml(dtList, "QC100T");
dbClient.ExecSPTrn("sp_QC100110_SAVE"
                 , new DbParameter("@WORKTYPE", "NEW")
                 , new DbParameter("@ORGDIV", "01")
                 , new DbParameter("@XML_QC100T", xml)
                  );
"""
        res_ok = check_sp_call(good_call, sp_sql)
        self.assertEqual([], res_ok.issues)

    def test_antigravity_host_tools_and_package_validation(self):
        pkg = check_package(ROOT)
        self.assertEqual([], pkg.issues)
        paths, unresolved = write_paths({
            'cwd': str(ROOT),
            'tool_name': 'write_file',
            'tool_input': {'Path': str(ROOT / 'Sample.sql'), 'Content': 'SELECT 1;'},
        })
        self.assertEqual([(ROOT / 'Sample.sql').resolve()], paths)
        self.assertEqual([], unresolved)
        rpaths = read_paths({
            'cwd': str(ROOT),
            'tool_name': 'read_file',
            'tool_input': {'Path': str(ROOT / 'Sample.sql')},
        })
        self.assertEqual([(ROOT / 'Sample.sql').resolve()], rpaths)

    def test_compound_engineering_and_edd_end_to_end_linkage(self):
        import json
        import os
        import subprocess
        import sys
        import tempfile
        from unittest.mock import patch
        from src.maintenance.agents import agent_definitions
        from src.runtime.hooks import handle

        defs = agent_definitions(ROOT)
        for role in ('kh-sql-worker', 'kh-csharp-worker', 'kh-pb-worker', 'kh-rule-auditor'):
            self.assertIn('compound_rules', defs[role])
            self.assertIn('EDD Scenario Matrix', defs[role])

        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder).resolve()
            project = base / 'project'
            project.mkdir()
            log = base / 'transcript.jsonl'
            log.write_text('', encoding='utf-8')
            data_dir = base / 'data'
            scope = {'cwd': str(project), 'session_id': 'compound-sess', 'transcript_path': str(log)}
            with patch.dict(os.environ, {'PLUGIN_DATA': str(data_dir), 'KH_HOOKS_MODE': 'enforce'}):
                handle({**scope, 'hook_event_name': 'UserPromptSubmit', 'prompt': '$sql-formatting task', 'turn_id': 't1'}, 'codex')
                cmd_base = [sys.executable, '-B', str(ROOT / 'scripts/kh_context.py'),
                            '--cwd', str(project), '--session', 'compound-sess', '--transcript', str(log),
                            '--host', 'codex', '--data-root', str(data_dir / 'context-v1')]
                comp = subprocess.run([*cmd_base, 'compound', 'ba030t-left-join', '--domain', 'sql',
                                       '--anti-pattern', 'INNER JOIN BA030T for display-only item names',
                                       '--rule', 'Use LEFT OUTER JOIN BA030T when only fetching ITEMNM/SPEC'],
                                      capture_output=True, text=True, encoding='utf-8', check=True)
                self.assertEqual('compounded', json.loads(comp.stdout)['status'])

                recalled = json.loads(subprocess.run([*cmd_base, 'recall'], capture_output=True, text=True, encoding='utf-8', check=True).stdout)
                self.assertEqual(1, len(recalled['compound_rules']))
                self.assertEqual('ba030t-left-join', recalled['compound_rules'][0]['id'])

                started = handle({**scope, 'hook_event_name': 'SessionStart'}, 'codex')
                self.assertIn('ba030t-left-join', started['hookSpecificOutput']['additionalContext'])


if __name__ == '__main__':
    unittest.main()
