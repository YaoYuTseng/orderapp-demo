from mysql.connector import MySQLConnection
from nicegui import ui

from database import queries
from database.DataAccessObjects import DaoFutureOrderPage

from . import constants, page_setup
from .components.Buttons import DropdownNavigate, VisibilityMenu
from .components.ConfirmDialogs import ConfirmDialog
from .components.GridOfCards import FutureOrderCards
from .components.InputDialogs import FutureOrderInputDialog
from .components.UpdateDialogs import FutureOrderUpdateDialog


def future_order_page(connection: MySQLConnection):
    page_setup.font_setup()
    page_setup.style_setup(dense_card=True, dynamic_scroll_padding=True)

    def reinitialize():
        # Reinitialize input dialogues
        input_dialog.refresh()
        # Reinitialize order cards
        new_orders = DAO_FUTURE_ORDER.fetch_future_orders()
        future_order_cards.recreate(new_orders)

    def commit_input():
        order_details = input_dialog.get_grid_values()
        o_basic = (
            input_dialog.get_summed_price(),
            input_dialog.get_note_value(),
            input_dialog.get_completion_datetime(),
            False,
        )
        DAO_FUTURE_ORDER.insert_order_records(o_basic, order_details)
        reinitialize()

    def commit_update(order_id: int):
        order_details = update_dialog.get_grid_values()
        old_o_basic = update_dialog.original_basic
        new_o_basic = (
            update_dialog.get_summed_price(),
            update_dialog.get_note_value(),
            update_dialog.get_completion_datetime(),
        )
        DAO_FUTURE_ORDER.update_order_basic(order_id, old_o_basic, new_o_basic)
        DAO_FUTURE_ORDER.update_order_detail(
            order_id, update_dialog.original_detail, order_details
        )
        reinitialize()

    # Order_details are to be deleted first, because the foreign key order_id in
    # orders table is referencing the order_details table
    def commit_delete(order_id: int):
        DAO_FUTURE_ORDER.commit_delete(order_id, "order_details")
        DAO_FUTURE_ORDER.commit_delete(order_id, "orders")
        reinitialize()

    def handle_status_change(order_id: int, new_status: str):
        DAO_FUTURE_ORDER.change_order_status(order_id, new_status)
        DAO_FUTURE_ORDER.match_order_completion(order_id)
        reinitialize()

    def handle_paid_change(order_id: int, is_paid: bool):
        DAO_FUTURE_ORDER.change_paid_status(order_id, is_paid)
        reinitialize()

    # Fetch SQL data for today's order and construct input/display schema
    DAO_FUTURE_ORDER = DaoFutureOrderPage(connection=connection)
    orders_data = DAO_FUTURE_ORDER.fetch_future_orders()
    input_template = [
        s
        for s in DAO_FUTURE_ORDER.get_value_options(
            constants.ORDERS_TEMPLATE, ["product_name"]
        )
        if s.field in ["product_name", "quantity", "price_total"]
    ]
    product_price_pairs = DAO_FUTURE_ORDER.query_data(queries.PRODUCT_PRICE)

    # Order input dialogs
    input_dialog = FutureOrderInputDialog(
        input_template, product_price_pairs, commit_input
    )
    update_dialog = FutureOrderUpdateDialog(
        input_template, product_price_pairs, commit_update
    )

    # Dialog for deleting order records
    confirm_delete = ConfirmDialog("刪除資料無法復原，請確認是否刪除")
    confirm_delete.on_confirm = commit_delete
    with ui.column().classes("w-full max-w-7xl h-full"):
        with ui.row().classes("w-full justify-between"):
            DropdownNavigate(constants.PAGES["/future_orders"], constants.PAGES)
            # Navigate to order page
            to_orders = ui.button(text="當日訂單", icon="first_page")
            to_orders.classes("text-base md:text-lg").props("flat padding='none'")
            to_orders.on_click(lambda: ui.navigate.to("/orders"))

        with ui.row().classes("w-full gap-1 !divide-y-2"):
            ui.button("新增訂單", on_click=input_dialog.open)
            with ui.button(icon="filter_list"):
                ui.tooltip("顯示/隱藏訂單")
                filter = VisibilityMenu(["準備中", "已完成", "已取消"])
            with ui.button(icon="edit_note").classes("ml-auto") as show_modify:
                ui.tooltip("顯示刪除/修改按鈕")

        future_order_cards = FutureOrderCards(
            constants.ORDERS_TEMPLATE,
            orders_data,
            "order",
            update_dialog.start_update,
            confirm_delete.start,
            handle_status_change,
            handle_paid_change,
        )

        # Deferred binding filter.on_change
        filter.on_change = future_order_cards.update_status_visibility
        show_modify.on_click(future_order_cards.show_modify)
