"""Software-only qualified-fact timeline from real Core Runtime publication.

Provider replies and observation time are mocked; this is never Pi/live proof.
"""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.test_session_facts import SessionFactsTest

if __name__ == "__main__":
    SessionFactsTest.setUpClass()
    try:
        fixture = SessionFactsTest(
            "test_four_independent_angles_publish_through_flow_and_broadcast_once"
        )
        fixture.test_four_independent_angles_publish_through_flow_and_broadcast_once()
        target = Path(sys.argv[1])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(fixture.runtime_capture, ensure_ascii=False, indent=2) + "\n")
        print("Captured four independent software-only fact Moments")
    finally:
        SessionFactsTest.tearDownClass()
