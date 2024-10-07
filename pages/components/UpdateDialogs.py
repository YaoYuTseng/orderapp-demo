from datetime import datetime
from typing import Callable, override

from database.FieldSchema import FieldSchema

from .ConfirmDialogs import ConfirmDialog
from .InputDialogs import (
    FutureOrderInputDialog,
    GenericInputDialog,
    OrderInputDialog,
    VendorInputDialog,
)

"""
Classes for updating record value using similar input method as InputDialogs
Add update_id and original data as fields to autofill InputGrid.
Disabled fields associated with primary ids.


BaseInputDialog
├── GenericInputDialog
│   └── GenericUpdateDialog
│       ├── PurchaseUpdateDialog
│       └── RecipeUpdateDialog
└── OrderInputDialog
    └── OrderUpdateDialog
"""


# Use ConfirmDialog as submit dialog
class GenericUpdateDialog(GenericInputDialog):
    def __init__(
        self,
        basic_grid_config: list[FieldSchema],
        detail_grid_config: list[FieldSchema],
        on_confirm: Callable[[None], None] = None,
    ) -> None:
        super().__init__(basic_grid_config, detail_grid_config, on_confirm)
        self.update_id: int | None = None
        self.original_basic: dict | None = None
        self.original_detail: list[dict] | None = None
        # on_confirm is instead handle by confirm dialog, not called directly
        self._submit_dialog = ConfirmDialog(confirm_msg="", on_confirm=on_confirm)
        self._submit_dialog.bind_value_to(self, "value")

    # Use original data to fill in fields in the update-input dialog
    ## Take in details data of a card from GridOfCards on_update
    def start_update(self, update_id: int, original_data: list[dict]):
        self.refresh()
        basic_fields = self._basic_grid._all_elements[0].keys()
        detail_fields = self._detail_grid._all_elements[0].keys()
        og_basic_data: dict = {
            key: val for key, val in original_data[0].items() if key in basic_fields
        }
        og_detail_data: list[dict] = [
            {key: val for key, val in row.items() if key in detail_fields}
            for row in original_data
        ]
        self.update_id = update_id
        self.original_basic = og_basic_data
        self.original_detail = og_detail_data

        for key, val in og_basic_data.items():
            self._basic_grid._all_elements[0][key].value = val
        self._disable_primary(basic_fields)
        for i, row in enumerate(og_detail_data):
            if i > 0:
                self._detail_grid.add_row()
            for key, val in row.items():
                self._detail_grid._all_elements[i][key].value = val
        self.open()

    # Disabled fields associated with the (one or more) primary id of the table
    # Usually is *_name under the basic field
    def _disable_primary(self, basic_fields: list[str]):
        disable_name = next(i for i in basic_fields if "name" in i)
        self._basic_grid._all_elements[0][disable_name].disable()

    @override
    def refresh(self):
        super().refresh()
        self.update_id = None
        self.original_basic = None
        self.original_detail = None


