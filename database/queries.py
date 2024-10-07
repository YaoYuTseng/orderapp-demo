### Note: DO NOT use FORMAT as it will put comma in numerical value and format it as string
def format_insert_query(
    table: str,
    cols: list[str],
    val_args: str | None = None,
    duplicate_args: str | None = None,
) -> str:
    joined = ", ".join(cols)
    if not val_args:
        placeholders = ", ".join(["%s"] * len(cols))
    else:
        placeholders = val_args
    if not duplicate_args:
        query = f"""
        INSERT INTO orderapp.{table} ({joined}) VALUES ({placeholders})
        """
    else:
        query = f"""
        INSERT INTO orderapp.{table} ({joined}) VALUES ({placeholders}) {duplicate_args}
        """
    return query


def format_delete_query(
    table: str,
    cols: list[str],
    val_args: str | None = None,
) -> str:
    if not val_args:
        conditions = "AND ".join([f"{col} = %s" for col in cols])
    else:
        conditions = val_args
    query = f"""
    DELETE FROM orderapp.{table} WHERE {conditions}
    """
    return query


# Queries for order_page
## Product price is the latest price for a given product
PRODUCT_PRICE = """
        SELECT
            p.product_name,
            pp.price
        FROM orderapp.products p
        JOIN orderapp.product_prices pp
            ON p.product_id = pp.product_id
            AND pp.effective_timestamp = (
                SELECT MAX(effective_timestamp)
                FROM orderapp.product_prices
                WHERE product_id = p.product_id)
        """

TODAY_ORDERS = """
        SELECT 
            o.order_id,
            p.product_name,
            od.quantity,
            uom.uom_name,
            (pp.price * od.quantity) AS price_total,
            o.order_status,
            o.note,
            o.price_total AS order_total,
            o.order_timestamp,
            o.is_paid
        FROM
            orderapp.order_details od
            JOIN orderapp.orders o ON od.order_id = o.order_id
            JOIN orderapp.products p ON od.product_id = p.product_id
            JOIN orderapp.uom ON p.uom_id = uom.uom_id
            JOIN orderapp.product_prices pp
                ON od.product_id = pp.product_id
                AND pp.effective_timestamp = (
                COALESCE(
                    (SELECT MAX(effective_timestamp)
                    FROM orderapp.product_prices
                    WHERE product_id = od.product_id
                    AND effective_timestamp <= o.order_timestamp),
                    (SELECT MIN(effective_timestamp)
                    FROM orderapp.product_prices
                    WHERE product_id = od.product_id))
            )
        WHERE
            DATE(o.order_timestamp) = CURDATE()
            AND o.completion_timestamp IS NULL
        """
FUTURE_ORDERS = """
        SELECT 
            o.order_id,
            p.product_name,
            od.quantity,
            uom.uom_name,
            (pp.price * od.quantity) AS price_total,
            o.order_status,
            o.note,
            o.price_total AS order_total,
            o.order_timestamp,
            o.completion_timestamp,
            o.is_paid
        FROM
            orderapp.order_details od
            JOIN orderapp.orders o ON od.order_id = o.order_id
            JOIN orderapp.products p ON od.product_id = p.product_id
            JOIN orderapp.uom ON p.uom_id = uom.uom_id
            JOIN orderapp.product_prices pp
                ON od.product_id = pp.product_id
                AND pp.effective_timestamp = (
                COALESCE(
                    (SELECT MAX(effective_timestamp)
                    FROM orderapp.product_prices
                    WHERE product_id = od.product_id
                    AND effective_timestamp <= o.order_timestamp),
                    (SELECT MIN(effective_timestamp)
                    FROM orderapp.product_prices
                    WHERE product_id = od.product_id))
            )
        WHERE
            o.completion_timestamp IS NOT NULL
            AND (
                o.order_status != "已完成"
                OR DATE(o.order_timestamp) >= CURDATE()
                )
        """
