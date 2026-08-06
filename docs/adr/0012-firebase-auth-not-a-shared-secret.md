# 0012 — Firebase Auth ID tokens, not a shared secret

- **Status:** Accepted (supersedes the shared-secret part of ADR-0011)
- **Date:** 2026-08-06

## Context

The contest deployment authenticates with a single shared secret in an
`X-Intake-Key` header. Every endpoint behind it spends money on Vertex AI, so
the secret is the only thing between the public internet and a paid API.

A shared secret has three problems that get worse the moment there is a mobile
app:

1. **It cannot be shipped in a client.** Vite inlines `import.meta.env.*` at
   build time, so `VITE_API_KEY` would be readable in the JS bundle. The
   contest build works around this by making the reviewer type an access code
   — acceptable for judging, useless for customers.
2. **It has no identity.** `practitioner_id` is a string the client asserts. Any
   holder of the key can read or mutate any session by guessing its id, and
   per-practitioner memory rests on nothing.
3. **It cannot be revoked per user, and it cannot express entitlement.** A
   subscription product needs to know *who* is calling and *whether they have
   paid*, and one secret answers neither.

## Decision

Replace the shared secret with **Firebase Authentication**.

- The client signs in (Sign in with Apple, Google, or email) and receives a
  short-lived **Firebase ID token** — a JWT, expiring in an hour, refreshed by
  the SDK.
- The client sends `Authorization: Bearer <id_token>`.
- The server verifies with `firebase_admin.auth.verify_id_token()`, which checks
  signature, expiry, issuer and audience against Google's rotating public keys.
  Nothing about JWTs is hand-rolled and no OAuth flow is implemented by us.
- **`practitioner_id` becomes the token's `uid`**, established server-side. The
  client can no longer assert who it is.
- Every session document gains an owner, and reads and writes are checked
  against `uid` — closing the guess-any-session hole.
- Entitlement lives at `entitlements/{uid}` in Firestore, written by a
  **RevenueCat webhook**, and is checked before any turn runs. The client is
  never asked whether it has paid.
- Rate limiting moves from a per-key in-process window to a **per-`uid`
  Firestore counter**, so it survives instance recycling and is per customer.

Cloud Run stays `--allow-unauthenticated` at the IAM layer. That is not a
weakening: a browser or a phone cannot mint a Google identity token without a
Google Cloud principal, and the product's users are not GCP principals.
Authentication belongs in the application, at the identity we actually have.

## Consequences

The access-code field disappears from the UI. ADR-0011's residual risk — a code
that grants a stranger full use of a paid endpoint — disappears with it, since
a token is per user, expires hourly, and can be revoked.

ADR-0007 is unaffected and worth restating: `uid` identifies the **practitioner**,
never the interviewee. Nothing about the person being interviewed is stored,
before or after this change.

New operational dependencies: the Firebase Admin SDK server-side, and a webhook
endpoint that must verify RevenueCat's signature — an unauthenticated webhook
that grants entitlement is a free-subscription bug.

Sequenced so each step is independently useful, and safest first:

1. Firebase Auth verification replacing the shared secret. Deletes the current
   weakness on its own.
2. Session ownership by `uid`, and per-`uid` rate limiting.
3. RevenueCat webhook and the entitlement check. Last, because it is the only
   one whose absence costs nothing.
