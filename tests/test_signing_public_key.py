import os
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class TestSigningPublicKey(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("IS_DEBUG", "1")
        os.environ.setdefault("DJANGO_SECRET_KEY", "test-django-secret-key")
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flight_blender.settings")

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")
        os.environ["OIDC_SIGNING_PRIVATE_KEY_PEM"] = pem

        import django
        from django.apps import apps

        if not apps.ready:
            django.setup()

    def test_signing_public_key_returns_jwks(self):
        from django.test import Client

        response = Client().get("/signing_public_key")
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertIn("keys", payload)
        self.assertIsInstance(payload["keys"], list)
        self.assertGreaterEqual(len(payload["keys"]), 1)

        jwk = payload["keys"][0]
        for field in ("kid", "kty", "n", "e"):
            self.assertIn(field, jwk)

        self.assertEqual(response["Access-Control-Allow-Origin"], "*")

