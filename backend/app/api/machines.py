# machines.py (API router)
#
# DESIGN.md ref: Section 9 - Machine endpoints
#
# TODO: POST   /    create_machine - simple create, no event sourcing
#                    needed (machine status is a plain stored field)
# TODO: GET    /     list_machines - consider whether to also surface each
#                    machine's currently-assigned spool (derived)
