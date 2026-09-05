# config.py
#
# DESIGN.md ref: Section 2 (Architecture)
#
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.

    Values can also be provided through a `.env` file during local
    development. Keeping configuration here prevents database paths,
    credentials, and other environment-specific values from being
    hardcoded throughout the application.
    """

    # SQLite database location.
    #
    # The database will be stored in the `data` directory at the
    # project root. SQLite will create the file when the application
    # first connects to it.
    database_url: str = "sqlite:///./data/lab_inventory.db"

    # Simple administrator credential for teacher-only actions.
    #
    # V1 intentionally does not implement full user authentication.
    # Normal users will be selected by name, while actions requiring
    # administrator privileges can require this PIN.
    #
    # This default is intended for local development only.
    # A real deployment should provide ADMIN_PIN through the environment.
    admin_pin: str = "CHANGE_ME"

    # Tell Pydantic Settings to also load values from a `.env` file.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Create one settings object for the application to use.
settings = Settings()
