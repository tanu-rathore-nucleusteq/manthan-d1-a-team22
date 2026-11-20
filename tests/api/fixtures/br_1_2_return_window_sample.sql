-- Sample data for manually testing BR 1.2 (30-day return window) with cURL or Postman.
-- Delivery dates are relative to now(), so the day counts stay correct whenever you run it.
-- Safe to re-run: it refreshes the delivery dates.
--
-- Load:  docker compose exec -T db psql -U returnright -d returnright < tests/api/fixtures/br_1_2_return_window_sample.sql
--
-- Customer email for every order: br12.tester@example.com
--   BR12-DAY05   delivered 5 days ago   -> returnable
--   BR12-DAY30   delivered 30 days ago  -> returnable (last day)
--   BR12-DAY31   delivered 31 days ago  -> not returnable
--   BR12-NOTDLV  not delivered yet      -> not returnable

SET search_path TO returnright;

INSERT INTO customers (full_name, email) VALUES ('BR12 Tester', 'br12.tester@example.com')
ON CONFLICT DO NOTHING;

INSERT INTO products (sku, name, category_id, price)
SELECT v.sku, v.name, c.category_id, v.price
FROM (VALUES ('BR12-SHIRT', 'Cotton shirt', 1499.00),
             ('BR12-TROUSERS', 'Linen trousers', 799.50)) AS v(sku, name, price)
JOIN categories c ON c.name = 'Apparel'
ON CONFLICT (sku) DO NOTHING;

INSERT INTO orders (order_number, customer_id, payment_method, ordered_at, delivered_at, total_amount)
SELECT v.order_number, cu.customer_id, 'UPI',
       now() - make_interval(days => COALESCE(v.days_ago, 0) + 3),
       now() - make_interval(days => v.days_ago),
       3098.00
FROM (VALUES ('BR12-DAY05', 5), ('BR12-DAY30', 30), ('BR12-DAY31', 31),
             ('BR12-NOTDLV', NULL::int)) AS v(order_number, days_ago)
JOIN customers cu ON lower(cu.email) = 'br12.tester@example.com'
ON CONFLICT (order_number) DO UPDATE
    SET ordered_at = EXCLUDED.ordered_at, delivered_at = EXCLUDED.delivered_at;

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, v.quantity, p.price
FROM orders o
CROSS JOIN (VALUES ('BR12-SHIRT', 1), ('BR12-TROUSERS', 2)) AS v(sku, quantity)
JOIN products p ON p.sku = v.sku
WHERE o.order_number LIKE 'BR12-%'
ON CONFLICT (order_id, product_id) DO NOTHING;

SELECT order_number, (now()::date - delivered_at::date) AS days_since_delivery
FROM orders WHERE order_number LIKE 'BR12-%' ORDER BY order_number;