# CTE1: SELECT the latest product cost closest to a specific order
# CTE2: Calculate the order total cost based on quantity and latest cost
## For overview, only the status="已完成" are selected (excluding "準備中", "已取消")
## so that unfinished orders' cost and income are properly
PREVIOUS_ORDERS_OVERVIEW = """
        WITH order_latest_product_costs AS (
            SELECT 
                od.order_id,
                od.product_id,
                pc.cost_per_unit
            FROM 
                orderapp.order_details od
                
            JOIN orderapp.orders o ON od.order_id = o.order_id
            JOIN LATERAL (
                SELECT 
                    pc.product_id,
                    pc.cost_per_unit,
                    pc.cost_date
                FROM 
                    orderapp.product_costs pc
                WHERE
                    pc.product_id = od.product_id
                    AND (
                        pc.cost_date <= DATE(o.order_timestamp)
                        OR pc.cost_date = (
                            SELECT MIN(cost_date)
                            FROM orderapp.product_costs
                            WHERE product_id = od.product_id
                        )
                    )
                ORDER BY 
                    CASE 
                        WHEN pc.cost_date <= DATE(o.order_timestamp) THEN 0
                        ELSE 1
                    END,
                    pc.cost_date DESC
                LIMIT 1
            ) pc ON true
        ),
        order_total_cost AS(
            SELECT
                od.order_id,
                CASE
                    WHEN COUNT(olpc.cost_per_unit) != COUNT(od.product_id) THEN NULL
                    ELSE CAST(SUM(od.quantity * olpc.cost_per_unit) AS DECIMAL(10, 2))
                END AS total_product_cost
            FROM 
                orderapp.order_details od
            LEFT JOIN 
                order_latest_product_costs olpc ON od.product_id = olpc.product_id AND od.order_id = olpc.order_id
            GROUP BY 
                od.order_id
        )
        SELECT
            DATE(o.order_timestamp) AS order_date,
            GROUP_CONCAT(o.order_id) AS total_id_list,
            GROUP_CONCAT(
                CASE
                    WHEN o.order_status = "已完成" THEN o.order_id
                    ELSE NULL
                END) AS finished_id_list,
            GROUP_CONCAT(
                CASE
                    WHEN o.order_status = "準備中" THEN o.order_id
                    ELSE NULL
                END) AS prepared_id_list,
            GROUP_CONCAT(
                CASE
                    WHEN o.order_status = "已取消" THEN o.order_id
                    ELSE NULL
                END) AS cancelled_id_list,
            CASE 
                WHEN COUNT(CASE WHEN o.order_status = '已完成' THEN 1 ELSE NULL END) = 0 THEN 'N/A'
                WHEN COUNT(
                    CASE 
                        WHEN o.order_status = '已完成' AND otc.total_product_cost IS NULL THEN 1
                        ELSE NULL
                    END
                ) > 0 THEN 'N/A'
                ELSE SUM(
                        CASE
                            WHEN o.order_status = '已完成' THEN otc.total_product_cost
                            ELSE 0
                        END)
            END AS summed_finished_cost,
            SUM(
                CASE
                    WHEN o.order_status = "已完成" THEN o.price_total
                    ELSE 0
                END) AS summed_finished_price

        FROM orderapp.orders o
        LEFT JOIN 
            order_total_cost otc ON o.order_id = otc.order_id
        WHERE
            DATE(o.order_timestamp) <= CURDATE()
        GROUP BY DATE(o.order_timestamp)
        ORDER BY DATE(o.order_timestamp) DESC
        """

# Should be called via helper function
## Product prices differ based on order timestamp
PREVIOUS_ORDER_DETAILS = """
        SELECT
            o.order_id,
            o.order_timestamp,
            p.product_name,
            od.quantity,
            uom.uom_name,
            (pp.price * od.quantity) AS price_total,
            COALESCE(CAST(pc.cost_per_unit * od.quantity AS DECIMAL(10, 2)), 'N/A') AS products_cost,
            o.price_total AS order_total,
            o.order_status,
            o.is_paid,
            o.note
        FROM
            orderapp.order_details od
        JOIN orderapp.orders o ON od.order_id = o.order_id
        JOIN orderapp.products p ON od.product_id = p.product_id
        JOIN orderapp.uom ON p.uom_id = uom.uom_id
        LEFT JOIN orderapp.product_costs pc 
            ON od.product_id = pc.product_id
            AND pc.cost_date = (
                COALESCE(
                    (SELECT MAX(cost_date)
                    FROM orderapp.product_costs
                    WHERE product_id = od.product_id
                    AND cost_date <= DATE(o.order_timestamp)),
                    (SELECT MIN(cost_date)
                    FROM orderapp.product_costs
                    WHERE product_id = od.product_id))
            )
        LEFT JOIN orderapp.product_prices pp 
            ON od.product_id = pp.product_id
            AND pp.effective_timestamp = (
                COALESCE(
                    (SELECT MAX(effective_timestamp)
                    FROM orderapp.product_prices
                    WHERE product_id = od.product_id
                    AND effective_timestamp <= o.order_timestamp),
                    (SELECT MIN(effective_timestamp)
                    FROM orderapp.product_prices
                    WHERE product_id = od.product_id))
            )
        WHERE
            o.order_id IN ({placeholders})
        ORDER BY o.order_timestamp
        """

