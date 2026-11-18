# main.py
#
# DESIGN.md ref: Section 2 (Architecture), Section 9 (API Operations)
#
# CRITICAL RULE (Section 2): the frontend never decides whether an action
# is valid. Every router you include here must independently re-validate
# requests via your services layer before touching the database.
#

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api import machines, requests, spools
from app.database import Base, engine

# Ensure the data directory exists for SQLite database
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

# Create all database tables on startup (for local development).
#
# For production, use Alembic migrations (see alembic.ini).
Base.metadata.create_all(bind=engine)

# Lightweight upgrade for databases created before spool capacity existed.
# This only runs for SQLite and only adds the missing column once.
with engine.begin() as connection:
    table_names = inspect(connection).get_table_names()
    if "machines" in table_names:
        columns = {
            column["name"] for column in inspect(connection).get_columns("machines")
        }
        if "spool_capacity" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE machines "
                    "ADD COLUMN spool_capacity INTEGER NOT NULL DEFAULT 1"
                )
            )
    if "print_requests" in table_names:
        columns = {
            column["name"]
            for column in inspect(connection).get_columns("print_requests")
        }
        if "color_count" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE print_requests "
                    "ADD COLUMN color_count INTEGER NOT NULL DEFAULT 1"
                )
            )

# Create the FastAPI app instance.
app = FastAPI(
    title="Print Lab Inventory API",
    description="Event-sourced inventory management system for 3D printer filament spools",
    version="1.0.0",
)

# Add CORS middleware so the Vite frontend (localhost:5173) can communicate with the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers with appropriate prefixes and tags.
app.include_router(
    spools.router,
    prefix="/spools",
    tags=["Spools"],
)

app.include_router(
    machines.router,
    prefix="/machines",
    tags=["Machines"],
)

app.include_router(
    requests.router,
    prefix="/requests",
    tags=["Print Requests & Reservations"],
)


# Simple health check endpoint.
@app.get("/health")
def health_check():
    """
    Health check endpoint for the API.

    Returns a 200 OK status to confirm the service is running.
    """
    return {"status": "healthy"}
