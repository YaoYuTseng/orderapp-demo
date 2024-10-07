from mysql.connector import MySQLConnection
from nicegui import ui

from database import queries
from database.DataAccessObjects import DaoOrderapp

from . import constants, page_setup
from .components.Buttons import DropdownNavigate
from .components.Notifications import NotifyAwaitInput
from .components.UtilsAggrids import RefreshableAggrid


def material_page(connection: MySQLConnection):
    page_setup.font_setup()
    page_setup.style_setup(responsive_ag=True)

    # Fetch SQL data
    DAO_MATERIAL = DaoOrderapp(connection=connection)
    materials_data = DAO_MATERIAL.query_data(queries.MATERIALS)

    # Notification for null data
    # Check for overview data intitally and on reinitialize
    notify_null = NotifyAwaitInput("無原料紀錄，請至採購頁面新增資料")
    notify_null.notify_if_null_data(materials_data)

    # ui.query(".nicegui-content").classes("h-screen")
    with ui.column().classes("w-full max-w-7xl h-full"):
        with ui.row().classes("w-full justify-between"):
            DropdownNavigate(constants.PAGES["/materials"], constants.PAGES)
            # Navigate to purchase page
            to_recipes = ui.button(text="產品設定", icon="first_page")
            to_recipes.classes("text-base md:text-lg").props("flat padding='none'")
            to_recipes.on_click(lambda: ui.navigate.to("/recipes"))

        RefreshableAggrid(constants.MATERIALS_TEMPLATE, materials_data)
