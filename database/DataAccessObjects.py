import os
from datetime import datetime
from typing import override

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import MySQLConnection

from logging_setup.setup import LOGGER
from pages.components.constants import DAYS_OPTIONS

from . import queries
from .FieldSchema import FieldSchema

load_dotenv()
connect_config = {
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
}

if not all(connect_config.values()):
    LOGGER.error(ValueError(f"Failed to load .env mysql config. {connect_config}"))
    raise ValueError(f"Failed to load .env mysql config. {connect_config}")


# Base data access object for interfacing with MySQL database
class DaoOrderapp:
    def __init__(self, connection: MySQLConnection | None = None):
        self.connection = connection if connection != None else None

    def connect_orderapp(self) -> str:
        try:
            if self.connection is None:
                self.connection = mysql.connector.connect(**connect_config)
                LOGGER.info("Connection success")
            else:
                self.connection.ping(reconnect=True, attempts=3, delay=5)
                LOGGER.info("Connection existed")
        except Exception as e:
            LOGGER.error(ConnectionError(f"Fail to connect: {e}"))

    def close_connection(self):
        try:
            self.connection.close()
            LOGGER.info("Close SQL connection")
        except Exception as e:
            LOGGER.error(e)

    def check_existence(self, table: str, col: str, val: str) -> bool:
        try:
            cursor = self.connection.cursor()
            params = {"val": val}
            query = f"""
                SELECT EXISTS(SELECT * FROM orderapp.{table} WHERE {col} = %(val)s)
                """
            cursor.execute(query, params)
            existence = True if cursor.fetchone()[0] else False
            return existence
        except Exception as e:
            LOGGER.error(e)

    def query_data(
        self, query: str, params: dict | tuple | None = None
    ) -> list[dict] | None:
        cursor = self.connection.cursor(dictionary=True)
        cursor.execute(query, params)
        results = cursor.fetchall()
        try:
            if len(results) == 0:
                return None
            else:
                return results
        except Exception as e:
            LOGGER.error(e)

    def perform_transaction(self, operations: list[tuple]) -> str:
        try:
            for query, params in operations:
                cursor = self.connection.cursor()
                cursor.execute(query, params)
                row_count = cursor.rowcount
            self.connection.commit()
            return f"Transaction successful. Affected: {row_count}."
        except Exception as e:
            self.connection.rollback()
            return f"Transaction failed (Rollback...): {e}\nOperations: {operations}"

    def get_value_options(self, schemas: list[FieldSchema], fields: list[str]):
        for s in schemas:
            if s.field in fields:
                if not queries.existed[s.field]:
                    LOGGER.error(f"No query for checking existence of {s.field}")
                else:
                    existed_vals = self.query_data(queries.existed[s.field])
                    value_options = (
                        [i[s.field] for i in existed_vals] if existed_vals else []
                    )
                    s.value_options = value_options
        return schemas

    def insert_new_names(self, insert_col: str, insert_vals: list[str]):
        try:
            queries_to_commit = []
            if insert_col not in queries.existed:
                LOGGER.error(f"No query for checking existence of {insert_col}")
            if insert_col not in queries.insert:
                LOGGER.error(f"No query for inserting {insert_col}")
            existed = self.query_data(queries.existed[insert_col])
            exisited_names = [i[insert_col] for i in existed] if existed else []
            for val in insert_vals:
                if val not in exisited_names:
                    queries_to_commit.append((queries.insert[insert_col], (val,)))

            if queries_to_commit:
                transaction_result = self.perform_transaction(queries_to_commit)
                LOGGER.info(f"Insert new {insert_col}. {transaction_result}")
            else:
                LOGGER.info(f"No new {insert_col} need inserting")
        except Exception as e:
            LOGGER.error(e)

    # Commit delete is design to be called on one table of a time to identify foreign key violation if happened
    # Note: Beaware of the sequence of delete operations
    def commit_delete(self, delete_id: int, table: str):
        try:
            queries_to_commit = []
            if table not in queries.delete:
                LOGGER.error(f"No delete query for deleting from {table}")
            else:
                queries_to_commit.append((queries.delete[table], (delete_id,)))
                transaction_result = self.perform_transaction(queries_to_commit)
                LOGGER.info(
                    f"Delete id: {delete_id} from {table}. {transaction_result}"
                )
        except Exception as e:
            LOGGER.error(e)

    def clean_up_uom(self, uom_id: int):
        uom_exist = self.check_existence("products", "uom_id", uom_id)
        if not uom_exist:
            self.commit_delete(uom_id, "uom")

    def clean_up_materials(self, material_ids: list[int]):
        for m_id in material_ids:
            in_purchase = self.check_existence("purchase_details", "material_id", m_id)
            in_recipe = self.check_existence("recipes", "material_id", m_id)
            in_cost = self.check_existence("material_costs", "material_id", m_id)
            if not in_purchase and not in_recipe and not in_cost:
                self.commit_delete(m_id, "materials")


