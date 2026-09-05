# 3D Print Lab Inventory System — Design Specification

## 1. Project Goals

Build an inventory and print-request management system for a school 3D printing
lab (~10 users: a small number of teachers/admins and students). The system
must:

- Track filament at the level of individual spools, not just materials.
- Allow print requests to check filament availability before printing.
- Prevent two requests from over-committing the same filament.
- Provide a truthful, auditable history of everything that happened to the
  inventory — not just its current snapshot.
- Stay simple enough to build and reason about at this scale (10 users, a
  handful of machines, low request volume). Do not pre-engineer for scale,
  auth complexity, or hosting concerns the project doesn't have yet.

Release strategy is usable-release-driven, not phase-driven — see Section 10
for the release/testing sequence.

## 2. Architecture

```
                ┌─────────────────────┐
                │       React         │
                │  TypeScript / UI    │
                └──────────┬──────────┘
                           │
                          API
                           │
                ┌──────────▼──────────┐
                │       FastAPI       │
                │                     │
                │ Business Rules      │
                │ Validation          │
                │ Calculations        │
                └──────────┬──────────┘
                           │
                      SQLAlchemy
                           │
                ┌──────────▼──────────┐
                │       SQLite        │
                │                     │
                │ Spools              │
                │ Materials           │
                │ Machines            │
                │ Print Requests      │
                │ Inventory Events    │
                │ Reservation Events  │
                └─────────────────────┘
```

Critical rule: **the frontend never decides whether an action is valid.** The
UI may disable a button because an action *looks* invalid, but FastAPI must
independently re-validate every request. A malformed or direct API call must
never be able to corrupt inventory state.

SQLite is used for now; the ORM boundary (SQLAlchemy) means moving to
PostgreSQL later is a configuration change, not a rewrite. No caching or
snapshotting layer exists yet — derived state is always computed live from
events (see Section 5). This is intentional: correct and simple beats fast
and complicated for a performance problem that doesn't exist at this scale.

No full user-account/auth system for v1. A simple named-user selector plus a
single admin credential for teacher-only actions is sufficient at 10 users.
Real authentication is deferred until there's an actual requirement for it.

## 3. Domain Model

Relatively stable, non-event entities:

```
Material
├── id
├── name
└── color (optional)

Spool
├── id
├── material_id
├── original_filament_weight
├── empty_spool_weight
└── low_stock_threshold

Machine
├── id
├── name
└── status (online / offline / etc., simple field — not event-sourced)

PrintRequest
├── id
├── requested_by (user)
├── project_name
├── material_id
├── amount_required
└── status (Pending / Approved / Printing / Complete / Rejected)
```

`Spool` and `Machine` hold the descriptive facts about a physical object.
They do **not** hold current weight or current assignment — those are
derived (Section 5).

## 4. Event Streams

Two separate, append-only event streams. Keeping them separate preserves a
clean domain boundary: a reservation is a *plan*, not a *physical change*.

### 4.1 Inventory Events

Concern the physical spool.

```
InventoryEvent
├── id
├── spool_id
├── event_type
├── quantity_change      (nullable — not every event changes weight)
├── machine_id           (nullable — only for machine-assignment events)
├── user_id
├── related_event_id     (nullable — for corrections/fulfillments)
├── related_request_id   (nullable — for fulfillment traceability)
├── note
└── created_at
```

Event types:

- `SPOOL_CREATED` — establishes the spool's starting weight as an event, not
  a hidden initial field. The full history must always be able to explain
  the spool's existence from zero.
- `FILAMENT_USED` — quantity_change is negative.
- `WEIGHT_ADJUSTMENT` — manual re-weigh correction.
- `SPOOL_CORRECTION` — compensates for an erroneous prior event; references
  the event being corrected via `related_event_id`. Never edits or deletes
  the original.
- `ASSIGNED_TO_MACHINE` — sets `machine_id`, no `quantity_change`.
- `REMOVED_FROM_MACHINE` — clears assignment, no `quantity_change`.
- (Later, optional) `SPOOL_ARCHIVED`

### 4.2 Reservation Events

Concern planned, not-yet-physical filament usage.

```
ReservationEvent
├── id
├── spool_id
├── print_request_id
├── event_type
├── amount
├── user_id
├── related_event_id   (nullable — links fulfillment to its RESERVATION_CREATED)
└── created_at
```

Event types:

- `RESERVATION_CREATED`
- `RESERVATION_RELEASED`
- `RESERVATION_FULFILLED`

A reservation never itself changes physical inventory — see Section 6.4 for
how fulfillment bridges the two streams.

## 5. Core Invariants

These are the derivations every other rule and every test is built on.

**Inventory invariant**
```
Current filament (per spool) = sum of quantity_change over all
                                inventory_events for that spool
```

**Reservation invariant**
```
Reserved filament (per spool) = sum(RESERVATION_CREATED amounts)
                                 − sum(RESERVATION_RELEASED amounts)
                                 − sum(RESERVATION_FULFILLED amounts)
```

**Availability invariant**
```
Available filament (per spool) = Current filament − Reserved filament
```

**Machine assignment invariant**
```
Current machine (per spool) = spool_id of the latest valid
                               ASSIGNED_TO_MACHINE / REMOVED_FROM_MACHINE
                               event for that spool
```

**Fulfillment atomicity invariant**
```
A RESERVATION_FULFILLED event and its corresponding FILAMENT_USED event
are created in a single transaction. Both succeed, or neither is persisted.
Fulfillment is a single atomic domain operation, never two independent writes.
```

