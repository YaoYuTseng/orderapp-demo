from datetime import date, datetime
from typing import Callable, override

from nicegui import ui

from database.FieldSchema import FieldSchema
from logging_setup.setup import LOGGER

from .InputGrids import InputGrid, ProductInputGrid, OrderInputGrid, VendorInputGrid

"""
Classes utilizing InputGrid ui.dialog to handle user input.
Include additional input validation.
On confirm (via submitting) call for pages to execute MySQL insertions.

BaseInputDialog
├── GenericInputDialog
│   ├── PurchaseInputDialog
│   └── RecipeInputDialog
├── OrderInputDialog
└── VendorInputDialog
"""


class BaseInputDialog(ui.dialog):
    def __init__(
        self,
        detail_grid_config: list[FieldSchema],
        on_confirm: Callable[[None], None] = None,
    ) -> None:
        super().__init__()
        self.detail_grid_config = detail_grid_config
        self.on_confirm = on_confirm
        self._detail_grid: InputGrid | None = None
        self._create()

    def _create(self):
        with self, ui.card().classes("h-2/3 lg:w-3/4"):
            with ui.column().classes("w-full h-full justify-between"):
                self._create_input_grid()
                self._create_footer()

    def _create_input_grid(self):
        with ui.column().classes("w-full"):
            self._detail_grid = InputGrid(self.detail_grid_config)

    def _create_footer(self):
        with ui.column().classes("w-full"):
            ui.separator().classes()
            with ui.row().classes("!w-full justify-between"):
                if self._detail_grid:
                    ui.button(icon="remove", on_click=self._detail_grid.delete_row)
                    ui.button(icon="add", on_click=self._detail_grid.add_row)
                confirm_button = ui.button("送出", icon="check").classes(
                    "rounded-md ml-auto"
                )
                confirm_button.on_click(self._submit_input)

    @staticmethod
    def _validate_fields_not_null(values: list) -> bool:
        if any([v is None for v in values]):
            LOGGER.warning(f"One of the input value is null: {values}")
            ui.notify("資料填寫不全")
            return False
        return True

    @staticmethod
    def _validate_quantity_positive(quantity_vals: str) -> bool:
        if any([v == 0 for v in quantity_vals]):
            LOGGER.warning(f"One of the input value is zero")
            ui.notify("請注意，數量不應為零")
            return False
        return True

    def _submit_input(self):
        detail = self.get_grid_values()
        detail_vals = [v for row in detail for v in row.values()]
        quantity = [v for row in detail for key, v in row.items() if key == "quantity"]
        if self._validate_fields_not_null(
            detail_vals
        ) and self._validate_quantity_positive(quantity):
            self.on_confirm()
            self.close()
        else:
            pass

    def get_grid_values(self):
        return self._detail_grid.get_input_value()

    def refresh(self):
        self._detail_grid.reinitialize_grid()


# Base class for inputting and validating inserting data
class GenericInputDialog(BaseInputDialog):
    def __init__(
        self,
        basic_grid_config: list[FieldSchema],
        detail_grid_config: list[FieldSchema],
        on_confirm: Callable[[None], None] = None,
    ) -> None:
        self.basic_grid_config = basic_grid_config
        self._basic_grid: InputGrid | None = None
        self._submit_summary: ui.label | None = None
        self._submit_dialog = ui.dialog()
        super().__init__(detail_grid_config=detail_grid_config, on_confirm=on_confirm)

    @override
    def _create(self):
        super()._create()
        self._create_submit_dialog()

    @override
    def _create_input_grid(self):
        with ui.column().classes("w-full"):
            self._basic_grid = InputGrid(self.basic_grid_config)
            ui.separator()
            self._detail_grid = InputGrid(self.detail_grid_config)

    def _create_submit_dialog(self):
        with self._submit_dialog, ui.card():
            self._submit_summary = ui.label().classes("whitespace-pre-wrap")
            with ui.row().classes("w-full items-center justify-between"):
                keep_adding = ui.button("送出並繼續新增", on_click=self.on_confirm)
                finish = ui.button("送出並結束", on_click=self.on_confirm)
                keep_adding.classes("text-black font-semibold").props("outline")
                keep_adding.on_click(self.refresh)
                keep_adding.on_click(self._submit_dialog.close)
                finish.classes("text-black font-semibold").props("outline")
                finish.on_click(self.refresh)
                finish.on_click(self._submit_dialog.close)
                finish.on_click(self.close)

    @override
    def _submit_input(self):
        raise NotImplementedError(
            "GenericInputDialog served as a parent for purchase and recipe input uses only"
        )

    @override
    def get_grid_values(self):
        return self._basic_grid.get_input_value(), self._detail_grid.get_input_value()

    @override
    def refresh(self):
        self._basic_grid.reinitialize_grid()
        self._detail_grid.reinitialize_grid()


