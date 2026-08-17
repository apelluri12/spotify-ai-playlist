import base64
import hashlib
import string

from app.spotify.auth import generate_pkce_challenge, generate_pkce_verifier

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
