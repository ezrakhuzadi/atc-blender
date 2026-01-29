import os
import subprocess
import sys
import unittest


class TestSettingsDjangoSecretKeyValidation(unittest.TestCase):
    def run_settings_import(self, extra_env):
        env = os.environ.copy()
        env.update(extra_env)
        return subprocess.run(
            [sys.executable, "-c", "import flight_blender.settings"],
            env=env,
            capture_output=True,
            text=True,
        )

    def test_placeholder_secret_key_fails_in_non_debug(self):
        result = self.run_settings_import(
            {
                "IS_DEBUG": "0",
                "DJANGO_SECRET_KEY": "change-me-flight-blender-secret-key",
            }
        )
        self.assertNotEqual(result.returncode, 0)
        combined = (result.stdout or "") + (result.stderr or "")
        self.assertIn("DJANGO_SECRET_KEY", combined)

    def test_short_secret_key_fails_in_non_debug(self):
        result = self.run_settings_import(
            {
                "IS_DEBUG": "0",
                "DJANGO_SECRET_KEY": "too-short",
            }
        )
        self.assertNotEqual(result.returncode, 0)
        combined = (result.stdout or "") + (result.stderr or "")
        self.assertIn("DJANGO_SECRET_KEY", combined)

