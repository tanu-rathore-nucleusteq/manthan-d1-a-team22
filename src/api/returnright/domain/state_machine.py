"""Allowed ReturnStatus transitions and who may trigger each; any other transition raises
InvalidTransition (409). Requested → Approved happens in the create transaction once every
submitted item is confirmed eligible. Received → Rejected when every item is rejected at
inspection; Inspected → Rejected when finance rejects. Refunded and Rejected are final.
"""