# Queries for recipe_page
## RECIPES used LEFT JOIN because some materials in recipes may not have a purchase record
PRODUCT_OVERVIEW = """
        SELECT
            p.product_id,
            p.product_name,
            uom.uom_name,
            pp.price,
            COALESCE(CAST(pc.cost_per_unit AS DECIMAL(10,2)), "N/A") AS cost_per_product
        FROM orderapp.products p
        JOIN orderapp.uom ON p.uom_id = uom.uom_id
        JOIN orderapp.product_prices pp
            ON p.product_id = pp.product_id
            AND pp.effective_timestamp = (
                SELECT MAX(effective_timestamp)
                FROM orderapp.product_prices
                WHERE product_id = p.product_id)
        LEFT JOIN orderapp.product_costs pc 
            ON p.product_id = pc.product_id
            AND pc.cost_date = (
                SELECT MAX(cost_date)
                FROM orderapp.product_costs
                WHERE product_id = p.product_id
                AND cost_date <= CURDATE()
            )
        """

## The latest (combination of) recipe content will have their end_timestamp as null
RECIPES = """
        SELECT
            p.product_id, 
            p.product_name,
            uom.uom_name,
            m.material_name,
            COALESCE(CAST(mc.cost_per_unit AS DECIMAL(10, 2)), "N/A") AS cost_per_material,
            r.quantity,
            COALESCE(CAST(r.quantity * mc.cost_per_unit AS DECIMAL(10, 2)), "N/A") AS total_material_cost,
            pp.price
        FROM orderapp.recipes r
        JOIN orderapp.products p ON r.product_id = p.product_id
        JOIN orderapp.uom ON p.uom_id = uom.uom_id
        JOIN orderapp.materials m ON r.material_id = m.material_id
        JOIN orderapp.product_prices pp
            ON r.product_id = pp.product_id
            AND pp.effective_timestamp = (
                SELECT MAX(effective_timestamp)
                FROM orderapp.product_prices
                WHERE product_id = r.product_id)
        LEFT JOIN orderapp.material_costs mc 
            ON r.material_id = mc.material_id
            AND mc.cost_date = (
                SELECT MAX(cost_date)
                FROM orderapp.material_costs
                WHERE material_id = r.material_id
                AND cost_date <= CURDATE()
            )
        WHERE r.end_timestamp IS NULL
        """

# Queries for material_page
# o.order_timestamp >= r.start_timestamp ensure recipe existence before order
# AND (r.end_timestamp IS NULL ...) include currently in use recipe
# (...OR o.order_timestamp < r.end_timestamp) include not currently in use but exist at order_timestamp recipe
MATERIALS = """
        WITH material_usage AS (
            SELECT 
                r.material_id,
                SUM(od.quantity * r.quantity) AS total_used_quantity
            FROM 
                orderapp.order_details od
            JOIN 
                orderapp.recipes r ON od.product_id = r.product_id
            JOIN 
                orderapp.orders o ON od.order_id = o.order_id
            WHERE o.order_status = "已完成"
            AND o.order_timestamp >= r.start_timestamp
            AND (r.end_timestamp IS NULL OR o.order_timestamp < r.end_timestamp)
            GROUP BY 
                r.material_id
        ),
        summed_purchase_details AS (
            SELECT 
                pd.material_id,
                SUM(pd.quantity) AS total_purchase_quantity
            FROM
                orderapp.purchase_details pd
            GROUP BY pd.material_id
        )
        SELECT
            m.material_name,
            COALESCE(spd.total_purchase_quantity, 0),
            COALESCE(mu.total_used_quantity, 0),
            CAST((COALESCE(spd.total_purchase_quantity, 0) - COALESCE(mu.total_used_quantity, 0)) AS DECIMAL(10,2)) AS material_stocked,
            COALESCE(CAST(mc.cost_per_unit AS DECIMAL(10, 2)), "N/A") AS cost_per_material
        FROM orderapp.materials m
        JOIN orderapp.uom ON m.uom_id = uom.uom_id
        LEFT JOIN material_usage mu ON m.material_id = mu.material_id
        LEFT JOIN summed_purchase_details spd ON m.material_id = spd.material_id
        LEFT JOIN orderapp.material_costs mc 
            ON m.material_id = mc.material_id
            AND mc.cost_date = (
                SELECT MAX(cost_date)
                FROM orderapp.material_costs
                WHERE material_id = m.material_id
                AND cost_date <= CURDATE()
            )
        """

