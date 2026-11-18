"""Compare a selected C# call with one real SELECT/SAVE procedure."""
import re

from src.common.results import CheckResult, Issue
from src.csharp.syntax import parameter_constructor_sites
from src.sql.lexer import _scan_sql_tokens
from src.sql.delta import _full_replace_records


def procedure_parameters(sql: str) -> dict[str, bool]:
    """Return parameter names and whether an explicit default is present."""
    tokens, errors = _scan_sql_tokens(sql)
    if errors:
        raise ValueError('SQL lexical errors prevent parameter comparison')
    start = next((i for i, t in enumerate(tokens) if t.normalized in {'PROC', 'PROCEDURE'}), None)
    if start is None:
        raise ValueError('A procedure definition is required')
    tokens = [token for token in tokens if token.kind not in {'line_comment', 'block_comment'}]
    start = next(i for i, token in enumerate(tokens) if token.normalized in {'PROC', 'PROCEDURE'})
    finish = next((i for i in range(start + 1, len(tokens))
                   if tokens[i].kind == 'word' and tokens[i].normalized == 'AS' and tokens[i].depth == 0
                   and not tokens[i - 1].text.startswith('@') and tokens[i - 1].normalized != 'EXECUTE'), None)
    if finish is None:
        raise ValueError('Procedure AS body boundary was not found')
    result = {}
    current = None
    for token in tokens[start+1:finish]:
        if token.text.startswith('@') and token.depth == 0:
            current = token.text.upper()
            result[current] = False
        elif token.text == '=' and current:
            result[current] = True
    return result


def procedure_worktypes(sql: str) -> set[str]:
    """Return literal @WORKTYPE values compared in the procedure body."""
    tokens, errors = _scan_sql_tokens(sql)
    if errors:
        return set()
    code = [t for t in tokens if t.kind not in {'line_comment', 'block_comment'}]
    values: set[str] = set()
    for idx, tok in enumerate(code):
        if tok.kind != 'word' or tok.normalized != '@WORKTYPE' or idx + 2 >= len(code):
            continue
        op = code[idx + 1].normalized
        if op in {'=', '<>', '!='} and code[idx + 2].kind in {'string', 'unicode_string'}:
            lit = code[idx + 2].text
            if lit.upper().startswith('N'):
                lit = lit[1:]
            values.add(lit.strip("'").replace("''", "'"))
        elif op == 'IN' and code[idx + 2].text == '(':
            cur = idx + 3
            while cur < len(code) and code[cur].text != ')':
                if code[cur].kind in {'string', 'unicode_string'}:
                    lit = code[cur].text
                    if lit.upper().startswith('N'):
                        lit = lit[1:]
                    values.add(lit.strip("'").replace("''", "'"))
                cur += 1
    return values


def procedure_openxml_tables(sql: str) -> set[str]:
    """Return table names referenced in OPENXML(..., '/ROOT/TableName', ...) paths."""
    return {m.group(1).upper() for m in re.finditer(r"OPENXML\s*\([^,]+,\s*N?'/ROOT/([A-Za-z0-9_]+)'", sql, re.I)}


def _csharp_worktype_literals(csharp_call: str) -> set[str]:
    values: set[str] = set()
    for m in re.finditer(r'"@WORKTYPE"\s*,\s*([^)\n;]+)', csharp_call, re.I):
        expr = m.group(1)
        for lit in re.finditer(r'"([A-Za-z0-9_]+)"', expr):
            val = lit.group(1)
            if val.upper() != '@WORKTYPE':
                values.add(val)
    return values


def _csharp_xml_tables(csharp_call: str) -> set[str]:
    return {m.group(1).upper() for m in re.finditer(r'DataTableToXml\s*\([^,)]+,\s*"([A-Za-z0-9_]+)"', csharp_call)}


def check_sp_call(csharp_call: str, procedure_sql: str) -> CheckResult:
    """The C# input must be the selected call, not an unrelated whole form."""
    result = CheckResult(checked=['selected call parameter names vs procedure definition',
                                  'literal @WORKTYPE values and DataTableToXml table names when present'],
                         not_checked=['parameter values and data types', 'parameter direction (OUTPUT/INPUTOUTPUT) and return values', 'XML column schema', 'stored procedure runtime behavior'])
    try:
        defined = procedure_parameters(procedure_sql)
    except ValueError as error:
        result.incomplete = True
        result.issues.append(Issue('procedure_input_incomplete', 'warning', str(error)))
        return result
    sites = parameter_constructor_sites(csharp_call)
    passed = {'@' + name.lstrip('@').upper() for _, name, _ in sites if name is not None}
    unresolved = not sites or any(name is None for _, name, _ in sites)
    if unresolved and defined:
        result.incomplete = True
        result.issues.append(Issue('call_parameters_unresolved', 'warning', 'Some parameter names need expression evaluation or no typed literal parameter constructors were found.'))
    for name in sorted(passed - defined.keys()):
        result.issues.append(Issue('unexpected_sp_parameter', 'error', 'The selected C# call passes a parameter absent from this SP.', details={'parameter': name}))
    for name in sorted(defined.keys() - passed):
        if not defined[name]:
            result.issues.append(Issue('required_sp_parameter_unconfirmed' if unresolved else 'required_sp_parameter_missing',
                'warning' if unresolved else 'error',
                'A required SP parameter is not resolved from the supplied constructors.' if unresolved else 'The selected call omits a required SP parameter.',
                details={'parameter': name}))
    sql_worktypes = procedure_worktypes(procedure_sql)
    cs_worktypes = _csharp_worktype_literals(csharp_call)
    if sql_worktypes and cs_worktypes:
        for wt in sorted(cs_worktypes):
            if wt.upper() not in {w.upper() for w in sql_worktypes}:
                result.issues.append(Issue('worktype_branch_missing_in_sql', 'error',
                    'The C# call passes a @WORKTYPE literal that is not handled in the procedure body.',
                    details={'worktype': wt, 'sql_worktypes': sorted(sql_worktypes)}))
    sql_xml_tables = procedure_openxml_tables(procedure_sql)
    cs_xml_tables = _csharp_xml_tables(csharp_call)
    if sql_xml_tables and cs_xml_tables:
        for tbl in sorted(cs_xml_tables - sql_xml_tables):
            result.issues.append(Issue('xml_table_path_mismatch', 'error',
                'DataTableToXml serializes a table root that is not read by OPENXML in this procedure.',
                details={'table': tbl, 'sql_openxml_tables': sorted(sql_xml_tables)}))
    result.metadata.update(passed_parameters=sorted(passed), defined_parameters=defined,
                           sql_worktypes=sorted(sql_worktypes), sql_openxml_tables=sorted(sql_xml_tables))
    result.not_checked.append('caller procedure identity; supply only the selected call for this procedure')
    return result


def review_save_delta(sql: str) -> CheckResult:
    findings = [Issue('full_replace_requires_review', 'warning', 'Confirm that whole-row replacement is requested; preserve actual NEW/MOD/DEL behavior otherwise.', details=r) for r in _full_replace_records(sql)]
    return CheckResult(issues=findings, checked=['DELETE followed by INSERT shape'], not_checked=['actual XML row states', 'DB post-write values'])
