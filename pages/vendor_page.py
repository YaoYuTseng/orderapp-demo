from copy import deepcopy

from mysql.connector import MySQLConnection
from nicegui import ui

from database.DataAccessObjects import DaoVendorPage

from . import constants, page_setup
from .components.Buttons import DropdownNavigate
from .components.ConfirmDialogs import ConfirmDeleteVendor
from .components.GridOfCards import VendorCards
from .components.InputDialogs import VendorInputDialog
from .components.Notifications import NotifyAwaitInput
from .components.UpdateDialogs import VendorUpdateDialog
from .components.UtilsAggrids import SelectableAggrid


def format_vendor_overview(vendor_data: list[dict]) -> list[dict]:
    formatted = deepcopy(vendor_data)
    for row in formatted:
        for key in row.keys():
            if not row[key]:
                row[key] = "N/A"
            elif key == "office_phone":
                row[key] = VendorCards.format_office_phone(row[key])
    return formatted


def vendor_page(connection: MySQLConnection):
    page_setup.font_setup()
    page_setup.style_setup(
        responsive_ag=True,
        dense_card=True,
        dynamic_scroll_padding=True,
        dense_select=True,
    )
    DAO_VENDORS = DaoVendorPage(connection=connection)

    def reinitialize():
        # Reinitialize input dialogues
        input_dialog.refresh()
        # Reinitialize aggrid and cards
        new_vendor_data = DAO_VENDORS.fetch_vendor_data()
        notify_null.notify_if_null_data(new_vendor_data)

        new_vendor_overview = format_vendor_overview(new_vendor_data)
        vendor_records.refresh(new_vendor_overview)
        vendor_cards.recreate(new_vendor_data)

    # Commit inserting purchase records into database
    def commit_input():
        vendor_details = input_dialog.get_grid_values()[0]
        DAO_VENDORS.insert_vendor_records(vendor_details)
        reinitialize()

    # Commit updating purchase details
    def commit_update(vendor_id: int):
        # Purchase basic (_) is diabled, no need to update
        update_detail = update_dialog.get_grid_values()[0]
        DAO_VENDORS.update_vendor_records(
            vendor_id, update_dialog.original_detail, update_detail
        )
        reinitialize()

    def commit_delete(vendor_id: int):
        DAO_VENDORS.commit_delete(vendor_id, "vendors")
        reinitialize()

    # Fetch SQL data
    vendor_data = DAO_VENDORS.fetch_vendor_data()
    existed_vendors = DAO_VENDORS.fetch_existed_vendor()

    # Notification for null data
    # Check for overview data intitally and on reinitialize
    notify_null = NotifyAwaitInput("請點擊「新增廠商資料」輸入首筆資料")
    notify_null.notify_if_null_data(vendor_data)

    # Dialog for inputting new purchase records to be inserted
    input_dialog = VendorInputDialog(
        constants.VENDORS_TEMPLATE, existed_vendors, commit_input
    )
    update_dialog = VendorUpdateDialog(
        constants.VENDORS_TEMPLATE, existed_vendors, commit_update
    )

    # Dialog for deleting purchase records
    confirm_delete = ConfirmDeleteVendor(
        "刪除資料無法復原，請確認是否刪除", DAO_VENDORS
    )
    confirm_delete.on_confirm = commit_delete
    with ui.column().classes("w-full max-w-7xl h-full"):
        with ui.row().classes("w-full justify-between"):
            DropdownNavigate(constants.PAGES["/vendors"], constants.PAGES)
            # Navigate to purchase page
            to_purchases = ui.button(text="採購紀錄", icon="first_page")
            to_purchases.classes("text-base md:text-lg").props("flat padding='none'")
            to_purchases.on_click(lambda: ui.navigate.to("/purchases"))

        # Buttons for open input dialogue, unselect, and show_delete
        with ui.row().classes("w-full gap-1 !divide-y-2"):
            ui.button("新增廠商資料", on_click=input_dialog.open)
            with ui.button(icon="deselect") as unselect:
                ui.tooltip("取消所有選取")
            with ui.button(icon="edit_note").classes("ml-auto") as show_modify:
                ui.tooltip("顯示刪除/修改按鈕")

        # Display vendor_records overview
        vendor_overview = format_vendor_overview(vendor_data)
        vendor_records = SelectableAggrid(constants.VENDORS_OVERVIEW, vendor_overview)

        # Display selected vendor details
        vendor_cards = VendorCards(
            constants.VENDORS_TEMPLATE,
            vendor_data,
            "vendor",
            update_dialog.start_update,
            confirm_delete.start,
        )
        vendor_cards.select(all=False)

        # Deferred binding
        unselect.on_click(vendor_records.uncheck_all)
        show_modify.on_click(vendor_cards.show_modify)
        vendor_records.select_cards = vendor_cards.select
