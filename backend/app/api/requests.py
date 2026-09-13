# requests.py (API router)
#
# DESIGN.md ref: Section 9 - Print request / reservation endpoints
#
# /{id}/fulfill is the most important endpoint in the whole API - it
# should call your reservations service's fulfill_reservation() function,
# which performs the atomic two-event write from Section 6.4. Keep this
# router thin; don't reimplement that logic here.
#

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import InventoryEvent, PrintRequest, Spool
from app.schemas.request import PrintRequestCreate, PrintRequestOut, ReservationCreate
from app.services.inventory import get_current_weight
from app.services.reservations import (
    create_reservation,
    fulfill_reservation,
    get_available,
    release_reservation,
)

router = APIRouter()


@router.post("/", response_model=PrintRequestOut, status_code=status.HTTP_201_CREATED)
def create_request(
    request_data: PrintRequestCreate,
    db: Session = Depends(get_db),
) -> PrintRequestOut:
    """
    Create a new print request.

    A print request represents a user's request to print a project using
    a specific material and amount of filament. The request starts in
    "Pending" status and can be moved through the workflow via the
    /reserve, /release, and /fulfill endpoints.

    Args:
        request_data: Creation data including requested_by, project_name, material_id, amount_grams
        db: Database session

    Returns:
        The created print request in Pending status

    Raises:
        HTTPException 404: If the material_id does not exist
        HTTPException 422: If validation fails
    """
    # Validate that the material exists
    from app.models import Material

    material = db.query(Material).filter(Material.id == request_data.material_id).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material with id {request_data.material_id} not found",
        )

    # Create the print request in Pending status
    print_request = PrintRequest(
        requested_by=request_data.requested_by,
        project_name=request_data.project_name,
        material_id=request_data.material_id,
        amount_grams=request_data.amount_grams,
        status="Pending",
    )
    db.add(print_request)
    db.commit()
    db.refresh(print_request)

    return PrintRequestOut(
        id=print_request.id,
        requested_by=print_request.requested_by,
        project_name=print_request.project_name,
        material_id=print_request.material_id,
        amount_grams=print_request.amount_grams,
        status=print_request.status,
    )


@router.get("/", response_model=list[PrintRequestOut])
def list_requests(db: Session = Depends(get_db)) -> list[PrintRequestOut]:
    """
    Retrieve all print requests.

    Returns:
        List of all print requests
    """
    requests = db.query(PrintRequest).all()

    return [
        PrintRequestOut(
            id=r.id,
            requested_by=r.requested_by,
            project_name=r.project_name,
            material_id=r.material_id,
            amount_grams=r.amount_grams,
            status=r.status,
        )
        for r in requests
    ]


@router.get("/{request_id}", response_model=PrintRequestOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
) -> PrintRequestOut:
    """
    Retrieve a single print request by ID.

    Args:
        request_id: The ID of the print request
        db: Database session

    Returns:
        The print request

    Raises:
        HTTPException 404: If the print request does not exist
    """
    print_request = db.query(PrintRequest).filter(PrintRequest.id == request_id).first()
    if not print_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Print request with id {request_id} not found",
        )

    return PrintRequestOut(
        id=print_request.id,
        requested_by=print_request.requested_by,
        project_name=print_request.project_name,
        material_id=print_request.material_id,
        amount_grams=print_request.amount_grams,
        status=print_request.status,
    )


@router.post(
    "/{request_id}/reserve",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
def reserve(
    request_id: int,
    reservation_data: ReservationCreate,
    db: Session = Depends(get_db),
) -> dict:
    """
    Create a reservation against a spool for a print request.

    V1 recommends the fullest compatible spool but does not auto-split
    across multiple spools. The amount reserved must not exceed the
    spool's available filament (current weight - already reserved amount).

    This endpoint must be called multiple times if the print request
    needs filament from multiple spools.

    Args:
        request_id: The ID of the print request
        reservation_data: Spool ID, amount, and user_id
        db: Database session

    Returns:
        The created reservation event details

    Raises:
        HTTPException 404: If the print request or spool does not exist
        HTTPException 422: If the reservation cannot be created (insufficient filament)
    """
    # Validate that the print request exists
    print_request = db.query(PrintRequest).filter(PrintRequest.id == request_id).first()
    if not print_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Print request with id {request_id} not found",
        )

    # Validate that the spool exists
    spool = db.query(Spool).filter(Spool.id == reservation_data.print_request_id).first()
    if not spool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Spool with id {reservation_data.print_request_id} not found",
        )

    try:
        reservation = create_reservation(
            db=db,
            spool_id=reservation_data.print_request_id,
            print_request_id=request_id,
            amount=reservation_data.amount,
            user_id=reservation_data.user_id,
        )

        return {
            "id": reservation.id,
            "spool_id": reservation.spool_id,
            "print_request_id": reservation.print_request_id,
            "amount": reservation.amount,
            "event_type": reservation.event_type,
            "created_at": reservation.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post("/{request_id}/release", status_code=status.HTTP_204_NO_CONTENT)
def release(
    request_id: int,
    reservation_id: int,
    user_id: str,
    db: Session = Depends(get_db),
) -> None:
    """
    Release an active reservation, freeing its filament back to availability.

    A reservation can only be released once. Attempting to release an
    already-released or fulfilled reservation will fail.

    Args:
        request_id: The ID of the print request (for validation)
        reservation_id: The ID of the original RESERVATION_CREATED event to release
        user_id: Identifier of the person releasing the reservation (query parameter)
        db: Database session

    Raises:
        HTTPException 404: If the print request or reservation does not exist
        HTTPException 422: If the reservation cannot be released (not active)
    """
    # Validate that the print request exists
    print_request = db.query(PrintRequest).filter(PrintRequest.id == request_id).first()
    if not print_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Print request with id {request_id} not found",
        )

    try:
        release_reservation(db=db, reservation_id=reservation_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post("/{request_id}/fulfill", status_code=status.HTTP_204_NO_CONTENT)
def fulfill(
    request_id: int,
    reservation_id: int,
    user_id: str,
    db: Session = Depends(get_db),
) -> None:
    """
    Fulfill a reservation: convert a planned allocation into an actual physical
    inventory reduction.

    This is the most critical endpoint in the API. It calls the reservations
    service's fulfill_reservation() function, which performs the atomic
    two-event write from Section 6.4 (fulfillment atomicity invariant).

    The fulfillment process:
      1. Confirms the reservation is active (not already released/fulfilled)
      2. Re-validates availability at fulfillment time (not just at reservation time)
      3. Inserts a FILAMENT_USED inventory event
      4. Inserts a RESERVATION_FULFILLED reservation event
      5. Both happen in a single transaction

    Args:
        request_id: The ID of the print request (for validation)
        reservation_id: The ID of the original RESERVATION_CREATED event
        user_id: Identifier of the person fulfilling the reservation (query parameter)
        db: Database session

    Raises:
        HTTPException 404: If the print request or reservation does not exist
        HTTPException 422: If the reservation cannot be fulfilled (not active or insufficient filament)
    """
    # Validate that the print request exists
    print_request = db.query(PrintRequest).filter(PrintRequest.id == request_id).first()
    if not print_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Print request with id {request_id} not found",
        )

    try:
        fulfill_reservation(db=db, reservation_id=reservation_id, user_id=user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