# Data access object for purchase page
class DaoPurchasePage(DaoOrderapp):
    def init(self, connection: MySQLConnection | None = None):
        self.connection = (
            connection if connection is not None else super().connect_orderapp()
        )
        super().__init__(connection)

    def fetch_purchase_data(self) -> tuple[list[dict], list[dict]]:
        try:
            overview_data = self.query_data(queries.PURCHASES_OVERVIEW)
            details_data = self.query_data(queries.PURCHASE_DETAILS)
            return overview_data, details_data
        except Exception as e:
            LOGGER.error(e)

    def fetch_purchase_date(self, purchase_id) -> str:
        result = self.query_data(
            "SELECT p.purchase_date from orderapp.purchases p WHERE p.purchase_id = %s",
            (purchase_id,),
        )
        purchase_date = result[0]["purchase_date"]
        return purchase_date

    def insert_purchase_records(
        self, purchase_basic: tuple[str, str], detail_data: list[dict]
    ):
        # Insert purchase basic

        self.query_data(queries.insert["purchase_basics"], purchase_basic)
        # Getting id is necessary to associate the same purchase details with its purchase basics
        purchase_id = self.query_data("SELECT LAST_INSERT_ID() AS purchase_id")[0][
            "purchase_id"
        ]

        # Insert purchase details
        queries_to_commit = []
        for vals in detail_data:
            params = (
                purchase_id,
                vals["material_name"],
                vals["quantity"],
                vals["price_total"],
            )
            insertion = (queries.insert["purchase_details"], params)
            queries_to_commit.append(insertion)

        # Commit
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(f"Insert purchase details. {transaction_result}")
        else:
            LOGGER.warning("No insertion was executed")

    # Product update disable basic info (vendor and purchase_date); thus no need to update those
    def update_purchase_records(
        self, update_id, original_rows: list[dict], update_rows: list[dict]
    ):
        og_vals = [i for row in original_rows for i in row.values()]
        new_vals = [i for row in update_rows for i in row.values()]
        # Early return if new product basic info is the same as old
        if og_vals == new_vals:
            LOGGER.warning(f"No purchase update was executed for id: {update_id}")
            return
        # Only need to consider material for add/delete, others will be handled by on duplicate
        og_materials = [vals["material_name"] for vals in original_rows]
        new_materials = [vals["material_name"] for vals in update_rows]
        # Materials existed in old but not new records should be deleted
        need_delete = [i for i in og_materials if i not in new_materials]
        queries_to_commit = []
        for vals in original_rows:
            if vals["material_name"] in need_delete:
                update_delete = (update_id, vals["material_name"])
                queries_to_commit.append(
                    (queries.update_delete["purchases"], update_delete)
                )
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(
                f"Material(s) deleted in purchase for id: {update_id}. {transaction_result}"
            )
        else:
            LOGGER.warning(
                f"No material was deleted during update from purchase for id: {update_id}"
            )
        queries_to_commit = []
        for vals in update_rows:
            update = (
                update_id,
                vals["material_name"],
                vals["quantity"],
                vals["price_total"],
            )
            insert_products = (queries.update["purchases"], update)
            queries_to_commit.append(insert_products)
        # Commit
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(
                f"Update purchase records for id: {update_id}. {transaction_result}"
            )


