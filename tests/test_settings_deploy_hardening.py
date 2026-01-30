import os
import subprocess
import sys
import unittest


class TestSettingsDeployHardening(unittest.TestCase):
    def test_security_settings_enabled_in_non_debug(self):
        env = os.environ.copy()
        env.update(
            {
                "IS_DEBUG": "0",
                "DJANGO_SECRET_KEY": "test-django-secret-key-abcdefghijklmnopqrstuvwxyz-0123456789",
            }
        )

        code = "\n".join(
            [
                "import flight_blender.settings as s",
                "assert s.SECURE_SSL_REDIRECT is True",
                "assert s.SESSION_COOKIE_SECURE is True",
                "assert s.CSRF_COOKIE_SECURE is True",
                "assert s.SECURE_HSTS_SECONDS > 0",
                "assert s.SECURE_HSTS_INCLUDE_SUBDOMAINS is True",
                "assert s.SECURE_HSTS_PRELOAD is True",
                "assert s.SECURE_CONTENT_TYPE_NOSNIFF is True",
                "assert s.SECURE_REFERRER_POLICY == 'strict-origin-when-cross-origin'",
                "assert s.X_FRAME_OPTIONS == 'DENY'",
            ]
        )

        result = subprocess.run(
            [sys.executable, "-c", code],
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            combined = (result.stdout or "") + (result.stderr or "")
            self.fail(combined)
