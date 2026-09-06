# models/__init__.py
#
# DESIGN.md ref: Section 3 (Domain Model)
#
# Re-export all SQLAlchemy models from this package so other modules
# can import them directly:
#
#     from app.models import Spool
#
# instead of:
#
#     from app.models.spool import Spool
#

from app.models.inventory_event import InventoryEvent, InventoryEventType
from app.models.machine import Machine
from app.models.material import Material
from app.models.print_request import PrintRequest, PrintRequestStatus
from app.models.reservation_event import (
    ReservationEvent,
    ReservationEventType,
)
from app.models.spool import Spool

__all__ = [
    "InventoryEvent",
    "InventoryEventType",
    "Machine",
    "Material",
    "PrintRequest",
    "PrintRequestStatus",
    "ReservationEvent",
    "ReservationEventType",
    "Spool",
]
