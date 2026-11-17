# machine.py (Pydantic schemas)
#
# DESIGN.md ref: Section 3, Section 9
#
from pydantic import BaseModel, Field


class MachineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    spool_capacity: int = Field(default=1, ge=1, le=100)


class MachineOut(BaseModel):
    id: int
    name: str
    spool_capacity: int
    status: str

    model_config = {"from_attributes": True}


class MachineStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=20)
