"""Closed, evaluation-only progress; never an execution or publication grant."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


PHASES = frozenset({'setup', 'case', 'model', 'teardown', 'report', 'terminal'})
OUTCOMES = frozenset({'RUNNING', 'FAIL', 'CANCELLED', 'COMPLETE_NOT_QUALIFIED'})
FIELDS = frozenset({'schema_version', 'manifest_sha256', 'phase', 'outcome',
    'current_case', 'completed_cases', 'failed_cases', 'sdk_attempts_reserved',
    'sdk_completed_responses', 'external_billing', 'qualification'})


def validate_progress(value, *, case_ids, manifest):
    """No exception text, prompts, answers, paths, identities or arbitrary keys."""
    if (type(value) is not dict or set(value) != FIELDS
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['manifest_sha256'] != manifest
            or type(value['phase']) is not str or type(value['outcome']) is not str
            or value['phase'] not in PHASES or value['outcome'] not in OUTCOMES
            or ((value['phase'] == 'terminal') != (value['outcome'] != 'RUNNING'))
            or (value['phase'] == 'terminal' and value['current_case'] is not None)
            or (value['current_case'] is not None and type(value['current_case']) is not str)
            or value['current_case'] not in {None, 'catalogue-start', *case_ids}
            or value['external_billing'] != 'UNKNOWN_NOT_A_BILLING_RECEIPT'
            or value['qualification'] != 'NOT_QUALIFIED'):
        return False
    completed, failed = value['completed_cases'], value['failed_cases']
    if (type(completed) is not list or type(failed) is not list
            or any(type(v) is not str for v in completed + failed)
            or len(completed) > 100 or len(set(completed)) != len(completed)
            or not set(completed) <= set(case_ids)
            or len(set(failed)) != len(failed) or not set(failed) <= set(completed)):
        return False
    attempts, responses = value['sdk_attempts_reserved'], value['sdk_completed_responses']
    return (type(attempts) is int and type(responses) is int
        and 0 <= responses <= attempts <= 392
        and (value['outcome'] != 'COMPLETE_NOT_QUALIFIED' or len(completed) == 100))


class CatalogueProgress:
    """One private file per original test; failed writes poison further calls.

    A reservation precedes SDK invocation, so it is an upper bound on attempted
    dispatches, not proof of billable usage. SIGKILL/ENOSPC may still leave an
    incomplete prefix. Existing files are never interpreted as retry authority.
    """
    def __init__(self, path: Path, *, case_ids, manifest):
        self.path = path
        self.case_ids = tuple(case_ids)
        if (len(self.case_ids) != 100 or len(set(self.case_ids)) != 100
                or type(manifest) is not str or len(manifest) != 64
                or any(c not in '0123456789abcdef' for c in manifest)):
            raise ValueError('catalogue_progress_scope_invalid')
        self.manifest = manifest
        self.healthy = True
        self.value = {'schema_version': 1, 'manifest_sha256': manifest,
            'phase': 'setup', 'outcome': 'RUNNING', 'current_case': None,
            'completed_cases': [], 'failed_cases': [], 'sdk_attempts_reserved': 0,
            'sdk_completed_responses': 0,
            'external_billing': 'UNKNOWN_NOT_A_BILLING_RECEIPT',
            'qualification': 'NOT_QUALIFIED'}
        # Exclusive first creation forbids silently resuming another attempt.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(fd)
        self._save()

    def _save(self):
        if not self.healthy:
            raise RuntimeError('catalogue_progress_closed')
        temporary = None
        try:
            if not validate_progress(self.value, case_ids=self.case_ids, manifest=self.manifest):
                raise ValueError('catalogue_progress_invalid')
            raw = (json.dumps(self.value, sort_keys=True) + '\n').encode()
            if len(raw) > 16384:
                raise ValueError('catalogue_progress_oversized')
            fd, temporary = tempfile.mkstemp(prefix='.catalogue-progress-', dir=self.path.parent)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            temporary = None
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except BaseException:
            self.healthy = False
            raise
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    # The original save error must win; leftover private bytes
                    # are not uploaded or used to recover execution authority.
                    self.healthy = False

    def phase(self, phase, case=None):
        self._running()
        self.value.update(phase=phase, current_case=case)
        self._save()

    def before_model(self, case):
        self._running()
        self.value.update(phase='model', current_case=case)
        self.value['sdk_attempts_reserved'] += 1
        self._save()
        return self.value['sdk_attempts_reserved']

    def completed_response(self):
        self._running()
        self.value['sdk_completed_responses'] += 1
        self._save()

    def completed_case(self, case, *, passed):
        self._running()
        self.value['completed_cases'].append(case)
        if not passed:
            self.value['failed_cases'].append(case)
        self.value.update(phase='case', current_case=case)
        self._save()

    def terminal(self, outcome):
        self._running()
        if outcome not in OUTCOMES - {'RUNNING'}:
            raise ValueError('catalogue_progress_terminal_invalid')
        self.value.update(phase='terminal', outcome=outcome, current_case=None)
        self._save()

    def _running(self):
        if not self.healthy or self.value['outcome'] != 'RUNNING':
            raise RuntimeError('catalogue_progress_closed')

    def failure_without_masking_primary(self, *, cancelled=False):
        try:
            self.terminal('CANCELLED' if cancelled else 'FAIL')
        except BaseException:
            # Original failure/cancellation wins; no further model call may pass.
            self.healthy = False
