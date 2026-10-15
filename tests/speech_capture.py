"""Optional bounded actual-output receipts for independent speech review."""
import json
import os
from pathlib import Path


def capture(name, row):
    if not (root := os.environ.get('DJC_SPEECH_MATRIX_CAPTURE_DIR')):
        return
    directory = Path(root)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (name + '.json')
    rows = json.loads(target.read_text()) if target.exists() else []
    if len(rows) >= 1000:
        raise AssertionError('Owned speech capture exceeded its declared bound')
    rows.append(row)
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n')
