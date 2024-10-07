from datetime import datetime
from pathlib import Path

from fastapi.responses import RedirectResponse
from mysql.connector import MySQLConnection
from nicegui import app, ui

from auth.login import EXPIRATION_FORMAT, SESSION_LENGTH, verify_password
from database.DataAccessObjects import DaoOrderapp

from . import page_setup


def login_page(connection: MySQLConnection) -> RedirectResponse | None:
    page_setup.font_setup()
    page_setup.style_setup()

    ui.query(".nicegui-content").classes("p-0")
    ui.image(Path("pages", "static", "images", "logo_removeb.png")).classes(
        "max-h-screen max-w-screen-lg absolute-center"
    )
    DAO = DaoOrderapp(connection)

    # local function to avoid passing username and password as arguments
    def try_login() -> None:
        if not user_name.value or not password.value:
            ui.notify("請輸入帳號密碼")
        elif user_name.value not in users.keys():
            ui.notify("無此帳號", color="negative")
        elif verify_password((password.value), users.get(user_name.value)):
            # Upon successful login set a session expiration date
            expiration = datetime.now() + SESSION_LENGTH
            expiration = expiration.strftime(EXPIRATION_FORMAT)
            status = {
                "username": user_name.value,
                "authenticated": True,
                "expiration": expiration,
            }
            app.storage.user.update(status)
            # go back to where the user wanted to go
            ui.navigate.to(app.storage.user.get("referrer_path", "/dashboard"))
        else:
            ui.notify("密碼錯誤", color="negative")

    # Fetch user info
    users = {
        row["user_name"]: row["hashed_password"]
        for row in DAO.query_data(
            "SELECT user_name, hashed_password FROM orderapp.users"
        )
    }

    with ui.card().classes("w-2/3 lg:1/2 absolute-center").style(
        "background-color: rgba(255, 255, 255, 0.98)"
    ):
        user_name = ui.input("帳號").classes("w-full")
        password = ui.input("密碼", password=True, password_toggle_button=True).classes(
            "w-full"
        )
        user_name.on("keydown.enter", try_login)
        password.on("keydown.enter", try_login)
        ui.button("登入", on_click=try_login).classes("text-base md:!text-lg ml-auto")
    return None
