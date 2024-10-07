from datetime import date
from pathlib import Path

import schedule
from nicegui import app, ui

from api import ping
from auth.login import AuthMiddleware
from database.DataAccessObjects import DaoOrderapp
from database.update_cost import update_costs
from pages.dashboard_page import dashboard_page
from pages.future_order_page import future_order_page
from pages.login_page import login_page
from pages.material_page import material_page
from pages.order_page import order_page
from pages.previous_order_page import previous_order_page
from pages.purchase_page import purchase_page
from pages.recipe_page import recipe_page
from pages.vendor_page import vendor_page

DAO = DaoOrderapp()
DAO.connect_orderapp()

COST_UPDATE_TIME = "08:00:00"
ICON = Path("pages", "static", "images", "logo_removeb.ico")

app.add_static_files("/fonts", "pages/static/fonts")
app.on_shutdown(DAO.close_connection)
app.add_middleware(AuthMiddleware)

# Schedule cost update at every day 8:00 AM
# Check every second but according to https://github.com/zauberzeug/nicegui/discussions/3197 shouldn't impact performance
schedule.every().day.at(COST_UPDATE_TIME, "Asia/Taipei").do(
    lambda: update_costs(
        DAO, app.storage.general.get("update_start_date", date.today())
    )
)

ui.timer(1, schedule.run_pending)

# Responsive design for general elements (specific ones would require customzation)
ui.button.default_classes("md:text-base")
ui.card.default_classes("md:text-base")
ui.tooltip.default_classes("md:text-base")
ui.switch.default_classes("md:text-base")
ui.input.default_classes("md:text-lg")
ui.select.default_classes("md:text-lg")
ui.number.default_classes("md:text-lg")


# Page functions
@ui.page("/dashboard")
def dashboard():
    DAO.connect_orderapp()
    dashboard_page()


@ui.page("/login")
def login():
    DAO.connect_orderapp()
    login_page(DAO.connection)


@ui.page("/future_orders")
def future_orders():
    DAO.connect_orderapp()
    future_order_page(DAO.connection)


@ui.page("/orders")
def orders():
    DAO.connect_orderapp()
    order_page(DAO.connection)


@ui.page("/previous_orders")
def previous_order():
    DAO.connect_orderapp()
    previous_order_page(DAO.connection)


@ui.page("/recipes")
def recipes():
    DAO.connect_orderapp()
    recipe_page(DAO.connection)


@ui.page("/materials")
def materials():
    DAO.connect_orderapp()
    material_page(DAO.connection)


@ui.page("/purchases")
def purchases():
    DAO.connect_orderapp()
    purchase_page(DAO.connection)


@ui.page("/vendors")
def vendors():
    DAO.connect_orderapp()
    vendor_page(DAO.connection)


dashboard()

# ui.run(window_size=(390, 844), language="zh-TW", storage_secret="persistent")
ui.run(title="幸福掌心", favicon=ICON, language="zh-TW", storage_secret="persistent")
