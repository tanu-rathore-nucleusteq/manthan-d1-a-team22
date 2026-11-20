-- ReturnRight database schema v2 (PostgreSQL 18)
-- Main API tables live in schema "returnright"; the mock gateway's table lives in schema "gateway".
--
-- The compose database (docker compose up -d db) loads this file automatically on first start.
-- To load it into an existing container instead (container "pg", any database you choose):
--   docker cp db/schema_v2.sql pg:/tmp/schema_v2.sql
--   docker exec pg psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f /tmp/schema_v2.sql
-- App connection string (psycopg 3):
--   postgresql+psycopg://postgres:change-me@localhost:5433/postgres?options=-csearch_path%3Dreturnright
--
-- WARNING: development reset. It drops and recreates schema "returnright", so all API data is lost.
-- The gateway table is created only if missing and is never dropped, so the gateway keeps its
-- record of processed payments. In the first Alembic migration, leave out the DROP SCHEMA line.
--
-- Changes from v1:
-- 1. Finance approval applies to the return total, not to each item. refunds no longer forces
--    requires_approval = (amount > 10000); finance_approvals has one row per return.
-- 2. Store-credit refunds can be marked PAID without a gateway reference.
-- 3. A bought item can be in only one eligible return, so a double click on Submit cannot
--    create a second return for it.
-- 4. Return reasons gain OTHER, used with the free-text note.
-- 5. The gateway table is created if missing and never dropped by this script.

BEGIN;

DROP SCHEMA IF EXISTS returnright CASCADE;
CREATE SCHEMA returnright;
SET search_path TO returnright;

-- =========================================================
-- 1. MASTER DATA
-- =========================================================

-- Categories carry the return rules, so rules are data, not hard-coded.
CREATE TABLE categories (
    category_id         SMALLSERIAL PRIMARY KEY,
    name                VARCHAR(50)  NOT NULL UNIQUE,
    is_returnable       BOOLEAN      NOT NULL DEFAULT TRUE,
    return_window_days  SMALLINT     CHECK (return_window_days > 0),
    CONSTRAINT chk_window_when_returnable
        CHECK (is_returnable = FALSE OR return_window_days IS NOT NULL)
);

CREATE TABLE products (
    product_id   SERIAL        PRIMARY KEY,
    sku          VARCHAR(30)   NOT NULL UNIQUE,
    name         VARCHAR(150)  NOT NULL,
    category_id  SMALLINT      NOT NULL REFERENCES categories(category_id),
    price        NUMERIC(12,2) NOT NULL CHECK (price > 0)
);

