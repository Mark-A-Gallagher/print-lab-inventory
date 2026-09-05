# main.py
#
# DESIGN.md ref: Section 2 (Architecture), Section 9 (API Operations)
#
# CRITICAL RULE (Section 2): the frontend never decides whether an action
# is valid. Every router you include here must independently re-validate
# requests via your services layer before touching the database.
#
# TODO: Create the FastAPI app instance.
#
# TODO: Add CORS middleware so your Vite dev server (localhost:5173) can
#   actually talk to this API. Look up fastapi.middleware.cors.
#
# TODO: Include your spools, machines, and requests routers
#   (see app/api/) with appropriate prefixes and tags.
#
# TODO: Decide how tables get created for local dev - Base.metadata.create_all()
#   is a quick way to bootstrap, but you should learn Alembic migrations
#   (see alembic.ini) since that's the "real" way schema changes should
#   happen once this isn't a brand new project.
#
# TODO: Add a simple health check endpoint (e.g. GET /health).