# Class for inputting and validating purchase data
class PurchaseInputDialog(GenericInputDialog):
    def __init__(
        self,
        basic_grid_config: list[FieldSchema],
        detail_grid_config: list[FieldSchema],
        on_confirm: Callable[[None], None] = None,
    ) -> None:
        super().__init__(basic_grid_config, detail_grid_config, on_confirm)

    @override
    def _submit_input(self):
        basic, detail = self.get_grid_values()
        basic_vals = [v for row in basic for v in row.values()]
        detail_vals = [v for row in detail for v in row.values()]
        values = basic_vals + detail_vals
        m_quantity = [
            v for row in detail for key, v in row.items() if key == "quantity"
        ]
        if self._validate_fields_not_null(values) and self._validate_quantity_positive(
            m_quantity
        ):
            purcahse_date = basic[0]["purchase_date"]
            vendor_name = basic[0]["vendor_name"]
            self._submit_summary.text = f"購買廠商：{vendor_name}\n購買日期：{purcahse_date}\n新增{len(detail)}購買資料"
            self._submit_dialog.open()
        else:
            pass


# Class for inputting and validating prodcut recipe data
class RecipeInputDialog(GenericInputDialog):
    def __init__(
        self,
        basic_grid_config: list[FieldSchema],
        detail_grid_config: list[FieldSchema],
        existed_products: list,
        on_confirm: Callable[[None], None] = None,
    ) -> None:
        self.existed_products = existed_products
        super().__init__(basic_grid_config, detail_grid_config, on_confirm)

    # Use ProductInputGrid for default uom value in product basic
    @override
    def _create_input_grid(self):
        with ui.column().classes("w-full"):
            self._basic_grid = ProductInputGrid(self.basic_grid_config)
            ui.separator()
            self._detail_grid = InputGrid(self.detail_grid_config)

    def _validate_product_unique(self, product: str) -> bool:
        if product in self.existed_products:
            LOGGER.warning(f"Product {product} existed")
            ui.notify("產品已存在，請修改該產品")
            return False
        return True

    @override
    def _submit_input(self):
        basic, detail = self.get_grid_values()
        product_name = basic[0]["product_name"]
        basic_vals = [v for row in basic for v in row.values()]
        detail_vals = [v for row in detail for v in row.values()]
        values = basic_vals + detail_vals
        m_quantity = [
            v for row in detail for key, v in row.items() if key == "quantity"
        ]
        if (
            self._validate_fields_not_null(values)
            and self._validate_quantity_positive(m_quantity)
            and self._validate_product_unique(product_name)
        ):
            price = basic[0]["price"]
            self._submit_summary.text = (
                f"產品：{product_name}\n定價：{price}元\n包含{len(detail)}筆原料"
            )
            self._submit_dialog.open()
        else:
            pass


# Add auto price calculation and note display for order input
class OrderInputDialog(BaseInputDialog):
    def __init__(
        self,
        detail_grid_config: list[FieldSchema],
        product_price_pairs: list[dict],
        on_confirm: Callable[[None], None] = None,
    ) -> None:
        self.product_price_pairs = product_price_pairs
        self._note: ui.input | None = None
        super().__init__(detail_grid_config, on_confirm)

    @override
    def _create_input_grid(self):
        with ui.column().classes("w-full"):
            with ui.row().classes("w-full gap-0"):
                ui.label(f"總金額：").classes("ml-auto text-base")
                price_summed = ui.label().classes("text-base")
                ui.label(f"元").classes("text-base")

            self._detail_grid = OrderInputGrid(
                self.detail_grid_config, self.product_price_pairs, 4
            )
            price_summed.bind_text_from(self._detail_grid, "summed_price")

    @override
    def _create_footer(self):
        with ui.column().classes("w-full"):
            self._note = ui.input("備註").classes("w-full")
            super()._create_footer()

    @override
    def refresh(self):
        super().refresh()
        self._note.value = None

    def get_note_value(self):
        return self._note.value

    def get_summed_price(self):
        return self._detail_grid.summed_price


