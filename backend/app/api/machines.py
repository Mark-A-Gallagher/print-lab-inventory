# machines.py (API router)
#
# DESIGN.md ref: Section 9 - Machine endpoints
#

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InventoryEvent, InventoryEventType, Machine
from app.models.machine import MACHINE_RETIRED
from app.schemas.machine import MachineCreate, MachineOut, MachineStatusUpdate
from app.services.inventory import get_current_machine

router = APIRouter()


def _get_active_machine(db: Session, machine_id: int) -> Machine:
    """Fetch a machine that has not been removed, or raise 404."""
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine or machine.status == MACHINE_RETIRED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {machine_id} not found",
        )
    return machine


def get_current_spool_for_machine(db: Session, machine_id: int) -> int | None:
    """
    Helper function to find the currently assigned spool for a machine.

    This queries the most recent ASSIGNED_TO_MACHINE or REMOVED_FROM_MACHINE
    event for this machine across all spools to determine the current assignment.

    Args:
        db: Database session
        machine_id: The machine to query

    Returns:
        The spool_id currently assigned to this machine, or None if no assignment
    """
    # Find all assignment/removal events involving this machine, ordered by recency
    latest_event = (
        db.query(InventoryEvent)
        .filter(
            InventoryEvent.machine_id == machine_id,
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

    # If the latest event is an assignment, return the spool_id
    if latest_event.event_type == InventoryEventType.ASSIGNED_TO_MACHINE:
        return latest_event.spool_id

    # If the latest event is a removal, no spool is currently assigned
    return None


@router.post("/", response_model=MachineOut, status_code=status.HTTP_201_CREATED)
def create_machine(
    machine_data: MachineCreate,
    db: Session = Depends(get_db),  # noqa: B008
) -> MachineOut:
    """
    Create a new machine (3D printer).

    Machines do not use event sourcing in V1 - their status is stored
    directly on the machine row.

    Args:
        machine_data: Creation data including name
        db: Database session

    Returns:
        The created machine with current_spool_id (initially None)

    Raises:
        HTTPException 422: If validation fails
    """
    machine = Machine(name=machine_data.name, status="offline")
    db.add(machine)
    db.commit()
    db.refresh(machine)

    return MachineOut(
        id=machine.id,
        name=machine.name,
        status=machine.status,
        current_spool_id=None,  # New machines have no assigned spool
    )


@router.get("/", response_model=list[MachineOut])
def list_machines(db: Session = Depends(get_db)) -> list[MachineOut]:  # noqa: B008
    """
    Retrieve all machines with their current spool assignment (if any).

    Each machine includes:
      - id, name, status (stored directly on the machine)
      - current_spool_id: The spool currently assigned to this machine (derived from events)

    Returns:
        List of all machines with current assignments
    """
    machines = db.query(Machine).filter(Machine.status != MACHINE_RETIRED).all()

    response = []
    for machine in machines:
        response.append(
            MachineOut(
                id=machine.id,
                name=machine.name,
                status=machine.status,
                current_spool_id=get_current_spool_for_machine(db, machine.id),
            )
        )

    return response


@router.get("/{machine_id}", response_model=MachineOut)
def get_machine(
    machine_id: int,
    db: Session = Depends(get_db),  # noqa: B008
) -> MachineOut:
    """
    Retrieve a single machine by ID.

    Args:
        machine_id: The ID of the machine to retrieve
        db: Database session

    Returns:
        The machine with its current spool assignment (if any)

    Raises:
        HTTPException 404: If the machine does not exist
    """
    machine = _get_active_machine(db, machine_id)

    return MachineOut(
        id=machine.id,
        name=machine.name,
        status=machine.status,
        current_spool_id=get_current_spool_for_machine(db, machine_id),
    )


@router.patch("/{machine_id}", response_model=MachineOut)
def update_machine_status(
    machine_id: int,
    status_data: MachineStatusUpdate,
    db: Session = Depends(get_db),  # noqa: B008
) -> MachineOut:
    """
    Update a machine's operational status (e.g., online/offline).

    Since machine status is not event-sourced in V1, it is updated
    directly on the machine row.

    Args:
        machine_id: The ID of the machine to update
        status_data: New status (e.g., "online" or "offline")
        db: Database session

    Returns:
        The updated machine

    Raises:
        HTTPException 404: If the machine does not exist
    """
    machine = _get_active_machine(db, machine_id)

    machine.status = status_data.status
    db.commit()
    db.refresh(machine)

    return MachineOut(
        id=machine.id,
        name=machine.name,
        status=machine.status,
        current_spool_id=get_current_spool_for_machine(db, machine_id),
    )


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(
    machine_id: int,
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    """
    Remove a machine.

    Inventory events are append-only and reference machines by id, so:
      - a machine with no history is deleted outright
      - a machine that appears in any event is retired instead (hidden
        everywhere, row kept so history stays valid)

    Raises:
        HTTPException 404: If the machine does not exist
        HTTPException 422: If a spool is still assigned to the machine
    """
    machine = _get_active_machine(db, machine_id)

    # Spools that have ever been assigned to / removed from this machine.
    spool_ids = [
        row[0]
        for row in db.query(InventoryEvent.spool_id)
        .filter(InventoryEvent.machine_id == machine_id)
        .distinct()
        .all()
    ]

    if any(get_current_machine(db, sid) == machine_id for sid in spool_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Machine still has filament assigned. Remove it first.",
        )

    if spool_ids:
        machine.status = MACHINE_RETIRED
    else:
        db.delete(machine)
    db.commit()
