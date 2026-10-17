"""Offline ROUTE-1 review corpus, never live route or installation authority."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

# Share production lexical policy; the Node WHATWG corpus remains independent.
_spec = importlib.util.spec_from_file_location("display_origin_contract",
    Path(__file__).resolve().parents[2] / "custom_components/djconnect/display_origin.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
lexical_route_allowed = _module.lexical_route_allowed


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    corpus = json.loads((root/'examples/client_contracts/vibecast_display_admission_v1/route-cases.json').read_text())
    assert corpus['status'] == 'REVIEW_CANDIDATE_NOT_FROZEN'
    for case in corpus['cases']:
        actual = lexical_route_allowed(case['entry_url'], case['selected_origin'])
        if actual is not case['allowed']:
            raise AssertionError(case['id'])
    print(json.dumps({'lexical_cases': len(corpus['cases']), 'result': 'PASS_LEXICAL_CORPUS_ONLY',
                      'trust_TLS_DNS_redirect_HA_runtime': 'NOT_QUALIFIED'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
