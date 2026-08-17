"""PKCE (Proof Key for Code Exchange) helpers for Spotify's Authorization Code flow.

These functions are pure: no I/O, no network calls, no logging. Keeping them
side-effect-free makes them trivial to unit test and keeps the verifier itself
out of any log line by construction. See RFC 7636 for the underlying spec.
"""

import base64
import hashlib
import secrets

# RFC 7636 requires the code_verifier to be 43-128 characters, drawn from
# [A-Z] [a-z] [0-9] "-" "." "_" "~". secrets.token_urlsafe already produces a
# subset of that character set, so we only need to pick a byte length that
# lands the encoded output in range. 64 bytes -> ~86 characters.
_VERIFIER_BYTES = 64


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