# Queries for purchase_page
PURCHASES_OVERVIEW = """
        SELECT
            p.purchase_id,
            p.purchase_date,
            v.vendor_name,
            pd.material_name_list,
            pd.purchase_summed_price
        FROM
            orderapp.purchases p
            JOIN orderapp.vendors v ON p.vendor_id = v.vendor_id
            JOIN(
                SELECT
                    pd.purchase_id,
                    SUM(pd.price_total) AS purchase_summed_price,
                    GROUP_CONCAT(m.material_name ORDER BY m.material_id SEPARATOR '、') AS material_name_list
                FROM
                    orderapp.purchase_details pd
                    JOIN orderapp.materials m ON pd.material_id = m.material_id
                GROUP BY pd.purchase_id
            )pd ON p.purchase_id = pd.purchase_id
        ORDER BY p.purchase_date DESC
        """

PURCHASE_DETAILS = """
        SELECT 
            p.purchase_id,
            v.vendor_name,
            p.purchase_date,
            m.material_name,
            pd.quantity,
            pd.price_total
        FROM orderapp.purchases p
        JOIN orderapp.purchase_details pd ON p.purchase_id = pd.purchase_id
        JOIN orderapp.materials m ON pd.material_id = m.material_id
        JOIN orderapp.vendors v ON p.vendor_id = v.vendor_id
        """

# Queries for existing data
existed = {
    "product_name": "SELECT product_name FROM orderapp.products",
    "vendor_name": "SELECT vendor_name FROM orderapp.vendors",
    "uom_name": "SELECT uom_name FROM orderapp.uom",
    "material_name": "SELECT material_name FROM orderapp.materials",
    "vendor_name": "SELECT vendor_name FROM orderapp.vendors",
}

