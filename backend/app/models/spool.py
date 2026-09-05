# spool.py
#
# DESIGN.md ref: Section 3 (Domain Model), Section 8 (Database Schema)
#
# TODO: Define a Spool SQLAlchemy model with:
#   - id (primary key)
#   - material_id (foreign key -> materials.id)
#   - original_filament_weight
#   - empty_spool_weight
#   - low_stock_threshold
#
# IMPORTANT (read this before adding columns): this table must NOT have a
# current_weight or current_machine_id column. Per DESIGN.md, those are
# always DERIVED from inventory_events, never stored - so stored state and
# event history can never disagree. If you're tempted to add them for
# convenience, go re-read Section 5 first.
