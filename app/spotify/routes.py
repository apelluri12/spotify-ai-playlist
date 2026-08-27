"""State management for Spotify OAuth routes.

The first authentication milestone runs as a single local process, so pending
OAuth attempts are kept in memory. This storage is intentionally temporary: it
is lost on restart and must be replaced before using multiple workers or running
in production.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass

_DEFAULT_STATE_TTL_SECONDS = 600.0


@dataclass(frozen=True, slots=True)
class _PendingAuthorization:
    code_verifier: str
    expires_at: float


class InMemoryOAuthStateStore:
    """Store short-lived, single-use OAuth state in the current process."""

    def __init__(
        self,
        *,
        ttl_seconds: float = _DEFAULT_STATE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")

        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._pending: dict[str, _PendingAuthorization] = {}

    def save(self, *, state: str, code_verifier: str) -> None:
        """Associate a verifier with an OAuth state until its expiry time."""
        self._pending[state] = _PendingAuthorization(
            code_verifier=code_verifier,
            expires_at=self._clock() + self._ttl_seconds,
        )

    def consume(self, *, state: str) -> str | None:
        """Remove a state and return its verifier only while it is valid."""
        pending = self._pending.pop(state, None)
        if pending is None:
            return None

        if pending.expires_at <= self._clock():
            return None

        return pending.code_verifier
