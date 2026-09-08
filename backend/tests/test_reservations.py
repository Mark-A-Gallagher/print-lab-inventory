# test_reservations.py
#
# DESIGN.md ref: Section 10
#
# TODO: test an already-released reservation cannot be released again

import pytest
from app.models import (
    InventoryEvent,
    InventoryEventType,
    Material,
    PrintRequest,
    ReservationEventType,
    Spool,
)
from app.services.reservations import (
    create_reservation,
    get_available,
    get_reserved_amount,
    release_reservation,
)


def test_400g_reservation_succeeds_with_500g_available(db_session):
    """
    Test that a 400g reservation succeeds when 500g of filament is available.

    This test follows the standard "Arrange / Act / Assert" pattern:
        - Arrange: set up a spool with 500g of filament and a print request.
        - Act: create a 400g reservation.
        - Assert: check that the reservation was created and that
          100g remains available.
    """

    # --- Arrange ---
    # Create a material and a spool with 500g of filament.
    material = Material(name="Black PLA")
    db_session.add(material)
    db_session.commit()

    spool = Spool(
        material_id=material.id,
        original_weight=500,
        empty_spool_weight=100,
        low_stock_threshold=100,
    )
    db_session.add(spool)
    db_session.commit()

    # Create and inventory event establishing the spool's initial
    # filament weight. Current weight is derived from these events.
    creation_event = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.SPOOL_CREATED,
        quantity_change=500,
        user_id="test-user",
        note="Initial test spool",
    )
    db_session.add(creation_event)
    db_session.commit()

    # Create a print request for 400g of filament.
    request = PrintRequest(
        requested_by="test-user",
        project_name="Test Print",
        material_id=material.id,
        amount_grams=400,
        status="Pending",
    )
    db_session.add(request)
    db_session.commit()

    # --- Act ---
    # Create a 400g reservation against the spool.
    reservation = create_reservation(
        db_session,
        spool.id,
        request.id,
        400,
        "test-user",
    )

    # --- Assert ---
    # Check that the reservation was created correctly.
    assert reservation.event_type == ReservationEventType.RESERVATION_CREATED
    assert reservation.amount == 400

    # The spool should now have:
    # 500g total physical filament
    # 400g reserved
    # 100g availible
    assert get_reserved_amount(db_session, spool.id) == 400
    assert get_available(db_session, spool.id) == 100


def test_200g_reservation_rejected_when_only_100g_remains(db_session):
    """
    Test that a 200g reservation is rejected when only 100g remains available.

    This test follows the standard "Arrange / Act / Assert" pattern:
        - Arrange: create a 500g spool and reserve 400g of it.
        - Act: attempt to reserve another 200g.
        - Assert: check that the second reservation is rejected and
          that the original 400g reservation remains unchanged.
    """

    # --- Arrange ---
    # Create a material and a spool with 500g of filament.
    material = Material(name="Black PLA")
    db_session.add(material)
    db_session.commit()

    spool = Spool(
        material_id=material.id,
        original_weight=500,
        empty_spool_weight=100,
        low_stock_threshold=100,
    )
    db_session.add(spool)
    db_session.commit()

    starting_event = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.SPOOL_CREATED,
        quantity_change=500,
        user_id="test-user",
    )
    db_session.add(starting_event)
    db_session.commit()

    # Create the first print request.
    request1 = PrintRequest(
        requested_by="test-user",
        project_name="First Test Print",
        material_id=material.id,
        amount_grams=400,
        status="Pending",
    )
    db_session.add(request1)
    db_session.commit()

    # Reserve 400g of the availible 500g.
    create_reservation(
        db_session,
        spool.id,
        request1.id,
        400,
        "test-user",
    )

    # Create a second print request asking for 200g
    request2 = PrintRequest(
        requested_by="test-user",
        project_name="Second Test Print",
        material_id=material.id,
        amount_grams=200,
        status="Pending",
    )
    db_session.add(request2)
    db_session.commit()

    # --- Act ---
    # Attempt to reserve 200g when only 100g is availible.
    with pytest.raises(ValueError) as exc_info:
        create_reservation(
            db_session,
            spool.id,
            request2.id,
            200,
            "test-user",
        )

    # --- Assert ---
    # check that the correct error was raised.
    assert "only 100.0g available" in str(exc_info.value)

    # The failed reservation should not have changed anything.
    assert get_reserved_amount(db_session, spool.id) == 400
    assert get_available(db_session, spool.id) == 100


