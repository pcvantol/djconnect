"""Closed schema check over actual HA settings operation receipts."""
import copy
import json
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT/'examples/client_contracts/settings_confirmation_v1'


def validate():
    schema = json.loads((DIRECTORY/'receipt.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema,format_checker=FormatChecker())
    wire = json.loads((DIRECTORY/'actual-ha-wire.json').read_text())
    values = [row['response']['settings_confirmation'] for row in wire['examples']]
    values.append(wire['profile_only_response']['settings_confirmation'])
    for value in values:
        validator.validate(value)
    bad = []
    original = values[0]
    for change in ({'schema_version':True},{'changed_fields':[]},{'changed_fields':['mood','mood']},
                   {'changed_fields':['voice']},{'locale':'xx'},{'moment_id':None},
                   {'settings_revision':None},{'accepted_at':'not-a-date'},
                   {'caller_text':'invented'},{'defaults_revision':-1}):
        bad.append({**original,**change})
    value = copy.deepcopy(original)
    value['settings']['mood']='fake-bpm'
    bad.append(value)
    value = copy.deepcopy(original)
    value['settings']['caller']='untrusted'
    bad.append(value)
    for value in bad:
        assert list(validator.iter_errors(value)),value
    return {'positive':len(values),'negative':len(bad),'native_audio_install':'NOT_RUN'}


if __name__ == '__main__':
    print(json.dumps(validate()))
