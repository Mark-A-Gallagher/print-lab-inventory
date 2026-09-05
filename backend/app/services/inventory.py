# inventory.py
#
# DESIGN.md ref: Section 5 (Core Invariants) - inventory + machine
# assignment invariants. These are the two most important functions in
# the whole backend - almost everything else depends on them being
# correct, so make sure you actually understand the SQL you write here
# rather than just getting it to pass a test.
#
# TODO: get_current_weight(db, spool_id) -> float
#   Implements: "Current filament = sum of quantity_change over all
#   inventory_events for that spool"
#   - Careful: some events have a NULL quantity_change (e.g. machine
#     assignment events). Make sure those don't break your SUM or get
#     treated as zero incorrectly - look up SQL's handling of NULL in
#     aggregate functions, and coalesce() if you need it.
#
# TODO: get_current_machine(db, spool_id) -> int | None
#   Implements: "Current machine = latest valid ASSIGNED_TO_MACHINE /
#   REMOVED_FROM_MACHINE event for that spool"
#   - Query only those two event types, order by created_at (and id, as a
#     tiebreaker - why might you need that?) descending, and look at
#     whichever one is most recent.
#
# TODO: record_filament_used(db, spool_id, amount, user_id)
#   Section 6.1: must reject if get_current_weight() - amount < 0.
#   Validate THEN insert, inside a single transaction (Section 7 - why
#   does it matter that this isn't two separate calls?).
#
# TODO: record_weight_adjustment(db, spool_id, new_total_weight, user_id)
#   Think about how this differs from record_filament_used - what event
#   type does it produce, and how do you calculate the quantity_change
#   from a "new total weight" input?
#
# TODO: record_correction(db, related_event_id, amount, reason, user_id)
#   Section 6.5: NEVER edit or delete the original event.
#
# TODO: assign_to_machine(db, spool_id, machine_id, user_id)
#   Section 6.2: reject if get_current_machine() already returns a
#   DIFFERENT machine (must be removed first).
#
# TODO: remove_from_machine(db, spool_id, user_id)
#
# No caching/snapshotting per DESIGN.md Section 2 - always compute these
# derivations live from the event table. Don't add a stored "current
# weight" field to Spool as an optimization; that's the exact bug class
# this design exists to avoid.
