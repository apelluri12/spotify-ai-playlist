from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import AppSettings, LOCAL_SPOTIFY_REDIRECT_URI


def test_settings_load_client_id_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test-client-id")

    settings = AppSettings(_env_file=None)

    assert settings.spotify_client_id == "test-client-id"


def test_settings_use_local_redirect_uri_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SPOTIFY_REDIRECT_URI", raising=False)

    settings = AppSettings(spotify_client_id="test-client-id", _env_file=None)

    assert str(settings.spotify_redirect_uri) == LOCAL_SPOTIFY_REDIRECT_URI


def test_settings_load_from_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_REDIRECT_URI", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "SPOTIFY_CLIENT_ID=file-client-id\n"
        "SPOTIFY_REDIRECT_URI=http://127.0.0.1:8000/auth/callback\n",
        encoding="utf-8",
    )

    settings = AppSettings(_env_file=env_file)

    assert settings.spotify_client_id == "file-client-id"


def test_settings_reject_missing_client_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)

    with pytest.raises(ValidationError, match="spotify_client_id"):
        AppSettings(_env_file=None)


def test_settings_reject_blank_client_id() -> None:
    with pytest.raises(ValidationError, match="spotify_client_id"):
        AppSettings(spotify_client_id="   ", _env_file=None)


def test_settings_reject_localhost_redirect_uri() -> None:
    with pytest.raises(ValidationError, match="explicit loopback IP"):
        AppSettings(
            spotify_client_id="test-client-id",
            spotify_redirect_uri="http://localhost:8000/auth/callback",
            _env_file=None,
        )


def test_settings_reject_insecure_non_loopback_redirect_uri() -> None:
    with pytest.raises(ValidationError, match="HTTP redirect URIs"):
        AppSettings(
            spotify_client_id="test-client-id",
            spotify_redirect_uri="http://example.com/auth/callback",
            _env_file=None,
        )


@pytest.mark.parametrize(
    "redirect_uri",
    [
        "http://127.0.0.1:8000/wrong-path",
        "http://127.0.0.1:8000/auth/callback?source=test",
        "http://127.0.0.1:8000/auth/callback#fragment",
    ],
)
def test_settings_reject_redirect_uri_that_cannot_match_callback_route(
    redirect_uri: str,
) -> None:
    with pytest.raises(ValidationError):
        AppSettings(
            spotify_client_id="test-client-id",
            spotify_redirect_uri=redirect_uri,
            _env_file=None,
        )


def test_settings_allow_https_redirect_uri_for_future_deployment() -> None:
    settings = AppSettings(
        spotify_client_id="test-client-id",
        spotify_redirect_uri="https://playlist.example.com/auth/callback",
        _env_file=None,
    )

    assert str(settings.spotify_redirect_uri) == (
        "https://playlist.example.com/auth/callback"
    )
