# request.py (Pydantic schemas)
#
# DESIGN.md ref: Section 3, Section 6.3/6.4, Section 9
#
# TODO: PrintRequestCreate - what does creating a print request need?
#   (requested_by, project_name, material_id, amount_required)
#
# TODO: PrintRequestOut - what does the API return?
#
# TODO: think about a schema for the /reserve endpoint - does the client
#   choose the spool, or does the server pick "the fullest compatible
#   spool" per DESIGN.md's v1 decision (Section 6.3)? That decision
#   affects what this schema needs to contain.
