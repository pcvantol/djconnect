"""Exercise runner routing without contacting GitHub or registering runners."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / 'scripts' / 'runner'


class MacOSRunnerRepositoryOwners(unittest.TestCase):
    def run_shell(self, body):
        prefix = '''set -e
SCRIPT_DIRECTORY="$1"
HOST_BOOTSTRAP_PACKAGE_DIRECTORY="$1/macos_host_bootstrap"
source "$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/config.sh"
source "$HOST_BOOTSTRAP_PACKAGE_DIRECTORY/runners.sh"
gh() { printf '%s\\n' "$*"; }
'''
        return subprocess.run(['/bin/bash', '-c', prefix + body, 'routing-test', str(RUNNER)],
                              capture_output=True, text=True, check=False)

    def test_registration_targets_current_repository_owners(self):
        expected = {
            'djconnect': 'pcvantol',
            'djconnect-app': 'djconnect-music-dj',
            'djconnect-esp32': 'djconnect-music-dj',
            'djconnect-pi': 'djconnect-music-dj',
            'djconnect-windows': 'djconnect-music-dj',
        }
        for repository, owner in expected.items():
            with self.subTest(repository=repository):
                result = self.run_shell(f'registration_token {repository}\n')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'repos/{owner}/{repository}/actions/runners/registration-token', result.stdout)

    def test_dry_run_uses_organization_for_moved_esp32(self):
        result = self.run_shell('''
DESIRED_PROFILES=(esp32)
require_desired_state_value() {
  case "$1" in
    profile.esp32.repository) printf %s djconnect-esp32 ;;
    profile.esp32.runner_name) printf %s example-esp32 ;;
    profile.esp32.labels) printf %s firmware,esp32 ;;
    profile.esp32.provisioning) printf %s local_macos ;;
  esac
}
log() { :; }
die() { printf %s "$*" >&2; exit 1; }
RUNNER_ROOT=/nonexistent-djconnect-routing-test
DRY_RUN=1
install_runner_profile esp32
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('djconnect-music-dj/djconnect-esp32', result.stdout)
        self.assertNotIn('api --method POST', result.stdout)

    def test_unknown_repository_cannot_request_a_registration_token(self):
        result = self.run_shell('registration_token unrelated-repo\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('registration-token', result.stdout)


if __name__ == '__main__':
    unittest.main()
