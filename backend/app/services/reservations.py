# reservations.py
#
# DESIGN.md ref: Section 5 (reservation + availability invariants),
# Section 6.3 (reservation creation), Section 6.4 (fulfillment atomicity).

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    InventoryEvent,
    InventoryEventType,
    ReservationEvent,
    ReservationEventType,
)
from app.services.inventory import get_current_weight


def get_reserved_amount(db: Session, spool_id: int) -> float:
    """
    Get the total amount of filament currently reserved (but not yet
    fulfilled or released) for a given spool.

    Implements DESIGN.md Section 5:
        Reserved = sum(CREATED) - sum(RELEASED) - sum(FULFILLED)

    Args:
        db (Session): The SQLAlchemy database session.
        spool_id (int): The ID of the spool to check.

    Returns:
        float: The total amount currently reserved for this spool.
    """

    def _sum_for(event_type: ReservationEventType) -> float:
        total = (
            db.query(func.coalesce(func.sum(ReservationEvent.amount), 0.0))
            .filter(
                ReservationEvent.spool_id == spool_id,
                ReservationEvent.event_type == event_type,
            )
            .scalar()
        )
        return float(total)

    created = _sum_for(ReservationEventType.RESERVATION_CREATED)
    released = _sum_for(ReservationEventType.RESERVATION_RELEASED)
    fulfilled = _sum_for(ReservationEventType.RESERVATION_FULFILLED)

    return created - released - fulfilled


def get_available(db: Session, spool_id: int) -> float:
    """
    Get the amount of filament available for new reservations on a spool.

    Implements DESIGN.md Section 5:
        Available = current filament - reserved filament

    Args:
        db (Session): The SQLAlchemy database session.
        spool_id (int): The ID of the spool to check.

    Returns:
        float: The amount currently available for new reservations.
    """
    current_weight = get_current_weight(db, spool_id)
    reserved = get_reserved_amount(db, spool_id)
    return current_weight - reserved


def _get_reservation_status(db: Session, reservation_id: int) -> str:
    """
    Internal helper. Determine whether a reservation (identified by the
    id of its original RESERVATION_CREATED event) is "active", "released",
    or "fulfilled".

    Not part of the public TODO list, but needed by both
    release_reservation and fulfill_reservation to check Section 5's
    global constraint: "a released reservation cannot be released again"
    and "a fulfilled reservation cannot be fulfilled twice".
    """
    resolving_event = (
        db.query(ReservationEvent)
        .filter(
            ReservationEvent.related_event_id == reservation_id,
            ReservationEvent.event_type.in_(
                [
                    ReservationEventType.RESERVATION_RELEASED,
                    ReservationEventType.RESERVATION_FULFILLED,
                ]
            ),
        )
        .first()
    )

    if resolving_event is None:
        return "active"
    if resolving_event.event_type == ReservationEventType.RESERVATION_RELEASED:
        return "released"
    return "fulfilled"


def create_reservation(
    db: Session,
    spool_id: int,
    print_request_id: int,
    amount: float,
    user_id: str,
) -> ReservationEvent:
    """
    Create a new reservation against a spool's available filament.
    """

    available = get_available(db, spool_id)

    if amount > available:
        raise ValueError(f"Cannot reserve {amount}g - only {available}g available.")

    new_reservation = ReservationEvent(
        spool_id=spool_id,
        print_request_id=print_request_id,
        event_type=ReservationEventType.RESERVATION_CREATED,
        amount=amount,
        user_id=user_id,
    )

    db.add(new_reservation)
    db.commit()

    return new_reservation


def release_reservation(db: Session, reservation_id: int, user_id: str) -> None:
    """
    Release an active reservation, freeing its amount back to availability.

    Args:
        db (Session): The SQLAlchemy database session.
        reservation_id (int): The id of the original RESERVATION_CREATED
            event to release.
        user_id (str): The identifier of the person releasing it.

    Raises:
        ValueError: If no such reservation exists, or it's not currently
            active (already released or fulfilled).
    """
    original = db.get(ReservationEvent, reservation_id)
    if (
        original is None
        or original.event_type != ReservationEventType.RESERVATION_CREATED
    ):
        raise ValueError(f"No reservation found with id {reservation_id}")

    status = _get_reservation_status(db, reservation_id)
    if status != "active":
        raise ValueError(
            f"Reservation {reservation_id} cannot be released (status: {status}"
        )

    release_event = ReservationEvent(
        spool_id=original.spool_id,
        print_request_id=original.print_request_id,
        event_type=ReservationEventType.RESERVATION_RELEASED,
        amount=original.amount,
        user_id=user_id,
        related_event_id=reservation_id,
    )
    db.add(release_event)
    db.commit()


def fulfill_reservation(db: Session, reservation_id: int, user_id: str) -> None:
    """
    Fulfill an active reservation: convert a planned allocation into an
    actual physical inventory reduction.

    DESIGN.md Section 6.4 - the fulfillment atomicity invariant. This is
    the most important function in the file:

      1. Confirm the reservation is active (not already released/fulfilled).
      2. RE-VALIDATE availability at fulfillment time using the spool's
         actual current weight - do not trust the original reservation-time
         check, since the spool's real weight may have changed since (e.g.
         a correction was applied in between).
      3. Insert a FILAMENT_USED inventory_event (negative quantity_change).
      4. Insert a RESERVATION_FULFILLED reservation_event.
      5. Both (3) and (4) happen in a single transaction - if anything
         fails partway through, neither is persisted.

    Args:
        db (Session): The SQLAlchemy database session.
        reservation_id (int): The id of the original RESERVATION_CREATED
            event to fulfill.
        user_id (str): The identifier of the person fulfilling it.

    Raises:
        ValueError: If no such reservation exists, it's not active, or
            there isn't enough physical filament remaining to fulfill it.
    """
    original = db.get(ReservationEvent, reservation_id)
    if (
        original is None
        or original.event_type != ReservationEventType.RESERVATION_CREATED
    ):
        raise ValueError(f"No reservation found with id {reservation_id}")

    status = _get_reservation_status(db, reservation_id)
    if status != "active":
        raise ValueError(
            f"Reservation {reservation_id} cannot be fulfilled (status: {status})"
        )

    # Re-validate against the spool's actual physical weight right now -
    # NOT the original reservation-time availability check.
    current_weight = get_current_weight(db, original.spool_id)
    if current_weight < original.amount:
        raise ValueError(
            "Insufficient filament remaining to fulfill this reservation - "
            "the spool's weight may have changed since the reservation was made"
        )

    try:
        usage_event = InventoryEvent(
            spool_id=original.spool_id,
            event_type=InventoryEventType.FILAMENT_USED,
            quantity_change=-original.amount,
            user_id=user_id,
            related_request_id=original.print_request_id,
            note=f"Fulfillment of reservation #{reservation_id}",
        )
        db.add(usage_event)

        fulfilled_event = ReservationEvent(
            spool_id=original.spool_id,
            print_request_id=original.print_request_id,
            event_type=ReservationEventType.RESERVATION_FULFILLED,
            amount=original.amount,
            user_id=user_id,
            related_event_id=reservation_id,
        )
        db.add(fulfilled_event)

        db.commit()
    except Exception:
        db.rollback()
        raise
