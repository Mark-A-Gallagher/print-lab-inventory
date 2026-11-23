# 3D Print Lab Inventory System --- Design Specification

## 1. Project Goals

Build an inventory and print-request management system for a school 3D
printing lab (\~10 users: a small number of teachers/admins and
students). The system must:

-   Track filament at the level of individual spools, not just
    materials.
-   Allow print requests to check filament availability before printing.
-   Prevent two requests from over-committing the same filament.
-   Provide a truthful, auditable history of everything that happened to
    the inventory --- not just its current snapshot.
-   Stay simple enough to build and reason about at this scale (10
    users, a handful of machines, low request volume). Do not
    pre-engineer for scale, auth complexity, or hosting concerns the
    project doesn't have yet.

Release strategy is usable-release-driven, not phase-driven --- see
Section 10 for the release/testing sequence.

## 2. Architecture

### 2.1 Application Architecture

``` text
                 ┌─────────────────────┐
                 │       React         │
                 │  TypeScript / UI    │
                 └──────────┬──────────┘
                            │
                           API
                            │
                 ┌──────────▼──────────┐
                 │       FastAPI       │
                 │ Business Rules      │
                 │ Validation          │
                 │ Calculations        │
                 └──────────┬──────────┘
                            │
                       SQLAlchemy
                            │
                 ┌──────────▼──────────┐
                 │       SQLite        │
                 │ Spools / Materials  │
                 │ Machines / Requests │
                 │ Inventory Events    │
                 │ Reservation Events │
                 └─────────────────────┘
```

Critical rule: **the frontend never decides whether an action is
valid.** The UI may disable a button because an action *looks* invalid,
but FastAPI must independently re-validate every request. A malformed or
direct API call must never be able to corrupt inventory state.

SQLite is used for the current deployment. SQLAlchemy centralizes
database interactions and makes a future database migration more
manageable, although migration would still require testing and
potentially configuration or schema changes. No caching or snapshotting
layer exists yet --- derived state is computed from events. This is
intentional: correctness and simplicity are more valuable than
optimizing a performance problem that does not exist at this scale.

The initial application uses a simple named-user selector and a single
administrator credential for teacher-only actions rather than a full
user-account system. Authentication and authorization should be
strengthened if the deployment's users, network exposure, or operational
requirements make the current approach insufficient.

### 2.2 Production Deployment Architecture

The production application is deployed on a Raspberry Pi 3 Model B.
Nginx serves the built frontend and acts as the entry point for browser
requests. API requests are proxied to the FastAPI application running
under Uvicorn. SQLite stores application data locally on the Pi.

``` text
                 Browser / Chromium
                         |
                         | HTTP
                         v
                  Nginx (port 80)
                         |
                +--------+--------+
                |                 |
          Frontend files      API requests
                |                 |
                v                 v
          React production     Uvicorn
              build               |
                                  v
                               FastAPI
                                  |
                              SQLAlchemy
                                  |
                                  v
                                SQLite
                         Local database file
```

The backend listens on the Pi's loopback interface (`127.0.0.1`) and is
reached through Nginx. Client devices use Nginx as the application entry
point rather than connecting directly to the backend port.

## 3. Domain Model

Relatively stable, non-event entities:

``` text
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

`Spool` and `Machine` hold descriptive facts about a physical object.
They do **not** hold current weight or current assignment --- those are
derived (Sections 4 and 5).

## 4. Event Streams

Two separate, append-only event streams. Keeping them separate preserves
a clean domain boundary: a reservation is a *plan*, not a *physical
change*.

### 4.1 Inventory Events

Concern the physical spool.

``` text
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

-   `SPOOL_CREATED` --- establishes the spool's starting weight as an
    event, not a hidden initial field. The full history must always be
    able to explain the spool's existence from zero.
-   `FILAMENT_USED` --- quantity_change is negative.
-   `WEIGHT_ADJUSTMENT` --- manual re-weigh correction.
-   `SPOOL_CORRECTION` --- compensates for an erroneous prior event;
    references the event being corrected via `related_event_id`. Never
    edits or deletes the original.
-   `ASSIGNED_TO_MACHINE` --- sets `machine_id`, no `quantity_change`.
-   `REMOVED_FROM_MACHINE` --- clears assignment, no `quantity_change`.
-   (Later, optional) `SPOOL_ARCHIVED`

### 4.2 Reservation Events

Concern planned, not-yet-physical filament usage.

``` text
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

-   `RESERVATION_CREATED`
-   `RESERVATION_RELEASED`
-   `RESERVATION_FULFILLED`

A reservation never itself changes physical inventory --- see Section
6.4 for how fulfillment bridges the two streams.

## 5. Core Invariants

These are the derivations every other rule and every test are built on.

**Inventory invariant**

``` text
Current filament (per spool) = sum of quantity_change over all
                                inventory_events for that spool
