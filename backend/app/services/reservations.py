# reservations.py
#
# DESIGN.md ref: Section 5 (reservation + availability invariants),
# Section 6.3 (reservation creation), Section 6.4 (fulfillment atomicity).

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    InventoryEvent,
    InventoryEventType,
    PrintRequest,
    PrintRequestStatus,
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

    print_request = db.get(PrintRequest, print_request_id)
    if print_request is None:
        raise ValueError(f"Print request {print_request_id} does not exist.")

    if get_active_reservations_for_request(db, print_request_id):
        raise ValueError(f"Ticket {print_request_id} has already been reserved.")

    already_reserved = get_reserved_for_request(db, print_request_id)
    if already_reserved + amount > print_request.amount_grams:
        remaining = max(0.0, print_request.amount_grams - already_reserved)
        raise ValueError(
            f"Reservation total for ticket {print_request_id} would exceed "
            f"the total of {print_request.amount_grams}g. "
            f"Only {remaining:g}g remains to reserve."
        )

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


def get_reserved_for_request(db: Session, print_request_id: int) -> float:
    """Return the active reservation total for one print request."""
    created_ids = {
        row[0]
        for row in db.query(ReservationEvent.id)
        .filter(
            ReservationEvent.print_request_id == print_request_id,
            ReservationEvent.event_type == ReservationEventType.RESERVATION_CREATED,
        )
        .all()
    }

    if not created_ids:
        return 0.0

    created = sum(
        float(row.amount)
        for row in db.query(ReservationEvent)
        .filter(
            ReservationEvent.id.in_(created_ids),
        )
        .all()
    )

    resolved = sum(
        float(row.amount)
        for row in db.query(ReservationEvent)
        .filter(
            ReservationEvent.print_request_id == print_request_id,
            ReservationEvent.event_type.in_(
                [
                    ReservationEventType.RESERVATION_RELEASED,
                    ReservationEventType.RESERVATION_FULFILLED,
                ]
            ),
        )
        .all()
    )
    return created - resolved


def get_active_reservations_for_request(
    db: Session, print_request_id: int
) -> list[ReservationEvent]:
    """Return active reservation-created events for a print request."""
    created = (
        db.query(ReservationEvent)
        .filter(
            ReservationEvent.print_request_id == print_request_id,
            ReservationEvent.event_type == ReservationEventType.RESERVATION_CREATED,
        )
        .all()
    )

    return [
        reservation
        for reservation in created
        if _get_reservation_status(db, reservation.id) == "active"
    ]


def create_reservation_batch(
    db: Session,
    print_request_id: int,
    allocations: list[tuple[int, float]],
    user_id: str,
) -> list[ReservationEvent]:
    """Create all color allocations for a ticket as one locked reservation batch."""
    print_request = db.get(PrintRequest, print_request_id)
    if print_request is None:
        raise ValueError(f"Print request {print_request_id} does not exist.")

    if get_active_reservations_for_request(db, print_request_id):
        raise ValueError(f"Ticket {print_request_id} has already been reserved.")

    if not allocations:
        raise ValueError("At least one spool allocation is required.")

    combined = sum(amount for _, amount in allocations)
    if combined > print_request.amount_grams:
        raise ValueError(
            f"Reservation total {combined:g}g exceeds ticket total "
            f"of {print_request.amount_grams}g."
        )

    totals_by_spool: dict[int, float] = {}
    for spool_id, amount in allocations:
        if amount <= 0:
            raise ValueError("Reservation amounts must be greater than zero.")
        totals_by_spool[spool_id] = totals_by_spool.get(spool_id, 0.0) + amount

    for spool_id, amount in totals_by_spool.items():
        available = get_available(db, spool_id)
        if amount > available:
            raise ValueError(
                f"Cannot reserve {amount:g}g from spool {spool_id}; "
                f"only {available:g}g is available."
            )

    events = [
        ReservationEvent(
            spool_id=spool_id,
            print_request_id=print_request_id,
            event_type=ReservationEventType.RESERVATION_CREATED,
            amount=amount,
            user_id=user_id,
        )
        for spool_id, amount in allocations
    ]
    db.add_all(events)
    db.commit()
    for event in events:
        db.refresh(event)
    return events


def complete_print_request(
    db: Session,
    print_request_id: int,
    user_id: str,
) -> None:
    """Complete a printing ticket and fulfill all active spool reservations atomically."""
    print_request = db.get(PrintRequest, print_request_id)
    if print_request is None:
        raise ValueError(f"Print request {print_request_id} does not exist.")

    if print_request.status not in (
        PrintRequestStatus.APPROVED,
        PrintRequestStatus.PRINTING,
    ):
        raise ValueError(
            f"Ticket {print_request_id} must be active before it can be completed."
        )

    active = get_active_reservations_for_request(db, print_request_id)
    if not active:
        raise ValueError(f"Ticket {print_request_id} has no active reservations.")

    try:
        for reservation in active:
            current_weight = get_current_weight(db, reservation.spool_id)
            if current_weight < reservation.amount:
                raise ValueError(
                    f"Insufficient filament remains in spool {reservation.spool_id}."
                )

            db.add(
                InventoryEvent(
                    spool_id=reservation.spool_id,
                    event_type=InventoryEventType.FILAMENT_USED,
                    quantity_change=-reservation.amount,
                    machine_id=None,
                    user_id=user_id,
                    related_request_id=print_request_id,
                    note=f"Completion of ticket #{print_request_id}",
                )
            )
            db.add(
                ReservationEvent(
                    spool_id=reservation.spool_id,
                    print_request_id=print_request_id,
                    event_type=ReservationEventType.RESERVATION_FULFILLED,
                    amount=reservation.amount,
                    user_id=user_id,
                    related_event_id=reservation.id,
                )
            )

        print_request.status = PrintRequestStatus.COMPLETE
        db.commit()
    except Exception:
        db.rollback()
        raise
