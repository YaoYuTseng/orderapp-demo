from pathlib import Path

from nicegui import ui

from . import constants, page_setup


def dashboard_page():
    page_setup.font_setup()
    page_setup.style_setup()

    # Note: query auto-generated div nicegui-content to remove its default padding
    # otherwise the image can not span the whole screen
    ui.query(".nicegui-content").classes("p-0").style("background-color:#F9F3EC")
    ui.image(Path("pages", "static", "images", "logo_removeb.png")).classes(
        "max-h-screen max-w-screen-lg absolute-center"
    )
    dash_pages = {
        key: val
        for key, val in constants.PAGES.items()
        if key not in ("/materials", "/vendors")
    }

    with ui.column().classes(
        "items-center justify-center h-screen w-screen bg-transparent"
    ):
        # Button background have a slight transparency; customed rgb corresponding to primary color for rgba
        # Remeber to change the rgb if primary color change
        for key, val in dash_pages.items():
            ui.button(val, on_click=lambda x=key: ui.navigate.to(x)).classes(
                "p-1 my-1 w-1/2 xl:w-1/3 !outline !outline-2 min-h-fit self-center !text-2xl md:!text-3xl text-black font-semibold hover:!text-white hover:!outline-black hover:font-extrabold"
            ).props("rounded").style(
                "background-color: rgba(166, 123, 91, 0.95) !important"
            )
