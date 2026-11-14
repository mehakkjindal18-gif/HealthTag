# HealthTag–Maritime–Prune Integration Contract (Draft)

**Status:** Design proposal only. No runtime integration is implemented by this document.
**Base:** `main` as inspected on 14 November 2026.
**Scope:** Define safe boundaries for future operational automation (Maritime) and AI-assisted workflows (Prune), without changing HealthTag authentication or emergency-access behaviour.

## 1. Current repository facts

The current `main` application is a Flask + SQLite system. Its existing data structures include:

- `profiles`: patient profile and emergency-contact fields.
- `records`: hospital treatment notes (`profile_id`, timestamp, author, organisation, note).
- `events`: audit events (`profile_id`, timestamp, tier, actor, action, detail).
- `requests`: emergency full-history requests and approval state.
- `professionals`: professional credential ID, name, organisation and PIN hash.
- `notifications`: in-app notification records, recipient type/ID, optional profile ID, title/body, creation time, push status/submission time and read time.
- `push_subscriptions`: browser push endpoints and encrypted key material associated with the current recipient type/ID.

Current code uses patient profile IDs as patient notification recipients and professional credential IDs as professional notification recipients. The repository also has an existing professional session and an owner authentication helper/flow. A teammate is building the next login system; therefore these current identifiers are **temporary integration facts**, not the final external identity contract.

The current event table uses a free-text `action` and `detail`, not a versioned event schema. There is no confirmed transactional outbox or external webhook contract in the inspected `main` code.

No Maritime or Prune runtime integration was found on `main`. The branch `feature/maritime-notification-agent` is 57 commits behind `main` and has no unique commits ahead at the time of inspection; do not use it as an integration base.

## 2. System responsibilities

### HealthTag — system of record

HealthTag remains authoritative for:
- Patient profiles and medical records.
- Professional verification and authentication.
- Emergency-access tiers and time-limited grants.
- Emergency-contact approval or denial.
- Audit history and notification history.
- Consent, role and resource-level access checks.

External systems must not directly write to HealthTag's SQLite database or bypass its application APIs.

### Maritime — deterministic operations and orchestration

Candidate responsibilities:
- Run scheduled, rule-based reminders after HealthTag defines eligibility and timing.
- Coordinate operational tasks such as hospital onboarding follow-ups and support-ticket routing.
- Retry transient delivery failures with bounded backoff and idempotency.
- Report job outcomes to HealthTag.
- Trigger approved workflows through narrow, authenticated HealthTag endpoints.

Maritime should not independently determine medical urgency, diagnose, grant access, approve an emergency request, or edit medical records.

### Prune — AI assistance

Prune may assist with language and administrative tasks, subject to an explicitly approved model/provider and data policy:
- Multilingual explanations of HealthTag's non-diagnostic product workflows.
- Drafting administrative responses for human review.
- Extracting candidate fields from user-submitted documents into a proposed draft.
- Classifying support requests and suggesting the next administrative queue.

Prune must not diagnose, recommend treatment as a clinician, change a medical record, verify a professional, approve/deny access, or send an emergency-contact approval on its own. AI-generated output must be labelled and reviewed where it could affect a person's care or access.

The exact Prune API, deployment model, and data-handling terms are not specified in this repository. No integration should be implemented until these are selected and reviewed.

## 3. Identity contract — blocked on the login project

Do not make patient profile IDs or professional credential IDs the permanent cross-system identity.

After the login project is agreed, HealthTag should expose a stable opaque internal principal ID and role claims:
- `principal_id`: stable opaque ID, not a phone number, email, credential number or patient profile ID.
- `role`: patient, professional, hospital_admin, support_agent, or another explicitly authorised role.
- `profile_ids`: resource associations authorised by HealthTag, not blanket access.
- `organisation_id`: where relevant, assigned and verified by HealthTag.
- `scopes`: narrow permissions for the specific operation.

A principal may have multiple devices and may be associated with more than one permitted resource. Logout, account recovery, role changes, professional deactivation and hospital affiliation changes must have defined subscription/session revocation behaviour.

**Integration gate:** the login teammate must confirm the identity model, token/session format, issuer/audience, expiry, revocation strategy, and role/resource-authorization API before external services are connected.

## 4. Event contract proposal

Use a versioned, typed event envelope rather than forwarding free-text rows from `events` or `notifications`.

Example envelope (illustrative; not an implemented API):

```json
{
  "event_id": "opaque-unique-id",
  "event_type": "healthtag.emergency_access.requested",
  "schema_version": 1,
  "occurred_at": "2026-11-14T10:00:00Z",
  "actor_principal_id": "opaque-id",
  "subject_principal_id": "opaque-id",
  "resource_ref": "opaque-resource-id",
  "correlation_id": "opaque-id",
  "data": {
    "request_ref": "opaque-request-id",
    "status": "pending"
  }
}
```

