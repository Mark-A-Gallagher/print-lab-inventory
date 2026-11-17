from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# Status given to a removed machine that still has event history.
# Hidden from the API; the row stays so old events keep a valid machine_id.
MACHINE_RETIRED = "retired"


class Machine(Base):
    """
    Represents a 3D printer in the lab.

    Unlike spool weight and machine assignment, a machine's operational
    status is stored directly on the machine because it is not
    event-sourced in V1.
    """

    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    spool_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offline")