# Data access object for recipe page
class DaoRecipePage(DaoOrderapp):
    def __init__(self, connection: MySQLConnection | None = None):
        self.connection = (
            connection if connection is not None else super().connect_orderapp()
        )
        super().__init__(connection)

    def fetch_recipe_data(self) -> tuple[list[dict], list[dict]]:
        try:
            overview_data = self.query_data(queries.PRODUCT_OVERVIEW)
            details_data = self.query_data(queries.RECIPES)
            return overview_data, details_data
        except Exception as e:
            LOGGER.error(e)

    def insert_product_records(self, product_data: dict):
        # Insert product record
        product = (product_data["product_name"], product_data["uom_name"])
        product_price = product_data["price"]
        product_name = product_data["product_name"]

        self.perform_transaction([(queries.insert["product_basics"], product)])
        product_id = self.query_data("SELECT LAST_INSERT_ID() AS product_id")[0][
            "product_id"
        ]
        transaction_result = self.perform_transaction(
            [(queries.insert["product_prices"], (product_id, product_price))]
        )
        LOGGER.info(f"Insert product records for {product_name}. {transaction_result}")

    def insert_recipe_records(self, product_name: str, recipe_data: list[dict]):
        # Insert recipe records for the specific product
        queries_to_commit = []
        for vals in recipe_data:
            recipe = (product_name, vals["material_name"], vals["quantity"])
            queries_to_commit.append((queries.insert["recipes"], recipe))
        # Commit
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(
                f"Insert recipe records for {product_name}. {transaction_result}"
            )
        else:
            LOGGER.warning("No insertion was executed")

    def update_product_records(self, update_id, original_rows: dict, update_rows: dict):
        og_vals = [i for i in original_rows.values()]
        new_vals = [i for i in update_rows.values()]
        # Early return if new product basic info is the same as old
        if og_vals == new_vals:
            LOGGER.warning(f"No product basic update was executed for id: {update_id}")
            return

        queries_to_commit = []
        og_price = original_rows["price"]
        new_price = update_rows["price"]
        # Insert new price (will automatically default a new effective_timestamp) if price change
        if og_price != new_price:
            update_price = (update_id, new_price)
            queries_to_commit.append((queries.insert["product_prices"], update_price))
            LOGGER.warning(f"Price changed for id: {update_id}")

        update_basic = (update_id, update_rows["product_name"], update_rows["uom_name"])
        queries_to_commit.append((queries.update["product_basics"], update_basic))
        # Commit
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(
                f"Update product basic for id: {update_id}. {transaction_result}"
            )

    def update_recipe_records(
        self, update_id, original_rows: list[dict], update_rows: list[dict]
    ):
        og_vals = [i for row in original_rows for i in row.values()]
        new_vals = [i for row in update_rows for i in row.values()]
        # Early return if new recipe info is exactly the same as old
        if og_vals == new_vals:
            LOGGER.warning(f"No recipe update was executed for id: {update_id}")
            return

        og_materials = [vals["material_name"] for vals in original_rows]
        new_materials = [vals["material_name"] for vals in update_rows]
        # Materials existed in old but not new records should be deleted
        stop_using = [i for i in og_materials if i not in new_materials]
        check_quantity = [i for i in og_materials if i in new_materials]
        add_into = [i for i in new_materials if i not in og_materials]

        queries_to_commit = []
        for row in original_rows:
            material_name = row["material_name"]
            quantity = row["quantity"]
            if material_name in stop_using:
                queries_to_commit.append(
                    (
                        queries.update_delete["set_recipes_end"],
                        (update_id, material_name),
                    )
                )
            elif material_name in check_quantity:
                update_match_row = next(
                    i for i in update_rows if i["material_name"] == material_name
                )
                if quantity != update_match_row["quantity"]:
                    queries_to_commit.append(
                        (
                            queries.update_delete["set_recipes_end"],
                            (update_id, material_name),
                        )
                    )
                    recipe = (
                        update_id,
                        update_match_row["material_name"],
                        update_match_row["quantity"],
                    )
                    queries_to_commit.append((queries.update["recipes"], recipe))
        for row in update_rows:
            material_name = row["material_name"]
            quantity = row["quantity"]
            if material_name in add_into:
                recipe = (update_id, material_name, quantity)
                queries_to_commit.append((queries.update["recipes"], recipe))

        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(
                f"Update product recipe for id: {update_id}. {transaction_result}"
            )


