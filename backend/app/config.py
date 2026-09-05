# config.py
#
# DESIGN.md ref: Section 2 (Architecture)
#
# TODO: Define a Settings class (consider pydantic-settings' BaseSettings)
#   - database_url: where's the SQLite file going to live?
#   - admin_pin (or similar): DESIGN.md decided against full auth for v1 -
#     just a simple named-user selector + one admin credential for
#     teacher-only actions. What's the simplest way to store/check that?
#
# TODO: Load values from a .env file rather than hardcoding secrets.
#
# TODO: Instantiate a single `settings` object other modules can import.
