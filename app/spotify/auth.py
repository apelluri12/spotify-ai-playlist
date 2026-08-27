"""PKCE (Proof Key for Code Exchange) helpers for Spotify's Authorization Code flow.

These functions are pure: no I/O, no network calls, no logging. Keeping them
side-effect-free makes them trivial to unit test and keeps the verifier itself
out of any log line by construction. See RFC 7636 for the underlying spec.
"""

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

# RFC 7636 requires the code_verifier to be 43-128 characters, drawn from
# [A-Z] [a-z] [0-9] "-" "." "_" "~". secrets.token_urlsafe already produces a
# subset of that character set, so we only need to pick a byte length that
# lands the encoded output in range. 64 bytes -> ~86 characters.
_VERIFIER_BYTES = 64

# 32 bytes of entropy is plenty for a CSRF token; state doesn't need to meet
# PKCE's length requirements since it isn't part of the RFC 7636 exchange.
_STATE_BYTES = 32

_AUTHORIZE_ENDPOINT = "https://accounts.spotify.com/authorize"
_TOKEN_ENDPOINT = "https://accounts.spotify.com/api/token"

# Explicit connect/read timeouts, per CLAUDE.md: never let an external call
# hang indefinitely.
_HTTP_TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# Least-privilege default: only what's needed for the current milestone
# (creating and adding tracks to private playlists). Widen this deliberately,
# not by accident, as later features need more.
DEFAULT_SCOPE = "playlist-modify-private"


def generate_pkce_verifier() -> str:
    """Generate a cryptographically random PKCE code verifier.

    Returns a URL-safe string between 43 and 128 characters, per RFC 7636.
    A fresh verifier must be generated for every login attempt; never reuse
    one across requests.
    """
    return secrets.token_urlsafe(_VERIFIER_BYTES)


def generate_pkce_challenge(verifier: str) -> str:
    """Derive the S256 PKCE code challenge for a given verifier.

    Hashes the verifier with SHA-256 and returns the digest as unpadded
    base64url text, per RFC 7636's S256 transformation. This is what gets
    sent when starting the login; the verifier itself is sent later, only
    when exchanging the authorization code for a token.
    """
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def generate_oauth_state() -> str:
    """Generate a cryptographically random, single-use OAuth state value.

    A fresh state must be generated for every login attempt, stored
    server-side alongside an expiry, and invalidated immediately once the
    callback validates it. This function only produces the value; storing,
    expiring, and single-use enforcement happen where the login route is
    implemented, not here.
    """
    return secrets.token_urlsafe(_STATE_BYTES)


def build_authorization_url(
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    scope: str = DEFAULT_SCOPE,
) -> str:
    """Build the Spotify authorization URL for the Authorization Code + PKCE flow.

    Pure string construction: no network calls. Callers must generate and
    persist `state` and the PKCE pair before calling this, and must validate
    `state` on the callback before proceeding with the token exchange.
    """
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    }
    return f"{_AUTHORIZE_ENDPOINT}?{urlencode(params)}"


class SpotifyTokenError(Exception):
    """Raised when Spotify's token endpoint rejects the exchange.

    The message intentionally carries only the HTTP status and Spotify's
    short error code (e.g. "invalid_grant") — never the authorization code,
    the PKCE verifier, or any token, since exception messages can end up in
    logs or client-visible error responses.
    """


class TokenResponse(BaseModel):
    """Validated shape of a successful response from Spotify's token endpoint.

    This is a system boundary: the payload comes from an external service,
    so it's parsed into a typed model rather than passed around as a raw
    dict with `.get()` calls scattered at every use site.
    """

    access_token: str
    refresh_token: str | None = None
    expires_in: int
    token_type: str
    scope: str | None = None


def _extract_error_code(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return "unknown_error"
    return body.get("error", "unknown_error") if isinstance(body, dict) else "unknown_error"


async def exchange_code_for_tokens(
    *,
    code: str,
    redirect_uri: str,
    client_id: str,
    code_verifier: str,
    http_client: httpx.AsyncClient,
) -> TokenResponse:
    """Exchange an authorization code for an access/refresh token pair.

    Uses PKCE: `code_verifier` is sent instead of a client secret, proving
    this request comes from the app that started the login. `http_client`
    is injected rather than created here so tests can supply a mocked
    transport instead of making a real network call, and so the caller
    controls the client's lifecycle.

    Raises SpotifyTokenError if Spotify rejects the exchange.
    """
    response = await http_client.post(
        _TOKEN_ENDPOINT,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": code_verifier,
        },
        timeout=_HTTP_TIMEOUT,
    )

    if response.status_code != 200:
        raise SpotifyTokenError(
            f"Spotify token exchange failed with status {response.status_code}: "
            f"{_extract_error_code(response)}"
        )

    return TokenResponse.model_validate(response.json())
