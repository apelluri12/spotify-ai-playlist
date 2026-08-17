import asyncio
import base64
import hashlib
import string
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.spotify.auth import (
    SpotifyTokenError,
    TokenResponse,
    build_authorization_url,
    exchange_code_for_tokens,
    generate_oauth_state,
    generate_pkce_challenge,
    generate_pkce_verifier,
)

_UNRESERVED_CHARACTERS = set(string.ascii_letters + string.digits + "-._~")


def test_verifier_length_within_rfc_bounds() -> None:
    verifier = generate_pkce_verifier()
    assert 43 <= len(verifier) <= 128


def test_verifier_uses_only_unreserved_characters() -> None:
    verifier = generate_pkce_verifier()
    assert set(verifier) <= _UNRESERVED_CHARACTERS


def test_verifier_is_random_across_calls() -> None:
    assert generate_pkce_verifier() != generate_pkce_verifier()


def test_challenge_is_deterministic_for_a_given_verifier() -> None:
    verifier = "fixed-example-verifier-for-testing-purposes-only"
    assert generate_pkce_challenge(verifier) == generate_pkce_challenge(verifier)


def test_challenge_matches_s256_transformation() -> None:
    verifier = "fixed-example-verifier-for-testing-purposes-only"
    expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected_challenge = (
        base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode("ascii")
    )
    assert generate_pkce_challenge(verifier) == expected_challenge


def test_challenge_has_no_padding() -> None:
    verifier = generate_pkce_verifier()
    challenge = generate_pkce_challenge(verifier)
    assert "=" not in challenge


def test_state_is_random_across_calls() -> None:
    assert generate_oauth_state() != generate_oauth_state()


def test_state_uses_only_unreserved_characters() -> None:
    state = generate_oauth_state()
    assert set(state) <= _UNRESERVED_CHARACTERS


def test_authorization_url_targets_spotify_authorize_endpoint() -> None:
    url = build_authorization_url(
        client_id="test-client-id",
        redirect_uri="http://127.0.0.1:8000/auth/callback",
        state="test-state",
        code_challenge="test-challenge",
    )
    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == (
        "https://accounts.spotify.com/authorize"
    )


def test_authorization_url_includes_required_params() -> None:
    url = build_authorization_url(
        client_id="test-client-id",
        redirect_uri="http://127.0.0.1:8000/auth/callback",
        state="test-state",
        code_challenge="test-challenge",
    )
    query = parse_qs(urlsplit(url).query)

    assert query["client_id"] == ["test-client-id"]
    assert query["response_type"] == ["code"]
    assert query["redirect_uri"] == ["http://127.0.0.1:8000/auth/callback"]
    assert query["state"] == ["test-state"]
    assert query["code_challenge"] == ["test-challenge"]
    assert query["code_challenge_method"] == ["S256"]


def test_authorization_url_defaults_to_least_privilege_scope() -> None:
    url = build_authorization_url(
        client_id="test-client-id",
        redirect_uri="http://127.0.0.1:8000/auth/callback",
        state="test-state",
        code_challenge="test-challenge",
    )
    query = parse_qs(urlsplit(url).query)
    assert query["scope"] == ["playlist-modify-private"]


def test_authorization_url_accepts_explicit_scope() -> None:
    url = build_authorization_url(
        client_id="test-client-id",
        redirect_uri="http://127.0.0.1:8000/auth/callback",
        state="test-state",
        code_challenge="test-challenge",
        scope="playlist-modify-private playlist-read-private",
    )
    query = parse_qs(urlsplit(url).query)
    assert query["scope"] == ["playlist-modify-private playlist-read-private"]


def _run(coro):
    return asyncio.run(coro)


async def _exchange_with_handler(handler, **overrides) -> TokenResponse:
    kwargs = {
        "code": "test-code",
        "redirect_uri": "http://127.0.0.1:8000/auth/callback",
        "client_id": "test-client-id",
        "code_verifier": "test-verifier",
        **overrides,
    }
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await exchange_code_for_tokens(http_client=client, **kwargs)


def test_exchange_code_for_tokens_returns_validated_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/token"
        return httpx.Response(
            200,
            json={
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "playlist-modify-private",
            },
        )

    result = _run(_exchange_with_handler(handler))

    assert isinstance(result, TokenResponse)
    assert result.access_token == "test-access-token"
    assert result.refresh_token == "test-refresh-token"
    assert result.expires_in == 3600
    assert result.token_type == "Bearer"


def test_exchange_code_for_tokens_sends_correct_request_body() -> None:
    captured: dict[str, list[str]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(parse_qs(request.content.decode()))
        return httpx.Response(
            200,
            json={
                "access_token": "a",
                "refresh_token": "r",
                "expires_in": 1,
                "token_type": "Bearer",
            },
        )

    _run(_exchange_with_handler(handler))

    assert captured["grant_type"] == ["authorization_code"]
    assert captured["code"] == ["test-code"]
    assert captured["redirect_uri"] == ["http://127.0.0.1:8000/auth/callback"]
    assert captured["client_id"] == ["test-client-id"]
    assert captured["code_verifier"] == ["test-verifier"]


def test_exchange_code_for_tokens_raises_on_failure_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    with pytest.raises(SpotifyTokenError, match="invalid_grant"):
        _run(_exchange_with_handler(handler))


def test_exchange_code_for_tokens_error_does_not_leak_sensitive_values() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant"})

    with pytest.raises(SpotifyTokenError) as exc_info:
        _run(
            _exchange_with_handler(
                handler,
                code="super-secret-code",
                code_verifier="super-secret-verifier",
            )
        )

    message = str(exc_info.value)
    assert "super-secret-code" not in message
    assert "super-secret-verifier" not in message
