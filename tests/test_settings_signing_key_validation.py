import os
import subprocess
import sys
import unittest


class TestSettingsSigningKeyValidation(unittest.TestCase):
    def test_invalid_signing_key_fails_startup(self):
        env = os.environ.copy()
        env["IS_DEBUG"] = "1"
        env["DJANGO_SECRET_KEY"] = "test-django-secret-key"
        env["OIDC_SIGNING_PRIVATE_KEY_PEM"] = "not-a-pem"

        result = subprocess.run(
            [sys.executable, "-c", "import flight_blender.settings"],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OIDC_SIGNING_PRIVATE_KEY_PEM", (result.stdout or "") + (result.stderr or ""))