# Data access object for order page
class DaoOrderPage(DaoOrderapp):
    def init(self, connection: MySQLConnection | None = None):
        self.connection = (
            connection if connection is not None else super().connect_orderapp()
        )
        super().__init__(connection)

    def fetch_today_orders(self) -> list[dict]:
        try:
            orders_data = self.query_data(queries.TODAY_ORDERS)
            return orders_data
        except Exception as e:
            LOGGER.error(e)

    def fetch_order_date(self, order_id) -> str:
        result = self.query_data(
            "SELECT DATE(o.order_timestamp) AS order_date from orderapp.orders o WHERE o.order_id = %s",
            (order_id,),
        )
        order_date = result[0]["order_date"]
        return order_date

    def insert_order_records(
        self, order_basic: tuple[int, str], detail_data: list[dict]
    ):
        # Insert order record and get its id
        self.query_data(queries.insert["order_basics"], order_basic)
        order_id = self.query_data("SELECT LAST_INSERT_ID() AS order_id")[0]["order_id"]

        # Insert order details
        queries_to_commit = []
        for vals in detail_data:
            o_detail = (order_id, vals["product_name"], vals["quantity"])
            insert_o_detail = (queries.insert["order_details"], o_detail)
            queries_to_commit.append(insert_o_detail)

        # Commit
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(f"Insert order details. {transaction_result}")
        else:
            LOGGER.warning("No insertion was executed")

    def update_order_basic(
        self, update_id, original_basic: tuple[int, str], update_basic: tuple[int, str]
    ):
        # Early return if new order basic info is the same as old
        if original_basic == update_basic:
            LOGGER.warning(f"No order basic update was executed for id: {update_id}")
            return
        update = (update_id, update_basic[0], update_basic[1])
        queries_to_commit = []
        queries_to_commit.append((queries.update["order_basics"], update))
        # Commit
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(f"Update order basic for id: {update_id}. {transaction_result}")

    def update_order_detail(
        self, update_id, original_rows: list[dict], update_rows: list[dict]
    ):
        og_vals = [i for row in original_rows for i in row.values()]
        new_vals = [i for row in update_rows for i in row.values()]
        # Early return if new recipe info is the same as old
        if og_vals == new_vals:
            LOGGER.warning(f"No order detail update was executed for id: {update_id}")
            return

        # Only need to consider product for add/delete, others will be handled by on duplicate
        og_products = [vals["product_name"] for vals in original_rows]
        new_products = [vals["product_name"] for vals in update_rows]
        # Products existed in old but not updated order should be deleted
        need_delete = [i for i in og_products if i not in new_products]
        queries_to_commit = []
        for vals in original_rows:
            if vals["product_name"] in need_delete:
                update_delete = (update_id, vals["product_name"])
                queries_to_commit.append(
                    (queries.update_delete["order_details"], update_delete)
                )
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(
                f"product(s) deleted in product recipe for id: {update_id}. {transaction_result}"
            )
        else:
            LOGGER.warning(
                f"No product was deleted during update from product recipe for id: {update_id}"
            )
        queries_to_commit = []
        for vals in update_rows:
            update = (update_id, vals["product_name"], vals["quantity"])
            insert_products = (queries.update["order_details"], update)
            queries_to_commit.append(insert_products)
        # Commit
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(
                f"Update product order detail for id: {update_id}. {transaction_result}"
            )

    def change_order_status(self, order_id: int, new_status: str):
        try:
            queries_to_commit = [
                (queries.update["order_status"], (new_status, order_id))
            ]
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(f"Update status on order {order_id}. {transaction_result}")
        except Exception as e:
            LOGGER.error(e)

    def change_paid_status(self, order_id: int, is_paid: bool):
        try:
            queries_to_commit = [(queries.update["order_paid"], (is_paid, order_id))]
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(f"Update is_paid on order {order_id}. {transaction_result}")
        except Exception as e:
            LOGGER.error(e)


class DaoPreOrderPage(DaoOrderPage):
    def __init__(self, connection: MySQLConnection | None = None):
        super().__init__(connection)

    @override
    def fetch_today_orders(self) -> list[dict]:
        raise NotImplementedError("Use DaoOrderPage for current day orders")

    def fetch_previous_orders(self) -> list[dict]:
        def count_ids_num(s: str | None) -> int:
            if isinstance(s, str):
                return len(s.split(","))
            return 0

        try:
            previos_orders = self.query_data(queries.PREVIOUS_ORDERS_OVERVIEW)
            if previos_orders:
                for row in previos_orders:
                    finish_count = count_ids_num(row["finished_id_list"])
                    prep_count = count_ids_num(row["prepared_id_list"])
                    cancel_count = count_ids_num(row["cancelled_id_list"])
                    row["order_counts"] = (
                        f"完成{finish_count}/準備{prep_count}/取消{cancel_count}"
                    )
            return previos_orders
        except Exception as e:
            LOGGER.error(e)

    # Fetch order details based on the provided id_list
    def fetch_previous_order_details(self, id_list: list[str]):
        placeholders = ", ".join(["%s"] * len(id_list))
        query = queries.PREVIOUS_ORDER_DETAILS.format(placeholders=placeholders)
        order_details = self.query_data(query, params=tuple(id_list))
        return order_details