**Global constraints**
```
Current filament            >= 0
A spool                     cannot be assigned to two machines simultaneously
A reservation                cannot exceed available filament at creation time
A reservation                cannot exceed available filament at fulfillment time (re-validated)
A released reservation       cannot be released again
A fulfilled reservation      cannot be fulfilled twice
Events                       are never edited or deleted, only compensated
```

## 6. Business Rules

Enforced in the API layer, before any event is inserted:

```
User action
     │
     ▼
Validate request shape
     │
     ▼
Calculate current derived state (from events)
     │
     ▼
Check business rules against derived state
     │
     ▼
 Valid? ── No → Reject, no event inserted
     │
    Yes
     │
     ▼
Insert immutable event(s)
```

### 6.1 Filament usage
`FILAMENT_USED` may not reduce a spool's current filament below zero. If
attempted, reject with the shortfall shown (e.g. "Cannot record 100g of
usage — spool only has 80g remaining").

### 6.2 Machine assignment
A spool cannot be assigned to a new machine while already assigned to
another. The prior `REMOVED_FROM_MACHINE` event must exist first.

### 6.3 Reservations
A `RESERVATION_CREATED` event may not exceed the spool's currently available
filament (current filament − existing active reservations).

### 6.4 Fulfillment (atomic, two-stream operation)

On `RESERVATION_FULFILLED`:

1. **Reservation must be active** — cannot fulfill an already released or
   already fulfilled reservation.
2. **Re-validate availability at fulfillment time** — do not trust the
   original reservation-time check; the spool's actual weight may have
   changed since (e.g. via a correction).
3. **Create `FILAMENT_USED`** — quantity = negative reserved amount,
   referencing the reservation/fulfillment for traceability.
4. **Create `RESERVATION_FULFILLED`** — marks the planned allocation
   consumed; does not itself change physical inventory.
5. **Single transaction** — both events commit together or neither persists.
6. **No double counting** — an active reservation is subtracted from
   availability only while active; once fulfilled it contributes 0 to
   reserved filament, and the `FILAMENT_USED` event is what reduces actual
   inventory.

Example transition:
```
Before:
  Physical filament = 643g
  Reserved          = 400g
  Available         = 243g

Fulfill 400g:
  Physical filament = 243g   ← FILAMENT_USED -400g
  Reserved          = 0g     ← RESERVATION_FULFILLED
  Available         = 243g
```

### 6.5 Corrections
Mistakes are never fixed by editing/deleting the original event. A
`SPOOL_CORRECTION` event is inserted with a `related_event_id` pointing to
the event being corrected and a note explaining why. The UI presents this as
"Correct Event," never "Edit Event."

## 7. Transaction & Concurrency Rules

- Validation ("check current state") and the resulting insert must happen
  inside a single database transaction — not as two independent calls. A
  gap between check and insert would allow two concurrent requests to both
  read "available" and both be approved against filament that only exists
  once.
- SQLite's default transaction isolation is sufficient at this scale; no
  additional locking infrastructure is needed for v1.
- Fulfillment's two-event write (Section 6.4) is a single transaction by the
  same rule.

## 8. Database Schema

Tables: `materials`, `spools`, `machines`, `print_requests`,
`inventory_events`, `reservation_events`. See Section 3 (stable entities) and
Section 4 (event streams) for field-level detail. No `current_weight` or
`current_machine_id` column exists on `spools` — those are always derived,
never stored, so there is no way for stored state and event history to
disagree.

## 9. API Operations (initial set)

```
POST   /spools                     create spool (+ SPOOL_CREATED event)
GET    /spools                     list spools with derived state
GET    /spools/{id}                spool detail + history
POST   /spools/{id}/weight         record WEIGHT_ADJUSTMENT / FILAMENT_USED
POST   /spools/{id}/correct        record SPOOL_CORRECTION
POST   /spools/{id}/assign         ASSIGNED_TO_MACHINE
POST   /spools/{id}/unassign       REMOVED_FROM_MACHINE

POST   /machines                   create machine
GET    /machines                   list with current assignment

POST   /requests                   create print request
POST   /requests/{id}/reserve      RESERVATION_CREATED
POST   /requests/{id}/release      RESERVATION_RELEASED
POST   /requests/{id}/fulfill      atomic RESERVATION_FULFILLED + FILAMENT_USED
```

## 10. Testing Requirements

Tests are written against the invariants and business rules above, before
UI work begins:

```
✓ Creating a 1kg spool produces 1kg inventory
✓ Using 100g leaves 900g
✓ Using 1,001g is rejected
✓ Correcting a usage event changes derived inventory
✓ Assigning a spool to Printer #1 works
✓ Assigning the same spool to Printer #2 is rejected
✓ Removing the spool allows reassignment
✓ Creating a 400g reservation succeeds with 500g available
✓ Creating another 200g reservation is rejected when only 100g remains
✓ Releasing a reservation restores availability
✓ Fulfilling a reservation consumes the appropriate inventory
✓ Fulfilling a reservation always produces exactly one corresponding
  FILAMENT_USED event, atomically (both succeed or both fail)
✓ An already-fulfilled reservation cannot be fulfilled again
✓ An already-released reservation cannot be released again
✓ Events cannot be edited or deleted
✓ Two simultaneous reservations cannot overbook the same spool
```

### Release sequence

```
0.1  Foundation      — schema, event model, derivation logic, all tests above
0.2  Inventory UI    — view/search/add/edit spools, assign/remove, low-stock
0.3  Print Requests  — request → check → reserve workflow
0.4  QR workflow     — /spools/{id} pages reachable via printed QR codes
0.5  History polish  — history views, dashboard, error/empty/loading states
1.0  Teacher handoff — deployed on localhost for real testing; feedback
                        drives the next cycle before any hosting decision
```
