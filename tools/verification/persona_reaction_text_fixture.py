"""Export actual literal producer outputs; no model, native or audio claim."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT/'custom_components/djconnect/persona_reaction_text.py'
FIXTURE = ROOT/'examples/client_contracts/persona_touch_reaction_v1/curated-texts.json'


def build():
    spec = importlib.util.spec_from_file_location('persona_reaction_copy', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = []
    for language in module.LANGUAGES:
        for persona in module.PERSONAS:
            for mood in module.MOODS:
                for kind in module.KINDS:
                    rows.append({'language': language, 'persona': persona, 'mood': mood, 'kind': kind,
                        'texts': [module.render(persona=persona, mood=mood, language=language,
                                               kind=kind, sequence=i) for i in range(2)]})
    return {'schema_version': 1, 'content_basis': 'core_owned_curated_reaction_v1',
        'proof_boundary': 'Actual literal producer catalog; independent editorial review separate. Not model-generated stories, installed/native/gesture or audible proof.',
        'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'cases': rows}


if __name__ == '__main__':
    text = json.dumps(build(), ensure_ascii=False, indent=2)+'\n'
    if '--check' in sys.argv:
        if FIXTURE.read_text() != text:
            raise SystemExit('persona reaction text fixture differs')
        print('persona reaction text fixture: MATCH')
    else:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(text)
        print('Exported240cells/480literal variants; no audio/model/native execution.')
