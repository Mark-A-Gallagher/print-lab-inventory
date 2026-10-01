# spool.py (Pydantic schemas)
#
# DESIGN.md ref: Section 3, Section 9 (spool endpoints)
#
from pydantic import BaseModel, Field


class SpoolCreate(BaseModel):
    material_id: int
    material_type: str | None = Field(default=None, max_length=50)
    color: str | None = Field(default=None, max_length=50)
    original_weight: int = Field(gt=0)
    empty_spool_weight: int = Field(ge=0)
    low_stock_threshold: float = Field(ge=0)


class SpoolOut(BaseModel):
    id: int
    material_id: int
    original_weight: float
    low_stock_threshold: float

    # From the spool's material, so cards can show what is on the spool.
    material_type: str | None = None
    color: str | None = None

    # Derived from inventory and reservation events.
    current_weight: float
    current_machine_id: int | None
    reserved_amount: float
    available: float

    model_config = {"from_attributes": True}


class WeightUpdate(BaseModel):
    new_total_weight: float = Field(ge=0)
    user_id: str = Field(min_length=1, max_length=100)


class SpoolAssignment(BaseModel):
    machine_id: int
    user_id: str = Field(min_length=1, max_length=100)


class SpoolUnassignment(BaseModel):
    # The machine is looked up from the spool's current assignment,
    # so the caller only says who is doing it.
    user_id: str = Field(min_length=1, max_length=100)


class SpoolCorrection(BaseModel):
    related_event_id: int
    user_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=500)
    amount: int
