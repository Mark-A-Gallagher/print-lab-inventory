# print_request.py
#
# DESIGN.md ref: Section 3 (Domain Model)
#
# TODO: Define a PrintRequest SQLAlchemy model with:
#   - id (primary key)
#   - requested_by (just a plain identifier string - no full auth in v1)
#   - project_name
#   - material_id (foreign key -> materials.id)
#   - amount_required
#   - status (Pending / Approved / Printing / Complete / Rejected -
#     consider whether a plain string or a proper Enum column fits better)