class FutureOrderInputDialog(OrderInputDialog):
    def __init__(
        self,
        detail_grid_config: list[FieldSchema],
        product_price_pairs: list[dict],
        on_confirm: Callable[[None], None] = None,
    ) -> None:
        self._cp_date: ui.input | None = None
        self._cp_time: ui.input | None = None
        self._datetime_display: ui.label | None = None
        super().__init__(detail_grid_config, product_price_pairs, on_confirm)

    @override
    def _create_input_grid(self):
        with ui.column().classes("w-full"):
            with ui.row().classes("w-full gap-0"):
                self._datetime_display = ui.label().classes("text-base")
                ui.label("交貨").classes("text-base")
                ui.label(f"總金額：").classes("ml-auto text-base")
                price_summed = ui.label().classes("text-base")
                ui.label(f"元").classes("text-base")

            with ui.grid(columns=2).classes("w-full justify-end"):
                self._cp_date, self._cp_time = self._create_datetime_inputs()
                self._combine_cp_datetime()
                self._cp_date.on_value_change(self._combine_cp_datetime)
                self._cp_time.on_value_change(self._combine_cp_datetime)
            ui.separator()

            self._detail_grid = OrderInputGrid(
                self.detail_grid_config, self.product_price_pairs, 4
            )
            price_summed.bind_text_from(self._detail_grid, "summed_price")

    def _create_datetime_inputs(self) -> tuple[ui.input, ui.input]:
        todate = date.today().strftime("%Y-%m-%d")
        todate_js = date.today().strftime("%Y/%m/%d")
        with ui.input("預約日期", value=todate) as date_input:
            with ui.menu() as d_menu:
                date_select = ui.date().props("minimal").bind_value(date_input)
                date_select.props(f''':options="date => date >= '{todate_js}'"''')
            with date_input.add_slot("append"):
                ui.button(on_click=lambda: d_menu.open(), icon="edit_calendar").props(
                    "flat padding=none"
                ).classes("cursor-pointer")
        with ui.input("預約時間", value="00:00") as time_input:
            with ui.menu() as t_menu:
                ui.time().props("format24h").bind_value(time_input)
            with time_input.add_slot("append"):
                ui.button(on_click=lambda: t_menu.open(), icon="schedule").props(
                    "flat padding=none"
                ).classes("cursor-pointer")
        return date_input, time_input

    def _combine_cp_datetime(self):
        date_str = self._cp_date.value
        time_str = self._cp_time.value
        datetime_str = f"{date_str} {time_str}"
        self._datetime_display.text = datetime_str

    def get_completion_datetime(self):
        return datetime.strptime(self._datetime_display.text, "%Y-%m-%d %H:%M")

    # Include check for _co_date/time not null in _submit_input
    @override
    def _submit_input(self):
        detail = self.get_grid_values()
        detail_vals = [v for row in detail for v in row.values()]
        detail_vals.extend([self._cp_date.value, self._cp_time.value])
        quantity = [v for row in detail for key, v in row.items() if key == "quantity"]

        if self._validate_fields_not_null(
            detail_vals
        ) and self._validate_quantity_positive(quantity):
            self.on_confirm()
            self.close()
        else:
            pass

    @override
    def refresh(self):
        super().refresh()
        self._cp_date.value = date.today().strftime("%Y-%m-%d")
        self._cp_time.value = "00:00"


class VendorInputDialog(BaseInputDialog):
    def __init__(
        self,
        detail_grid_config: list[FieldSchema],
        existed_vendors: list,
        on_confirm: Callable[[None], None] = None,
    ) -> None:
        self.existed_vendors = existed_vendors
        super().__init__(detail_grid_config, on_confirm)

    @override
    def _create(self):
        with self, ui.card().classes("lg:w-3/4"):
            with ui.column().classes("w-full h-full justify-between"):
                self._create_input_grid()
                self._create_footer()

    @override
    def _create_input_grid(self):
        with ui.column().classes("w-full"):
            self._detail_grid = VendorInputGrid(self.detail_grid_config)

    @override
    def _create_footer(self):
        with ui.column().classes("w-full"):
            with ui.row().classes("!w-full"):
                confirm_button = ui.button("送出", icon="check").classes(
                    "rounded-md ml-auto"
                )
                confirm_button.on_click(self._submit_input)

    @override
    def _submit_input(self):
        detail = self.get_grid_values()
        vendor_name = detail[0]["vendor_name"]
        if self._validate_vendor_name_not_null(
            vendor_name
        ) and self._validate_vendor_unique(vendor_name):
            self.on_confirm()
            self.close()
        else:
            pass

    def _validate_vendor_unique(self, vendor: str) -> bool:
        if vendor in self.existed_vendors:
            LOGGER.warning(f"Vendor {vendor} existed")
            ui.notify("廠商已存在，請修改該廠商資料")
            return False
        return True

    @staticmethod
    def _validate_vendor_name_not_null(vendor: str):
        if not vendor:
            ui.notify("須輸入廠商名稱方能送出資料")
            return False
        return True