# Queries for inserting transaction
insert = {
    "product_name": format_insert_query("products", ["product_name"]),
    "vendor_name": format_insert_query("vendors", ["vendor_name"]),
    "uom_name": format_insert_query("uom", ["uom_name"]),
    "material_name": format_insert_query("materials", ["material_name"]),
    "order_basics": format_insert_query("orders", ["price_total", "note"]),
    "order_details": format_insert_query(
        "order_details",
        ["order_id", "product_id", "quantity"],
        val_args="%s, (SELECT product_id FROM orderapp.products WHERE product_name = %s), %s",
    ),
    "future_order_basics": format_insert_query(
        "orders", ["price_total", "note", "completion_timestamp", "is_paid"]
    ),
    "product_basics": format_insert_query(
        "products",
        ["product_name", "uom_id"],
        val_args="%s, (SELECT uom_id FROM orderapp.uom WHERE uom_name = %s)",
    ),
    "product_prices": format_insert_query("product_prices", ["product_id", "price"]),
    "recipes": format_insert_query(
        "recipes",
        ["product_id", "material_id", "quantity"],
        val_args="(SELECT product_id FROM orderapp.products WHERE product_name = %s), (SELECT material_id FROM orderapp.materials WHERE material_name = %s), %s",
    ),
    "purchase_basics": format_insert_query(
        "purchases",
        ["purchase_date", "vendor_id"],
        val_args="%s, (SELECT vendor_id FROM orderapp.vendors WHERE vendor_name = %s)",
    ),
    "purchase_details": format_insert_query(
        "purchase_details",
        ["purchase_id", "material_id", "quantity", "price_total"],
        val_args="%s,(SELECT material_id FROM orderapp.materials WHERE material_name = %s),%s,%s",
    ),
    "vendors": format_insert_query(
        "vendors",
        [
            "vendor_name",
            "office_phone",
            "mobile_phone",
            "address",
            "tax_id",
            "contact_name",
            "contact_mobile_phone",
            "open_days",
            "note",
        ],
    ),
}
# Queries for updating data
update = {
    "order_status": "UPDATE orderapp.orders SET order_status= %s WHERE order_id = %s",
    "order_paid": "UPDATE orderapp.orders SET is_paid= %s WHERE order_id = %s",
    "order_completion_timestamp": """
        UPDATE orderapp.orders 
            SET order_timestamp = CASE 
                WHEN order_status = '已完成' THEN completion_timestamp
                ELSE CURRENT_TIMESTAMP 
            END
            WHERE order_id = %s;
        """,
    "purchases": format_insert_query(
        "purchase_details",
        ["purchase_id", "material_id", "quantity", "price_total"],
        val_args="%s,(SELECT material_id FROM orderapp.materials WHERE material_name = %s),%s,%s",
        duplicate_args="AS new_vals ON DUPLICATE KEY UPDATE material_id = new_vals.material_id, quantity = new_vals.quantity, price_total = new_vals.price_total;",
    ),
    # Update need to include product name because it does not have a default value in table
    # Product prices update was an simple insert with a new default effective timestamp (if price change)
    "product_basics": format_insert_query(
        "products",
        ["product_id", "product_name", "uom_id"],
        val_args="%s, %s, (SELECT uom_id FROM orderapp.uom WHERE uom_name = %s)",
        duplicate_args="AS new_vals ON DUPLICATE KEY UPDATE uom_id = new_vals.uom_id;",
    ),
    # Noted that table recipe has composite primary key of product and material_id
    "recipes": format_insert_query(
        "recipes",
        ["product_id", "material_id", "quantity"],
        val_args="%s, (SELECT material_id FROM orderapp.materials WHERE material_name = %s), %s",
    ),
    "order_basics": format_insert_query(
        "orders",
        ["order_id", "price_total", "note"],
        duplicate_args="AS new_vals ON DUPLICATE KEY UPDATE price_total = new_vals.price_total, note = new_vals.note;",
    ),
    "future_order_basics": format_insert_query(
        "orders",
        ["order_id", "price_total", "note", "completion_timestamp"],
        duplicate_args="AS new_vals ON DUPLICATE KEY UPDATE price_total = new_vals.price_total, note = new_vals.note, completion_timestamp = new_vals.completion_timestamp;",
    ),
    # Noted that table order_details has composite primary key of order and product_id
    "order_details": format_insert_query(
        "order_details",
        ["order_id", "product_id", "quantity"],
        val_args="%s, (SELECT product_id FROM orderapp.products WHERE product_name = %s), %s",
        duplicate_args="AS new_vals ON DUPLICATE KEY UPDATE quantity = new_vals.quantity;",
    ),
    "vendors": format_insert_query(
        "vendors",
        [
            "vendor_id",
            "vendor_name",
            "office_phone",
            "mobile_phone",
            "address",
            "tax_id",
            "contact_name",
            "contact_mobile_phone",
            "open_days",
            "note",
        ],
        duplicate_args="""
            AS new_vals ON DUPLICATE KEY UPDATE 
                vendor_name = new_vals.vendor_name,
                office_phone = new_vals.office_phone,
                mobile_phone = new_vals.mobile_phone,
                address = new_vals.address,
                tax_id = new_vals.tax_id,
                contact_name = new_vals.contact_name,
                contact_mobile_phone = new_vals.contact_mobile_phone,
                open_days = new_vals.open_days,
                note = new_vals.note;
        """,
    ),
}

update_delete = {
    "purchases": format_delete_query(
        "purchase_details",
        ["purchase_id", "material_id"],
        val_args="purchase_id = %s AND material_id = (SELECT material_id FROM orderapp.materials WHERE material_name = %s)",
    ),
    # No recipe is deleted on update, instead a end_timestamp is assigned to it (for associating with product ordered in such timeframe)
    "set_recipes_end": """
        UPDATE orderapp.recipes
            SET end_timestamp = CURRENT_TIMESTAMP
            WHERE product_id = %s
            AND material_id = (SELECT material_id FROM orderapp.materials WHERE material_name = %s)
            AND end_timestamp IS NULL;
        """,
    "order_details": format_delete_query(
        "order_details",
        ["order_id", "product_id"],
        val_args="order_id = %s AND product_id = (SELECT product_id FROM orderapp.products WHERE product_name = %s)",
    ),
}

# Queries for deleting data
delete = {
    "orders": format_delete_query("orders", ["order_id"]),
    "order_details": format_delete_query("order_details", ["order_id"]),
    "purchases": format_delete_query("purchases", ["purchase_id"]),
    "purchase_details": format_delete_query("purchase_details", ["purchase_id"]),
    "products": format_delete_query("products", ["product_id"]),
    "product_prices": format_delete_query("product_prices", ["product_id"]),
    "product_costs": format_delete_query("product_costs", ["product_id"]),
    "recipes": format_delete_query("recipes", ["product_id"]),
    "vendors": format_delete_query("vendors", ["vendor_id"]),
    "uom": format_delete_query("uom", ["uom_id"]),
    "materials": format_delete_query("materials", ["material_id"]),
}
