from mysql.connector import MySQLConnection
from nicegui import ui

from database import queries
from database.DataAccessObjects import DaoPreOrderPage
from database.update_cost import store_update_startdate

from . import constants, page_setup
from .components.Buttons import DropdownNavigate, VisibilityMenu
from .components.ConfirmDialogs import ConfirmDialog
from .components.GridOfCards import PreviousOrderCards
from .components.Notifications import NotifyAwaitInput
from .components.UpdateDialogs import OrderUpdateDialog
from .components.UtilsAggrids import PreviousOrderGrid


def previous_order_page(connection: MySQLConnection):
    page_setup.font_setup()
    page_setup.style_setup(
        responsive_ag=True, dense_card=True, dynamic_scroll_padding=True
    )

    def reinitialize(deleted_id: int | None = None):
        new_previous_overview = DAO_PREORDER.fetch_previous_orders()
        previous_order_grid.refresh(new_previous_overview)
        notify_null.notify_if_null_data(new_previous_overview)
        # Although refresh order_grid is unchecked all, still render the remained cards from delete as QoL
        if deleted_id:
            previous_order_grid.recreate_selected(str(deleted_id))
        else:
            previous_order_grid.recreate_selected()

    def commit_update(order_id: int):
        order_details = update_dialog.get_grid_values()
        old_o_basic = update_dialog.original_basic
        new_o_basic = (update_dialog.get_summed_price(), update_dialog.get_note_value())
        DAO_PREORDER.update_order_basic(order_id, old_o_basic, new_o_basic)
        DAO_PREORDER.update_order_detail(
            order_id, update_dialog.original_detail, order_details
        )
        reinitialize()

    # Order_details are to be deleted first, because the foreign key order_id in
    # orders table is referencing the order_details table
    def commit_delete(order_id):
        update_date = DAO_PREORDER.fetch_order_date(order_id)
        store_update_startdate(update_date)

        DAO_PREORDER.commit_delete(order_id, "order_details")
        DAO_PREORDER.commit_delete(order_id, "orders")
        reinitialize(deleted_id=order_id)

    def handle_status_change(order_id: int, new_status: str):
        update_date = DAO_PREORDER.fetch_order_date(order_id)
        store_update_startdate(update_date)

        DAO_PREORDER.change_order_status(order_id, new_status)
        reinitialize()

    def handle_paid_change(order_id: int, is_paid: bool):
        DAO_PREORDER.change_paid_status(order_id, is_paid)
        reinitialize()

    # Fetch SQL data
    DAO_PREORDER = DaoPreOrderPage(connection=connection)
    previous_orders_overview = DAO_PREORDER.fetch_previous_orders()
    input_template = [
        s
        for s in DAO_PREORDER.get_value_options(
            constants.ORDERS_TEMPLATE, ["product_name"]
        )
        if s.field in ["product_name", "quantity", "price_total"]
    ]
    product_price_pairs = DAO_PREORDER.query_data(queries.PRODUCT_PRICE)

    update_dialog = OrderUpdateDialog(
        input_template, product_price_pairs, commit_update
    )

    # Notification for null data
    # Check for overview data intitally and on delete
    notify_null = NotifyAwaitInput("無過往訂單紀錄，請待未來訂單完成")
    notify_null.notify_if_null_data(previous_orders_overview)

    # Dialog for deleting
    confirm_delete = ConfirmDialog("刪除資料無法復原，請確認是否刪除")
    confirm_delete.on_confirm = commit_delete
    with ui.column().classes("w-full max-w-7xl h-full"):
        DropdownNavigate(constants.PAGES["/previous_orders"], constants.PAGES)
        with ui.row().classes("w-full gap-1"):
            with ui.button(icon="deselect") as unselect:
                ui.tooltip("取消所有選取")
            with ui.button(icon="filter_list"):
                ui.tooltip("顯示/隱藏訂單")
                filter = VisibilityMenu(["準備中", "已完成", "已取消"])
            with ui.button(icon="settings").classes("ml-auto") as show_footer:
                ui.tooltip("顯示訂單狀態列")
            with ui.button(icon="edit_note") as show_modify:
                ui.tooltip("顯示刪除/修改按鈕")

        previous_order_grid = PreviousOrderGrid(
            constants.PREVIOUS_ORDERS_OVERVIEW, previous_orders_overview
        )

        previous_order_cards = PreviousOrderCards(
            constants.PREVIOUS_ORDERS_DETAIL,
            None,
            "order",
            update_dialog.start_update,
            confirm_delete.start,
            handle_status_change,
            handle_paid_change,
        )

        # Deferred bindings
        filter.on_change = previous_order_cards.update_status_visibility
        unselect.on_click(previous_order_grid.uncheck_all)
        show_footer.on_click(previous_order_cards.show_footer)
        show_modify.on_click(previous_order_cards.show_modify)
        previous_order_grid.get_selected_details = (
            DAO_PREORDER.fetch_previous_order_details
        )
        previous_order_grid.create_select_cards = previous_order_cards.create_on_select