CREATE TABLE customers (
    customer_id  SERIAL        PRIMARY KEY,
    full_name    VARCHAR(120)  NOT NULL,
    email        VARCHAR(255)  NOT NULL,
    phone        VARCHAR(20),
    is_flagged   BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_customers_email ON customers (lower(email));

CREATE TABLE staff_users (
    staff_id       SERIAL       PRIMARY KEY,
    full_name      VARCHAR(120) NOT NULL,
    email          VARCHAR(255) NOT NULL UNIQUE,
    role           VARCHAR(20)  NOT NULL CHECK (role IN ('WAREHOUSE_AGENT','FINANCE_REVIEWER','OPS_MANAGER')),
    password_hash  VARCHAR(255) NOT NULL,
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE return_reasons (
    reason_id  SMALLSERIAL  PRIMARY KEY,
    code       VARCHAR(30)  NOT NULL UNIQUE,
    label      VARCHAR(100) NOT NULL
);

-- =========================================================
-- 2. ORDERS
-- =========================================================

CREATE TABLE orders (
    order_id        SERIAL        PRIMARY KEY,
    order_number    VARCHAR(20)   NOT NULL UNIQUE,
    customer_id     INT           NOT NULL REFERENCES customers(customer_id),
    payment_method  VARCHAR(20)   NOT NULL CHECK (payment_method IN ('CARD','UPI','NETBANKING','COD')),
    ordered_at      TIMESTAMPTZ   NOT NULL,
    delivered_at    TIMESTAMPTZ,
    total_amount    NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    CONSTRAINT chk_delivery_after_order CHECK (delivered_at IS NULL OR delivered_at >= ordered_at)
);
CREATE INDEX ix_orders_customer ON orders (customer_id);

CREATE TABLE order_items (
    order_item_id  SERIAL        PRIMARY KEY,
    order_id       INT           NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id     INT           NOT NULL REFERENCES products(product_id),
    quantity       SMALLINT      NOT NULL CHECK (quantity > 0),
    unit_price     NUMERIC(12,2) NOT NULL CHECK (unit_price > 0),   -- price at time of purchase
    CONSTRAINT uq_order_product UNIQUE (order_id, product_id)
);
CREATE INDEX ix_order_items_product ON order_items (product_id);

-- =========================================================
-- 3. RETURNS
-- =========================================================

CREATE TABLE returns (
    return_id         SERIAL       PRIMARY KEY,
    return_number     VARCHAR(20)  NOT NULL UNIQUE,
    order_id          INT          NOT NULL REFERENCES orders(order_id),
    customer_id       INT          NOT NULL REFERENCES customers(customer_id),
    status            VARCHAR(20)  NOT NULL DEFAULT 'REQUESTED'
                      CHECK (status IN ('REQUESTED','APPROVED','IN_TRANSIT','RECEIVED','INSPECTED','REFUNDED','REJECTED')),
    refund_method     VARCHAR(20)  NOT NULL CHECK (refund_method IN ('ORIGINAL_PAYMENT','STORE_CREDIT')),
    awaiting_finance  BOOLEAN      NOT NULL DEFAULT FALSE,  -- TRUE while the return's refund total above 10,000 waits
    label_code        VARCHAR(40)  UNIQUE,              -- value inside the QR code
    version           INT          NOT NULL DEFAULT 1,  -- optimistic lock: stops two agents updating at once
    requested_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    closed_at         TIMESTAMPTZ,                      -- set when REFUNDED or REJECTED (cycle time)
    CONSTRAINT chk_closed_only_final CHECK ((status IN ('REFUNDED','REJECTED')) = (closed_at IS NOT NULL))
);
CREATE INDEX ix_returns_status          ON returns (status);
CREATE INDEX ix_returns_customer_recent ON returns (customer_id, requested_at);
CREATE INDEX ix_returns_order           ON returns (order_id);

CREATE TABLE return_items (
    return_item_id       SERIAL        PRIMARY KEY,
    return_id            INT           NOT NULL REFERENCES returns(return_id) ON DELETE CASCADE,
    order_item_id        INT           NOT NULL REFERENCES order_items(order_item_id),
    quantity             SMALLINT      NOT NULL CHECK (quantity > 0),
    reason_id            SMALLINT      NOT NULL REFERENCES return_reasons(reason_id),
    reason_note          VARCHAR(500),
    days_since_delivery  SMALLINT      NOT NULL,
    is_eligible          BOOLEAN       NOT NULL,
    eligibility_reason   VARCHAR(300)  NOT NULL,          -- plain-English explanation shown to customer
    CONSTRAINT uq_return_order_item UNIQUE (return_id, order_item_id)
);
CREATE INDEX ix_return_items_order_item ON return_items (order_item_id);
CREATE INDEX ix_return_items_reason     ON return_items (reason_id);
-- v2: a bought item can be in only one eligible return, so a double click on Submit cannot
-- create a second return for it. Insert the return and its items in one transaction.
CREATE UNIQUE INDEX uq_return_items_eligible_order_item ON return_items (order_item_id) WHERE is_eligible;

CREATE TABLE return_photos (
    photo_id        SERIAL       PRIMARY KEY,
    return_item_id  INT          NOT NULL REFERENCES return_items(return_item_id) ON DELETE CASCADE,
    file_path       VARCHAR(300) NOT NULL,              -- stored locally, e.g. uploads/2026/11/abc.jpg
    uploaded_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_photos_item ON return_photos (return_item_id);

-- One inspection per return item (scan twice = no second inspection).
CREATE TABLE inspections (
    inspection_id   SERIAL       PRIMARY KEY,
    return_item_id  INT          NOT NULL UNIQUE REFERENCES return_items(return_item_id),
    agent_id        INT          NOT NULL REFERENCES staff_users(staff_id),
    grade           CHAR(1)      NOT NULL CHECK (grade IN ('A','B','C')),
    decision        VARCHAR(10)  NOT NULL CHECK (decision IN ('ACCEPT','REJECT')),
    refund_percent  SMALLINT     NOT NULL CHECK (refund_percent IN (0,50,100)),
    notes           VARCHAR(500),
    inspected_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT chk_grade_percent CHECK (
        (decision = 'REJECT' AND refund_percent = 0) OR
        (decision = 'ACCEPT' AND grade = 'C' AND refund_percent = 50) OR
        (decision = 'ACCEPT' AND grade IN ('A','B') AND refund_percent = 100))
);
CREATE INDEX ix_inspections_agent ON inspections (agent_id);

-- =========================================================
-- 4. MONEY: REFUNDS, FINANCE APPROVALS, LEDGER
-- =========================================================

-- UNIQUE(return_item_id) + UNIQUE(idempotency_key) = a refund can never be created twice.
CREATE TABLE refunds (
    refund_id          SERIAL        PRIMARY KEY,
    return_item_id     INT           NOT NULL UNIQUE REFERENCES return_items(return_item_id),
    amount             NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    method             VARCHAR(20)   NOT NULL CHECK (method IN ('ORIGINAL_PAYMENT','STORE_CREDIT')),
    requires_approval  BOOLEAN       NOT NULL,          -- v2: TRUE when the RETURN's refund total is above 10,000
    status             VARCHAR(20)   NOT NULL
                       CHECK (status IN ('PENDING_APPROVAL','APPROVED','PROCESSING','PAID','FAILED','REJECTED')),
    idempotency_key    VARCHAR(64)   NOT NULL UNIQUE,   -- 'refund-<return_item_id>'
    gateway_reference  VARCHAR(64),                     -- NULL for store credit (never sent to the gateway)
    attempt_count      SMALLINT      NOT NULL DEFAULT 0,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT now(),
    paid_at            TIMESTAMPTZ,
    -- v2: the threshold is checked by the service on the return total, so the database only
    -- makes sure a refund waiting for finance is marked as needing approval.
    CONSTRAINT chk_pending_needs_approval CHECK (status <> 'PENDING_APPROVAL' OR requires_approval),
    -- v2: store credit is paid without the gateway, so only gateway refunds need a reference.
    CONSTRAINT chk_paid_has_ref CHECK (
        status <> 'PAID' OR
        (paid_at IS NOT NULL AND (method = 'STORE_CREDIT' OR gateway_reference IS NOT NULL)))
);
CREATE INDEX ix_refunds_status ON refunds (status);

-- v2: one finance decision per return, because the threshold applies to the return total.
CREATE TABLE finance_approvals (
    approval_id  SERIAL       PRIMARY KEY,
    return_id    INT          NOT NULL UNIQUE REFERENCES returns(return_id),
    reviewer_id  INT          NOT NULL REFERENCES staff_users(staff_id),
    decision     VARCHAR(10)  NOT NULL CHECK (decision IN ('APPROVED','REJECTED')),
    comment      VARCHAR(500),
    decided_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Insert-only money record. Corrections are new REVERSAL rows.
CREATE TABLE ledger_entries (
    entry_id           BIGSERIAL     PRIMARY KEY,
    refund_id          INT           NOT NULL REFERENCES refunds(refund_id),
    customer_id        INT           NOT NULL REFERENCES customers(customer_id),
    entry_type         VARCHAR(10)   NOT NULL CHECK (entry_type IN ('REFUND','REVERSAL')),
    amount             NUMERIC(12,2) NOT NULL,          -- positive for REFUND, negative for REVERSAL
    method             VARCHAR(20)   NOT NULL CHECK (method IN ('ORIGINAL_PAYMENT','STORE_CREDIT')),
    gateway_reference  VARCHAR(64),
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CONSTRAINT uq_one_entry_per_type UNIQUE (refund_id, entry_type),
    CONSTRAINT chk_sign CHECK ((entry_type = 'REFUND' AND amount > 0) OR (entry_type = 'REVERSAL' AND amount < 0))
);
CREATE INDEX ix_ledger_customer ON ledger_entries (customer_id);

CREATE FUNCTION block_changes() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% is insert-only; add a new row instead', TG_TABLE_NAME;
END $$;
CREATE TRIGGER trg_ledger_insert_only
    BEFORE UPDATE OR DELETE ON ledger_entries
    FOR EACH ROW EXECUTE FUNCTION block_changes();

-- =========================================================
-- 5. AUDIT AND FLAGS
-- =========================================================

CREATE TABLE audit_log (
    audit_id     BIGSERIAL    PRIMARY KEY,
    return_id    INT          REFERENCES returns(return_id),   -- filled for return events; powers the timeline
    entity_type  VARCHAR(30)  NOT NULL,                        -- RETURN, RETURN_ITEM, REFUND, CUSTOMER ...
    entity_id    INT          NOT NULL,
    action       VARCHAR(30)  NOT NULL,                        -- STATUS_CHANGE, INSPECTED, APPROVED ...
    old_status   VARCHAR(20),
    new_status   VARCHAR(20),
    actor_type   VARCHAR(10)  NOT NULL CHECK (actor_type IN ('CUSTOMER','STAFF','SYSTEM')),
    actor_id     INT,                                          -- customer_id or staff_id; NULL for SYSTEM
    details      JSONB,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_return_time ON audit_log (return_id, created_at);
CREATE INDEX ix_audit_entity      ON audit_log (entity_type, entity_id);

CREATE TRIGGER trg_audit_insert_only
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION block_changes();

CREATE TABLE customer_flags (
    flag_id           SERIAL       PRIMARY KEY,
    customer_id       INT          NOT NULL REFERENCES customers(customer_id),
    trigger_return_id INT          NOT NULL REFERENCES returns(return_id),
    returns_in_30d    SMALLINT     NOT NULL CHECK (returns_in_30d > 3),
    flagged_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    reviewed_by       INT          REFERENCES staff_users(staff_id),
    review_note       VARCHAR(500),
    resolved_at       TIMESTAMPTZ
);
-- only one open flag per customer
CREATE UNIQUE INDEX uq_open_flag ON customer_flags (customer_id) WHERE resolved_at IS NULL;

-- =========================================================
-- 6. DASHBOARD VIEWS
-- =========================================================

CREATE VIEW v_return_rate_by_category AS
SELECT c.name AS category,
       COUNT(DISTINCT oi.order_item_id)                       AS items_sold,
       COUNT(DISTINCT ri.order_item_id)                       AS items_returned,
       ROUND(100.0 * COUNT(DISTINCT ri.order_item_id)
             / NULLIF(COUNT(DISTINCT oi.order_item_id), 0), 2) AS return_rate_pct
FROM categories c
JOIN products p        ON p.category_id = c.category_id
JOIN order_items oi    ON oi.product_id = p.product_id
LEFT JOIN return_items ri ON ri.order_item_id = oi.order_item_id
GROUP BY c.name;

CREATE VIEW v_top_reasons AS
SELECT rr.label AS reason, COUNT(*) AS times_used
FROM return_items ri JOIN return_reasons rr ON rr.reason_id = ri.reason_id
GROUP BY rr.label ORDER BY times_used DESC;

CREATE VIEW v_avg_cycle_time AS
SELECT ROUND(AVG(EXTRACT(EPOCH FROM (closed_at - requested_at)) / 3600)::numeric, 1) AS avg_cycle_hours
FROM returns WHERE closed_at IS NOT NULL;

CREATE VIEW v_flagged_customers AS
SELECT cu.customer_id, cu.full_name, cu.email, f.returns_in_30d, f.flagged_at
FROM customer_flags f JOIN customers cu ON cu.customer_id = f.customer_id
WHERE f.resolved_at IS NULL;

CREATE VIEW v_ledger_check AS   -- must always return 0 rows
SELECT r.refund_id, r.amount, COALESCE(SUM(l.amount), 0) AS ledger_total
FROM refunds r LEFT JOIN ledger_entries l ON l.refund_id = r.refund_id
WHERE r.status = 'PAID'
GROUP BY r.refund_id, r.amount
HAVING COALESCE(SUM(l.amount), 0) <> r.amount;

-- =========================================================
-- 7. REFERENCE DATA
-- =========================================================

INSERT INTO categories (name, is_returnable, return_window_days) VALUES
 ('Electronics', TRUE, 10), ('Apparel', TRUE, 30), ('Footwear', TRUE, 30),
 ('Home & Kitchen', TRUE, 30), ('Innerwear', FALSE, NULL), ('Perishables', FALSE, NULL);

INSERT INTO return_reasons (code, label) VALUES
 ('DAMAGED','Arrived damaged'), ('WRONG_ITEM','Wrong item sent'), ('SIZE','Size or fit issue'),
 ('NOT_AS_DESCRIBED','Not as described'), ('CHANGED_MIND','Changed my mind'), ('QUALITY','Poor quality'),
 ('OTHER','Other reason');

-- =========================================================
-- 8. MOCK GATEWAY (separate service, separate schema, no FK to main tables)
-- v2: created only if missing and never dropped here. The gateway service should run this
-- part itself at startup so it works on its own for other teams.
-- =========================================================

CREATE SCHEMA IF NOT EXISTS gateway;
CREATE TABLE IF NOT EXISTS gateway.payments (
    payment_id        BIGSERIAL     PRIMARY KEY,
    idempotency_key   VARCHAR(64)   NOT NULL UNIQUE,   -- same key = same answer, never a second payment
    amount            NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    currency          CHAR(3)       NOT NULL DEFAULT 'INR',
    method            VARCHAR(20)   NOT NULL,
    status            VARCHAR(10)   NOT NULL CHECK (status IN ('SUCCESS','FAILED')),
    gateway_reference VARCHAR(64)   NOT NULL UNIQUE,
    response_body     JSONB         NOT NULL,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT now()
);

COMMIT;
