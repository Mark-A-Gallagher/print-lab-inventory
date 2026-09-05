# spools.py (API router)
#
# DESIGN.md ref: Section 9 - Spool endpoints
#
# Remember the critical rule from Section 2: this router must never trust
# the frontend's judgment about validity. Every mutating endpoint here
# should call into your services layer for validation before any event
# is inserted - don't put business logic directly in these route handlers.
#
# TODO: POST   /            create_spool - creates a Spool row AND a
#                            SPOOL_CREATED inventory_event, together
#                            (Section 4.1 - "history starts at zero")
# TODO: GET    /             list_spools - all spools with derived fields
#                            attached via your services functions
# TODO: GET    /{spool_id}   get_spool - this is also the endpoint the
#                            QR-code page (Release 0.4) will hit
# TODO: POST   /{spool_id}/weight     update_weight
# TODO: POST   /{spool_id}/correct    correct_event (Section 6.5 - UI
#                            should call this "Correct Event," not "Edit")
# TODO: POST   /{spool_id}/assign     assign_to_machine
# TODO: POST   /{spool_id}/unassign   remove_from_machine
