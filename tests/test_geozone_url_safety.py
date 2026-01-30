import socket
import unittest
from unittest.mock import patch

from geo_fence_operations.url_safety import validate_public_url


class TestGeoZoneUrlSafety(unittest.TestCase):
    def test_rejects_localhost(self):
        ok, reason = validate_public_url("https://localhost/data.json", allow_http=False, require_https=True)
        self.assertFalse(ok)
        self.assertEqual(reason, "localhost_not_allowed")

    def test_rejects_link_local_metadata_ip(self):
        ok, reason = validate_public_url("https://169.254.169.254/latest/meta-data", allow_http=False, require_https=True)
        self.assertFalse(ok)
        self.assertEqual(reason, "ip_not_allowed")

    def test_rejects_userinfo(self):
        ok, reason = validate_public_url("https://user:pass@example.com/data.json", allow_http=False, require_https=True)
        self.assertFalse(ok)
        self.assertEqual(reason, "userinfo_not_allowed")

    def test_rejects_http_when_https_required(self):
        ok, reason = validate_public_url("http://example.com/data.json", allow_http=False, require_https=True)
        self.assertFalse(ok)
        self.assertEqual(reason, "https_required")

    def test_rejects_domain_resolving_to_private_ip(self):
        fake_result = [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("10.0.0.5", 443)),
        ]
        with patch("geo_fence_operations.url_safety.socket.getaddrinfo", return_value=fake_result):
            ok, reason = validate_public_url("https://evil.example/data.json", allow_http=False, require_https=True)
        self.assertFalse(ok)
        self.assertEqual(reason, "resolved_ip_not_allowed")

    def test_allows_https_public_domain(self):
        fake_result = [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443)),
        ]
        with patch("geo_fence_operations.url_safety.socket.getaddrinfo", return_value=fake_result):
            ok, reason = validate_public_url("https://example.com/data.json", allow_http=False, require_https=True)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