```

**Reservation invariant**

``` text
Reserved filament (per spool) = sum(RESERVATION_CREATED amounts)
                                 − sum(RESERVATION_RELEASED amounts)
                                 − sum(RESERVATION_FULFILLED amounts)
```

**Availability invariant**

``` text
Available filament (per spool) = Current filament − Reserved filament
```

**Machine assignment invariant**

``` text
Current machine (per spool) = machine_id of the latest valid
                               ASSIGNED_TO_MACHINE / REMOVED_FROM_MACHINE
                               event for that spool
```

**Fulfillment atomicity invariant**

``` text
A RESERVATION_FULFILLED event and its corresponding FILAMENT_USED event
are created in a single transaction. Both succeed, or neither is persisted.
Fulfillment is a single atomic domain operation, never two independent writes.
```

**Global constraints**

``` text
Current filament             >= 0
A spool                      cannot be assigned to two machines simultaneously
A reservation                cannot exceed available filament at creation time
A reservation                cannot exceed available filament at fulfillment time (re-validated)
A released reservation       cannot be released again
A fulfilled reservation      cannot be fulfilled twice
Events                       are never edited or deleted, only compensated
```

## 6. Business Rules

Enforced in the API layer, before any event is inserted:

``` text
User action
     |
     v
Validate request shape
     |
     v
Calculate current derived state (from events)
     |
     v
Check business rules against derived state
     |
     v
 Valid? ---- No ---> Reject, no event inserted
     |
    Yes
     |
     v
Insert immutable event(s)
```

### 6.1 Filament Usage

`FILAMENT_USED` may not reduce a spool's current filament below zero. If
attempted, reject with the shortfall shown (e.g. "Cannot record 100g of
usage --- spool only has 80g remaining").

### 6.2 Machine Assignment

A spool cannot be assigned to a new machine while already assigned to
another. The prior `REMOVED_FROM_MACHINE` event must exist first.

### 6.3 Reservations

A `RESERVATION_CREATED` event may not exceed the spool's currently
available filament (current filament − existing active reservations).

### 6.4 Fulfillment (Atomic, Two-Stream Operation)

On `RESERVATION_FULFILLED`:

1.  **Reservation must be active** --- cannot fulfill an already
    released or already fulfilled reservation.
2.  **Re-validate availability at fulfillment time** --- do not trust
    the original reservation-time check; the spool's actual weight may
    have changed since (e.g. via a correction).
3.  **Create `FILAMENT_USED`** --- quantity = negative reserved amount,
    referencing the reservation/fulfillment for traceability.
4.  **Create `RESERVATION_FULFILLED`** --- marks the planned allocation
    consumed; does not itself change physical inventory.
5.  **Single transaction** --- both events commit together or neither
    persists.
6.  **No double counting** --- an active reservation is subtracted from
    availability only while active; once fulfilled it contributes 0 to
    reserved filament, and the `FILAMENT_USED` event is what reduces
    actual inventory.

Example transition:

``` text
Before:
  Physical filament = 643g
  Reserved          = 400g
  Available         = 243g

Fulfill 400g:
  Physical filament = 243g   <- FILAMENT_USED -400g
  Reserved          = 0g     <- RESERVATION_FULFILLED
  Available         = 243g
```

### 6.5 Corrections

Mistakes are never fixed by editing/deleting the original event. A
`SPOOL_CORRECTION` event is inserted with a `related_event_id` pointing
to the event being corrected and a note explaining why. The UI presents
this as "Correct Event," never "Edit Event."

## 7. Transaction & Concurrency Rules

-   Validation ("check current state") and the resulting insert must
    happen inside a single database transaction --- not as two
    independent calls. A gap between check and insert would allow two
    concurrent requests to both read "available" and both be approved
    against filament that only exists once.
-   SQLite's transaction behavior is appropriate for the expected
    initial scale when writes are handled carefully. Write contention
    and transaction boundaries should still be tested under realistic
    concurrent use.
-   Fulfillment's two-event write (Section 6.4) is a single transaction
    by the same rule.

## 8. Database Schema

Tables: `materials`, `spools`, `machines`, `print_requests`,
`inventory_events`, `reservation_events`. See Section 3 (stable
entities) and Section 4 (event streams) for field-level detail.

No `current_weight` or `current_machine_id` column exists on `spools`
--- those are always derived, never stored, so there is no way for
stored state and event history to disagree.

## 9. API Operations (Initial Set)

``` text
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

This is the initial API contract. The running application's OpenAPI
documentation at `/docs` is the source of truth for endpoints currently
implemented and exposed.

## 10. Testing Requirements and Release Sequence

Tests are written against the invariants and business rules above:

