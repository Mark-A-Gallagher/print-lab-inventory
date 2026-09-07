# machine.py
#
# DESIGN.md ref: Section 3 (Domain Model)
#

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Machine(Base):
    """
    Represents a 3D printer in the lab.

    Unlike spool weight and machine assignment, a machine's operational
    status is stored directly on the machine because it is not
    event-sourced in V1.
    """

    __tablename__ = "machines"

    # Unique identifier for the machine.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Human-readable machine name.
    #
    # Example: "Printer #1" or "Bambu Lab A1".
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Current operational status of the machine.
    #
    # Expected values in V1:
    #   - "online"
    #   - "offline"
    #
    # This is deliberately stored as a normal field rather than
    # being derived from an event stream.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline")
