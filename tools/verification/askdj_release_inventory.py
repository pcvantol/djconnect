"""Validate reactive Golden coverage against current Core routes and owning tests."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = Path('docs/verification/fixtures/askdj_golden_release_matrix_v1.json')


def validate(root=ROOT):
    raw = (root/MATRIX).read_bytes()
    matrix = json.loads(raw)
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
        bindings.extend(family['owning_tests'])
    for binding in bindings:
        path=Path(binding['file'])
        if path.is_absolute() or '..' in path.parts or path.parts[0]!='tests':
            raise ValueError('invalid_test_binding')
        methods={n.name for n in ast.walk(ast.parse((root/path).read_text()))
                 if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        if binding['method'] not in methods:
            raise ValueError('missing_bound_test:'+binding['method'])
    return {'status':'PASS','literal_core_routes':len(names),'single_turn_cases':len(base),'executable_help_cases':len(help_rows),
            'conversation_families':len(families),'conversation_steps':sum(len(f['steps']) for f in families),
            'matrix_sha256':hashlib.sha256(raw).hexdigest(),
            'single_turn_sha256':hashlib.sha256(base_raw).hexdigest()}


if __name__=='__main__':
    print(json.dumps(validate(),sort_keys=True))
