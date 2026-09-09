# test_fulfillment.py
#
# DESIGN.md ref: Section 10, Section 6.4
#
# These tests are the executable version of the fulfillment atomicity
# invariant. Fulfillment is one of the most important operations in
# the inventory system because it connects reservation events with
# actual inventory events.
#

import pytest
from app.models import (
    InventoryEvent,
    InventoryEventType,
    Material,
    PrintRequest,
    ReservationEvent,
    ReservationEventType,
    Spool,
)
from app.services.inventory import get_current_weight
from app.services.reservations import (
    create_reservation,
    fulfill_reservation,
)


def create_test_spool(db_session, weight=500):
    """
    Create a test material and spool with an initial inventory event.

    Current filament weight is event-sourced, so the initial weight
    must be established through a SPOOL_CREATED inventory event.
    """

    # Create a material.
    material = Material(name="Black PLA")
    db_session.add(material)
    db_session.commit()  # commit so `material.id` gets assigned

    # Create a spool.
    spool = Spool(
        material_id=material.id,
        original_weight=weight,
        empty_spool_weight=100,
        low_stock_threshold=100,
    )
    db_session.add(spool)
    db_session.commit()  # commit so `spool.id` gets assigned

    # Establish the spool's initial filament weight through the
    # event-sourced inventory system.
    creation_event = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.SPOOL_CREATED,
        quantity_change=weight,
        user_id="test-user",
        note="Initial test spool",
    )
    db_session.add(creation_event)
    db_session.commit()

    return spool


def create_test_request(db_session, material_id, amount=400):
    """
    Create a print request for the test spool's material.
    """

    request = PrintRequest(
        requested_by="test-user",
        project_name="Test Print",
        material_id=material_id,
        amount_grams=amount,
        status="Pending",
    )

    db_session.add(request)
    db_session.commit()  # commit so `request.id` gets assigned

    return request


def test_fulfilling_reservation_consumes_inventory(db_session):
    """
    Test that fulfilling a reservation actually consumes filament.

    This test follows the standard "Arrange / Act / Assert" pattern:
        - Arrange: create a 500g spool and reserve 400g.
        - Act: fulfill the 400g reservation.
        - Assert: check that the physical inventory is now 100g and
          that the appropriate inventory and reservation events exist.
    """

    # --- Arrange ---
    # Create a spool containing 500g of filament.
    spool = create_test_spool(db_session, weight=500)

    # Create a print request for 400g.
    request = create_test_request(
        db_session,
        material_id=spool.material_id,
        amount=400,
    )

    # Reserve 400g of filament.
    reservation = create_reservation(
        db=db_session,
        spool_id=spool.id,
        print_request_id=request.id,
        amount=400,
        user_id="test-user",
    )

    # Verify that the spool initially contains 500g.
    assert get_current_weight(db_session, spool.id) == 500

    # --- Act ---
    # Fulfill the reservation.
    fulfill_reservation(
        db=db_session,
        reservation_id=reservation.id,
        user_id="test-user",
    )

    # --- Assert ---
    # The physical inventory should now be reduced by 400g.
    assert get_current_weight(db_session, spool.id) == 100

    # Find the FILAMENT_USED event created by the fulfillment.
    usage_events = (
        db_session.query(InventoryEvent)
        .filter(
            InventoryEvent.spool_id == spool.id,
            InventoryEvent.event_type == InventoryEventType.FILAMENT_USED,
        )
        .all()
    )

    # Exactly one FILAMENT_USED event should have been created.
    assert len(usage_events) == 1

    # The event should represent 400g being consumed.
    assert usage_events[0].quantity_change == -400

    # The usage event should be connected to the print request.
    assert usage_events[0].related_request_id == request.id

    # Find the fulfillment event.
    fulfilled_events = (
        db_session.query(ReservationEvent)
        .filter(
            ReservationEvent.spool_id == spool.id,
            ReservationEvent.event_type == ReservationEventType.RESERVATION_FULFILLED,
        )
        .all()
    )

    # Exactly one fulfillment event should have been created.
    assert len(fulfilled_events) == 1

    # The fulfillment should reference the original reservation.
    assert fulfilled_events[0].related_event_id == reservation.id


def test_fulfillment_creates_both_events_atomically(db_session):
    """
    Test the fulfillment atomicity invariant.

    A successful fulfillment must create exactly:
        1. One FILAMENT_USED inventory event.
        2. One RESERVATION_FULFILLED reservation event.

    These two events must be persisted together.
    """

    # --- Arrange ---
    # Create a spool containing 500g.
    spool = create_test_spool(db_session, weight=500)

    # Create a print request for 400g.
    request = create_test_request(
        db_session,
        material_id=spool.material_id,
        amount=400,
    )

    # Reserve 400g.
    reservation = create_reservation(
        db=db_session,
        spool_id=spool.id,
        print_request_id=request.id,
        amount=400,
        user_id="test-user",
    )

    # --- Act ---
    # Fulfill the reservation.
    fulfill_reservation(
        db=db_session,
        reservation_id=reservation.id,
        user_id="test-user",
    )

    # --- Assert ---
    # There must be exactly one FILAMENT_USED event.
    usage_events = (
        db_session.query(InventoryEvent)
        .filter(
            InventoryEvent.spool_id == spool.id,
            InventoryEvent.event_type == InventoryEventType.FILAMENT_USED,
        )
        .all()
    )

    assert len(usage_events) == 1

    # There must be exactly on RESERVATION_FULFILLED event.
    fulfilled_events = (
        db_session.query(ReservationEvent)
        .filter(
            ReservationEvent.spool_id == spool.id,
            ReservationEvent.event_type == ReservationEventType.RESERVATION_FULFILLED,
        )
        .all()
    )

    assert len(fulfilled_events) == 1

    # The FILAMENT_USED event should reference the print request.
    assert usage_events[0].related_request_id == request.id

    # The RESERVATION_FULFILLED event should reference the original
    # RESERVATION_CREATED event.
    assert fulfilled_events[0].related_event_id == reservation.id

    # The physical inventory should have decreased exactly once.
    assert get_current_weight(db_session, spool.id) == 100


