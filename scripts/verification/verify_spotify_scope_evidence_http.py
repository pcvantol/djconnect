"""Actual HA OAuth callback/ConfigFlow/refresh/Store scope proof; no live OAuth."""
import os
from pathlib import Path
import runpy
if __name__ == '__main__':
    os.environ['DJC_SCOPE_EVIDENCE_PROBE'] = '1'
    runpy.run_path(str(Path(__file__).with_name('verify_spotify_connection_repair_http.py')),run_name='__main__')
