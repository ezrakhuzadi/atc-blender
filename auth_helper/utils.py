import json
import threading
import time
from functools import wraps
from os import environ as env
from urllib.parse import urlparse

import jwt
import requests
from dotenv import find_dotenv, load_dotenv
from loguru import logger

load_dotenv(find_dotenv())

REQUEST_TIMEOUT_S = float(env.get("HTTP_TIMEOUT_S", "10"))
JWKS_CACHE_TTL_S = float(env.get("JWKS_CACHE_TTL_S", "300"))
JWKS_FETCH_BACKOFF_INITIAL_S = float(env.get("JWKS_FETCH_BACKOFF_INITIAL_S", "1"))
JWKS_FETCH_BACKOFF_MAX_S = float(env.get("JWKS_FETCH_BACKOFF_MAX_S", "60"))

_JWKS_CACHE_LOCK = threading.Lock()
_JWKS_CACHE = {}


class JwksFetchError(Exception):
    def __init__(self, url: str, message: str):
        super().__init__(message)
        self.url = url
        self.message = message


def _now_s() -> float:
    return time.time()


def _build_public_keys(jwks: dict) -> dict:
    keys = {}
    for jwk in jwks.get("keys", []):
        if not isinstance(jwk, dict):
            continue
        kid = jwk.get("kid")
        if not kid:
            continue
        try:
            keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
        except Exception as error:  # noqa: BLE001
            logger.warning(f"Skipping invalid JWK kid={kid}: {error}")
    return keys


def _get_jwks_cached(url: str, session: requests.Session, *, force_refresh: bool, required: bool, label: str) -> tuple[dict, dict]:
    now = _now_s()
    with _JWKS_CACHE_LOCK:
        entry = _JWKS_CACHE.get(url)
        if not entry:
            entry = {
                "jwks": None,
                "public_keys": {},
                "expires_at": 0.0,
                "next_retry_at": 0.0,
                "backoff_s": max(JWKS_FETCH_BACKOFF_INITIAL_S, 0.1),
            }
            _JWKS_CACHE[url] = entry

        jwks = entry.get("jwks")
        public_keys = entry.get("public_keys") or {}
        expires_at = float(entry.get("expires_at") or 0.0)
        next_retry_at = float(entry.get("next_retry_at") or 0.0)

        if not force_refresh and jwks and now < expires_at:
            return jwks, public_keys

        if not force_refresh and now < next_retry_at:
            if jwks:
                return jwks, public_keys
            if required:
                raise JwksFetchError(url, f"{label} JWKS fetch is in backoff and no cached keys exist.")
            return {}, {}

    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT_S)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("JWKS response was not a JSON object")
        public_keys = _build_public_keys(data)
        now = _now_s()
        with _JWKS_CACHE_LOCK:
            entry = _JWKS_CACHE[url]
            entry["jwks"] = data
            entry["public_keys"] = public_keys
            entry["expires_at"] = now + max(JWKS_CACHE_TTL_S, 0.0)
            entry["next_retry_at"] = 0.0
            entry["backoff_s"] = max(JWKS_FETCH_BACKOFF_INITIAL_S, 0.1)
        return data, public_keys
    except (requests.exceptions.RequestException, ValueError) as error:
        logger.error(f"Error fetching {label} JWKS: {error}")
        now = _now_s()
        with _JWKS_CACHE_LOCK:
            entry = _JWKS_CACHE[url]
            jwks = entry.get("jwks")
            public_keys = entry.get("public_keys") or {}
            backoff_s = float(entry.get("backoff_s") or max(JWKS_FETCH_BACKOFF_INITIAL_S, 0.1))
            entry["next_retry_at"] = now + backoff_s
            entry["backoff_s"] = min(backoff_s * 2.0, max(JWKS_FETCH_BACKOFF_MAX_S, backoff_s))
        if jwks:
            return jwks, public_keys
        if required:
            raise JwksFetchError(url, f"{label} JWKS could not be fetched and no cached keys exist.")
        return {}, {}

def jwt_get_username_from_payload_handler(payload):
    from django.contrib.auth import authenticate

    username = payload.get("sub").replace("|", ".")
    authenticate(remote_user=username)
    return username


