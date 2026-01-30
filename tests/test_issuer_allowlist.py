import os
import sys
import types
import unittest
from unittest.mock import patch

from auth_helper import utils


class JsonResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status_code = status


class DummyRequest:
    def __init__(self, authorization: str):
        self.META = {"HTTP_AUTHORIZATION": authorization}


class DjangoStub:
    def __init__(self):
        self._original = {}

    def __enter__(self):
        django = types.ModuleType("django")
        django_http = types.ModuleType("django.http")
        django_http.JsonResponse = JsonResponse
        django.http = django_http

        for name, module in {"django": django, "django.http": django_http}.items():
            self._original[name] = sys.modules.get(name)
            sys.modules[name] = module
        return self

    def __exit__(self, exc_type, exc, tb):
        for name, previous in self._original.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
        return False


class TestIssuerAllowlist(unittest.TestCase):
    def test_requires_scopes_rejects_wrong_issuer(self):
        env_overrides = {
            "PASSPORT_AUDIENCE": "aud",
            "PASSPORT_URL": "https://passport.example",
            "PASSPORT_ISSUER": "https://passport.example",
            "DSS_AUTH_JWKS_ENDPOINT": "https://dss.example/.well-known/jwks.json",
            "DSS_AUTH_ISSUER": "https://dss.example",
            "IS_DEBUG": "0",
            "BYPASS_AUTH_TOKEN_VERIFICATION": "0",
        }

        with DjangoStub(), patch.dict(os.environ, env_overrides, clear=False):
            decorator = utils.requires_scopes(["scope1"])

            @decorator
            def handler(_request):  # noqa: ARG001
                return "OK"

            request = DummyRequest("Bearer token")

            with (
                patch.object(utils.jwt, "get_unverified_header", return_value={"kid": "k1"}),
                patch.object(
                    utils,
                    "_get_jwks_cached",
                    side_effect=[({}, {"k1": "PUB"}), ({}, {})],
                ),
                patch.object(
                    utils.jwt,
                    "decode",
                    return_value={
                        "iss": "https://evil.example",
                        "aud": "aud",
                        "exp": 9999999999,
                        "scope": "scope1",
                    },
                ),
            ):
                response = handler(request)

        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data.get("detail"), "Invalid token issuer")

    def test_requires_scopes_allows_allowed_issuer(self):
        env_overrides = {
            "PASSPORT_AUDIENCE": "aud",
            "PASSPORT_URL": "https://passport.example",
            "PASSPORT_ISSUER": "https://passport.example",
            "DSS_AUTH_JWKS_ENDPOINT": "https://dss.example/.well-known/jwks.json",
            "DSS_AUTH_ISSUER": "https://dss.example",
            "IS_DEBUG": "0",
            "BYPASS_AUTH_TOKEN_VERIFICATION": "0",
        }

        with DjangoStub(), patch.dict(os.environ, env_overrides, clear=False):
            decorator = utils.requires_scopes(["scope1"])

            @decorator
            def handler(_request):  # noqa: ARG001
                return "OK"

            request = DummyRequest("Bearer token")

            with (
                patch.object(utils.jwt, "get_unverified_header", return_value={"kid": "k1"}),
                patch.object(
                    utils,
                    "_get_jwks_cached",
                    side_effect=[({}, {"k1": "PUB"}), ({}, {})],
                ),
                patch.object(
                    utils.jwt,
                    "decode",
                    return_value={
                        "iss": "https://passport.example/",
                        "aud": "aud",
                        "exp": 9999999999,
                        "scope": "scope1",
                    },
                ),
            ):
                response = handler(request)

        self.assertEqual(response, "OK")

