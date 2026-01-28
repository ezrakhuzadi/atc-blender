import unittest
from unittest.mock import patch

import requests

from auth_helper import utils


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def get(self, _url, timeout):  # noqa: ARG002
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class TestJwksCache(unittest.TestCase):
    def setUp(self):
        utils._JWKS_CACHE.clear()
        utils.JWKS_CACHE_TTL_S = 100.0
        utils.JWKS_FETCH_BACKOFF_INITIAL_S = 1.0
        utils.JWKS_FETCH_BACKOFF_MAX_S = 60.0

    def test_caches_within_ttl(self):
        session = FakeSession([FakeResponse({"keys": [{"kid": "k1"}]})])
        with patch.object(utils, "_now_s", side_effect=[1000.0, 1000.0, 1050.0]), patch.object(
            utils.jwt.algorithms.RSAAlgorithm, "from_jwk", return_value="PUB"
        ):
            _, keys1 = utils._get_jwks_cached(
                "http://jwks.example", session, force_refresh=False, required=True, label="Test"
            )
            _, keys2 = utils._get_jwks_cached(
                "http://jwks.example", session, force_refresh=False, required=True, label="Test"
            )

        self.assertEqual(session.calls, 1)
        self.assertEqual(keys1, {"k1": "PUB"})
        self.assertEqual(keys2, {"k1": "PUB"})

    def test_backoff_skips_fetch_when_no_cache(self):
        session = FakeSession([requests.exceptions.Timeout()])
        with patch.object(utils, "_now_s", side_effect=[1000.0, 1000.0, 1000.5]):
            with self.assertRaises(utils.JwksFetchError):
                utils._get_jwks_cached(
                    "http://jwks.example", session, force_refresh=False, required=True, label="Test"
                )
            with self.assertRaises(utils.JwksFetchError):
                utils._get_jwks_cached(
                    "http://jwks.example", session, force_refresh=False, required=True, label="Test"
                )

        self.assertEqual(session.calls, 1)

    def test_fetch_failure_returns_stale_cached_keys(self):
        session = FakeSession([FakeResponse({"keys": [{"kid": "k1"}]}), requests.exceptions.Timeout()])
        utils.JWKS_CACHE_TTL_S = 1.0
        with patch.object(utils, "_now_s", side_effect=[1000.0, 1000.0, 1002.0, 1002.0]), patch.object(
            utils.jwt.algorithms.RSAAlgorithm, "from_jwk", return_value="PUB"
        ):
            _, keys1 = utils._get_jwks_cached(
                "http://jwks.example", session, force_refresh=False, required=True, label="Test"
            )
            _, keys2 = utils._get_jwks_cached(
                "http://jwks.example", session, force_refresh=False, required=True, label="Test"
            )

        self.assertEqual(session.calls, 2)
        self.assertEqual(keys1, {"k1": "PUB"})
        self.assertEqual(keys2, {"k1": "PUB"})

    def test_force_refresh_bypasses_backoff(self):
        session = FakeSession([requests.exceptions.Timeout(), FakeResponse({"keys": [{"kid": "k1"}]})])
        with patch.object(utils, "_now_s", side_effect=[1000.0, 1000.0, 1000.5, 1000.5]), patch.object(
            utils.jwt.algorithms.RSAAlgorithm, "from_jwk", return_value="PUB"
        ):
            with self.assertRaises(utils.JwksFetchError):
                utils._get_jwks_cached(
                    "http://jwks.example", session, force_refresh=False, required=True, label="Test"
                )
            _, keys = utils._get_jwks_cached(
                "http://jwks.example", session, force_refresh=True, required=True, label="Test"
            )

        self.assertEqual(session.calls, 2)
        self.assertEqual(keys, {"k1": "PUB"})

