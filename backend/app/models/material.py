# material.py
#
# DESIGN.md ref: Section 3 (Domain Model)
#

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Material(Base):
    """
    Represents a type of filament material available in the lab.

    A material describes the filament category and optionally its color.
    Individual spools reference a Material rather than storing these
    values directly on the spool.
    """

    __tablename__ = "materials"

    # Unique identifier for this material.
    id: Mapped[int] = mapped_column(primary_key=True)

    # Material type, such as PLA, PETG, or TPU.
    name: Mapped[str] = mapped_column(String(50), nullable=False)

    # Optional filament color, such as Black, White, or Red.
    color: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
