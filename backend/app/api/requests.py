# requests.py (API router)
#
# DESIGN.md ref: Section 9 - Print request / reservation endpoints
#
# /{id}/fulfill is the most important endpoint in the whole API - it
# should call your reservations service's fulfill_reservation() function,
# which performs the atomic two-event write from Section 6.4. Keep this
# router thin; don't reimplement that logic here.
#
# TODO: POST   /                     create_request
# TODO: POST   /{request_id}/reserve  reserve - Section 6.3 ("recommend
#                            fullest compatible spool" for v1 - no
#                            auto-splitting across spools)
# TODO: POST   /{request_id}/release  release
# TODO: POST   /{request_id}/fulfill  fulfill