def test_failed_fulfillment_creates_neither_event(db_session):
    """
    Test the failure half of the fulfillment atomicity invariant.

    If the re-validation discovers that there is no longer enough
    physical filament to fulfill the reservation, the operation must
    fail without creating either:

        - a FILAMENT_USED event
        - a RESERVATION_FULFILLED event

    This ensures the two events are truly atomic.
    """

    # --- Arrange ---
    # Create a spool containing 500g.
    spool = create_test_spool(db_session, weight=500)

    # Create a print request requiring 400g.
    request = create_test_request(
        db_session,
        material_id=spool.material_id,
        amount=400,
    )

    # Reserve 400g.
    reservation = create_reservation(
        db=db_session,
        spool_id=spool.id,
        print_request_id=request.id,
        amount=400,
        user_id="test-user",
    )

    # Simulate the physical spool losing another 200g after the
    # reservation was created.
    #
    # The reservation still expects 400g, but the spool now only
    # contains 300g. Fulfillment must therefore fail its re-validation.
    unexpected_usage = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.FILAMENT_USED,
        quantity_change=-200,
        user_id="test-user",
        note="Simulated inventory change before fulfillment",
    )
    db_session.add(unexpected_usage)
    db_session.commit()

    # Confirm that only 300g physically remains.
    assert get_current_weight(db_session, spool.id) == 300

    # --- Act ---
    # Attempt to fulfill the 400g reservation.
    with pytest.raises(
        ValueError,
        match="Insufficient filament remaining",
    ):
        fulfill_reservation(
            db=db_session,
            reservation_id=reservation.id,
            user_id="test-user",
        )

    # --- Assert ---
    # The failed fulfillment must NOT create a FILAMENT_USED event
    # for the reservation.
    fulfillment_usage_events = (
        db_session.query(InventoryEvent)
        .filter(
            InventoryEvent.spool_id == spool.id,
            InventoryEvent.event_type == InventoryEventType.FILAMENT_USED,
            InventoryEvent.related_request_id == request.id,
        )
        .all()
    )

    assert len(fulfillment_usage_events) == 0

    # The failed fulfillment must also NOT create a
    # RESERVATION_FULFILLED event.
    fulfilled_events = (
        db_session.query(ReservationEvent)
        .filter(
            ReservationEvent.spool_id == spool.id,
            ReservationEvent.event_type == ReservationEventType.RESERVATION_FULFILLED,
        )
        .all()
    )

    assert len(fulfilled_events) == 0

    # The original reservation should still exist and remain active.
    original_reservation = db_session.get(
        ReservationEvent,
        reservation.id,
    )

    assert original_reservation is not None
    assert original_reservation.event_type == ReservationEventType.RESERVATION_CREATED


def test_already_fulfilled_reservation_cannot_be_fulfilled_again(db_session):
    """
    Test that an already-fulfilled reservation cannot be fulfilled twice.

    Fulfilling the same reservation twice would incorrectly consume the
    same amount of filament more than once, so the second attempt must
    be rejected.
    """

    # --- Arrange ---
    # Create a spool containing 500g.
    spool = create_test_spool(db_session, weight=500)

    # Create a print request for 400g.
    request = create_test_request(
        db_session,
        material_id=spool.material_id,
        amount=400,
    )

    # Create the reservation.
    reservation = create_reservation(
        db=db_session,
        spool_id=spool.id,
        print_request_id=request.id,
        amount=400,
        user_id="test-user",
    )

    # Fulfill the reservation once.
    fulfill_reservation(
        db=db_session,
        reservation_id=reservation.id,
        user_id="test-user",
    )

    # Confirm the first fulfillment consumed the correct amount.
    assert get_current_weight(db_session, spool.id) == 100

    # --- Act ---
    # Attempt to fulfill the same reservation a second time.
    with pytest.raises(
        ValueError,
        match="cannot be fulfilled",
    ):
        fulfill_reservation(
            db=db_session,
            reservation_id=reservation.id,
            user_id="test-user",
        )

    # --- Assert ---
    # The second fulfillment must not consume any additional filament.
    assert get_current_weight(db_session, spool.id) == 100

    # There must still be exactly one FILAMENT_USED event.
    usage_events = (
        db_session.query(InventoryEvent)
        .filter(
            InventoryEvent.spool_id == spool.id,
            InventoryEvent.event_type == InventoryEventType.FILAMENT_USED,
        )
        .all()
    )

    assert len(usage_events) == 1

    # There must still be exactly one RESERVATION_FULFILLED event.
    fulfilled_events = (
        db_session.query(ReservationEvent)
        .filter(
            ReservationEvent.spool_id == spool.id,
            ReservationEvent.event_type == ReservationEventType.RESERVATION_FULFILLED,
        )
        .all()
    )

    assert len(fulfilled_events) == 1
