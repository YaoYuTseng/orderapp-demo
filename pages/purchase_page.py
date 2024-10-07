from mysql.connector import MySQLConnection
from nicegui import ui

from database.DataAccessObjects import DaoPurchasePage
from database.update_cost import store_update_startdate, update_costs

from . import constants, page_setup
from .components.Buttons import DropdownNavigate
from .components.ConfirmDialogs import ConfirmDialog
from .components.GridOfCards import PurchaseCards
from .components.InputDialogs import PurchaseInputDialog
from .components.Notifications import NotifyAwaitInput
from .components.UpdateDialogs import PurchaseUpdateDialog
from .components.UtilsAggrids import SelectableAggrid


def purchase_page(connection: MySQLConnection):
    page_setup.font_setup()
    page_setup.style_setup(
        responsive_ag=True, dense_card=True, dynamic_scroll_padding=True
    )
    DAO_PURCHASE = DaoPurchasePage(connection=connection)

    def reinitialize():
        # Reinitialize input dialogues
        input_dialog.refresh()
        # Reinitialize aggrid and cards
        new_overview_data, new_details_data = DAO_PURCHASE.fetch_purchase_data()
        notify_null.notify_if_null_data(new_overview_data)
        purchase_records.refresh(new_overview_data)
        purchase_cards.recreate(new_details_data)

    # Commit inserting purchase records into database
    def commit_input():
        purchase_basic, purchase_details = input_dialog.get_grid_values()
        store_update_startdate(purchase_basic[0]["purchase_date"])

        input_vendors = [i["vendor_name"] for i in purchase_basic]
        input_materials = [i["material_name"] for i in purchase_details]
        DAO_PURCHASE.insert_new_names("vendor_name", input_vendors)
        DAO_PURCHASE.insert_new_names("material_name", input_materials)
        p_bascic = (
            purchase_basic[0]["purchase_date"],
            purchase_basic[0]["vendor_name"],
        )
        DAO_PURCHASE.insert_purchase_records(p_bascic, purchase_details)
        update_costs(DAO_PURCHASE)
        reinitialize()

    # Commit updating purchase details
    def commit_update(purchase_id: int):
        # Purchase basic (_) is diabled, no need to update
        _, update_detail = update_dialog.get_grid_values()
        update_materials = [i["material_name"] for i in update_detail]
        DAO_PURCHASE.insert_new_names("material_name", update_materials)
        DAO_PURCHASE.update_purchase_records(
            purchase_id, update_dialog.original_detail, update_detail
        )
        update_costs(DAO_PURCHASE)
        reinitialize()

    # Purchase_details are to be deleted first, because the foreign key order_id in
    # orders table is referencing the order_details table
    def commit_delete(purchase_id: int):
        update_date = DAO_PURCHASE.fetch_purchase_date(purchase_id)
        store_update_startdate(update_date)

        material_ids = DAO_PURCHASE.query_data(
            "SELECT material_id from orderapp.purchase_details WHERE purchase_id = %s",
            (purchase_id,),
        )
        material_ids = [i["material_id"] for i in material_ids]

        DAO_PURCHASE.commit_delete(purchase_id, "purchase_details")
        DAO_PURCHASE.commit_delete(purchase_id, "purchases")

        # Will check for existence and clean up none-referecing uom_id AFTER product deletions
        DAO_PURCHASE.clean_up_materials(material_ids)
        update_costs(DAO_PURCHASE)
        reinitialize()

    # Fetch SQL data and construct input/display schema
    purchases_overview, purchase_details_data = DAO_PURCHASE.fetch_purchase_data()
    purchase_basic = [
        s
        for s in DAO_PURCHASE.get_value_options(
            constants.PURCHASES_OVERVIEW_TEMPLATE, ["vendor_name"]
        )
        if s.field in ["purchase_date", "vendor_name"]
    ]
    purchase_details = [
        s
        for s in DAO_PURCHASE.get_value_options(
            constants.PURCHASE_DETAILS_TEMPLATE, ["material_name"]
        )
    ]
    # Notification for null data
    # Check for overview data intitally and on reinitialize
    notify_null = NotifyAwaitInput("請點擊「新增採購資料」輸入首筆資料")
    notify_null.notify_if_null_data(purchases_overview)

    # Dialog for inputting new purchase records to be inserted
    input_dialog = PurchaseInputDialog(purchase_basic, purchase_details, commit_input)
    update_dialog = PurchaseUpdateDialog(
        purchase_basic, purchase_details, commit_update
    )

    # Dialog for deleting purchase records
    confirm_delete = ConfirmDialog("刪除資料無法復原，請確認是否刪除")
    confirm_delete.on_confirm = commit_delete
    with ui.column().classes("w-full max-w-7xl h-full"):
        with ui.row().classes("w-full "):
            # Dropdown for page navigation
            DropdownNavigate(constants.PAGES["/purchases"], constants.PAGES)
            # Navigate to vendors page
            to_vendors = ui.button(text="廠商資料")
            to_vendors.classes("ml-auto text-base md:text-lg").props(
                "flat icon-right='last_page' padding='none'"
            )
            to_vendors.on_click(lambda: ui.navigate.to("/vendors"))

        # Buttons for open input dialogue, unselect, and show_delete
        with ui.row().classes("w-full gap-1 !divide-y-2"):
            ui.button("新增採購資料", on_click=input_dialog.open)
            with ui.button(icon="deselect") as unselect:
                ui.tooltip("取消所有選取")
            with ui.button(icon="edit_note").classes("ml-auto") as show_modify:
                ui.tooltip("顯示刪除/修改按鈕")

        # Display purchase records overview
        purchase_records = SelectableAggrid(
            constants.PURCHASES_OVERVIEW_TEMPLATE, purchases_overview
        )

        # Display selected (if not selected = all) purchase details
        purchase_cards = PurchaseCards(
            constants.PURCHASE_DETAILS_TEMPLATE,
            purchase_details_data,
            "purchase",
            update_dialog.start_update,
            confirm_delete.start,
        )
        purchase_cards.select(all=False)

        # Deferred binding
        unselect.on_click(purchase_records.uncheck_all)
        show_modify.on_click(purchase_cards.show_modify)
        purchase_records.select_cards = purchase_cards.select
