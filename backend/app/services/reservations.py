# reservations.py
#
# DESIGN.md ref: Section 5 (reservation + availability invariants),
# Section 6.3 (reservation creation), Section 6.4 (fulfillment atomicity -
# read this section multiple times before writing fulfill_reservation;
# it's the trickiest part of the whole system).
#
# TODO: get_reserved_amount(db, spool_id) -> float
#   Implements: "Reserved = sum(CREATED) - sum(RELEASED) - sum(FULFILLED)"
#
# TODO: get_available(db, spool_id) -> float
#   Implements: "Available = current filament - reserved filament"
#   (this should call your inventory.py function, not duplicate its logic)
#
# TODO: create_reservation(db, spool_id, print_request_id, amount, user_id)
#   Section 6.3: reject if amount > get_available(db, spool_id).
#   Validate + insert in a single transaction.
#
# TODO: release_reservation(db, reservation_id, user_id)
#   Reject if the reservation isn't currently active (already
#   released/fulfilled - Section 5's global constraints).
#
# TODO: fulfill_reservation(db, reservation_id, user_id)
#   THE critical function. Per Section 6.4, in ONE database transaction:
#     1. Confirm the reservation is active.
#     2. RE-VALIDATE availability at fulfillment time - do not trust the
#        original reservation-time check (why not? think about what could
#        have changed the spool's weight since the reservation was made).
#     3. Insert a FILAMENT_USED inventory_event (negative quantity_change),
#        cross-referencing the reservation for traceability.
#     4. Insert a RESERVATION_FULFILLED reservation_event.
#     5. Commit both together, or roll back both on any failure - look up
#        how to structure a SQLAlchemy transaction so a failure partway
#        through undoes everything.
