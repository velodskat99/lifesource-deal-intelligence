import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    subcategory TEXT,
    aliases TEXT,  -- JSON array of alternate names
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deals (
    id INTEGER PRIMARY KEY,
    store TEXT NOT NULL,
    item_name TEXT NOT NULL,
    product_id INTEGER REFERENCES products(id),
    category TEXT,
    regular_price REAL,
    sale_price REAL NOT NULL,
    unit TEXT,
    start_date DATE,
    end_date DATE,
    source_url TEXT,
    source_type TEXT,
    confidence REAL,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS purchase_history (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    store TEXT,
    item_name TEXT,
    price REAL,
    quantity REAL DEFAULT 1,
    unit TEXT,
    purchase_date DATE,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_preferences (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    avg_purchase_frequency_days REAL,
    preferred_store TEXT,
    avg_price_paid REAL,
    last_purchased DATE,
    total_purchases INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    store TEXT,
    price REAL,
    date DATE,
    UNIQUE(product_id, store, date)
);

CREATE TABLE IF NOT EXISTS shopping_list (
    id INTEGER PRIMARY KEY,
    item_name TEXT NOT NULL,
    quantity REAL DEFAULT 1,
    unit TEXT,
    notes TEXT,
    checked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_deals_store ON deals(store);
CREATE INDEX IF NOT EXISTS idx_deals_end_date ON deals(end_date);
CREATE INDEX IF NOT EXISTS idx_deals_product_id ON deals(product_id);
CREATE INDEX IF NOT EXISTS idx_purchase_history_product_id ON purchase_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON price_history(product_id);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db(db_path: str):
    """Context manager for exception-safe database access."""
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    """Initialize the database schema. Safe to call multiple times."""
    with get_db(db_path) as conn:
        conn.executescript(SCHEMA)
        existing_deal_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(deals)").fetchall()
        }
        if "image_url" not in existing_deal_columns:
            conn.execute("ALTER TABLE deals ADD COLUMN image_url TEXT")
        conn.commit()
