from datetime import date, datetime, timedelta

from nicegui import app

from logging_setup.setup import LOGGER

from .DataAccessObjects import DaoOrderapp

# CTE (Common Table Expression)

# CTE1: SELECT the latest material cost (include today's)
# CTE2: SELECT purchase details to calculate stocked material and total spent (include today's)
# CTE3: SELECT order details to calculate used material (NOT include today's)
#       -> to avoid cyclical updating where new_cost was applied to today's order, and a new cost is calculated again
#       (based on recipe of sold products existed when the o.timestamp occur)
#       and the associated cost that is took away from the used of such material
## Divided (stocked material - used material) by (total spent - total income) for the material
## Use the earliest documented cost to calculate order cost if no cost is available earlier than the order
## Ignore update when: stocked quantity and cost remain as before
UPDATE_MATERIAL_COST = """
        INSERT INTO orderapp.material_costs (material_id, cost_date, stocked_quantity, stocked_cost, cost_per_unit)
        WITH latest_material_costs AS (
            SELECT 
                mc.material_id,
                mc.stocked_quantity,
                mc.stocked_cost,
                mc.cost_per_unit
            FROM 
                orderapp.material_costs mc
            JOIN (
                SELECT 
                    material_id, 
                    MAX(cost_date) AS max_cost_date
                FROM 
                    orderapp.material_costs
                WHERE cost_date <= %(target_date)s
                GROUP BY 
                    material_id
            ) lmc ON mc.material_id = lmc.material_id AND mc.cost_date = lmc.max_cost_date
        ),
        material_purchases AS (
            SELECT 
                pd.material_id,
                SUM(pd.quantity) AS total_purchased_quantity,
                SUM(pd.price_total) AS total_purchased_cost
            FROM 
                orderapp.purchase_details pd
            JOIN orderapp.purchases p ON pd.purchase_id = p.purchase_id
            WHERE p.purchase_date <= %(target_date)s
            GROUP BY 
                pd.material_id
        ),
        material_usage AS (
            SELECT 
                r.material_id,
                SUM(CASE 
                        WHEN mc.cost_per_unit IS NOT NULL THEN (od.quantity * r.quantity)
                        ELSE NULL
                END) AS total_used_quantity,
                SUM(CASE 
                    WHEN mc.cost_per_unit IS NOT NULL THEN (od.quantity * r.quantity * mc.cost_per_unit)
                    ELSE NULL
                END) AS total_used_cost
            FROM 
                orderapp.order_details od
            JOIN 
                orderapp.recipes r ON od.product_id = r.product_id
            JOIN 
                orderapp.orders o ON od.order_id = o.order_id
            LEFT JOIN 
                orderapp.material_costs mc ON r.material_id = mc.material_id
                AND mc.cost_date = (
                    COALESCE(
                        (SELECT MAX(cost_date)
                        FROM orderapp.material_costs
                        WHERE material_id = r.material_id
                        AND cost_date < DATE(o.order_timestamp)),
                        (SELECT MIN(cost_date)
                        FROM orderapp.material_costs
                        WHERE material_id = r.material_id))
                )
            WHERE o.order_status = "已完成"
            AND DATE(o.order_timestamp) < %(target_date)s -- smaller but not equal to avoid cyclical update
            AND o.order_timestamp >= r.start_timestamp
            AND (r.end_timestamp IS NULL OR o.order_timestamp < r.end_timestamp)
            GROUP BY 
                r.material_id
        )
        SELECT * 
        FROM(
        SELECT 
            m.material_id,
            %(target_date)s AS cost_date,
            (mp.total_purchased_quantity - COALESCE(mu.total_used_quantity, 0)) AS stocked_quantity,
            (mp.total_purchased_cost - COALESCE(mu.total_used_cost, 0)) AS stocked_cost,
            CAST(
                (mp.total_purchased_cost - COALESCE(mu.total_used_cost, 0)) / 
                (mp.total_purchased_quantity - COALESCE(mu.total_used_quantity, 0))
                AS DECIMAL(10, 5)
                )AS cost_per_unit
        FROM 
            orderapp.materials m
        LEFT JOIN 
            material_purchases mp ON m.material_id = mp.material_id
        LEFT JOIN 
            material_usage mu ON m.material_id = mu.material_id
        LEFT JOIN 
            latest_material_costs lmc ON m.material_id = lmc.material_id
        WHERE 
			(
                (mp.total_purchased_quantity - COALESCE(mu.total_used_quantity, 0)) IS NOT NULL AND
                (mp.total_purchased_cost - COALESCE(mu.total_used_cost, 0)) Is NOT NULL
            )
            AND (
                (mp.total_purchased_quantity - COALESCE(mu.total_used_quantity, 0)) != lmc.stocked_quantity OR
                (mp.total_purchased_cost - COALESCE(mu.total_used_cost, 0)) != lmc.stocked_cost OR
                lmc.cost_per_unit IS NULL OR
                CAST(
                (mp.total_purchased_cost - COALESCE(mu.total_used_cost, 0)) / 
                (mp.total_purchased_quantity - COALESCE(mu.total_used_quantity, 0))
                AS DECIMAL(10, 5)
                ) != lmc.cost_per_unit
            )
        )AS new_vals
        ON DUPLICATE KEY UPDATE
            stocked_quantity = new_vals.stocked_quantity,
            stocked_cost = new_vals.stocked_cost,
            cost_per_unit = new_vals.cost_per_unit;
"""

