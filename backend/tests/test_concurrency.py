# test_concurrency.py
#
# DESIGN.md ref: Section 10, Section 7
#
# These tests validate that two simultaneous reservation attempts cannot
# overbook the same spool.
#
# A normal sequential test is not enough here because:
#
#     Request A checks available
#     Request A creates reservation
#     Request B checks available
#
# does not reproduce the race condition.
#
# Instead, this test uses two separate database sessions and two threads.
# A barrier forces both reservation attempts to reach the availability
# check before either one is allowed to continue.
#
# With 500g available and two requests for 400g:
#
#     Request A → sees 500g available
#     Request B → sees 500g available
#
# Only ONE request should ultimately succeed.
# The other must be rejected.
#

import threading

from app.database import Base, configure_sqlite_locking
from app.models import (
    InventoryEvent,
    InventoryEventType,
    Material,
    PrintRequest,
    Spool,
)
from app.services import reservations
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_two_simultaneous_reservations_cannot_overbook(tmp_path, monkeypatch):
    """
    Test that two simultaneous reservation attempts cannot reserve
    more filament than the spool actually has available.

    This test follows the standard "Arrange / Act / Assert" pattern:

        - Arrange: create a 500g spool and two print requests that each
          attempt to reserve 400g.

        - Act: run both reservation attempts simultaneously and force
          them to check availability before either attempt continues.

        - Assert: exactly one reservation succeeds and exactly one
          reservation is rejected.

    If both reservations succeed, the application has a check-then-insert
    race condition.
    """

    # ------------------------------------------------------------------
    # Arrange
    # ------------------------------------------------------------------

    # Create a temporary SQLite database file.
    #
    # We use a file-based database instead of the normal in-memory
    # database because each thread needs its own independent SQLAlchemy
    # session and connection.
    database_path = tmp_path / "concurrency_test.db"

    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    configure_sqlite_locking(engine)

    # Create all database tables.
    Base.metadata.create_all(engine)

    # Create a session factory for this test database.
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    # Create the initial test data.
    setup_session = TestSessionLocal()

    try:
        # Create the material.
        material = Material(name="Black PLA")
        setup_session.add(material)
        setup_session.commit()

        # Create a 500g spool.
        spool = Spool(
            material_id=material.id,
            original_weight=500,
            empty_spool_weight=100,
            low_stock_threshold=100,
        )
        setup_session.add(spool)
        setup_session.commit()

        # Establish the spool's initial 500g inventory through the
        # event-sourced inventory system.
        creation_event = InventoryEvent(
            spool_id=spool.id,
            event_type=InventoryEventType.SPOOL_CREATED,
            quantity_change=500,
            user_id="test-user",
            note="Initial concurrency test spool",
        )
        setup_session.add(creation_event)

        # Create two print requests.
        request_one = PrintRequest(
            requested_by="user-one",
            project_name="Concurrency Test 1",
            material_id=material.id,
            amount_grams=400,
            status="Pending",
        )

        request_two = PrintRequest(
            requested_by="user-two",
            project_name="Concurrency Test 2",
            material_id=material.id,
            amount_grams=400,
            status="Pending",
        )

        setup_session.add(request_one)
        setup_session.add(request_two)
        setup_session.commit()

        # Save the IDs before closing the setup session.
        spool_id = spool.id
        request_one_id = request_one.id
        request_two_id = request_two.id

    finally:
        setup_session.close()

    # Both requests want 400g.
    #
    # The spool only has 500g, so both cannot succeed.
    reservation_amount = 400

    # This barrier is the important part of the test.
    #
    # Both threads must reach the availability check before either
    # thread is allowed to continue.
    availability_barrier = threading.Barrier(2)

    # Save the original function so our test can still perform the
    # real availability calculation after synchronization.
    original_get_available = reservations.get_available

    def synchronized_get_available(db, current_spool_id):
        """
        Force both threads to perform their availability checks at
        approximately the same time.
        """

        # Both threads stop here until both have reached this point.
        availability_barrier.wait()

        # After both threads have reached the check, perform the real
        # availability calculation.
        return original_get_available(db, current_spool_id)

    # Replace get_available inside the reservations service with our
    # synchronized version for this test.
    monkeypatch.setattr(
        reservations,
        "get_available",
        synchronized_get_available,
    )

    # Store the results from both threads.
    successful_reservations = []
    failed_reservations = []

    # A lock protects these result lists because both threads will
    # modify them.
    result_lock = threading.Lock()

    def attempt_reservation(request_id, user_id):
        """
        Attempt to create a reservation using a completely separate
        database session.
        """

        db = TestSessionLocal()

        try:
            reservation = reservations.create_reservation(
                db=db,
                spool_id=spool_id,
                print_request_id=request_id,
                amount=reservation_amount,
                user_id=user_id,
            )

            # Record successful reservation.
            with result_lock:
                successful_reservations.append(reservation)

        except Exception as exc:  # noqa: BLE001
            with result_lock:
                failed_reservations.append(exc)

        finally:
            db.close()

    # Create the two threads.
    thread_one = threading.Thread(
        target=attempt_reservation,
        args=(request_one_id, "user-one"),
    )

    thread_two = threading.Thread(
        target=attempt_reservation,
        args=(request_two_id, "user-two"),
    )

    # ------------------------------------------------------------------
    # Act
    # ------------------------------------------------------------------

    # Start both reservation attempts.
    thread_one.start()
    thread_two.start()

    # Wait for both attempts to finish.
    thread_one.join()
    thread_two.join()

    # ------------------------------------------------------------------
    # Assert
    # ------------------------------------------------------------------

    # Exactly ONE reservation should succeed.
    #
    # If both succeed, the application has overbooked the spool:
    #
    #     400g + 400g = 800g reserved
    #
    # even though only 500g exists.
    assert len(successful_reservations) == 1

    # Exactly ONE reservation should fail.
    assert len(failed_reservations) == 1

    # The failed reservation should have been rejected because there
    # was no longer enough availible filament.
    assert isinstance(failed_reservations[0], ValueError)

    # Open a fresh session so we verify what was actually persisted
    # in the database rather than relying only on the thread results.
    verification_session = TestSessionLocal()

    try:
        reservations_in_database = (
            verification_session.query(reservations.ReservationEvent)
            .filter(
                reservations.ReservationEvent.spool_id == spool_id,
                reservations.ReservationEvent.event_type
                == reservations.ReservationEventType.RESERVATION_CREATED,
            )
            .all()
        )

        # Only one reservation should actually exist.
        assert len(reservations_in_database) == 1

        # That reservation should be for 400g.
        assert reservations_in_database[0].amount == 400

    finally:
        verification_session.close()

    # Clean up the test database.
    Base.metadata.drop_all(engine)
    engine.dispose()
