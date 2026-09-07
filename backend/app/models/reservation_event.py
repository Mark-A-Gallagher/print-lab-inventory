# reservation_event.py
#
# DESIGN.md ref: Section 4.2 (Reservation Events)
#

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReservationEventType(str, Enum):
    """
    Types of events that can occur in the reservation system.

    Reservation events describe planned allocations of filament.
    They do not directly change the physical inventory of a spool.
    """

    RESERVATION_CREATED = "RESERVATION_CREATED"
    RESERVATION_RELEASED = "RESERVATION_RELEASED"
    RESERVATION_FULFILLED = "RESERVATION_FULFILLED"


class ReservationEvent(Base):
    """
    Immutable event representing a change to a filament reservation.

    Reservations represent planned or committed allocations of filament,
    while inventory events represent actual physical inventory changes.

    A reservation therefore does not reduce the spool's physical filament
    amount. It only reduces the amount considered available for other
    reservations or print requests.

    IMPORTANT:
        ReservationEvent rows are append-only. Existing events must never
        be updated or deleted. A reservation is released or fulfilled by
        creating a new event referencing its original CREATED event.
    """

    __tablename__ = "reservation_events"

    # Unique identifier for this reservation event.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    # Spool whose filament is being reserved.
    spool_id: Mapped[int] = mapped_column(
        ForeignKey("spools.id"),
        nullable=False,
    )

    # Print request that caused the reservation.
    print_request_id: Mapped[int] = mapped_column(
        ForeignKey("print_requests.id"),
        nullable=False,
    )

    # Type of reservation event.
    event_type: Mapped[ReservationEventType] = mapped_column(
        SQLEnum(ReservationEventType),
        nullable=False,
    )

    # Amount of filament involved in reservation, measured in grams.
    #
    # For CREATED:
    #   amount = amount being reserved
    #
    # For RELEASED:
    #   amount = amount being released
    #
    # For FULFILLED:
    #   amount = amount being fulfilled
    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Identifier of the person who performed the action.
    #
    # V1 intentionally uses a simple identifier rather than a full
    # authentication/user system.
    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # References the original CREATED event when this event releases
    # or fulfills a reservation.
    #
    # Example:
    #
    #   Event #12 → RESERVATION_CREATED
    #   Event #18 → RESERVATION_FULFILLED
    #                  related_event_id = 12
    #
    # This allows the complete lifecycle of a reservation to be traced.
    related_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("reservation_events.id"),
        nullable=True,
    )

    # Time at which the reservation event was created.
    #
    # Events are immutable, so this timestamp should never be changed.
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
