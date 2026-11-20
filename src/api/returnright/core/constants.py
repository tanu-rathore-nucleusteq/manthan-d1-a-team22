"""App-wide constants such as the API prefix and header names (X-Request-ID)."""

API_V1_PREFIX = "/api/v1"

REQUEST_ID_HEADER = "X-Request-ID"
CUSTOMER_EMAIL_HEADER = "X-Customer-Email"
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
