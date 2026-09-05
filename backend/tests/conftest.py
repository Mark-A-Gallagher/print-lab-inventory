# conftest.py
#
# TODO: write a pytest fixture (e.g. db_session) that:
#   - creates a fresh in-memory SQLite engine (sqlite:///:memory:) so
#     tests never touch your real print_lab.db or interfere with each
#     other
#   - creates all tables against it (Base.metadata.create_all)
#   - yields a session, and closes it afterward
#
# TODO: once your API routers are implemented, add a `client` fixture
#   wrapping FastAPI's TestClient for endpoint-level tests, not just
#   service-level tests.
