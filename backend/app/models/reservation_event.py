# reservation_event.py
#
# DESIGN.md ref: Section 4.2 (Reservation Events)
#
# TODO: Define a ReservationEventType enum with these values:
#   RESERVATION_CREATED, RESERVATION_RELEASED, RESERVATION_FULFILLED
#
# TODO: Define a ReservationEvent SQLAlchemy model with:
#   - id (primary key)
#   - spool_id (foreign key -> spools.id)
#   - print_request_id (foreign key -> print_requests.id)
#   - event_type
#   - amount
#   - user_id
#   - related_event_id (nullable, self-referencing FK - links a
#     RELEASED/FULFILLED event back to its originating CREATED event)
#   - created_at (timestamp, default to now)
#
# Think about why this is a SEPARATE table from inventory_events rather
# than reusing it with different event types - what's the conceptual
# distinction DESIGN.md draws in Section 4's intro?
