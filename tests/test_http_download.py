import unittest

from common.http_download import DownloadSettings, fetch_json_url


class _FakeResponse:
    def __init__(self, *, status_code: int, headers: dict[str, str] | None = None, body: bytes = b""):
        self.status_code = status_code
        self.headers = headers or {}
        self._body = body

    def iter_content(self, chunk_size: int = 65536):  # noqa: ARG002
        yield self._body


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse]):
        self._responses = list(responses)
        self.calls: list[str] = []

    def get(self, url, **_kwargs):  # noqa: ANN001
        self.calls.append(url)
        if not self._responses:
            raise RuntimeError("No more fake responses")
        return self._responses.pop(0)


class TestHttpDownload(unittest.TestCase):
    def test_rejects_localhost_without_request(self):
        class _BombSession:
            def get(self, *_args, **_kwargs):  # noqa: ANN001
                raise AssertionError("should not fetch")

        settings = DownloadSettings(allow_http=False, require_https=True)
        result = fetch_json_url("https://localhost/data.json", settings=settings, session=_BombSession())
        self.assertIsNone(result)

    def test_blocks_redirect_to_private_ip(self):
        session = _FakeSession(
            [
                _FakeResponse(status_code=302, headers={"Location": "https://127.0.0.1/evil"}),
            ]
        )
        settings = DownloadSettings(allow_http=False, require_https=True, max_redirects=3)
        result = fetch_json_url("https://93.184.216.34/redirect", settings=settings, session=session)
        self.assertIsNone(result)
        self.assertEqual(len(session.calls), 1)

    def test_follows_safe_redirect_and_parses_json(self):
        session = _FakeSession(
            [
                _FakeResponse(status_code=302, headers={"Location": "/final"}),
                _FakeResponse(
                    status_code=200,
                    headers={"Content-Type": "application/jwk-set+json"},
                    body=b'{"keys": []}',
                ),
            ]
        )
        settings = DownloadSettings(allow_http=False, require_https=True, max_redirects=3)
        result = fetch_json_url("https://93.184.216.34/redirect", settings=settings, session=session)
        self.assertEqual(result, {"keys": []})
        self.assertEqual(len(session.calls), 2)

    def test_enforces_max_download_bytes(self):
        session = _FakeSession(
            [
                _FakeResponse(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    body=b"0" * 20,
                ),
            ]
        )
        settings = DownloadSettings(allow_http=False, require_https=True, max_download_bytes=10)
        result = fetch_json_url("https://93.184.216.34/data.json", settings=settings, session=session)
        self.assertIsNone(result)

    def test_rejects_non_json_content_type(self):
        session = _FakeSession(
            [
                _FakeResponse(
                    status_code=200,
                    headers={"Content-Type": "text/html"},
                    body=b"<html></html>",
                ),
            ]
        )
        settings = DownloadSettings(allow_http=False, require_https=True)
        result = fetch_json_url("https://93.184.216.34/data.json", settings=settings, session=session)
        self.assertIsNone(result)