def requires_scopes(required_scopes, allow_any: bool = False):
    """
    Decorator to enforce required scopes for accessing a view.

    Args:
        required_scopes (list): A list of scopes required to access the decorated view.

    Returns:
        function: The decorated function which checks for the required scopes.

    The decorator performs the following steps:
    1. Extracts the authorization token from the request headers.
    2. Verifies the token using the public keys from the JWKS endpoint.
    3. Decodes the token and checks if it contains the required scopes.
    4. If the token is valid and contains the required scopes, the original function is executed.
    5. If the token is invalid or does not contain the required scopes, an appropriate JSON response is returned.

    Raises:
        JsonResponse: If the authorization token is missing, invalid, or does not contain the required scopes.
    """

    s = requests.Session()

    def require_scope(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from django.http import JsonResponse

            API_IDENTIFIER = env.get("PASSPORT_AUDIENCE", "testflight.flightblender.com")
            BYPASS_AUTH_TOKEN_VERIFICATION = int(env.get("BYPASS_AUTH_TOKEN_VERIFICATION", 0))
            IS_DEBUG = int(env.get("IS_DEBUG", 0))
            PASSPORT_URL = env.get("PASSPORT_URL", "http://local.test:9000")
            DSS_AUTH_JWKS_ENDPOINT = env.get("DSS_AUTH_JWKS_ENDPOINT", "http://local.test:9000/.well-known/jwks.json")
            # remove the trailing slash if present
            if PASSPORT_URL.endswith("/"):
                PASSPORT_URL = PASSPORT_URL[:-1]
            PASSPORT_JWKS_URL = f"{PASSPORT_URL}/.well-known/jwks.json"

            request = args[0]
            auth = request.META.get("HTTP_AUTHORIZATION", None)
            if not auth or len(parts := auth.split()) <= 1:
                return JsonResponse(
                    {"detail": "Authentication credentials were not provided"},
                    status=401,
                )

            token = parts[1]
            try:
                unverified_token_headers = jwt.get_unverified_header(token)
            except jwt.DecodeError:
                return JsonResponse({"detail": "Bearer token could not be decoded properly"}, status=401)

            bypass_enabled = BYPASS_AUTH_TOKEN_VERIFICATION and IS_DEBUG
            if BYPASS_AUTH_TOKEN_VERIFICATION and not IS_DEBUG:
                logger.warning("BYPASS_AUTH_TOKEN_VERIFICATION is set but IS_DEBUG is false; ignoring bypass.")
            if bypass_enabled:
                return handle_bypass_verification(token, required_scopes, f, *args, **kwargs)

            try:
                _, passport_public_keys = _get_jwks_cached(
                    PASSPORT_JWKS_URL, s, force_refresh=False, required=True, label="Passport"
                )
            except JwksFetchError:
                return JsonResponse(
                    {"detail": f"Public Key Server necessary to validate the token could not be reached, tried to reach URL: {PASSPORT_JWKS_URL}"},
                    status=503,
                )
            try:
                _, dss_public_keys = _get_jwks_cached(DSS_AUTH_JWKS_ENDPOINT, s, force_refresh=False, required=False, label="DSS")
            except JwksFetchError:
                dss_public_keys = {}
                logger.info(
                    f"DSS Public Key Server necessary to validate the token could not be reached, tokens for DSS operations will not be validated, tried to reach URL:{DSS_AUTH_JWKS_ENDPOINT}"
                )
            public_keys = {**passport_public_keys, **dss_public_keys}

            kid = unverified_token_headers.get("kid")
            if not kid or kid not in public_keys:
                try:
                    _, passport_public_keys = _get_jwks_cached(
                        PASSPORT_JWKS_URL, s, force_refresh=True, required=True, label="Passport"
                    )
                    _, dss_public_keys = _get_jwks_cached(
                        DSS_AUTH_JWKS_ENDPOINT, s, force_refresh=True, required=False, label="DSS"
                    )
                    public_keys = {**passport_public_keys, **dss_public_keys}
                except JwksFetchError:
                    pass
                return JsonResponse(
                    {"detail": f"Error in parsing public keys, the signing key id {kid} is not present in JWKS"},
                    status=401,
                )

            public_key = public_keys[kid]
            try:
                decoded = jwt.decode(
                    token,
                    public_key,
                    audience=API_IDENTIFIER,
                    algorithms=["RS256"],
                    options={"require": ["exp", "iss", "aud"]},
                )
            except (
                jwt.ImmatureSignatureError,
                jwt.ExpiredSignatureError,
                jwt.InvalidAudienceError,
                jwt.InvalidIssuerError,
                jwt.InvalidSignatureError,
                jwt.DecodeError,
                jwt.exceptions.MissingRequiredClaimError,
            ) as token_error:
                logger.error(f"Token verification failed: {token_error}")
                return JsonResponse(
                    {"detail": "Invalid token", "error details": f"{token_error}"},
                    status=401,
                )
            decoded_scopes_set = set(decoded.get("scope", "").split())
            if (allow_any and decoded_scopes_set & set(required_scopes)) or set(required_scopes).issubset(decoded_scopes_set):
                return f(*args, **kwargs)

            return JsonResponse({"message": "You don't have access to this resource"}, status=403)

        return decorated

    return require_scope


def handle_bypass_verification(token, required_scopes, f, *args, **kwargs):
    from django.http import JsonResponse

    try:
        unverified_token_details = jwt.decode(token, algorithms=["RS256"], options={"verify_signature": False})
    except jwt.DecodeError:
        return JsonResponse({"detail": "Invalid token provided"}, status=401)
    decoded_scopes_set = set(unverified_token_details.get("scope", "").split())
    if not set(required_scopes).issubset(decoded_scopes_set):
        return JsonResponse({"message": "You don't have access to this resource"}, status=403)

    iss = unverified_token_details.get("iss")
    if not iss:
        return JsonResponse(
            {"detail": "Incomplete token provided, issuer (iss) claim must be present and should not be empty"},
            status=401,
        )
    if iss != "dummy":
        parsed_iss = urlparse(iss)
        if not (parsed_iss.scheme in ("http", "https") and parsed_iss.netloc):
            return JsonResponse({"detail": "Issuer (iss) claim is not a valid URL"}, status=401)

    if not unverified_token_details.get("aud"):
        return JsonResponse(
            {"detail": "Incomplete token provided, audience claim must be present and should not be empty"},
            status=401,
        )

    return f(*args, **kwargs)


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r
