def test_init_db_creates_tables(tmp_db):
    from lifesource.db import init_db, get_connection

    init_db(tmp_db)
    conn = get_connection(tmp_db)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert "products" in tables
    assert "deals" in tables
    assert "purchase_history" in tables
    assert "user_preferences" in tables
    assert "price_history" in tables


def test_init_db_is_idempotent(tmp_db):
    from lifesource.db import init_db

    init_db(tmp_db)
    init_db(tmp_db)  # Should not raise


def test_insert_and_query_deal(db):
    db.execute(
        """INSERT INTO deals (store, item_name, category, regular_price, sale_price, unit,
           start_date, end_date, source_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("heb", "Large Eggs 18ct", "dairy", 3.49, 1.99, "each",
         "2026-04-06", "2026-04-12", "scraper"),
    )
    db.commit()

    row = db.execute("SELECT * FROM deals WHERE store = 'heb'").fetchone()
    assert row is not None
    assert row["item_name"] == "Large Eggs 18ct"
    assert row["sale_price"] == 1.99


def test_insert_and_query_product(db):
    db.execute(
        "INSERT INTO products (name, category, aliases) VALUES (?, ?, ?)",
        ("Large Eggs 18ct", "dairy", '["eggs 18ct", "lg eggs"]'),
    )
    db.commit()

    row = db.execute("SELECT * FROM products WHERE name = 'Large Eggs 18ct'").fetchone()
    assert row is not None
    assert row["category"] == "dairy"


def test_insert_and_query_purchase(db):
    db.execute(
        """INSERT INTO purchase_history (store, item_name, price, quantity, unit,
           purchase_date, source)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("heb", "Large Eggs 18ct", 2.49, 1, "each", "2026-04-01", "manual"),
    )
    db.commit()

    row = db.execute("SELECT * FROM purchase_history").fetchone()
    assert row is not None
    assert row["price"] == 2.49
    assert row["source"] == "manual"
