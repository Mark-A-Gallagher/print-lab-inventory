# print_request.py
#
# DESIGN.md ref: Section 3 (Domain Model)
#

from enum import Enum

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PrintRequestStatus(str, Enum):
    """
    Valid states for a print request.

    Requests move through these states as they are processed by the lab.
    """

    PENDING = "Pending"
    APPROVED = "Approved"
    PRINTING = "Printing"
    COMPLETE = "Complete"
    REJECTED = "Rejected"


class PrintRequest(Base):
    """
    Represents a request to print a project using a specific material.

    V1 uses a simple identifier for the requester instead of full user
    authentication. The requested material is linked to the Material
    table, while the amount required is stored in grams.
    """

    __tablename__ = "print_requests"

    # Unique identifier for the print request.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Identifier of the person who submitted the request.
    #
    # V1 intentionally does not use a User/authentication system.
    requester_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Name of the project being requested.
    project_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Material required for this print request.
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False)

    # Amount of filament required, measured in grams.
    amount_grams: Mapped[int] = mapped_column(Integer, nullable=False)

    # Current status of the request.
    #
    # SQLAlchemy stores the allowed PrintRequestStatus values in the
    # database rather than allowing arbitrary strings.
    status: Mapped[PrintRequestStatus] = mapped_column(
        SQLEnum(PrintRequestStatus), nullable=False, default=PrintRequestStatus.PENDING
    )
