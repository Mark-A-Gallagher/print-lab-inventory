# inventory.py
#
# DESIGN.md ref: Section 5 (Core Invariants) - inventory + machine
# assignment invariants. These are the two most important functions in
# the whole backend - almost everything else depends on them being
# correct, so make sure you actually understand the SQL you write here
# rather than just getting it to pass a test.
#

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import InventoryEvent, InventoryEventType, Spool


def get_current_weight(db: Session, spool_id: int) -> float:
    """
    Get the current filament weight for a given spool.

    This function calculates the current filament weight by summing the
    `quantity_change` of all inventory events associated with the specified
    spool. Events with a NULL `quantity_change` are ignored in the sum.

    Args:
        db (Session): The SQLAlchemy database session.
        spool_id (int): The ID of the spool for which to calculate the current weight.

    Returns:
        float: The current filament weight for the specified spool.
    """
    current_weight = (
        db.query(func.coalesce(func.sum(InventoryEvent.quantity_change), 0.0))
        .filter(InventoryEvent.spool_id == spool_id)
        .scalar()
    )
    return float(current_weight)


def get_current_machine(db: Session, spool_id: int) -> int | None:
    """
    Get the current machine assignment for a given spool.

    This function retrieves the most recent machine assignment event
    (either ASSIGNED_TO_MACHINE or REMOVED_FROM_MACHINE) for the specified
    spool and returns the associated machine ID. If there are no relevant
    events, it returns None.

    Args:
        db (Session): The SQLAlchemy database session.
        spool_id (int): The ID of the spool for which to retrieve the current machine assignment.

    Returns:
        int | None: The ID of the currently assigned machine, or None if no assignment exists.
    """
    latest_event = (
        db.query(InventoryEvent)
        .filter(
            InventoryEvent.spool_id == spool_id,
            InventoryEvent.event_type.in_(
                [
                    InventoryEventType.ASSIGNED_TO_MACHINE,
                    InventoryEventType.REMOVED_FROM_MACHINE,
                ]
            ),
        )
        .order_by(InventoryEvent.created_at.desc(), InventoryEvent.id.desc())
        .first()
    )

    if latest_event is None:
        return None

    if latest_event.event_type == InventoryEventType.ASSIGNED_TO_MACHINE:
        return latest_event.machine_id
    else:
        return None  # If the latest event is REMOVED_FROM_MACHINE, return None


def record_filament_used(
    db: Session, spool_id: int, amount: float, user_id: str
) -> None:
    """
    Record the usage of filament from a spool.

    This function creates a new inventory event of type FILAMENT_USED,
    representing the usage of a specified amount of filament from the
    given spool. It ensures that the current weight of the spool does not
    go below zero after the usage.

    Args:
        db (Session): The SQLAlchemy database session.
        spool_id (int): The ID of the spool from which filament is being used.
        amount (float): The amount of filament used, measured in grams.
        user_id (str): The identifier of the person who performed the action.
    Raises:
    ValueError: If the requested usage would reduce the spool's
        weight below zero.
    """
    current_weight = get_current_weight(db, spool_id)
    if current_weight - amount < 0:
        raise ValueError("Insufficient filament weight for the requested usage.")

    new_event = InventoryEvent(
        spool_id=spool_id,
        event_type=InventoryEventType.FILAMENT_USED,
        quantity_change=-amount,  # Negative because filament is being used
        machine_id=None,  # Not applicable for this event type
        user_id=user_id,
    )
    db.add(new_event)
    db.commit()


def record_weight_adjustment(
    db: Session, spool_id: int, new_total_weight: float, user_id: str
) -> None:
    """
    Record a weight adjustment for a spool.

    This function creates a new inventory event of type WEIGHT_ADJUSTMENT,
    representing an adjustment to the total weight of filament in the
    specified spool. It calculates the quantity change based on the
    difference between the new total weight and the current weight.

    Args:
        db (Session): The SQLAlchemy database session.
        spool_id (int): The ID of the spool for which the weight is being adjusted.
        new_total_weight (float): The new total weight of filament in grams.
        user_id (str): The identifier of the person who performed the action.
    """
    spool = db.get(Spool, spool_id)  # look up the spool row itself
    empty_weight = spool.empty_spool_weight  # already stored, not computed

    # Calculate net filament weight
    new_filament_weight = new_total_weight - empty_weight

    # Scale reading lighter than the empty spool - bad input
    if new_filament_weight < 0:
        raise ValueError("Total weight cannot be less than the empty spool weight.")

    current_weight = get_current_weight(db, spool_id)

    # Delta between new and current filament weight
    quantity_change = new_filament_weight - current_weight

    # Zero-floor guard: prevent adjusting below zero current weight
    if current_weight + quantity_change < 0:
        raise ValueError("Adjustment would result in negative filament weight.")

    # Construct and insert the InventoryEvent
    event = InventoryEvent(
        spool_id=spool_id,
        quantity_change=quantity_change,
        user_id=user_id,
        event_type=InventoryEventType.WEIGHT_ADJUSTMENT,
        machine_id=None,  # Not applicable for this event type
    )
    db.add(event)
    db.commit()