class PurchaseUpdateDialog(GenericUpdateDialog):
    def __init__(
        self,
        basic_grid_config: list[FieldSchema],
        detail_grid_config: list[FieldSchema],
        on_confirm: Callable[[int], None] = None,
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
            old_m_num = len(self.original_detail)
            new_m_num = len(detail)
            self._submit_dialog.target_id = self.update_id
            self._submit_dialog._confirm_msg_display.text = f"購買廠商：{vendor_name}\n購買日期：{purcahse_date}\n新/舊原料：{old_m_num}/{new_m_num}筆原料"
            self._submit_dialog.open()
        else:
            pass

    # Product update disable vendor name and purchase date (otherwise it is a entirely new update)
    @override
    def _disable_primary(self, _: list[str]):
        self._basic_grid._all_elements[0]["vendor_name"].disable()
        self._basic_grid._all_elements[0]["purchase_date"].disable()


class RecipeUpdateDialog(GenericUpdateDialog):
    def __init__(
        self,
        basic_grid_config: list[FieldSchema],
        detail_grid_config: list[FieldSchema],
        on_confirm: Callable[[int], None] = None,
    ) -> None:
        super().__init__(basic_grid_config, detail_grid_config, on_confirm)

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
        if self._validate_fields_not_null(values) and self._validate_quantity_positive(
            m_quantity
        ):
            old_price = self.original_basic["price"]
            new_price = basic[0]["price"]
            old_m_num = len(self.original_detail)
            new_m_num = len(detail)
            self._submit_dialog.target_id = self.update_id
            self._submit_dialog._confirm_msg_display.text = f"產品：{product_name}\n新/舊定價：{old_price}/{new_price}元\n新/舊原料：{old_m_num}/{new_m_num}筆原料"
            self._submit_dialog.open()
        else:
            pass


class OrderUpdateDialog(OrderInputDialog):
    def __init__(
        self,
        detail_grid_config: list[FieldSchema],
        product_price_pairs: list[dict],
        on_confirm: Callable[[int], None] = None,
    ) -> None:
        super().__init__(detail_grid_config, product_price_pairs, on_confirm)
        self.update_id: int | None = None
        self.original_basic: tuple[int, str] | None = None
        self.original_detail: list[dict] | None = None
        self._submit_dialog = ConfirmDialog(confirm_msg="", on_confirm=on_confirm)
        self._submit_dialog.bind_value_to(self, "value")

    # Use original data to fill in fields in the update-input dialog
    ## Take in details data of a card from GridOfCards on_update
    def start_update(self, update_id: int, original_data: list[dict]):
        self.refresh()
        detail_fields = self._detail_grid._all_elements[0].keys()
        og_detail_data: list[dict] = [
            {key: val for key, val in row.items() if key in detail_fields}
            for row in original_data
        ]
        self.update_id = update_id
        self.original_basic = (
            original_data[0]["order_total"],
            original_data[0]["note"],
        )
        self.original_detail = og_detail_data

        for i, row in enumerate(og_detail_data):
            if i > 0:
                self._detail_grid.add_row()
            for key, val in row.items():
                self._detail_grid._all_elements[i][key].value = val
        self.open()

    @override
    def _submit_input(self):
        detail = self.get_grid_values()
        detail_vals = [v for row in detail for v in row.values()]
        p_quantity = [
            v for row in detail for key, v in row.items() if key == "quantity"
        ]
        if self._validate_fields_not_null(
            detail_vals
        ) and self._validate_quantity_positive(p_quantity):
            old_price = sum(int(i["price_total"]) for i in self.original_detail)
            new_price = self._detail_grid.summed_price
            old_m_num = len(self.original_detail)
            new_m_num = len(detail)
            self._submit_dialog.target_id = self.update_id
            self._submit_dialog._confirm_msg_display.text = f"新/舊金額：{old_price}/{new_price}元\n新/舊銷售：{old_m_num}/{new_m_num}項產品"
            self._submit_dialog.open()
        else:
            pass

    @override
    def refresh(self):
        super().refresh()
        self.update_id = None
        self.original_basic = None
        self.original_detail = None


class FutureOrderUpdateDialog(OrderUpdateDialog, FutureOrderInputDialog):
    def __init__(
        self,
        detail_grid_config: list[FieldSchema],
        product_price_pairs: list[dict],
        on_confirm: Callable[[int], None] = None,
    ) -> None:
        super().__init__(detail_grid_config, product_price_pairs, on_confirm)
        self.update_id: int | None = None
        self.original_basic: tuple[int, str] | None = None
        self.original_detail: list[dict] | None = None
        self._submit_dialog = ConfirmDialog(confirm_msg="", on_confirm=on_confirm)
        self._submit_dialog.bind_value_to(self, "value")

    def start_update(self, update_id: int, original_data: list[dict]):
        self.refresh()
        detail_fields = self._detail_grid._all_elements[0].keys()
        og_detail_data: list[dict] = [
            {key: val for key, val in row.items() if key in detail_fields}
            for row in original_data
        ]
        self.update_id = update_id
        self.original_basic = (
            original_data[0]["order_total"],
            original_data[0]["note"],
            original_data[0]["completion_timestamp"],
        )
        cp_datetime: datetime = original_data[0]["completion_timestamp"]
        self._cp_date.value = cp_datetime.strftime("%Y-%m-%d")
        self._cp_time.value = cp_datetime.strftime("%H:%M")
        self.original_detail = og_detail_data
        for i, row in enumerate(og_detail_data):
            if i > 0:
                self._detail_grid.add_row()
            for key, val in row.items():
                self._detail_grid._all_elements[i][key].value = val
        self.open()

    @override
    def refresh(self):
        super().refresh()
        self.update_id = None
        self.original_basic = None
        self.original_detail = None
        self._cp_date.value = None
        self._cp_time.value = None


# Forgo using submit dialog because vednor update does not involve complex changes
class VendorUpdateDialog(VendorInputDialog):
    def __init__(
        self,
        detail_grid_config: list[FieldSchema],
        existed_vendors: list,
        on_confirm: Callable[[int], None] = None,
    ) -> None:
        super().__init__(detail_grid_config, existed_vendors, on_confirm)
        self.update_id: int | None = None
        self.original_detail: dict | None = None

    # Use original data to fill in fields in the update-input dialog
    ## Take in details data of a card from GridOfCards on_update
    ## Vendor original_data would have only one row each card
    def start_update(self, update_id: int, original_data: list[dict]):
        self.refresh()
        detail_fields = self._detail_grid._all_elements[0].keys()
        og_detail_data = {
            key: val for key, val in original_data[0].items() if key in detail_fields
        }
        self.original_detail = og_detail_data
        self.update_id = update_id

        for key, val in og_detail_data.items():
            self._detail_grid._all_elements[0][key].value = val
        self._detail_grid._all_elements[0]["vendor_name"].disable()
        self.open()

    @override
    def _submit_input(self):
        self.on_confirm(self.update_id)
        self.close()
