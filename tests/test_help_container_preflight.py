"""Ownership and closed setup evidence; no Docker, provider or model calls."""
import ast
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools.verification import verify_help_container_preflight as preflight
from tools.verification import run_help_catalogue_qualification_20261023 as runner


def valid(expected):
    return {'schema_version': 1, 'status': 'PASS_SETUP_ONLY', 'phase': 'complete',
        'owner_matches': True, 'lab_write': True, 'source_hashes': expected,
        'checkpoint_initialized': True, 'model_calls': 0, 'qualification': 'NOT_QUALIFIED'}


class HelpContainerPreflightTest(unittest.TestCase):
    def test_current_costfree_host_inventory_matches_actual_container_harness(self):
        root = Path(__file__).resolve().parents[1]
        harness = root / 'scripts/verification/verify_ask_dj_contextual_dialogue_http.py'
        tree = ast.parse(harness.read_text())
        actual_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
            and node.name == 'hashes')
        namespace = {'ROOT': root, 'Path': Path, 'hashlib': hashlib, '__file__': str(harness)}
        exec(compile(ast.Module(body=[actual_function], type_ignores=[]), str(harness), 'exec'), namespace)
        actual = namespace['hashes']()
        self.assertEqual(preflight.profile_source_hashes(root), actual)
        helper = 'scripts/verification/artist_public_input_receipts.py'
        self.assertEqual(actual[helper], hashlib.sha256((root / helper).read_bytes()).hexdigest())

    def test_costfree_command_has_matching_user_no_network_no_secrets_and_readonly_source(self):
        command = preflight.command(Path('/synthetic-source'), Path('/synthetic-lab'), 'own-container')
        self.assertEqual(command[command.index('--user') + 1], f'{os.getuid()}:{os.getgid()}')
        self.assertEqual(command[command.index('--network') + 1], 'none')
        self.assertEqual(command[command.index('--cap-drop') + 1], 'ALL')
        self.assertIn('no-new-privileges', command)
        self.assertIn('/synthetic-source:/candidate:ro', command)
        self.assertNotIn('--privileged', command)
        environment = [command[i + 1] for i, value in enumerate(command) if value == '-e']
        self.assertFalse(any('KEY' in value or 'TOKEN' in value or 'GRANT' in value for value in environment))
        compile(preflight.PROBE, '<costfree-container-probe>', 'exec')

    def test_setup_receipt_never_means_paid_or_catalogue_qualification(self):
        expected = {'synthetic-source.py': 'a' * 64}
        value = valid(expected)
        self.assertTrue(preflight.valid_probe(value, expected))
        for key, changed in [('schema_version', True), ('owner_matches', 1),
            ('lab_write', False), ('checkpoint_initialized', False), ('model_calls', True),
            ('model_calls', 1), ('qualification', 'QUALIFIED'), ('source_hashes', {}),
            ('status', 'PASS'), ('phase', 'source_import')]:
            with self.subTest(key=key, changed=changed):
                self.assertFalse(preflight.valid_probe({**value, key: changed}, expected))
        self.assertFalse(preflight.valid_probe({**value, 'arbitrary': 'field'}, expected))
        with self.assertRaises(ValueError):
            preflight.unique([('status', 'FAIL'), ('status', 'PASS_SETUP_ONLY')])

    def test_unknown_cleanup_cannot_produce_a_passing_setup_receipt(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            products = {f'synthetic-{i}': 'a' * 64 for i in range(298)}
            result = SimpleNamespace(returncode=0, stdout=json.dumps(valid({})).encode())
            with patch.object(preflight, 'product_hashes', return_value=products), \
                 patch.object(preflight, 'profile_source_hashes', return_value={}), \
                 patch.object(preflight.subprocess, 'run', return_value=result), \
                 patch.object(preflight, 'container_absent', return_value=False):
                self.assertEqual(preflight.run(root, root / 'new-proof'), 1)
            receipt = json.loads((root / 'new-proof/preflight.json').read_text())
            self.assertEqual(receipt['status'], 'FAIL_SETUP_ONLY')
            self.assertEqual(receipt['own_container'], 'UNKNOWN')
            self.assertEqual(receipt['qualification'], 'NOT_QUALIFIED')

    def test_exact_current_inventory_admits_only_current_files_before_container_IO(self):
        source = Path(__file__).resolve().parents[1]
        products = preflight.product_hashes(source)
        expected = preflight.profile_source_hashes(source)
        self.assertEqual(len(products), 298)
        self.assertIn('custom_components/djconnect/artist_review_words.py', products)
        self.assertIn('custom_components/djconnect/surface_bootstrap_once.py', products)
        self.assertIn('custom_components/djconnect/surface_source_origin.py', products)
        self.assertIn('custom_components/djconnect/installation_principal_data.py', products)
        self.assertIn('custom_components/djconnect/installation_once_journal.py', products)
        self.assertIn('custom_components/djconnect/installation_custody_once.py', products)
        self.assertIn('custom_components/djconnect/installation_management.py', products)
        self.assertIn('custom_components/djconnect/direct_rich_wire.py', products)
        self.assertIn('custom_components/djconnect/direct_rich_store.py', products)
        self.assertIn('custom_components/djconnect/direct_rich_pair.py', products)
        self.assertIn('custom_components/djconnect/direct_rich_context.py', products)
        self.assertIn('custom_components/djconnect/host_wake_management.py', products)
        self.assertIn('custom_components/djconnect/host_wake_withdrawal.py', products)
        output = SimpleNamespace(returncode=0, stdout=json.dumps(valid(expected)).encode())
        with TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with patch.object(preflight.subprocess, 'run', return_value=output) as execute, \
                 patch.object(preflight, 'container_absent', return_value=True):
                self.assertEqual(preflight.run(source, directory / 'current'), 0)
                self.assertEqual(execute.call_count, 2)  # One probe plus owned cleanup.
            for size in (297, 299):
                with patch.object(preflight, 'product_hashes', return_value={str(i): 'a' * 64 for i in range(size)}), \
                     patch.object(preflight.subprocess, 'run') as execute:
                    with self.assertRaisesRegex(ValueError, 'preflight_source_or_owner_invalid'):
                        preflight.run(source, directory / str(size))
                    execute.assert_not_called()

    def test_paid_command_uses_private_lab_creator_without_relaxing_caps_or_secret_scope(self):
        marker = 'synthetic-credential-never-a-real-key'
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner.write_json(root / 'admission.json', {'coordinates': {}, 'product_hashes': {}})
            with patch.object(runner.subprocess, 'run', return_value=SimpleNamespace(returncode=1)) as execute, \
                 patch.object(runner, 'container_absent', return_value=True), \
                 patch.object(runner, 'finish_execution', return_value=1):
                self.assertEqual(runner.execute(root, root, {}, {}, None,
                    {'DJCONNECT_GOLDEN_OPENAI_API_KEY': marker}), 1)
            command = execute.call_args_list[0].args[0]
            owner = (root / 'private-work').stat().st_uid
            self.assertEqual(command[command.index('--user') + 1], f'{owner}:{os.getgid()}')
            self.assertEqual(command[command.index('--cap-drop') + 1], 'ALL')
            self.assertNotIn('--privileged', command)
            self.assertNotIn(marker, repr(command))
            self.assertEqual(json.loads((root / 'once-reservation.json').read_text())['state'],
                             'RESERVED_BEFORE_MODEL_SECRET_READ')
