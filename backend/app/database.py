# database.py
#
# TODO: Create a SQLAlchemy engine using your settings.database_url.
#   - Note: SQLite + FastAPI needs connect_args={"check_same_thread": False}
#     because FastAPI can serve a request on a different thread than the
#     one that created the session. Look up why this matters.
#
# TODO: Create a sessionmaker (commonly called SessionLocal).
#
# TODO: Create a declarative Base that all your models will inherit from.
#
# TODO: Write a get_db() generator function to use as a FastAPI dependency
#   - it should yield a session and close it in a `finally` block.
#   - Look up FastAPI's dependency injection docs if this pattern is new.
