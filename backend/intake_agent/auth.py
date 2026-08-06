"""Caller identity.

Two modes, one interface. Which one runs is decided by configuration, never by
a request — a header can't talk the server into the weaker one.

- **Access code** (contest): a shared secret in `X-Intake-Key`. No identity; the
  caller is recorded as `code:shared`. Documented in ADR-0011.
- **Firebase ID token** (ADR-0012): `Authorization: Bearer <token>`, verified by
  the Firebase Admin SDK. `uid` becomes the practitioner id — established
  server-side, not asserted by the client.

Nothing here is hand-rolled crypto. `verify_id_token` checks signature, expiry,
issuer and audience against Google's rotating keys; writing that ourselves would
be the mistake.

Enable by setting `FIREBASE_PROJECT_ID` and installing `firebase-admin`. Until
then the access-code path stays in force, so this module is inert rather than
half-on.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from fastapi import HTTPException

log = logging.getLogger(__name__)

FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "")


@dataclass(frozen=True)
class Caller:
    """Who is making this request, as far as the server can prove."""

    practitioner_id: str
    method: str  # "firebase" | "access_code"
    email_verified: bool = False

    @property
    def is_identified(self) -> bool:
        """True when a real per-user identity was proved.

        Session ownership and entitlement checks must require this. The
        access-code path deliberately returns False: one secret shared by
        everyone is not an identity, and treating it as one would let any
        holder read any session.
        """
        return self.method == "firebase"


def firebase_enabled() -> bool:
    return bool(FIREBASE_PROJECT_ID)


def verify_bearer_token(authorization: str | None) -> Caller:
    """Verify a Firebase ID token and return the caller it identifies."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    # "Bearer " with nothing after it passes the prefix check but carries no
    # token; without this it reaches verify_id_token as an empty string.
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="missing bearer token")

    try:
        from firebase_admin import auth as fb_auth  # imported lazily
    except ImportError:  # pragma: no cover - depends on deployment extras
        log.error("FIREBASE_PROJECT_ID is set but firebase-admin is not installed")
        raise HTTPException(status_code=500, detail="auth not configured") from None

    try:
        # check_revoked costs a round trip and is what makes "sign out
        # everywhere" and account disable actually take effect.
        decoded = fb_auth.verify_id_token(token, check_revoked=True)
    except Exception as exc:
        # Deliberately vague to the caller: which of expired, malformed,
        # wrong-audience or revoked it was is useful only to an attacker.
        log.info("rejected id token: %s", type(exc).__name__)
        raise HTTPException(status_code=401, detail="invalid token") from None

    uid = decoded.get("uid") or decoded.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="token carries no subject")

    return Caller(
        practitioner_id=uid,
        method="firebase",
        email_verified=bool(decoded.get("email_verified")),
    )


def require_entitlement(caller: Caller, store) -> None:
    """Refuse a turn unless this practitioner's subscription is active.

    Read from `entitlements/{uid}`, which only the RevenueCat webhook writes.
    The client is never asked whether it has paid — a client that answers that
    question is a client that lies about it.

    Not wired up yet: no billing exists. Present so the check has one home when
    it does, rather than being sprinkled through the endpoints.
    """
    raise NotImplementedError(
        "entitlement checks land with the RevenueCat webhook; see ADR-0012"
    )
