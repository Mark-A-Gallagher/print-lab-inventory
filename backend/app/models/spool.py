# spool.py
#
# DESIGN.md ref: Section 3 (Domain Model), Section 8 (Database Schema)
#

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Spool(Base):
    """
    Represents an individual physical filament spool.

    A spool stores only stable information about the physical spool.
    Current filament weight and current machine assignment are derived
    from inventory events and are intentionally NOT stored on this model.
    """

    __tablename__ = "spools"

    # Unique identifier for the spool.
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Material associated with this spool.
    #
    # This references the materials table rather than duplicating
    # material information on every spool.
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False)

    # Amount of filament originally contained on the spool, in grams.
    #
    # Example: a standard 1kg spool would have a value of 1000.
    original_weight: Mapped[int] = mapped_column(Integer, nullable=False)

    # Weight of the empty spool itself, in grams.
    #
    # This allows us to distinguish the weight of the plastic spool
    # from the weight of the filament when a physical weighing is done.
    empty_spool_weight: Mapped[int] = mapped_column(Integer, nullable=False)

    # Amount of remaining filament at which the spool should be
    # considered low stock, in grams.
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