def record_correction(
    db: Session,
    related_event_id: int,
    amount: float,
    reason: str,
    user_id: str,
) -> None:
    """
    Record a correction to a previous inventory event.

    This function creates a new inventory event of type SPOOL_CORRECTION,
    representing a correction to a previous inventory event. It references
    the original event and includes the reason for the correction.

    Args:
        db (Session): The SQLAlchemy database session.
        related_event_id (int): The ID of the original inventory event being corrected.
        amount (float): The amount of filament involved in the correction, measured in grams.
        reason (str): The reason for the correction.
        user_id (str): The identifier of the person who performed the action.
    """

    original_event = db.get(InventoryEvent, related_event_id)

    if original_event is None:
        raise ValueError(f"No inventory event found with id {related_event_id}")

    spool_id = original_event.spool_id

    current_weight = get_current_weight(db, spool_id)

    if current_weight + amount < 0:
        raise ValueError("Correction would result in negative filament weight.")

    new_event = InventoryEvent(
        spool_id=spool_id,
        event_type=InventoryEventType.SPOOL_CORRECTION,
        quantity_change=amount,  # Positive or negative based on correction
        machine_id=None,  # Not applicable for this event type
        user_id=user_id,
        related_event_id=related_event_id,
        note=reason,
    )
    db.add(new_event)
    db.commit()


def assign_to_machine(
    db: Session, spool_id: int, machine_id: int, user_id: str
) -> None:
    """
    Assign a spool to a machine.

    This function creates a new inventory event of type ASSIGNED_TO_MACHINE,
    representing the assignment of a spool to a specific machine. It ensures
    that the spool is not already assigned to a different machine.

    Args:
        db (Session): The SQLAlchemy database session.
        spool_id (int): The ID of the spool being assigned.
        machine_id (int): The ID of the machine to which the spool is being assigned.
        user_id (str): The identifier of the person who performed the action.

    Raises:
        ValueError: If the spool is already assigned to any machine.
    """
    current_machine = get_current_machine(db, spool_id)

    if current_machine is not None:
        raise ValueError(
            f"Spool {spool_id} is already assigned to machine {current_machine}."
        )

    new_event = InventoryEvent(
        spool_id=spool_id,
        event_type=InventoryEventType.ASSIGNED_TO_MACHINE,
        quantity_change=None,  # Not applicable for this event type
        machine_id=machine_id,
        user_id=user_id,
    )
    db.add(new_event)
    db.commit()


def remove_from_machine(db: Session, spool_id: int, user_id: str) -> None:
    """
    Remove a spool from its currently assigned machine.

    This function creates a new inventory event of type REMOVED_FROM_MACHINE,
    representing the removal of a spool from its currently assigned machine.
    It ensures that the spool is currently assigned to a machine before
    proceeding with the removal.

    Args:
        db (Session): The SQLAlchemy database session.
        spool_id (int): The ID of the spool being removed from the machine.
        user_id (str): The identifier of the person who performed the action.

    Raises:
        ValueError: If the spool is not currently assigned to any machine.
    """
    current_machine = get_current_machine(db, spool_id)

    if current_machine is None:
        raise ValueError(f"Spool {spool_id} is not currently assigned to any machine.")

    new_event = InventoryEvent(
        spool_id=spool_id,
        event_type=InventoryEventType.REMOVED_FROM_MACHINE,
        quantity_change=None,  # Not applicable for this event type
        machine_id=current_machine,
        user_id=user_id,
    )
    db.add(new_event)
    db.commit()
