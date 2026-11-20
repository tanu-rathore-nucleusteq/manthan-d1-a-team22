"""Seed synthetic data with Faker seed 42: 2,000 orders, 40 products in 6 categories, 500
customers, one staff user per role (warehouse1, finance1, manager1; password from DEMO_PASSWORD)
and the demo orders in docs/implementation-plan.md section 7, dated relative to the day the seed
runs. --if-empty skips seeding when data exists; without it the script truncates and reloads.
"""