Proposed event types:
- `healthtag.emergency_card.viewed`
- `healthtag.emergency_access.requested`
- `healthtag.emergency_access.decided`
- `healthtag.treatment_note.created`
- `healthtag.notification.created`
- `healthtag.notification.push_submitted`
- `healthtag.notification.read`
- `healthtag.professional.onboarding_submitted`
- `healthtag.professional.verification_changed`

Only publish events needed for a defined workflow. Do not mirror the entire audit log to an external service.

### Sensitive-data rules

Never include in external event payloads:
- Medical history, diagnoses, allergies, medications, treatment-note text, or raw profile fields.
- OTPs, approval tokens, private owner codes, passwords, PINs, session cookies or access tokens.
- Browser push endpoint URLs or encryption keys.
- Full phone numbers, email addresses, or other direct identifiers unless a separately approved workflow has a documented need.

Prefer opaque references and minimal status fields. If an external workflow needs patient-specific context, it must request the minimum permitted data from HealthTag through an authenticated, audited endpoint at execution time.

## 5. Delivery and reliability contract

Before production integrations:
1. Add a transactional outbox in HealthTag so a committed business event and its outbound event record cannot diverge.
2. Give every event a unique ID and every external action an idempotency key.
3. Deliver asynchronously; do not make emergency QR access or emergency approval wait for Maritime or Prune.
4. Retry transient failures with bounded exponential backoff and jitter.
5. Dead-letter repeated failures and expose an operator-visible status.
6. Record attempted, accepted, failed and completed states separately. Provider acceptance is not proof of device delivery or human receipt.
7. Authenticate service-to-service calls, rotate credentials, enforce TLS, and apply rate limits.
8. Validate signatures/timestamps or use short-lived scoped service tokens to prevent replay.
9. Make external service outages fail closed for privileged actions but fail open for non-critical core HealthTag access where safe.
10. Keep an audit trail of who/what initiated each external action and its result.

## 6. Candidate API boundaries

These are design targets, not current routes:
- HealthTag publishes an event to an internal outbox.
- Maritime receives only approved event types and schedules deterministic tasks.
- Maritime calls a narrow HealthTag action endpoint with a scoped service identity and idempotency key.
- HealthTag independently authenticates/authorises the action and performs the write.
- Prune receives only the minimum approved text or structured fields for a specific task, with retention and model-provider rules defined first.
- AI-generated suggestions return as drafts; a human or authorised HealthTag user explicitly confirms any consequential action.

No external service receives direct database credentials.

## 7. Notifications and channel boundaries

The existing HealthTag notification centre and browser push implementation should remain under HealthTag control.

- HealthTag owns notification creation, recipient authorization, history and read state.
- Push payloads remain generic and must not contain PHI, OTPs or approval tokens.
- Push submission status must not be described as device delivery or user read.
- The SMS provider remains a separate channel, disabled during development and testing unless the project owner explicitly authorises a real send.
- Browser push subscription ownership must be migrated to the final authenticated principal model after the login work is complete.
- Maritime may orchestrate retries or reminders only through approved HealthTag APIs; it must not impersonate a user or silently change notification preferences.

## 8. Phased implementation gates

| Phase | Deliverable | Gate |
|---|---|---|
| 0 | Confirm login identity and authorization contract | Login teammate review |
| 1 | Define typed event schemas and outbox | Security review |
| 2 | Add one non-sensitive Maritime workflow in staging | Idempotency and outage tests |
| 3 | Add Prune for a low-risk administrative draft workflow | Provider/privacy review and human review |
| 4 | Migrate browser push subscriptions to stable principal IDs | Login integration tests |
| 5 | Expand workflows only after audit, security and reliability tests | Project owner approval |

## 9. Explicit non-goals

This proposal does not authorise:
- Deployment, production credentials, or external API connections.
- Changes to the login system being built by another teammate.
- Any AI diagnosis or autonomous clinical decision.
- Automated emergency-history approval or denial.
- Direct database access for Maritime or Prune.
- SMS testing or paid message sends.
- Merging this design branch into `main`.

## 10. Open decisions

- What is the final authenticated principal and role model?
- What exact Maritime service/API will host the deterministic workflows?
- What is Prune (specific product/service), where will it run, and which model/provider and retention terms apply?
- Which one low-risk workflow should be piloted first?
- Who is the human owner for each workflow and its failure queue?
- What are the approved data-retention, consent, audit and incident-response policies?

**Next recommended action:** review this draft with the login teammate, then select one low-risk, non-medical administrative workflow for a staging pilot.
