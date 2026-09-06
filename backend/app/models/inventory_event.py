# inventory_event.py
#
# DESIGN.md ref: Section 4.1 (Inventory Events)
#

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InventoryEventType(str, Enum):
    """
    Types of events that can occur in the inventory system.

    Inventory events are immutable. Changes to inventory are represented
    by adding new events rather than modifying existing events.
    """

    SPOOL_CREATED = "SPOOL_CREATED"
    FILAMENT_USED = "FILAMENT_USED"
    WEIGHT_ADJUSTMENT = "WEIGHT_ADJUSTMENT"
    SPOOL_CORRECTION = "SPOOL_CORRECTION"
    ASSIGNED_TO_MACHINE = "ASSIGNED_TO_MACHINE"
    REMOVED_FROM_MACHINE = "REMOVED_FROM_MACHINE"


class InventoryEvent(Base):
    """
    Immutable event representing a change or action involving a spool.

    This table is the source of truth for event-sourced inventory state.

    Current filament weight is calculated from the applicable inventory
    events rather than being stored directly on the Spool model.

    Machine assignment is also derived from the assignment/removal events.

    IMPORTANT:
        InventoryEvent rows are append-only. Existing events must never
        be updated or deleted. Corrections are represented by creating
        a new SPOOL_CORRECTION event.
    """

    __tablename__ = "inventory_events"

    # Unique identifier for the event.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    # Spool affected by this event.
    spool_id: Mapped[int] = mapped_column(
        ForeignKey("spools.id"),
        nullable=False,
    )

    # Type of inventory event.
    event_type: Mapped[InventoryEventType] = mapped_column(
        SQLEnum(InventoryEventType),
        nullable=False,
    )

    # Change in filament quantity, measured in grams.
    #
    # Not every event changes inventory weight:
    #
    #   SPOOL_CREATED          → quantity change
    #   FILAMENT_USED          → quantity change
    #   WEIGHT_ADJUSTMENT      → quantity change
    #   SPOOL_CORRECTION       → quantity change
    #   ASSIGNED_TO_MACHINE    → NULL
    #   REMOVED_FROM_MACHINE   → NULL
    #
    # A nullable field allows machine assignment events to exist without
    # pretending that they changed the amount of filament.
    quantity_change: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Machine involved in an assignment/removal event.
    #
    # This should only be populated for:
    #   ASSIGNED_TO_MACHINE
    #   REMOVED_FROM_MACHINE
    machine_id: Mapped[int | None] = mapped_column(
        ForeignKey("machines.id"),
        nullable=True,
    )

    # Identifier of the person who performed the action.
    #
    # V1 intentionally uses a simple identifier rather than a full
    # authentication/user system.
    user_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    # References another inventory event when this event is related
    # directly to it.
    #
    # Most importantly, SPOOL_CORRECTION events can point to the
    # incorrect event they are correcting.
    #
    # Reservation events live in a separate event stream, so this field
    # should NOT be used to reference reservation_events.
    related_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("inventory_events.id"),
        nullable=True,
    )

    # Print request associated with this inventory event, when applicable.
    related_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("print_requests.id"),
        nullable=True,
    )

    # Optional explanation or additional context for the event.
    note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Time at which the event was created.
    #
    # The timestamp is assigned by the server when the event is inserted and should
    # never be modified afterward.
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
