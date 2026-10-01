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


@pytest.fixture
def client():
    """
    FastAPI TestClient wired to a fresh in-memory database.

    `client.session_factory()` opens a session on that same database,
    for seeding rows (e.g. materials) that have no API endpoint.
    """
    from app.database import get_db
    from app.main import app
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection so every session sees the same data
    )
    Base.metadata.create_all(test_engine)
    session_factory = sessionmaker(bind=test_engine, autoflush=False)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.session_factory = session_factory
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()
