"""Caller identity. Firebase is not installed in CI, so this pins the contract."""

import pytest
from fastapi import HTTPException

from intake_agent import auth


def test_an_access_code_caller_is_not_treated_as_an_identity():
    # The distinction the whole model rests on: a shared secret proves someone
    # holds a secret, not who they are. Session ownership must never key off it.
    caller = auth.Caller(practitioner_id="code:shared", method="access_code")
    assert caller.is_identified is False


def test_a_firebase_caller_is_an_identity():
    caller = auth.Caller(practitioner_id="uid-123", method="firebase")
    assert caller.is_identified is True


@pytest.mark.parametrize("header", [None, "", "Token abc", "Bearer", "bearer "])
def test_a_malformed_authorization_header_is_rejected(header):
    with pytest.raises(HTTPException) as exc:
        auth.verify_bearer_token(header)
    assert exc.value.status_code == 401


def test_firebase_is_off_until_it_is_configured():
    # Mode is chosen by configuration, never by a request. A client cannot talk
    # the server into the weaker path by sending a different header.
    assert auth.firebase_enabled() is (bool(auth.FIREBASE_PROJECT_ID))


def test_entitlement_is_unimplemented_rather_than_silently_permissive():
    # An entitlement check that returns None when there is no billing system is
    # a free-subscription bug waiting for the day billing arrives.
    with pytest.raises(NotImplementedError):
        auth.require_entitlement(
            auth.Caller(practitioner_id="uid-123", method="firebase"), store=None)
