"""Validate reactive Golden coverage against current Core routes and owning tests."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = Path('docs/verification/fixtures/askdj_golden_release_matrix_v1.json')


def required_bindings(matrix):
    return [*matrix['additional_route_contracts'].values(),
            *(b for family in matrix['families'] for b in family['owning_tests']),
            *(b for family in matrix['families'] for step in family['steps'] for b in step['owning_tests'])]


def release_blockers(matrix):
    """Known open product findings cannot disappear behind inventory green."""
    families = {row['id'] for row in matrix['families']}
    issues = matrix.get('reported_issues', [])
    if not issues or len({row['id'] for row in issues}) != len(issues):
        raise ValueError('reported_issues_missing_or_duplicate')
    for issue in issues:
        if (not issue.get('finding') or issue.get('family_id') not in families
                or issue.get('core_qualification') not in {'open', 'locally_covered', 'qualified'}):
            raise ValueError('reported_issue_unbound_or_unqualified')
    steps = [step for family in matrix['families'] for step in family['steps']]
    if len({step.get('id') for step in steps}) != len(steps):
        raise ValueError('conversation_step_missing_or_duplicate')
    if any(not step.get('owning_tests') or not step.get('id')
           or step.get('acceptance_status') not in {'owner_contract', 'open_real_quality'} for step in steps):
        raise ValueError('unbound_conversation_step')
    return [row['id'] for row in issues if row['core_qualification'] == 'open'] + [
        step['id'] for family in matrix['families'] for step in family['steps']
        if step.get('acceptance_status') != 'owner_contract']


def validate_moment_matrix(root=ROOT):
    matrix=json.loads((root/'docs/verification/fixtures/dj_moment_persona_mood_golden_v1.json').read_text())
    expected={(p,m,l) for p in ('home_dj','radio_dj','club_dj','festival_dj')
              for m in ('chill','groove','energy','party') for l in ('en','nl','de','fr','es')}
    rows=matrix.get('cells',[])
    if (matrix.get('schema_version')!=1 or len(rows)!=80
        or len({r['id'] for r in rows})!=80
        or {(r['persona'],r['mood'],r['language']) for r in rows}!=expected
        or set(matrix.get('families',{}))!={'track','birth','formation','description','edition','genre'}):
        raise ValueError('incomplete_proactive_persona_mood_matrix')
    return {r['id']+'-'+family for r in rows for family in (*matrix['families'],'music-only')}


def validate(root=ROOT):
    proactive_cases=validate_moment_matrix(root)
    raw = (root/MATRIX).read_bytes()
    matrix = json.loads(raw)
    blockers = release_blockers(matrix)
    base_raw = (root/matrix['existing_single_turn_cases']).read_bytes()
    base = json.loads(base_raw)
    source = ast.parse((root/'custom_components/djconnect/ask_dj/__init__.py').read_text())
    names = {node.args[1].value for node in ast.walk(source)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == 'AskDjIntent' and len(node.args) > 1
             and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)}
    covered = {row.get('expect',{}).get('intent') for row in base}
    covered.update(matrix['additional_route_contracts'])
    missing = sorted(names-covered)
    if missing:
        raise ValueError('uncovered_core_routes:'+','.join(missing))
    # Catalog presence alone is insufficient: every generic help example must
    # bind executable fixture values, including repeated artist placeholders.
    import sys
    sys.path.insert(0,str(root))
    from tests.ask_dj_e2e_contract import materialize_case
    help_rows=[row for row in base if row['id'].startswith('help_prompt_')]
    for row in help_rows:
        executable=materialize_case(row)
        if '[' in executable['request']['text']:
            raise ValueError('unexecuted_help_placeholder')
    ids = [row['id'] for row in base]
    if not base or len(set(ids)) != len(ids):
        raise ValueError('single_turn_cases_empty_or_duplicate')
    families = matrix['families']
    if len({f['id'] for f in families}) != len(families) or not families:
        raise ValueError('conversation_families_empty_or_duplicate')
    bindings = list(matrix['additional_route_contracts'].values())
    for family in families:
        if not family['steps'] or not family['owning_tests']:
            raise ValueError('unowned_conversation_family')
        for step in family['steps']:
            if not all(isinstance(step.get(k),str) and step[k].strip()
                       for k in ('question','expected_answer','model_policy')):
                raise ValueError('incomplete_question_answer_contract')
            if (not step.get('id') or not step.get('owning_tests')
                    or step.get('acceptance_status') not in {'owner_contract', 'open_real_quality'}):
                raise ValueError('unbound_conversation_step')
            bindings.extend(step['owning_tests'])
        bindings.extend(family['owning_tests'])
    methods_by_path = {}
    for binding in bindings:
        path=Path(binding['file'])
        if path.is_absolute() or '..' in path.parts or path.parts[0]!='tests':
            raise ValueError('invalid_test_binding')
        if path not in methods_by_path:
            methods_by_path[path] = {n.name for n in ast.walk(ast.parse((root/path).read_text()))
                                    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        methods = methods_by_path[path]
        if binding['method'] not in methods:
            raise ValueError('missing_bound_test:'+binding['method'])
    # A newly added regression method is not silently omitted from the named
    # release matrix. The runner separately proves these bindings executed.
    for file in matrix.get('regression_suite_files', []):
        path = Path(file)
        if path.is_absolute() or '..' in path.parts or path.parts[0] != 'tests':
            raise ValueError('invalid_regression_suite')
        methods = {node.name for node in ast.walk(ast.parse((root/path).read_text()))
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_')}
        named = {row['method'] for row in bindings if row['file'] == file}
        if not methods or methods - named:
            raise ValueError('unbound_reported_issue_regression:'+','.join(sorted(methods - named)))
    return {'proactive_golden_cases':len(proactive_cases),'status':'PASS','literal_core_routes':len(names),'single_turn_cases':len(base),'executable_help_cases':len(help_rows),
            'conversation_families':len(families),'conversation_steps':sum(len(f['steps']) for f in families),
            'reported_issues':len(matrix['reported_issues']),
            'open_core_findings':[i for i in blockers if i.startswith('ASKDJ-ISSUE-')],
            'open_quality_steps':[i for i in blockers if not i.startswith('ASKDJ-ISSUE-')],
            'matrix_sha256':hashlib.sha256(raw).hexdigest(),
            'single_turn_sha256':hashlib.sha256(base_raw).hexdigest()}


if __name__=='__main__':
    print(json.dumps(validate(),sort_keys=True))
