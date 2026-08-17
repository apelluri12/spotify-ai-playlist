import pytest

from app.spotify.routes import InMemoryOAuthStateStore


class FakeClock:
    def __init__(self, initial_time: float = 0.0) -> None:
        self.current_time = initial_time

    def __call__(self) -> float:
        return self.current_time

    def advance(self, seconds: float) -> None:
        self.current_time += seconds


def test_consume_returns_verifier_for_valid_state() -> None:
    store = InMemoryOAuthStateStore()
    store.save(state="valid-state", code_verifier="valid-verifier")

    assert store.consume(state="valid-state") == "valid-verifier"


def test_consumed_state_cannot_be_replayed() -> None:
    store = InMemoryOAuthStateStore()
    store.save(state="single-use-state", code_verifier="single-use-verifier")

    store.consume(state="single-use-state")

    assert store.consume(state="single-use-state") is None


def test_unknown_state_returns_none() -> None:
    store = InMemoryOAuthStateStore()

    assert store.consume(state="unknown-state") is None


def test_expired_state_returns_none_without_waiting() -> None:
    clock = FakeClock()
    store = InMemoryOAuthStateStore(ttl_seconds=10.0, clock=clock)
    store.save(state="expired-state", code_verifier="expired-verifier")

    clock.advance(10.0)

    assert store.consume(state="expired-state") is None
    assert store.consume(state="expired-state") is None


def test_default_ttl_is_ten_minutes() -> None:
    clock = FakeClock()
    store = InMemoryOAuthStateStore(clock=clock)
    store.save(state="still-valid", code_verifier="valid-verifier")
    store.save(state="now-expired", code_verifier="expired-verifier")

    clock.advance(599.0)
    assert store.consume(state="still-valid") == "valid-verifier"

    clock.advance(1.0)
    assert store.consume(state="now-expired") is None


def test_non_positive_ttl_is_rejected() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        InMemoryOAuthStateStore(ttl_seconds=0.0)


def test_states_are_stored_independently() -> None:
    store = InMemoryOAuthStateStore()
    store.save(state="first-state", code_verifier="first-verifier")
    store.save(state="second-state", code_verifier="second-verifier")

    assert store.consume(state="second-state") == "second-verifier"
    assert store.consume(state="first-state") == "first-verifier"