class DaoFutureOrderPage(DaoOrderPage):
    def __init__(self, connection: MySQLConnection | None = None):
        super().__init__(connection)

    @override
    def fetch_today_orders(self) -> list[dict]:
        raise NotImplementedError("Use DaoOrderPage for current day orders")

    def fetch_future_orders(self) -> list[dict]:
        try:
            orders_data = self.query_data(queries.FUTURE_ORDERS)
            return orders_data
        except Exception as e:
            LOGGER.error(e)

    @override
    def insert_order_records(
        self,
        future_order_basic: tuple[int, str, datetime, bool],
        detail_data: list[dict],
    ):
        # Insert order record and get its id
        self.query_data(queries.insert["future_order_basics"], future_order_basic)
        order_id = self.query_data("SELECT LAST_INSERT_ID() AS order_id")[0]["order_id"]

        # Insert order details
        queries_to_commit = []
        for vals in detail_data:
            o_detail = (order_id, vals["product_name"], vals["quantity"])
            insert_o_detail = (queries.insert["order_details"], o_detail)
            queries_to_commit.append(insert_o_detail)

        # Commit
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(f"Insert order details. {transaction_result}")
        else:
            LOGGER.warning("No insertion was executed")

    @override
    def update_order_basic(
        self,
        update_id,
        original_basic: tuple[int, str, datetime],
        update_basic: tuple[int, str, datetime],
    ):
        # Early return if new order basic info is the same as old
        if original_basic == update_basic:
            LOGGER.warning(f"No order basic update was executed for id: {update_id}")
            return
        update = (update_id, *update_basic)
        queries_to_commit = []
        queries_to_commit.append((queries.update["future_order_basics"], update))
        # Commit
        if queries_to_commit:
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(f"Update order basic for id: {update_id}. {transaction_result}")

    def match_order_completion(self, order_id: int):
        try:
            queries_to_commit = [
                (queries.update["order_completion_timestamp"], (order_id,))
            ]
            transaction_result = self.perform_transaction(queries_to_commit)
            LOGGER.info(
                f"Update order_timestamp on order {order_id}. {transaction_result}"
            )
        except Exception as e:
            LOGGER.error(e)


class DaoVendorPage(DaoOrderapp):
    def __init__(self, connection: MySQLConnection | None = None):
        super().__init__(connection)

    # Handle empty string here because it is more concise than COALESCE every col
    # Convert set to list because niceGUI jasonify data
    def fetch_vendor_data(self) -> list[dict]:
        vendor_data = self.query_data("SELECT * FROM orderapp.vendors")
        vendor_data = [i for i in vendor_data if i["vendor_name"] != "無資料"]
        for row in vendor_data:
            if isinstance(row["open_days"], set):
                open_days = list(row["open_days"])
                open_days = sorted(open_days, key=lambda day: DAYS_OPTIONS[day])
                row["open_days"] = open_days
        return vendor_data

    def fetch_existed_vendor(self) -> list[str]:
        existed = [
            i["vendor_name"] for i in self.query_data(queries.existed["vendor_name"])
        ]
        return existed if existed else []

    # JOIN open_days value to be inserted as set
    def insert_vendor_records(self, detail_data: dict):
        vendor_name = detail_data["vendor_name"]
        detail_data["open_days"] = ",".join(detail_data["open_days"])
        vendor = [i for i in detail_data.values()]
        transaction_result = self.perform_transaction(
            [(queries.insert["vendors"], vendor)]
        )
        LOGGER.info(f"Insert product records for {vendor_name}. {transaction_result}")

    def update_vendor_records(self, update_id, original_dict: dict, update_dict: dict):
        # Early return if new vendor record stays the same
        if original_dict == update_dict:
            LOGGER.warning(f"No vendor update was executed for id: {update_id}")
            return
        update_dict["open_days"] = ",".join(update_dict["open_days"])
        update = [update_id, *update_dict.values()]
        transaction_result = self.perform_transaction(
            [(queries.update["vendors"], update)]
        )
        LOGGER.info(f"Update vendor records for id: {update_id}. {transaction_result}")
