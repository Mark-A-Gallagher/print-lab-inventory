# database.py

from sqlalchemy import create_engine
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
    Provide a database session to FastAPI endpoints.

    A new session is created for each request that depends on this function.
    The session is yielded to the endpoint and then closed afterward,
    including when an exception occurs.

    This function is intended to be used with FastAPI's Depends():

        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
