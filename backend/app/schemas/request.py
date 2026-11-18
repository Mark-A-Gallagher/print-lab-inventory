# request.py (Pydantic schemas)
#
from pydantic import BaseModel, Field

from app.models.print_request import PrintRequestStatus


class PrintRequestCreate(BaseModel):
    id: int | None = Field(default=None, gt=0)
    requested_by: str = Field(min_length=1, max_length=100)
    project_name: str = Field(min_length=1, max_length=200)
    material_id: int | None = None
    amount_grams: int = Field(gt=0)
    color_count: int = Field(default=1, ge=1, le=20)


class PrintRequestOut(BaseModel):
    id: int
    requested_by: str
    project_name: str
    material_id: int
    amount_grams: int
    color_count: int
    status: PrintRequestStatus

    model_config = {"from_attributes": True}


class PrintRequestStatusUpdate(BaseModel):
    status: PrintRequestStatus


class ReservationAllocation(BaseModel):
    spool_id: int
    amount: float = Field(gt=0)


class ReservationBatchCreate(BaseModel):
    allocations: list[ReservationAllocation]
    user_id: str = Field(min_length=1, max_length=100)


class ReservationCreate(BaseModel):
    # The print request comes from the URL (/requests/{id}/reserve),
    # so the body only needs the spool to reserve from.
    spool_id: int
    amount: float = Field(gt=0)
    user_id: str = Field(min_length=1, max_length=100)
