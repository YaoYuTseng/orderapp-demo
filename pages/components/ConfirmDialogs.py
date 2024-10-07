from typing import Callable, override

from nicegui import ui

from database.DataAccessObjects import DaoOrderapp


# Base class for confirming SQL action
class ConfirmDialog(ui.dialog):
    def __init__(
        self,
        confirm_msg: str,
        target_id: int | None = None,
        on_confirm: Callable[[int], None] = None,
    ) -> None:
        super().__init__()
        self._confirm_msg_display: ui.label | None = None
        self.confirm_msg = confirm_msg
        self.target_id = target_id
        self.on_confirm = on_confirm
        self._create()

    def _create(self):
        with self, ui.card():
            self._confirm_msg_display = ui.label(self.confirm_msg)
            self._confirm_msg_display.classes("whitespace-pre-wrap")
            with ui.row().classes("w-full items-center justify-between"):
                ui.button("取消").on_click(self.close).props("outline").classes(
                    "!text-black font-semibold"
                )
                self._create_confirm_button()

    def _create_confirm_button(self):
        confirm_button = ui.button("確定")
        confirm_button.props("outline").classes("!text-red-500 font-semibold")
        confirm_button.on_click(lambda: self.on_confirm(self.target_id))
        confirm_button.on_click(self.close)

    def start(self, target_id):
        self.target_id = target_id
        self.open()


# Adding existence check for recipe delete confirmation because of references to order tables
class ConfirmDeleteRecipe(ConfirmDialog):
    def __init__(
        self,
        confirm_msg: str,
        dao: DaoOrderapp,
        target_id: int | None = None,
        on_confirm: Callable[[int], None] = None,
    ) -> None:
        super().__init__(confirm_msg, target_id, on_confirm)
        self.dao = dao

    @override
    def start(self, target_id):
        self.target_id = target_id
        existed = self.dao.check_existence("order_details", "product_id", target_id)
        if existed:
            ui.notify("此產品已在訂單中被使用，無法刪除")
        else:
            self.open()


class ConfirmDeleteVendor(ConfirmDialog):
    def __init__(
        self,
        confirm_msg: str,
        dao: DaoOrderapp,
        target_id: int | None = None,
        on_confirm: Callable[[int], None] = None,
    ) -> None:
        super().__init__(confirm_msg, target_id, on_confirm)
        self.dao = dao

    @override
    def start(self, target_id):
        self.target_id = target_id
        existed = self.dao.check_existence("purchases", "vendor_id", target_id)
        if existed:
            ui.notify("此廠商具有相關採購紀錄，無法刪除")
        else:
            self.open()
