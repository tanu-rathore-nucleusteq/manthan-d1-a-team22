-- Sample data for manually testing BR 1.2 (innerwear and perishables are not returnable) with
-- cURL or Postman. Delivery dates are relative to now(); safe to re-run.
--
-- Load:  docker compose exec -T db psql -U returnright -d returnright < tests/api/fixtures/br_1_2_not_returnable_sample.sql
--
-- Customer email for every order: br12n.tester@example.com
-- Every order holds Cotton briefs (Innerwear), Organic honey (Perishables) and a Cotton shirt (Apparel).
--   BR12N-DAY01   delivered 1 day ago  -> briefs and honey NOT returnable, shirt returnable
--   BR12N-NOTDLV  not delivered yet    -> briefs and honey NOT returnable (policy reason), shirt not delivered

SET search_path TO returnright;

INSERT INTO customers (full_name, email) VALUES ('BR12N Tester', 'br12n.tester@example.com')
ON CONFLICT DO NOTHING;

INSERT INTO products (sku, name, category_id, price)
SELECT v.sku, v.name, c.category_id, v.price
FROM (VALUES ('BR12N-BRIEFS', 'Cotton briefs', 'Innerwear', 499.00),
             ('BR12N-HONEY', 'Organic honey', 'Perishables', 349.00),
             ('BR12N-SHIRT', 'Cotton shirt', 'Apparel', 1499.00)) AS v(sku, name, category, price)
JOIN categories c ON c.name = v.category
ON CONFLICT (sku) DO NOTHING;

INSERT INTO orders (order_number, customer_id, payment_method, ordered_at, delivered_at, total_amount)
SELECT v.order_number, cu.customer_id, 'UPI',
       now() - make_interval(days => COALESCE(v.days_ago, 0) + 2),
       now() - make_interval(days => v.days_ago),
       2347.00
FROM (VALUES ('BR12N-DAY01', 1), ('BR12N-NOTDLV', NULL::int)) AS v(order_number, days_ago)
JOIN customers cu ON lower(cu.email) = 'br12n.tester@example.com'
ON CONFLICT (order_number) DO UPDATE
    SET ordered_at = EXCLUDED.ordered_at, delivered_at = EXCLUDED.delivered_at;

INSERT INTO order_items (order_id, product_id, quantity, unit_price)
SELECT o.order_id, p.product_id, 1, p.price
FROM orders o
JOIN products p ON p.sku IN ('BR12N-BRIEFS', 'BR12N-HONEY', 'BR12N-SHIRT')
WHERE o.order_number LIKE 'BR12N-%'
ON CONFLICT (order_id, product_id) DO NOTHING;

SELECT order_number, (now()::date - delivered_at::date) AS days_since_delivery
FROM orders WHERE order_number LIKE 'BR12N-%' ORDER BY order_number;
