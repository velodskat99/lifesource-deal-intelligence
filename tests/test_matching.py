def test_exact_match(tmp_db):
    from lifesource.db import init_db, get_connection
    from lifesource.matching import find_or_create_product

    init_db(tmp_db)
    conn = get_connection(tmp_db)

    product_id_1 = find_or_create_product(conn, "Large Eggs 18ct", "dairy")
    assert product_id_1 is not None

    product_id_2 = find_or_create_product(conn, "Large Eggs 18ct", "dairy")
    assert product_id_1 == product_id_2

    conn.close()


def test_alias_match(tmp_db):
    from lifesource.db import init_db, get_connection
    from lifesource.matching import find_or_create_product, add_alias

    init_db(tmp_db)
    conn = get_connection(tmp_db)

    product_id = find_or_create_product(conn, "Large Eggs 18ct", "dairy")
    add_alias(conn, product_id, "lg eggs 18ct")

    matched_id = find_or_create_product(conn, "lg eggs 18ct", "dairy")
    assert matched_id == product_id

    conn.close()


def test_case_insensitive_match(tmp_db):
    from lifesource.db import init_db, get_connection
    from lifesource.matching import find_or_create_product

    init_db(tmp_db)
    conn = get_connection(tmp_db)

    product_id_1 = find_or_create_product(conn, "Large Eggs 18ct", "dairy")
    product_id_2 = find_or_create_product(conn, "large eggs 18ct", "dairy")
    assert product_id_1 == product_id_2

    conn.close()


def test_new_product_created_when_no_match(tmp_db):
    from lifesource.db import init_db, get_connection
    from lifesource.matching import find_or_create_product

    init_db(tmp_db)
    conn = get_connection(tmp_db)

    id1 = find_or_create_product(conn, "Apples", "produce")
    id2 = find_or_create_product(conn, "Bananas", "produce")
    assert id1 != id2

    conn.close()
