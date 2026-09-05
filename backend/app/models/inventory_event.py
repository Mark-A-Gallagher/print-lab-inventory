# inventory_event.py
#
# DESIGN.md ref: Section 4.1 (Inventory Events)
#
# TODO: Define an InventoryEventType enum with these values:
#   SPOOL_CREATED, FILAMENT_USED, WEIGHT_ADJUSTMENT, SPOOL_CORRECTION,
#   ASSIGNED_TO_MACHINE, REMOVED_FROM_MACHINE
#
# TODO: Define an InventoryEvent SQLAlchemy model with:
#   - id (primary key)
#   - spool_id (foreign key -> spools.id)
#   - event_type
#   - quantity_change (nullable - NOT every event changes weight; think
#     about which event types above should leave this null)
#   - machine_id (nullable - only set for the two machine-related events)
#   - user_id
#   - related_event_id (nullable, self-referencing FK - used for
#     corrections pointing at the event they fix, and for linking a
#     fulfillment's FILAMENT_USED event back to its reservation - Section 6.4/6.5)
#   - related_request_id (nullable FK -> print_requests.id)
#   - note (nullable)
#   - created_at (timestamp, default to now)
#
# CRITICAL: this table is append-only. NEVER write code anywhere in this
# project that UPDATEs or DELETEs a row here. Mistakes get compensated
# with a new SPOOL_CORRECTION event (Section 6.5), not a fix to the
# original row. Where will you enforce that rule so nobody "accidentally"
# adds an update method later?
