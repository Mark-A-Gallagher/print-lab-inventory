# machine.py
#
# DESIGN.md ref: Section 3 (Domain Model)
#
# TODO: Define a Machine SQLAlchemy model with:
#   - id (primary key)
#   - name
#   - status (this one IS a plain stored field, e.g. "online"/"offline" -
#     unlike spool weight/assignment, machine status isn't event-sourced
#     per DESIGN.md)
