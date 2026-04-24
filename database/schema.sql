-- ============================================================
--  Smart Boutique Management System  –  Database Schema
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    cust_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    UNIQUE,
    phone         VARCHAR(10),
    gender        TEXT    CHECK(gender IN ('M','W','Other')),
    age           INTEGER CHECK(age > 0 AND age < 120),
    age_group     TEXT,
    address       TEXT,
    city          TEXT,
    state         TEXT,
    pincode       VARCHAR(10),
    loyalty_tier  TEXT    DEFAULT 'Bronze',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tailors (
    tailor_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT    NOT NULL,
    phone          VARCHAR(10),
    specialty      TEXT,
    experience_yrs INTEGER DEFAULT 0,
    rating         REAL    DEFAULT 0.0,
    availability   TEXT    DEFAULT 'Available',
    joined_date    DATE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS designs (
    design_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    category    TEXT,
    style_tag   TEXT,
    size_range  TEXT,
    fabric      TEXT,
    base_price  REAL,
    image_url   TEXT,
    is_active   INTEGER DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        TEXT    PRIMARY KEY,
    cust_id         INTEGER REFERENCES customers(cust_id),
    tailor_id       INTEGER REFERENCES tailors(tailor_id),
    design_id       INTEGER REFERENCES designs(design_id),
    sku             TEXT,
    category        TEXT,
    size            TEXT,
    qty             INTEGER DEFAULT 1,
    amount          REAL,
    currency        TEXT    DEFAULT 'INR',
    status          TEXT,
    return_flag     INTEGER DEFAULT 0,
    order_date      DATE,
    delivery_date   DATE,
    delivery_days   INTEGER,
    estimated_days  INTEGER,
    season          TEXT,
    weekend_order   INTEGER DEFAULT 0,
    gender          TEXT,
    age             INTEGER,
    ship_city       TEXT,
    ship_state      TEXT,
    ship_postal     TEXT,
    ship_country    TEXT    DEFAULT 'IN',
    b2b             INTEGER DEFAULT 0,
    retail_supplier TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recommendations (
    rec_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    cust_id       INTEGER REFERENCES customers(cust_id),
    design_id     INTEGER REFERENCES designs(design_id),
    score         REAL,
    model_version TEXT,
    reason        TEXT,
    shown_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    clicked       INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS delivery_predictions (
    pred_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id       TEXT    REFERENCES orders(order_id),
    predicted_days INTEGER,
    actual_days    INTEGER,
    model_version  TEXT,
    predicted_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_cust   ON orders(cust_id);
CREATE INDEX IF NOT EXISTS idx_orders_date   ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_season ON orders(season);
CREATE INDEX IF NOT EXISTS idx_rec_cust      ON recommendations(cust_id);
