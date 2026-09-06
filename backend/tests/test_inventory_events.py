# test_inventory_events.py
#
# DESIGN.md ref: Section 10 - write these as real pytest test functions.
#

import pytest
from app.models import InventoryEvent, InventoryEventType, Material, Spool
from app.services.inventory import (
    get_current_weight,
    record_correction,
    record_filament_used,
)


def test_creating_spool_produces_correct_inventory(db_session):
    """
    ✓ Creating a 1kg spool produces 1kg inventory

    This test follows the standard "Arrange / Act / Assert" pattern:
      - Arrange: set up the data the test needs (a material, a spool with
        1000g of filament already recorded).
      - Act: call the one function actually being tested.
      - Assert: check the result is what you expect.
    """

    # --- Arrange ---
    # A Spool requires a material_id, so a Material row has to exist first.
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
    db_session.commit()  # commit so `spool.id` gets assigned

    # --- Act ---
    # This is the one line actually being tested.
    starting_event = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.SPOOL_CREATED,
        quantity_change=1000,
        user_id="test-user",
    )
    db_session.add(starting_event)
    db_session.commit()

    # --- Assert ---
    # Confirm the derived weight reflects the usage.
    assert get_current_weight(db_session, spool.id) == 1000.0


def test_using_filament_reduces_current_weight(db_session):
    """
    ✓ Using 100g leaves 900g

    This test follows the standard "Arrange / Act / Assert" pattern:
      - Arrange: set up the data the test needs (a material, a spool with
        1000g of filament already recorded).
      - Act: call the one function actually being tested.
      - Assert: check the result is what you expect.

    Notice the `db_session` argument - that's the fixture from
    conftest.py. Pytest sees a test function asking for a parameter named
    `db_session` and automatically runs the matching fixture, handing you
    a fresh in-memory database for this test only. You never call the
    fixture yourself; pytest wires it up for you based on the name.
    """

    # --- Arrange ---
    # A Spool requires a material_id, so a Material row has to exist first.
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
    db_session.commit()  # commit so `spool.id` gets assigned

    # We're not testing SPOOL_CREATED here, so we get the spool to 1000g
    # by directly calling record_filament_used with a *negative* usage...
    # actually, simpler and clearer: use record_weight_adjustment-style
    # reasoning is overkill for this test. Instead, just insert the
    # starting event directly, since SPOOL_CREATED isn't under test here
    # either - only record_filament_used and get_current_weight are.

    starting_event = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.SPOOL_CREATED,
        quantity_change=1000,
        user_id="test-user",
    )
    db_session.add(starting_event)
    db_session.commit()

    # Sanity check the arrangement itself before testing anything -
    # if this fails, the bug is in your test setup, not the code
    # under test.
    assert get_current_weight(db_session, spool.id) == 1000.0

    # --- Act ---
    # This is the one line actually being tested.
    record_filament_used(db_session, spool.id, amount=100, user_id="test-user")

    # --- Assert ---
    # Confirm the derived weight reflects the usage.
    assert get_current_weight(db_session, spool.id) == 900.0


def test_using_too_much_filament_is_rejected(db_session):
    """
    ✓ Using 1,001g is rejected

    This test follows the standard "Arrange / Act / Assert" pattern:
      - Arrange: set up the data the test needs (a material, a spool with
        1000g of filament already recorded).
      - Act: call the one function actually being tested.
      - Assert: check the result is what you expect.
    """

    # --- Arrange ---
    # A Spool requires a material_id, so a Material row has to exist first.
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
    db_session.commit()  # commit so `spool.id` gets assigned

    starting_event = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.SPOOL_CREATED,
        quantity_change=1000,
        user_id="test-user",
    )
    db_session.add(starting_event)
    db_session.commit()

    # Sanity check the arrangement itself before testing anything -
    # if this fails, the bug is in your test setup, not the code
    # under test.
    assert get_current_weight(db_session, spool.id) == 1000.0

    # --- Act & Assert ---
    # This is the one line actually being tested.
    with pytest.raises(ValueError):
        record_filament_used(db_session, spool.id, amount=1001, user_id="test-user")


def test_correcting_usage_event_changes_derived_inventory(db_session):
    """
    ✓ Correcting a usage event changes derived inventory
    """
    material = Material(name="Black PLA")
    db_session.add(material)
    db_session.commit()

    spool = Spool(
        material_id=material.id,
        original_weight=1000,
        empty_spool_weight=100,
        low_stock_threshold=200,
    )
    db_session.add(spool)
    db_session.commit()

    starting_event = InventoryEvent(
        spool_id=spool.id,
        event_type=InventoryEventType.SPOOL_CREATED,
        quantity_change=1000,
        user_id="test-user",
    )
    db_session.add(starting_event)
    db_session.commit()

    usage_event = record_filament_used(
        db_session, spool.id, amount=100, user_id="test-user"
    )

    assert get_current_weight(db_session, spool.id) == 900.0

    # --- Act ---
    record_correction(
        db_session,
        related_event_id=usage_event.id,
        amount=50,  # compensate 50g back, correcting the 100g usage to 50g
        reason="Correcting overstated usage",
        user_id="test-user",
    )

    # --- Assert ---
    assert get_current_weight(db_session, spool.id) == 950.0


def test_no_service_function_updates_or_deletes_events():
    """
    ✓ Events cannot be edited or deleted

    Immutability isn't enforced by a database constraint or SQLAlchemy
    hook in this codebase (nothing currently blocks a raw `session.delete()`
    or attribute mutation at the DB layer) — it's a rule this project
    follows by not writing any code that does that. This test checks the
    honest version of that claim: inventory.py exposes no function whose
    name suggests it updates or deletes an existing event.

    If real enforcement is ever added (e.g. a SQLAlchemy event listener
    blocking UPDATE/DELETE on this table), this test should be replaced
    with one that actually attempts a mutation and asserts it's blocked.
    """
    import app.services.inventory as inventory_module

    forbidden_terms = ("update_event", "edit_event", "delete_event")
    function_names = [
        name for name in dir(inventory_module) if not name.startswith("_")
    ]

    for forbidden in forbidden_terms:
        assert forbidden not in function_names
