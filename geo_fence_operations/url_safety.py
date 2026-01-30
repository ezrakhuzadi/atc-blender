import ipaddress
import socket
from urllib.parse import urlparse


def _looks_like_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _is_disallowed_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False

    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _resolved_ips(host: str, port: int) -> set[str]:
    infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    ips: set[str] = set()
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip = sockaddr[0]
        if ip:
            ips.add(ip)
    return ips


def validate_public_url(
    url: str, *, allow_http: bool = False, require_https: bool = True
) -> tuple[bool, str]:
    """
    Validate a URL for safe fetching.

    This is used to prevent SSRF primitives (localhost/private networks/link-local/metadata).
    """

    try:
        parsed = urlparse(url)
    except ValueError:
        return False, "invalid_url"

    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        return False, "unsupported_scheme"
    if require_https and scheme != "https" and not allow_http:
        return False, "https_required"
    if scheme == "http" and not allow_http:
        return False, "http_not_allowed"

    if not parsed.netloc:
        return False, "missing_host"
    if parsed.username or parsed.password:
        return False, "userinfo_not_allowed"

    host = parsed.hostname
    if not host:
        return False, "missing_host"
    host = host.strip().lower()
    if host in {"localhost"}:
        return False, "localhost_not_allowed"

    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80

    if _looks_like_ip(host) and _is_disallowed_ip(host):
        return False, "ip_not_allowed"

    try:
        ips = _resolved_ips(host, port)
    except socket.gaierror:
        return False, "dns_failed"

    if not ips:
        return False, "dns_failed"

    for ip in ips:
        if _is_disallowed_ip(ip):
            return False, "resolved_ip_not_allowed"

    return True, ""

