# request.py (Pydantic schemas)
#
from pydantic import BaseModel, Field

from app.models.print_request import PrintRequestStatus


class PrintRequestCreate(BaseModel):
    requested_by: str = Field(min_length=1, max_length=100)
    project_name: str = Field(min_length=1, max_length=200)
    material_id: int
    amount_grams: float = Field(gt=0)


class PrintRequestOut(BaseModel):
    id: int
    requested_by: str
    project_name: str
    material_id: int
    amount_grams: float
    status: PrintRequestStatus

    model_config = {"from_attributes": True}


class ReservationCreate(BaseModel):
    print_request_id: int
    amount: float = Field(gt=0)
    user_id: str = Field(min_length=1, max_length=100)