``` text
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

### Release Sequence

``` text
0.1  Foundation      — schema, event model, derivation logic, core tests
0.2  Inventory UI    — view/search/add spools, assign/remove, low-stock
0.3  Print Requests  — request -> check -> reserve workflow
0.4  QR workflow     — /spools/{id} pages reachable via printed QR codes
0.5  History polish  — history views, dashboard, error/empty/loading states
1.0  Teacher handoff — usable application deployed on Raspberry Pi for local
                       lab use and real-world feedback
```

## 11. Production Deployment

### 11.1 Deployment Hardware and Operating System

The production host is a Raspberry Pi 3 Model B.

  Component          Specification
  ------------------ --------------------------
  Device             Raspberry Pi 3 Model B
  Processor          Quad-core ARM Cortex-A53
  RAM                1 GB
  Storage            64 GB microSD card
  Operating System   Raspberry Pi OS 32-bit
  Python             3.13.4

The deployed system uses the existing 32-bit operating system. The Pi's
limited memory is considered when choosing how the application is built
and run.

### 11.2 Production Components

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Raspberry Pi OS                     Operating system, hardware,
                                      filesystem, networking, and
                                      processes

  Nginx                               Serves the production frontend and
                                      reverse-proxies API requests

  React production build              Browser interface compiled with
                                      Vite on a separate development
                                      computer

  Uvicorn                             ASGI server that runs the FastAPI
                                      application

  FastAPI                             API endpoints, validation, and
                                      business rules

  SQLAlchemy                          Python database access and ORM

  SQLite                              Local persistent application
                                      database

  systemd                             Starts and supervises the backend
                                      service

  Chromium                            Local full-screen kiosk interface
  -----------------------------------------------------------------------

### 11.3 Request Flow

1.  A user opens the application in Chromium or another browser using
    the Raspberry Pi's host address.
2.  Nginx receives the HTTP request.
3.  For frontend routes and static assets, Nginx serves the production
    React build.
4.  For API routes, Nginx forwards the request to Uvicorn on
    `127.0.0.1:8000`.
5.  FastAPI validates the request and executes the relevant application
    logic.
6.  SQLAlchemy performs the required database operations against SQLite.
7.  The response returns through Uvicorn and Nginx to the client
    browser.

The backend is bound to the loopback interface so client devices use
Nginx as the application entry point rather than connecting directly to
the backend port.

### 11.4 Frontend Build and Deployment

The React frontend is built on a separate development computer. The
generated production assets are transferred to the Raspberry Pi and
served by Nginx.

This avoids requiring the Raspberry Pi 3 Model B to perform frontend
compilation, reducing memory and CPU pressure on the production device.

Changes to frontend source code must be rebuilt and the resulting
production assets redeployed before they appear on the live site.

### 11.5 Backend Process Management

The FastAPI application is managed as a systemd service and runs in the
background. The service configuration defines the application user,
working directory, virtual-environment executable, startup command, and
restart behavior.

The service starts automatically during system boot. Service status and
logs can be inspected through systemd and the system journal.

### 11.6 Kiosk Operation

The Raspberry Pi desktop is configured to launch Chromium in kiosk mode
and open the locally hosted inventory application.

This allows the Pi to function as a dedicated inventory workstation with
a full-screen browser interface. Kiosk mode is a usability feature and
does not provide authentication or access control.

### 11.7 Network Model

The application is intended for local network access. Client devices
connect to the Raspberry Pi's network address and access the application
through Nginx.

The backend listens on `127.0.0.1:8000`, so the API is reached through
the reverse proxy. Availability from another device depends on the
network permitting client-to-Pi communication.

The deployment is intended for the lab's local network and is not
designed to be exposed directly to the public internet.

### 11.8 Hardware and Operational Constraints

The Raspberry Pi 3 Model B has 1 GB of RAM. The deployment accounts for
this by:

-   Building the frontend on a separate computer rather than on the Pi.
-   Running a single Uvicorn worker.
-   Using SQLite rather than a separate database server.
-   Serving static assets directly through Nginx.
-   Keeping the backend bound to the local loopback interface.
-   Avoiding unnecessary processes on the Pi.

### 11.9 Persistence, Backups, and Recovery

The SQLite database is stored locally on the Raspberry Pi and must
persist across application and system restarts.

The live database must not be committed to the source repository.
Backups should be created regularly, stored separately from the live
database, and copied off the Raspberry Pi to protect against microSD
failure.

A backup procedure is not considered complete until restoration has been
tested against a separate database file or test environment.

### 11.10 Deployment Verification

The following deployment checks have been completed:

-   [x] FastAPI runs successfully on the Raspberry Pi.
-   [x] The production frontend is served by Nginx.
-   [x] Nginx forwards API requests to FastAPI.
-   [x] SQLite stores application data locally.
-   [x] The backend is managed by systemd.
-   [x] The backend starts automatically during system boot.
-   [x] Chromium opens the application in kiosk mode.
-   [x] The application is accessible through the intended local network
    address.

Database backup and restore, access control, and reliability should
continue to be reviewed as part of normal operation.
