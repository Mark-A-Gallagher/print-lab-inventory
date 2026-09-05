# test_inventory_events.py
#
# DESIGN.md ref: Section 10 - write these as real pytest test functions.
#
# TODO: test creating a 1kg spool produces 1kg inventory
# TODO: test using 100g leaves 900g
# TODO: test using 1,001g is rejected
# TODO: test correcting a usage event changes derived inventory
# TODO: test events cannot be edited or deleted (how would you even test
#   this? think about asserting there's no code path that updates/deletes
#   an existing InventoryEvent row)
