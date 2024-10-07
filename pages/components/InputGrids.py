from datetime import date
from typing import override

from nicegui import ui

from database.FieldSchema import FieldSchema

from .constants import DAYS_OPTIONS

"""
InputGrid
├── OrderInputGrid
└── VendorInputGrid
"""


class InputGrid(ui.grid):
    def __init__(self, schemas: list[FieldSchema], columns: int | None = None):
        _columns = columns if columns else len(schemas)
        super().__init__(columns=_columns)
        self.schemas = schemas
        self._all_elements: list[dict[str, ui.input | ui.select | ui.number]] = []
        self._create()

    def _create(self):
        with self.classes("w-full"):
            first_row = self._create_elements()
            self._all_elements.append(first_row)

    def _create_elements(self) -> dict[str, ui.input | ui.select | ui.number]:
        _ele_references: dict[str, ui.input | ui.select | ui.number] = {}

        for s in self.schemas:
            if "date" in s.field:
                ele = self._create_date_input(s)
                _ele_references[s.field] = ele
            elif "name" in s.field and isinstance(s.value_options, list):
                ele = self._create_select_input(s)
                _ele_references[s.field] = ele
            elif "quantity" in s.field or "price" in s.field:
                ele = self._create_num_input(s)
                _ele_references[s.field] = ele
            else:
                ele = self._create_str_input(s)
                _ele_references[s.field] = ele
        return _ele_references

    @staticmethod
    def _create_date_input(s: FieldSchema) -> ui.input:
        todate = date.today().strftime("%Y-%m-%d")
        with ui.input(s.header_name, value=todate) as date_input:
            with ui.menu() as menu:
                ui.date().props("minimal").bind_value(date_input)
            with date_input.add_slot("append"):
                ui.button(on_click=lambda: menu.open(), icon="edit_calendar").props(
                    "flat padding=none"
                ).classes("cursor-pointer")
        return date_input

    @staticmethod
    def _create_num_input(s: FieldSchema) -> ui.number:
        num_input = ui.number(s.header_name, min=0)
        return num_input

    @staticmethod
    def _create_str_input(s: FieldSchema) -> ui.input:
        # ui.input wont update properly in dialog when close/reopen
        # See https://github.com/zauberzeug/nicegui/issues/2149
        str_input = ui.input(s.header_name)
        return str_input

    # _create_select_input is dependent on self for duplicate warning
    def _create_select_input(self, s: FieldSchema) -> ui.select:
        select_input = ui.select(
            options=s.value_options, label=s.header_name, new_value_mode="add-unique"
        )
        select_input.on_value_change(lambda: self.warn_duplicate(select_input))
        return select_input

    def warn_duplicate(self, select_input_ref: ui.select):
        select_vals = [
            e.value
            for eles in self._all_elements
            for key, e in eles.items()
            if isinstance(e, ui.select) and "name" in key and e.value
        ]
        num_of_val = len([i for i in select_vals if i == select_input_ref.value])
        if num_of_val > 1:
            # A crazy workaround to accomandate Qselect with input
            # It seems that None need to be one of the options for the value to be set to it
            # Will add a blank option (None) at the end of the selection, but with enough options hopefully isnt a big deal
            # If with_input = False the set_value(None) works fine

            select_input_ref.options.append(None)
            select_input_ref.set_value(None)
            select_input_ref.options.remove(None)
            ui.notify(f"此選項已被選取")

    def add_row(self):
        with self:
            added_row = self._create_elements()
            self._all_elements.append(added_row)

    def delete_row(self):
        if len(self._all_elements) == 1:
            ui.notify("無法刪除第一列資料")
        else:
            for _, element in self._all_elements.pop().items():
                element.delete()

    def reinitialize_grid(self):
        self.clear()
        self._all_elements = []
        self._create()

    def get_input_value(self):
        output: list[dict] = []
        for elements in self._all_elements:
            field_val_pairs = {}
            for field, ele in elements.items():
                field_val_pairs[field] = ele.value
            output.append(field_val_pairs)
        return output


