# spools.py (API router)
#
# DESIGN.md ref: Section 9 - Spool endpoints
#
# Remember the critical rule from Section 2: this router must never trust
# the frontend's judgment about validity. Every mutating endpoint here
# should call into your services layer for validation before any event
# is inserted - don't put business logic directly in these route handlers.
#

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InventoryEventType, Material, Spool
from app.schemas.spool import (
    SpoolAssignment,
    SpoolCorrection,
    SpoolCreate,
    SpoolOut,
    WeightUpdate,
)
from app.services.inventory import (
    assign_to_machine,
    get_current_machine,
    get_current_weight,
    record_correction,
    record_weight_adjustment,
    remove_from_machine,
)
from app.services.reservations import get_available, get_reserved_amount

router = APIRouter()


@router.post("/", response_model=SpoolOut, status_code=status.HTTP_201_CREATED)
def create_spool(
    spool_data: SpoolCreate,
    db: Session = Depends(get_db),
) -> SpoolOut:
    """
    Create a new spool with an initial SPOOL_CREATED inventory event.

    This endpoint creates both:
      1. A new Spool row with stable metadata
      2. A SPOOL_CREATED inventory event establishing the initial weight

    These are created together to ensure "history starts at zero" (Section 4.1).

    Args:
        spool_data: Creation data including material_id, original_weight, empty_spool_weight
        db: Database session

    Returns:
        The created spool with derived fields (current weight, reserved amount, available)

    Raises:
        HTTPException 404: If the material_id does not exist
        HTTPException 422: If validation fails
    """
    from app.models import InventoryEvent

    # Validate that the material exists
    material = db.query(Material).filter(Material.id == spool_data.material_id).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material with id {spool_data.material_id} not found",
        )

    # Create the Spool row
    spool = Spool(
        material_id=spool_data.material_id,
        original_weight=spool_data.original_weight,
        empty_spool_weight=spool_data.empty_spool_weight,
        low_stock_threshold=spool_data.low_stock_threshold,
    )
    db.add(spool)
    db.flush()  # Flush to get the spool.id without committing yet

    # Create the initial SPOOL_CREATED inventory event
    starting_event = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.SPOOL_CREATED,
        quantity_change=float(spool_data.original_weight),
        user_id="system",  # System-created during spool creation
    )
    db.add(starting_event)
    db.commit()

    # Build the response with derived fields
    return SpoolOut(
        id=spool.id,
        material_id=spool.material_id,
        original_weight=spool.original_weight,
        low_stock_threshold=spool.low_stock_threshold,
        current_weight=get_current_weight(db, spool.id),
        current_machine_id=get_current_machine(db, spool.id),
        reserved_amount=get_reserved_amount(db, spool.id),
        available=get_available(db, spool.id),
    )


@router.get("/", response_model=list[SpoolOut])
def list_spools(db: Session = Depends(get_db)) -> list[SpoolOut]:
    """
    Retrieve all spools with their derived fields.

    Each spool includes:
      - current_weight: Calculated from inventory events
      - reserved_amount: Calculated from reservation events
      - available: current_weight - reserved_amount
      - current_machine_id: Current machine assignment (if any)

    Returns:
        List of all spools with derived fields attached
    """
    spools = db.query(Spool).all()

    response = []
    for spool in spools:
        response.append(
            SpoolOut(
                id=spool.id,
                material_id=spool.material_id,
                original_weight=spool.original_weight,
                low_stock_threshold=spool.low_stock_threshold,
                current_weight=get_current_weight(db, spool.id),
                current_machine_id=get_current_machine(db, spool.id),
                reserved_amount=get_reserved_amount(db, spool.id),
                available=get_available(db, spool.id),
            )
        )

    return response


@router.get("/{spool_id}", response_model=SpoolOut)
def get_spool(
    spool_id: int,
    db: Session = Depends(get_db),
) -> SpoolOut:
    """
    Retrieve a single spool by ID with all derived fields.

    This endpoint is also used by the QR-code scanning page (Release 0.4).

    Args:
        spool_id: The ID of the spool to retrieve
        db: Database session

    Returns:
        The spool with derived fields attached

    Raises:
        HTTPException 404: If the spool does not exist
    """
    spool = db.query(Spool).filter(Spool.id == spool_id).first()
    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spool with id {spool_id} not found",
        )

    return SpoolOut(
        id=spool.id,
        material_id=spool.material_id,
        original_weight=spool.original_weight,
        low_stock_threshold=spool.low_stock_threshold,
        current_weight=get_current_weight(db, spool.id),
        current_machine_id=get_current_machine(db, spool.id),
        reserved_amount=get_reserved_amount(db, spool.id),
        available=get_available(db, spool.id),
    )


