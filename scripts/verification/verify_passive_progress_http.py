"""Disposable Mac paired HA passive progress; synthetic provider/CDN only."""
import os
from pathlib import Path
import runpy

if __name__ == '__main__':
    os.environ['DJC_PASSIVE_PROGRESS_PROBE'] = '1'
    runpy.run_path(str(Path(__file__).with_name('verify_session_artwork_http.py')), run_name='__main__')
