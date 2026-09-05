# spool.py (Pydantic schemas)
#
# DESIGN.md ref: Section 3, Section 9 (spool endpoints)
#
# TODO: SpoolCreate - what does a client need to send to create a spool?
#   (material_id, original_filament_weight, empty_spool_weight,
#   low_stock_threshold)
#
# TODO: SpoolOut - what does the API return? This should include the
#   DERIVED fields (current_weight, current_machine_id, reserved_amount,
#   available) even though those don't exist as columns on the Spool
#   model - they get computed in the service layer before this schema is
#   built. Don't put them on the ORM model; only on this response schema.
#
# TODO: think about what other request schemas you'll need for the
#   weight-update, assign, and correction endpoints.