@router.post("/{spool_id}/weight", status_code=status.HTTP_204_NO_CONTENT)
def update_weight(
    spool_id: int,
    weight_data: WeightUpdate,
    db: Session = Depends(get_db),
) -> None:
    """
    Update the spool's weight via a WEIGHT_ADJUSTMENT inventory event.

    This endpoint records a weight measurement and calculates the delta
    from the current recorded weight. The adjustment is recorded as a
    WEIGHT_ADJUSTMENT event (Section 4.1).

    Args:
        spool_id: The ID of the spool being updated
        weight_data: New total weight and user ID
        db: Database session

    Raises:
        HTTPException 404: If the spool does not exist
        HTTPException 422: If the weight adjustment fails (e.g., results in negative weight)
    """
    # Validate that the spool exists
    spool = db.query(Spool).filter(Spool.id == spool_id).first()
    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spool with id {spool_id} not found",
        )

    try:
        record_weight_adjustment(
            db=db,
            spool_id=spool_id,
            new_total_weight=weight_data.new_total_weight,
            user_id=weight_data.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post("/{spool_id}/correct", status_code=status.HTTP_204_NO_CONTENT)
def correct_event(
    spool_id: int,
    correction_data: SpoolCorrection,
    db: Session = Depends(get_db),
) -> None:
    """
    Correct a previous inventory event via a SPOOL_CORRECTION event.

    This endpoint does NOT allow editing the original event. Instead,
    it records a new SPOOL_CORRECTION event that references the original
    (Section 6.5 - UI should call this "Correct Event," not "Edit").

    Args:
        spool_id: The ID of the spool being corrected
        correction_data: Related event ID, amount, reason, and user ID
        db: Database session

    Raises:
        HTTPException 404: If the spool or related event does not exist
        HTTPException 422: If the correction fails (e.g., would result in negative weight)
    """
    # Validate that the spool exists
    spool = db.query(Spool).filter(Spool.id == spool_id).first()
    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spool with id {spool_id} not found",
        )

    try:
        record_correction(
            db=db,
            related_event_id=correction_data.related_event_id,
            amount=correction_data.amount,
            reason=correction_data.reason,
            user_id=correction_data.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post("/{spool_id}/assign", status_code=status.HTTP_204_NO_CONTENT)
def assign_to_machine_endpoint(
    spool_id: int,
    assignment_data: SpoolAssignment,
    db: Session = Depends(get_db),
) -> None:
    """
    Assign a spool to a machine via an ASSIGNED_TO_MACHINE event.

    This endpoint records the spool's assignment to a machine. A spool
    can only be assigned to one machine at a time. To reassign it,
    it must first be removed via the unassign endpoint.

    Args:
        spool_id: The ID of the spool being assigned
        assignment_data: Machine ID and user ID
        db: Database session

    Raises:
        HTTPException 404: If the spool or machine does not exist
        HTTPException 422: If the spool is already assigned to another machine
    """
    from app.models import Machine

    # Validate that the spool exists
    spool = db.query(Spool).filter(Spool.id == spool_id).first()
    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spool with id {spool_id} not found",
        )

    # Validate that the machine exists
    machine = db.query(Machine).filter(Machine.id == assignment_data.machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with id {assignment_data.machine_id} not found",
        )

    try:
        assign_to_machine(
            db=db,
            spool_id=spool_id,
            machine_id=assignment_data.machine_id,
            user_id=assignment_data.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post("/{spool_id}/unassign", status_code=status.HTTP_204_NO_CONTENT)
def unassign_from_machine_endpoint(
    spool_id: int,
    user_id: str,
    db: Session = Depends(get_db),
) -> None:
    """
    Remove a spool from its currently assigned machine.

    This endpoint records the spool's removal from a machine via a
    REMOVED_FROM_MACHINE event. The spool must currently be assigned
    to a machine for this to succeed.

    Args:
        spool_id: The ID of the spool being unassigned
        user_id: Identifier of the person performing the action (query parameter)
        db: Database session

    Raises:
        HTTPException 404: If the spool does not exist
        HTTPException 422: If the spool is not currently assigned to any machine
    """
    # Validate that the spool exists
    spool = db.query(Spool).filter(Spool.id == spool_id).first()
    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spool with id {spool_id} not found",
        )

    try:
        remove_from_machine(db=db, spool_id=spool_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