class ProductInputGrid(InputGrid):
    def __init__(self, schemas: list[FieldSchema], columns: int | None = None):
        super().__init__(schemas, columns)

    # Give product uom a defualt value as a qol feature
    @override
    def _create_select_input(self, s: FieldSchema) -> ui.select:
        select_input = super()._create_select_input(s)
        if s.field == "uom_name":
            select_input.value = "個"
        return select_input


# Modify InputGrid to add auto price calculation and selection behavior
class OrderInputGrid(InputGrid):
    def __init__(
        self, schemas: list[FieldSchema], product_prices: list[dict], columns: int
    ):
        super().__init__(schemas, columns=columns)
        self.product_prices = product_prices
        self.summed_price: int | None = None

    @override
    def _create_elements(self) -> dict[str, ui.input | ui.select | ui.number]:
        _ele_references: dict[str, ui.input | ui.select | ui.number] = {}

        def autofill_price():
            product = _ele_references["product_name"].value
            quantity = _ele_references["quantity"].value

            price = next(
                (
                    i["price"]
                    for i in self.product_prices
                    if i["product_name"] == product
                ),
                None,
            )
            # Specifically called quantity != None so falsy 0 quantity is still calculated
            if product and quantity != None and price:
                summed_price = price * int(quantity)
                _ele_references["price_total"].set_value(summed_price)

        for s in self.schemas:
            if "name" in s.field and isinstance(s.value_options, list):
                ele = self._create_select_input(s)
                ele.classes("col-span-2")
                _ele_references[s.field] = ele
            elif "quantity" in s.field or "price" in s.field:
                ele = self._create_num_input(s)
                ele.classes("col-span-1")
                _ele_references[s.field] = ele

        _ele_references["product_name"].on_value_change(lambda: autofill_price())
        _ele_references["quantity"].on_value_change(lambda: autofill_price())
        _ele_references["price_total"].on_value_change(lambda: self.get_summed_price())
        return _ele_references

    @override
    def _create_select_input(self, s: FieldSchema) -> ui.select:
        select_input = ui.select(
            options=s.value_options, label=s.header_name, with_input=True
        )
        select_input.on_value_change(lambda: self.warn_duplicate(select_input))
        return select_input

    @override
    def reinitialize_grid(self):
        self.clear()
        self.summed_price = None
        self._all_elements = []
        self._create()

    def get_summed_price(self):
        price_eles = [i["price_total"] for i in self._all_elements]
        prices = [int(i.value) for i in price_eles if i.value]
        summed_price = sum(prices)
        self.summed_price = summed_price


class VendorInputGrid(InputGrid):
    def __init__(self, schemas: list[FieldSchema]):
        super().__init__(schemas, columns=1)

    def _create_elements(self) -> dict[str, ui.input | ui.select | ui.number]:
        _ele_references: dict[str, ui.input | ui.select | ui.number] = {}

        for s in self.schemas:
            if s.field == "open_days":
                ele = self._create_days_select(s)
                ele.props("dense options-dense")
                _ele_references[s.field] = ele
            else:
                ele = self._create_str_input(s)
                ele.props("dense")
                _ele_references[s.field] = ele
        return _ele_references

    @staticmethod
    def _create_days_select(s: FieldSchema) -> ui.select:
        def sort_selected(days: list):
            return sorted(days, key=lambda day: DAYS_OPTIONS[day])

        select_input = ui.select(
            options=list(DAYS_OPTIONS.keys()), label=s.header_name, multiple=True
        )
        select_input.on_value_change(
            lambda: select_input.set_value(sort_selected(select_input.value))
        )
        return select_input

    @override
    def add_row(self):
        raise NotImplementedError("Vendor record does not require this functionality")

    @override
    def delete_row(self):
        raise NotImplementedError("Vendor record does not require this functionality")
