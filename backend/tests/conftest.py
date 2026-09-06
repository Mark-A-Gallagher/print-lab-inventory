# conftest.py
#

import pytest
from app import models  # noqa: F401 - registers all models with Base
from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def db_session():
    """
    Provide a fresh in-memory SQLite database for each test.

    The database exists only for the duration of the test and is
    completely separate from the application's real database.
    """

    # Create an isolated in-memory database for the test.
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    # Create all tables defined by our SQLAlchemy models.
    Base.metadata.create_all(test_engine)

    # Create a session connected to the test database.
    with Session(test_engine) as session:
        yield session  # Provide the session to the test.

    # Clean up the temporary database resources.
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


#
# TODO: once your API routers are implemented, add a `client` fixture
#   wrapping FastAPI's TestClient for endpoint-level tests, not just
#   service-level tests.