def test_releasing_reservation_restores_availability(db_session):
    """
    Test that releasing a reservation restores the filament to availability.

    This test follows the standard "Arrange / Act / Assert" pattern:
        - Arrange: create a 500g spool and reserve 400g.
        - Act: release the 400g reservation.
        - Assert: check that all 500g is available again.
    """

    # --- Arrange ---
    # Create a material and a spool with 500g of filament.
    # Create a material and a spool with 500g of filament.
    material = Material(name="Black PLA")
    db_session.add(material)
    db_session.commit()  # commit so `material.id` gets assigned by the DB

    spool = Spool(
        material_id=material.id,
        original_weight=500,
        empty_spool_weight=100,
        low_stock_threshold=100,
    )
    db_session.add(spool)
    db_session.commit()  # commit so `spool.id` gets assigned

    # Establish the spool's initial filament weight through an event.
    creation_event = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.SPOOL_CREATED,
        quantity_change=500,
        user_id="test-user",
        note="Initial test spool",
    )
    db_session.add(creation_event)
    db_session.commit()

    # Create a print request.
    request = PrintRequest(
        requested_by="test-user",
        project_name="Test Print",
        material_id=material.id,
        amount_grams=400,
        status="Pending",
    )
    db_session.add(request)
    db_session.commit()

    # Create a 400 g reservation.
    reservation = create_reservation(
        db_session,
        spool.id,
        request.id,
        400,
        "test-user",
    )

    # --- Act ---
    # Release the reservation.
    release_reservation(
        db_session,
        reservation.id,
        "test-user",
    )

    # --- Assert ---
    # The reservation should no longer count toward the reserved inventory.
    assert get_reserved_amount(db_session, spool.id) == 0

    # All 500g should now be availible again.
    assert get_available(db_session, spool.id) == 500


def test_already_released_reservation_cannot_be_released_again(db_session):
    """
    Test that an already-released reservation cannot be released again.

    This test follows the standard "Arrange / Act / Assert" pattern:
        - Arrange: create a 500g spool and a 400g reservation.
        - Act: release the reservation and then attempt to release it again.
        - Assert: check that the second release is rejected and that
          the reservation remains released.
    """

    # --- Arrange ---
    # Create a material and a spool with 500g of filament.
    material = Material(name="Black PLA")
    db_session.add(material)
    db_session.commit()  # commit so `material.id` gets assigned by the DB

    spool = Spool(
        material_id=material.id,
        original_weight=500,
        empty_spool_weight=100,
        low_stock_threshold=100,
    )
    db_session.add(spool)
    db_session.commit()  # commit so `spool.id` gets assigned

    # Establish the spool's initial filament weight through an event.
    creation_event = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.SPOOL_CREATED,
        quantity_change=500,
        user_id="test-user",
        note="Initial test spool",
    )
    db_session.add(creation_event)
    db_session.commit()

    # Create a print request.
    request = PrintRequest(
        requested_by="test-user",
        project_name="Test Print",
        material_id=material.id,
        amount_grams=400,
        status="Pending",
    )
    db_session.add(request)
    db_session.commit()

    # Create a 400g reservation.
    reservation = create_reservation(
        db_session,
        spool.id,
        request.id,
        400,
        "test-user",
    )

    # Release the reservation once.
    release_reservation(
        db_session,
        reservation.id,
        "test-user",
    )

    # --- Act ---
    # Attempt to release the same reservation a second time.
    with pytest.raises(ValueError) as exc_info:
        release_reservation(
            db_session,
            reservation.id,
            "test-user",
        )

    # --- Assert ---
    # Check that the error explains that the reservation was already released.
    assert "released" in str(exc_info.value).lower()

    # The reservation should still be considered released.
    assert get_reserved_amount(db_session, spool.id) == 0
    assert get_available(db_session, spool.id) == 500
