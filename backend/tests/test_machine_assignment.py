# test_machine_assignment.py
#
# DESIGN.md ref: Section 10
#

import pytest
from app.models import Machine, Material, Spool
from app.services.inventory import (
    assign_to_machine,
    get_current_machine,
    remove_from_machine,
)


def test_assigning_spool_to_printer(db_session):
    """
    Test that a spool can be assigned to a printer and that the assignment is recorded correctly.

    This test follows the standard "Arrange / Act / Assert" pattern:
        - Arrange: set up the data the test needs (a spool and a printer).
        - Act: call the function to assign the spool to the printer.
        - Assert: check that the assignment is recorded correctly.

    Notice the use of the `db_session` fixture to provide a fresh in-memory database for the test.
    """

    # --- Arrange ---
    # Create a material and a spool and a printer.
    material = Material(name="Black PLA")
    db_session.add(material)
    db_session.commit()  # commit so `material.id` gets assigned by the DB

    spool = Spool(
        material_id=material.id,
        original_weight=1000,
        empty_spool_weight=100,
        low_stock_threshold=200,
    )
    db_session.add(spool)
    db_session.commit()

    printer = Machine(name="Printer #1")
    user_id = "test-user"
    db_session.add(printer)
    db_session.commit()  # commit so `printer.id` gets assigned

    # --- Act ---
    # Assign the spool to the printer.
    assign_to_machine(db_session, spool.id, printer.id, user_id)

    # --- Assert ---
    # check that the assignment is recorded correctly.
    assert get_current_machine(db_session, spool.id) == printer.id


def test_assigning_same_spool_to_another_printer(db_session):
    """
    Test that assigning a already assigned spool to another printer is rejected.

    This test follows the standard "Arrange / Act / Assert" pattern:
        - Arrange: set up the data the test needs (a spool and two printers).
        - Act: call the function to assign the spool to the first printer, then attempt to assign it to the second printer.
        - Assert: check that the second assignment is rejected and that the spool remains assigned to the first printer.
    """

    # --- Arrange ---
    # Create a material and a spool and two printers.
    material = Material(name="Red PLA")
    db_session.add(material)
    db_session.commit()  # commit so `material.id` gets assigned by the DB

    spool = Spool(
        material_id=material.id,
        original_weight=1000,
        empty_spool_weight=100,
        low_stock_threshold=200,
    )
    db_session.add(spool)
    db_session.commit()

    printer1 = Machine(name="Printer #1")
    printer2 = Machine(name="Printer #2")
    db_session.add(printer1)
    db_session.add(printer2)
    db_session.commit()  # commit so `printer.id` gets assigned

    # --- Act ---
    # Assign the spool to the first printer.
    user_id = "test-user"
    assign_to_machine(db_session, spool.id, printer1.id, user_id)

    # --- Assert ---
    # Attempt to assign the same spool to the second printer and expect an exception.
    with pytest.raises(ValueError) as exc_info:
        assign_to_machine(db_session, spool.id, printer2.id, user_id)

    assert "already assigned" in str(exc_info.value)
    assert (
        get_current_machine(db_session, spool.id) == printer1.id
    )  # spool should still be assigned to printer1


def test_removing_spool_allows_reassignment(db_session):
    """
    Test that removing a spool from a printer allows it to be reassigned to another printer.

    This test follows the standard "Arrange / Act / Assert" pattern:
        - Arrange: set up the data the test needs (a spool and two printers).
        - Act: assign the spool to the first printer, remove it, and then assign it to the second printer.
        - Assert: check that the spool is successfully reassigned to the second printer.
    """

    # --- Arrange ---
    # create a material and a spool and two printers.
    material = Material(name="Blue PLA")
    db_session.add(material)
    db_session.commit()  # commit so `material.id` gets assigned by the DB

    spool = Spool(
        material_id=material.id,
        original_weight=1000,
        empty_spool_weight=100,
        low_stock_threshold=200,
    )
    db_session.add(spool)
    db_session.commit()

    printer1 = Machine(name="Printer #1")
    printer2 = Machine(name="Printer #2")
    db_session.add(printer1)
    db_session.add(printer2)
    db_session.commit()  # commit so `printer.id` gets assigned

    # --- Act ---
    # Assign the spool to the first printer.
    user_id = "test-user"
    assign_to_machine(db_session, spool.id, printer1.id, user_id)

    # Remove the spool from the first printer.
    remove_from_machine(db_session, spool.id, user_id)

    # Assign the spool to the second printer.
    assign_to_machine(db_session, spool.id, printer2.id, user_id)

    # --- Assert ---
    # Check that the spool is now assigned to the second printer.
    assert get_current_machine(db_session, spool.id) == printer2.id
