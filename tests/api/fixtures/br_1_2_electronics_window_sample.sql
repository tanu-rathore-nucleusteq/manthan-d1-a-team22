-- Sample data for manually testing BR 1.2 (electronics: 10-day return window) with cURL or Postman.
-- Delivery dates are relative to now(), so the day counts stay correct whenever you run it.
-- Safe to re-run: it refreshes the delivery dates.
--
-- Load:  docker compose exec -T db psql -U returnright -d returnright < tests/api/fixtures/br_1_2_electronics_window_sample.sql
--
-- Customer email for every order: br12e.tester@example.com
-- Every order holds a Smartphone (Electronics, 10 days) and a Cotton shirt (Apparel, 30 days).
--   BR12E-DAY10  delivered 10 days ago -> phone returnable (last day), shirt returnable
--   BR12E-DAY11  delivered 11 days ago -> phone NOT returnable,          shirt returnable
--   BR12E-DAY14  delivered 14 days ago -> phone NOT returnable,          shirt returnable

SET search_path TO returnright;

INSERT INTO customers (full_name, email) VALUES ('BR12E Tester', 'br12e.tester@example.com')
ON CONFLICT DO NOTHING;

INSERT INTO products (sku, name, category_id, price)
SELECT v.sku, v.name, c.category_id, v.price
FROM (VALUES ('BR12E-PHONE', 'Smartphone', 'Electronics', 24999.00),
             ('BR12E-SHIRT', 'Cotton shirt', 'Apparel', 1499.00)) AS v(sku, name, category, price)
JOIN categories c ON c.name = v.category
ON CONFLICT (sku) DO NOTHING;

INSERT INTO orders (order_number, customer_id, payment_method, ordered_at, delivered_at, total_amount)
SELECT v.order_number, cu.customer_id, 'CARD',
       now() - make_interval(days => v.days_ago + 2),
       now() - make_interval(days => v.days_ago),
       26498.00
FROM (VALUES ('BR12E-DAY10', 10), ('BR12E-DAY11', 11), ('BR12E-DAY14', 14)) AS v(order_number, days_ago)
JOIN customers cu ON lower(cu.email) = 'br12e.tester@example.com'
ON CONFLICT (order_number) DO UPDATE
    SET ordered_at = EXCLUDED.ordered_at, delivered_at = EXCLUDED.delivered_at;

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 1, p.price
FROM orders o
JOIN products p ON p.sku IN ('BR12E-PHONE', 'BR12E-SHIRT')
WHERE o.order_number LIKE 'BR12E-%'
ON CONFLICT (order_id, product_id) DO NOTHING;

SELECT order_number, (now()::date - delivered_at::date) AS days_since_delivery
FROM orders WHERE order_number LIKE 'BR12E-%' ORDER BY order_number;
