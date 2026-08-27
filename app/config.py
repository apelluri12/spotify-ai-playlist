"""Validated application configuration loaded from the environment."""

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8000/auth/callback"


class AppSettings(BaseSettings):
    """Environment-backed settings required by the application."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        str_strip_whitespace=True,
    )

    spotify_client_id: str = Field(min_length=1)
    spotify_redirect_uri: AnyHttpUrl = AnyHttpUrl(LOCAL_SPOTIFY_REDIRECT_URI)

    @field_validator("spotify_redirect_uri")
    @classmethod
    def validate_spotify_redirect_uri(cls, uri: AnyHttpUrl) -> AnyHttpUrl:
        """Enforce Spotify's redirect rules and this app's callback route."""
        if uri.host == "localhost":
            raise ValueError("use an explicit loopback IP instead of localhost")

        loopback_hosts = {"127.0.0.1", "::1", "[::1]"}
        if uri.scheme == "http" and uri.host not in loopback_hosts:
            raise ValueError("HTTP redirect URIs must use an explicit loopback IP")

        if uri.path != "/auth/callback":
            raise ValueError("redirect URI path must be /auth/callback")

        if uri.query is not None or uri.fragment is not None:
            raise ValueError("redirect URI must not contain a query or fragment")

        return uri
