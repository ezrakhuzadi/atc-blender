import unittest
from unittest.mock import patch

from common.redis_stream_operations import RedisStreamOperations


class FakeRedis:
    def __init__(self, hash_by_key):
        self._hash_by_key = dict(hash_by_key)
        self.scan_iter_called = False
        self.keys_called = False

    def scan_iter(self, match):  # noqa: ARG002
        self.scan_iter_called = True
        prefix = match.split("*", 1)[0]
        for key in self._hash_by_key.keys():
            if key.startswith(prefix):
                yield key

    def keys(self, _pattern):  # noqa: ARG002
        self.keys_called = True
        raise AssertionError("redis.keys should not be called when scan_iter is available")

    def hgetall(self, key):
        return self._hash_by_key.get(key, {})


class TestRedisStreamOperations(unittest.TestCase):
    def test_get_all_active_tracks_uses_scan_and_parses_observations(self):
        fake = FakeRedis(
            {
                "active_track:SESSION-1:ABC": {
                    "session_id": "SESSION-1",
                    "unique_aircraft_identifier": "ABC",
                    "last_updated_timestamp": "2026-01-01T00:00:00Z",
                    "observations": '[{"lat": 1}]',
                },
                "active_track:SESSION-1:DEF": {
                    "session_id": "SESSION-1",
                    "unique_aircraft_identifier": "DEF",
                    "last_updated_timestamp": "2026-01-01T00:00:01Z",
                    "observations": '[{"lat": 2}]',
                },
                "active_track:OTHER:ZZZ": {
                    "session_id": "OTHER",
                    "unique_aircraft_identifier": "ZZZ",
                    "last_updated_timestamp": "2026-01-01T00:00:02Z",
                    "observations": '[{"lat": 3}]',
                },
            }
        )

        with patch("common.redis_stream_operations.get_redis", return_value=fake):
            ops = RedisStreamOperations()

        tracks = ops.get_all_active_tracks_in_session("SESSION-1")

        self.assertTrue(fake.scan_iter_called)
        self.assertFalse(fake.keys_called)
        self.assertEqual({t.unique_aircraft_identifier for t in tracks}, {"ABC", "DEF"})
        for track in tracks:
            self.assertIsInstance(track.observations, list)
            self.assertIsInstance(track.observations[0], dict)