# CTE1: SELECT the latest product cost
# CTE2: SELECT the latest material cost
# CTE3: SELECT the summed cost based on latest material cost and the its quantity for each material in the latest recipe (r.end_timestamp IS NULL)
#       in CASE when one of more of material_cost record do not exist, return null
## Return the summed cost as the product cost
## Ignore updates when total_material_cost can not be calculated OR latest cost != new cost
UPDATE_PRODUCT_COST = """
        INSERT INTO orderapp.product_costs (product_id, cost_date, cost_per_unit)
        WITH latest_product_costs AS (
            SELECT 
                pc.product_id,
                pc.cost_per_unit
            FROM 
                orderapp.product_costs pc
            JOIN (
                SELECT 
                    product_id, 
                    MAX(cost_date) AS max_cost_date
                FROM 
                    orderapp.product_costs
                GROUP BY 
                    product_id
            ) lpc ON pc.product_id = lpc.product_id AND pc.cost_date = lpc.max_cost_date
        ),
        latest_material_costs AS (
            SELECT 
                mc.material_id,
                mc.cost_per_unit
            FROM 
                orderapp.material_costs mc
            JOIN (
                SELECT 
                    material_id, 
                    MAX(cost_date) AS max_cost_date
                FROM 
                    orderapp.material_costs
                GROUP BY 
                    material_id
            ) lmc ON mc.material_id = lmc.material_id AND mc.cost_date = lmc.max_cost_date
        ),
        product_material_costs AS (
            SELECT 
                r.product_id,
                CASE
                    WHEN COUNT(lmc.cost_per_unit) != COUNT(r.material_id) THEN NULL
                    ELSE CAST(SUM(r.quantity * lmc.cost_per_unit) AS DECIMAL(10, 5))
                END AS total_material_cost
            FROM 
                orderapp.recipes r
            LEFT JOIN 
                latest_material_costs lmc ON r.material_id = lmc.material_id
            WHERE r.end_timestamp IS NULL
            GROUP BY 
                r.product_id
        )
        SELECT * 
        FROM(
        SELECT 
            p.product_id,
            CURDATE() AS cost_date,
            pmc.total_material_cost AS cost_per_unit
        FROM 
            orderapp.products p
        LEFT JOIN 
            product_material_costs pmc ON p.product_id = pmc.product_id
        LEFT JOIN 
            latest_product_costs lpc ON p.product_id = lpc.product_id
        WHERE 
            pmc.total_material_cost IS NOT NULL 
            AND pmc.total_material_cost > 0
            AND (lpc.cost_per_unit IS NULL OR pmc.total_material_cost != lpc.cost_per_unit)
        )AS new_vals
        ON DUPLICATE KEY UPDATE
            cost_per_unit = new_vals.cost_per_unit;
"""


# Only store start date before(<) today since future date will be handle in the future, and today is default
# Get only the date of any time representation for comparison
def store_update_startdate(start_date: str | datetime | date):
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(start_date, datetime):
        start_date = start_date.date()

    if start_date < date.today():
        stored_start_date = {"update_start_date": start_date}
        app.storage.general.update(stored_start_date)
        LOGGER.debug(
            f"Cost update set as: {app.storage.general.get('update_start_date')}"
        )


# Update material and product cost when there are no new material and product cost for today
def perform_update(dao: DaoOrderapp, target_date):

    queries_to_commit = []
    queries_to_commit.append((UPDATE_MATERIAL_COST, {"target_date": target_date}))
    queries_to_commit.append((UPDATE_PRODUCT_COST, {"target_date": target_date}))
    transaction_result = dao.perform_transaction(queries_to_commit)

    return f"Update material and product cost for {target_date}. {transaction_result}"


def update_costs(dao: DaoOrderapp, start_date: date = date.today()):
    dao.connect_orderapp()
    # Generate a list of dates based on the start_date
    if start_date == date.today():
        # If start_date is today, the list contains only one date
        dates_to_update = [start_date]
    elif start_date < date.today():
        # If start_date is before today, generate a list of dates from start_date to today
        dates_to_update = [
            (start_date + timedelta(days=i))
            for i in range((date.today() - start_date).days + 1)
        ]
    else:
        LOGGER.error("Start date cannot be in the future.")
        return

    for d in dates_to_update:
        LOGGER.info(perform_update(dao, d))
