# test_concurrency.py
#
# DESIGN.md ref: Section 10, Section 7 - this validates the fix for the
# check-then-insert race condition.
#
# TODO: test that two simultaneous reservations cannot overbook the same
#   spool. Think about how to actually simulate this in a test - a plain
#   sequential test won't exercise the race. You may need threading, or
#   two separate DB sessions that both read "available" before either
#   commits.
