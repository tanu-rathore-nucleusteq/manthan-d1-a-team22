"""HTTP client for the mock gateway, implementing the PaymentGateway port: timeout, bounded
retries with the same idempotency key, latency recorded as a metric.
"""
