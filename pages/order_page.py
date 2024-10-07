from mysql.connector import MySQLConnection
from nicegui import ui

from database import queries
from database.DataAccessObjects import DaoOrderPage

from . import constants, page_setup
from .components.Buttons import DropdownNavigate, VisibilityMenu
from .components.ConfirmDialogs import ConfirmDialog
from .components.GridOfCards import OrderCards
from .components.InputDialogs import OrderInputDialog
from .components.UpdateDialogs import OrderUpdateDialog


def order_page(connection: MySQLConnection):
    page_setup.font_setup()
    page_setup.style_setup(dense_card=True, dynamic_scroll_padding=True)

    def reinitialize():
        # Reinitialize input dialogues
        input_dialog.refresh()
        # Reinitialize order cards
        new_orders = DAO_ORDER.fetch_today_orders()
        order_cards.recreate(new_orders)

    def commit_input():
        order_details = input_dialog.get_grid_values()
        o_basic = (input_dialog.get_summed_price(), input_dialog.get_note_value())
        DAO_ORDER.insert_order_records(o_basic, order_details)
        reinitialize()

    def commit_update(order_id: int):
        order_details = update_dialog.get_grid_values()
        old_o_basic = update_dialog.original_basic
        new_o_basic = (update_dialog.get_summed_price(), update_dialog.get_note_value())
        DAO_ORDER.update_order_basic(order_id, old_o_basic, new_o_basic)
        DAO_ORDER.update_order_detail(
            order_id, update_dialog.original_detail, order_details
        )
        reinitialize()

    # Order_details are to be deleted first, because the foreign key order_id in
    # orders table is referencing the order_details table
    def commit_delete(order_id: int):
        DAO_ORDER.commit_delete(order_id, "order_details")
        DAO_ORDER.commit_delete(order_id, "orders")
        reinitialize()

    def handle_status_change(order_id: int, new_status: str):
        DAO_ORDER.change_order_status(order_id, new_status)
        reinitialize()

    # Fetch SQL data for today's order and construct input/display schema
    DAO_ORDER = DaoOrderPage(connection=connection)
    orders_data = DAO_ORDER.fetch_today_orders()
    input_template = [
        s
        for s in DAO_ORDER.get_value_options(
            constants.ORDERS_TEMPLATE, ["product_name"]
        )
        if s.field in ["product_name", "quantity", "price_total"]
    ]
    product_price_pairs = DAO_ORDER.query_data(queries.PRODUCT_PRICE)

    # Order input dialogs
    input_dialog = OrderInputDialog(input_template, product_price_pairs, commit_input)
    update_dialog = OrderUpdateDialog(
        input_template, product_price_pairs, commit_update
    )

    # Dialog for deleting order records
    confirm_delete = ConfirmDialog("刪除資料無法復原，請確認是否刪除")
    confirm_delete.on_confirm = commit_delete
    with ui.column().classes("w-full max-w-7xl h-full"):
        with ui.row().classes("w-full justify-between"):
            # Dropdown for page navigation
            DropdownNavigate(constants.PAGES["/orders"], constants.PAGES)
            # Navigate to vendors page
            to_future_orders = ui.button(text="預約訂單")
            to_future_orders.classes("ml-auto text-base md:text-lg").props(
                "flat icon-right='last_page' padding='none'"
            )
            to_future_orders.on_click(lambda: ui.navigate.to("/future_orders"))

        with ui.row().classes("w-full gap-1 !divide-y-2"):
            ui.button("新增訂單", on_click=input_dialog.open)
            with ui.button(icon="filter_list"):
                ui.tooltip("顯示/隱藏訂單")
                filter = VisibilityMenu(["準備中", "已完成", "已取消"])
            with ui.button(icon="edit_note").classes("ml-auto") as show_modify:
                ui.tooltip("顯示刪除/修改按鈕")

        order_cards = OrderCards(
            constants.ORDERS_TEMPLATE,
            orders_data,
            "order",
            update_dialog.start_update,
            confirm_delete.start,
            handle_status_change,
        )

        # Deferred binding filter.on_change
        filter.on_change = order_cards.update_status_visibility
        show_modify.on_click(order_cards.show_modify)

        # Order_page default to hide order_cards on complete
        filter.manual_switch("已完成", False)
