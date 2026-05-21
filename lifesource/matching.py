import json
import logging
import sqlite3

logger = logging.getLogger(__name__)


def normalize_name(name: str) -> str:
    """Normalize a product name for matching: lowercase, strip whitespace/punctuation."""
    return name.lower().strip()


def find_or_create_product(
    conn: sqlite3.Connection,
    item_name: str,
    category: str | None = None,
) -> int:
    """Find an existing product by name/alias, or create a new one. Returns product_id."""
    normalized = normalize_name(item_name)

    # 1. Exact match on name (case-insensitive)
    row = conn.execute(
        "SELECT id FROM products WHERE LOWER(name) = ?", (normalized,)
    ).fetchone()
    if row:
        return row["id"]

    # 2. Alias match
    all_products = conn.execute(
        "SELECT id, aliases FROM products WHERE aliases IS NOT NULL"
    ).fetchall()
    for product in all_products:
        aliases = json.loads(product["aliases"]) if product["aliases"] else []
        for alias in aliases:
            if normalize_name(alias) == normalized:
                return product["id"]

    # 3. Fuzzy match (Jaccard similarity on word tokens)
    best_match_id = None
    best_similarity = 0.0
    query_tokens = set(normalized.split())

    for product in all_products:
        product_name = normalize_name(
            conn.execute("SELECT name FROM products WHERE id = ?", (product["id"],)).fetchone()["name"]
        )
        product_tokens = set(product_name.split())

        if query_tokens and product_tokens:
            intersection = query_tokens & product_tokens
            union = query_tokens | product_tokens
            similarity = len(intersection) / len(union)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match_id = product["id"]

    # Threshold: 0.6 = strong fuzzy match (auto-accept)
    if best_similarity >= 0.6 and best_match_id is not None:
        logger.info(
            f"Fuzzy matched '{item_name}' to product {best_match_id} "
            f"(similarity={best_similarity:.2f})"
        )
        # Auto-add as alias for future exact matching
        add_alias(conn, best_match_id, item_name)
        return best_match_id

    # 4. No match -- create new product
    cursor = conn.execute(
        "INSERT INTO products (name, category, aliases) VALUES (?, ?, ?)",
        (item_name, category, json.dumps([])),
    )
    conn.commit()
    product_id = cursor.lastrowid
    logger.info(f"Created new product: {item_name} (id={product_id})")
    return product_id


def add_alias(conn: sqlite3.Connection, product_id: int, alias: str) -> None:
    """Add an alias to a product for future matching."""
    row = conn.execute("SELECT aliases FROM products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        return

    aliases = json.loads(row["aliases"]) if row["aliases"] else []
    normalized = normalize_name(alias)
    if normalized not in [normalize_name(a) for a in aliases]:
        aliases.append(alias)
        conn.execute(
            "UPDATE products SET aliases = ? WHERE id = ?",
            (json.dumps(aliases), product_id),
        )
        conn.commit()
        logger.info(f"Added alias '{alias}' to product {product_id}")
