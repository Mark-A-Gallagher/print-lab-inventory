# test_fulfillment.py
#
# DESIGN.md ref: Section 10, Section 6.4 - these tests are the executable
# version of the fulfillment atomicity invariant. Arguably the most
# important tests in the whole suite.
#
# TODO: test fulfilling a reservation consumes the appropriate inventory
# TODO: test fulfilling a reservation always produces exactly one
#   corresponding FILAMENT_USED event, atomically - also test the FAILURE
#   half: force the re-validation to fail and assert NO
#   RESERVATION_FULFILLED event was persisted either (both-or-neither)
# TODO: test an already-fulfilled reservation cannot be fulfilled again
