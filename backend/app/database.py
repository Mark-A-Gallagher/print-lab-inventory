# database.py

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Create the SQLAlchemy database engine.
#
# The engine is responsible for managing connections to the database.
# `settings.database_url` determines which database we connect to.
#
# For SQLite, FastAPI may handle requests across different threads.
# `check_same_thread=False` allows SQLite connections to be used across
# those threads. It does NOT replace proper transaction handling.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # Only needed for SQLite
)


# SQLite normally lets the Python sqlite3 driver decide when to begin
# a transaction. For our inventory system, we want SQLAlchemy to control
# this explicitly so we can use BEGIN IMMEDIATE.
#
# BEGIN IMMEDIATE acquires SQLite's write transaction before our code
# performs the availability check. This prevents another reservation
# from changing the inventory between:
#
#  checking availability
#          ↓
#  inserting reservation
#
# Without this, two requests could both see the same available amount
# and both successfully reserve it.
def configure_sqlite_locking(engine):
    """
    Attach SQLite locking behavior to the given engine so that
    check-then-insert operations (like create_reservation) are safe
    under concurrent access.
    """

    @event.listens_for(engine, "connect")
    def set_sqlite_transaction_mode(dbapi_connection, connection_record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def begin_immediate(connection):
        connection.exec_driver_sql("BEGIN IMMEDIATE")


configure_sqlite_locking(engine)


# Create a session factory.
#
# `SessionLocal()` will create an individual SQLAlchemy Session that
# can be used to query or modify the database.
#
# autocommit=False:
#   Transactions must be explicitly committed. This is important for
#   operations that need to succeed or fail as one atomic unit.
#
# autoflush=False:
#   SQLAlchemy will not automatically flush pending changes before
#   certain operations. We will control database writes explicitly.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session. The session is always closed after the request, even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
