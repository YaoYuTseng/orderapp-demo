from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Callable, override

from nicegui import ui

from database.FieldSchema import FieldSchema

from .constants import DAYS_OPTIONS


# GridofCards handle getting (and sorting) primary id locally because it need to get distinct id set, overring ORDER BY
class GridOfCards(ui.grid):
    def __init__(
        self,
        schemas: list[FieldSchema],
        data: list[dict],
        group_by: str,
        on_update: Callable[[int, list[dict]], None] = None,
        on_delete: Callable[[int], None] = None,
    ):
        with ui.scroll_area().classes("w-full flex-1").props("visible='visible'"):
            super().__init__(columns=6)
            self.classes("w-full")
        self.schemas = schemas
        self.data = data
        self.group_by = group_by
        self.on_update = on_update
        self.on_delete = on_delete
        self._reference: defaultdict[int, dict[str, ui.card | ui.table | ui.button]] = (
            defaultdict(dict)
        )
        self._modify_visible = False
        self._selected_ids: list[int] = []
        self._create()

    def _create(self):
        cols = [
            {
                "label": s.header_name,
                "field": s.field,
                "align": "left" if "name" in s.field else "right",
                "style": f"width:{round((100/len(self.schemas)), 2)}%",
            }
            for s in self.schemas
        ]
        if not self.data:
            self.clear()
        else:
            primary_ids = self._get_primary_ids()
            for p_id in primary_ids:
                table_data = [i for i in self.data if i[f"{self.group_by}_id"] == p_id]

                with self:
                    with ui.card().tight() as card:
                        card.classes("col-span-6 sm:col-span-3 xl:col-span-2")
                        self._create_header(table_data)
                        table = self._create_table(cols, table_data)
                        self._create_footer(p_id, table_data)
                    self._reference[p_id]["card_ref"] = card
                    self._reference[p_id]["table_ref"] = table
                    card.visible = False

    def _get_primary_ids(self):
        return {row[f"{self.group_by}_id"] for row in self.data}

    def _create_header(self, rows: list[dict]):
        title = rows[0][f"{self.group_by}_name"]
        ui.label(title).classes("px-2 pt-2 font-extrabold")

    def _create_table(self, cols: list[dict], rows: list[dict]):
        table = ui.table(cols, rows).classes("w-full px-2 pb-1").props("dense")
        return table

    # Create initially invisible update and delete buttons as card footer
    def _create_footer(self, modify_id: int, rows: list[dict]):
        with ui.row().classes("w-full gap-1 pb-2 px-2 mt-auto justify-end") as modify:

            update = (
                ui.button("修改資料")
                .classes(" !text-black")
                .props("outline padding='none 4px'")
            )
            delete = (
                ui.button("刪除資料")
                .classes(" !text-red-500")
                .props("outline padding='none 4px'")
            )
            # On update sent id and table data to update
            if self.on_update:
                update.on_click(lambda x=modify_id, d=rows: self.on_update(x, d))
            # On delete sent id to delete
            if self.on_delete:
                delete.on_click(lambda x=modify_id: self.on_delete(x))
        modify.bind_visibility_from(self, "_modify_visible")

    def select(
        self, ids: list[int] | None = None, name: str | None = None, all: bool = False
    ):
        if ids:
            selected_id = ids
        elif name:
            selected_id = list(
                {
                    i[f"{self.group_by}_id"]
                    for i in self.data
                    if name in i[f"{self.group_by}_name"]
                }
            )
        elif all:
            selected_id = list({i[f"{self.group_by}_id"] for i in self.data})
        elif not all:
            selected_id = []
        self._selected_ids = selected_id
        for i in self._reference.keys():
            if i in selected_id:
                self._reference[i]["card_ref"].set_visibility(True)
            else:
                self._reference[i]["card_ref"].set_visibility(False)

    # Delete and update visibilities are bind, so showing one is enough
    def show_modify(self):
        if self._modify_visible:
            self._modify_visible = False
        else:
            self._modify_visible = True

    def recreate(self, new_data: list[dict]):
        self.data = new_data
        self._references = defaultdict(dict)
        self.clear()
        self._create()
        if self._selected_ids:
            self.select(self._selected_ids)


class VendorCards(GridOfCards):
    def __init__(
        self,
        schemas: list[FieldSchema],
        data: list[dict],
        group_by: str,
        on_update: Callable[[int, list[dict]], None] = None,
        on_delete: Callable[[int], None] = None,
    ):
        super().__init__(schemas, data, group_by, on_update, on_delete)

    @override
    def _create(self):
        if not self.data:
            self.clear()
        else:
            primary_ids = self._get_primary_ids()
            for p_id in primary_ids:
                table_data = [i for i in self.data if i[f"{self.group_by}_id"] == p_id]
                with self:
                    with ui.card().tight() as card:
                        card.classes("col-span-6 sm:col-span-3 xl:col-span-2")
                        self._create_labels(table_data)
                        self._create_footer(p_id, table_data)
                    self._reference[p_id]["card_ref"] = card
                    card.visible = False

    @override
    def _create_header(self):
        raise NotImplementedError("Vendor cards do not include header")

    @override
    def _create_table(self):
        raise NotImplementedError("Vendor cards do not use labels instead of table")

    def _create_labels(self, rows: list[dict]):
        if len(rows) > 1:
            raise ValueError("Vendor should only have one row each card")
        with ui.column().classes("p-2 gap-0.5 w-full"):
            for key, val in rows[0].items():
                schema = next((s for s in self.schemas if s.field == key), None)
                if schema and val:
                    if key == "vendor_name":
                        with ui.row().classes("w-full justify-between items-end gap-0"):
                            ui.label(val).classes("font-extrabold text-lg")
                            open_today = ui.label().classes("font-bold text-base")
                            ui.separator().classes("mb-1")
                    else:
                        if key == "open_days":
                            self._indicate_open(val, open_today)
                            val = self._format_open_days(val)
                        elif "office_phone" in key:
                            val = self.format_office_phone(val)
                        elif "mobile_phone" in key:
                            val = self.format_mobile_phone(val)
                        with ui.row().classes("w-full gap-0"):
                            ui.label(f"{schema.header_name}：").classes(
                                "font-bold text-base"
                            )
                            ui.label(val).classes("text-base")

    def _indicate_open(self, open_days: list, label: ui.label):
        today_weekday_num = datetime.today().weekday()
        open_weekday_nums = [
            val for key, val in DAYS_OPTIONS.items() if key in open_days
        ]
        if today_weekday_num in open_weekday_nums:
            label.text = "今日營業"
            label.classes("text-green-600")
        else:
            label.text = "今日休息"
            label.classes("text-red-600")

    def _format_open_days(self, open_days: list):
        open_days = [day if idx == 0 else day[-1] for idx, day in enumerate(open_days)]
        return "、".join(open_days)

    @staticmethod
    def format_mobile_phone(phone: str):
        # xxxx-xxx-xxx mobile_phone
        return f"{phone[:4]}-{phone[4:7]}-{phone[7:]}"

    @staticmethod
    def format_office_phone(phone: str):
        # (area code) office_phone
        # see https://zh.wikipedia.org/zh-tw/%E4%B8%AD%E8%8F%AF%E6%B0%91%E5%9C%8B%E9%9B%BB%E8%A9%B1%E8%99%9F%E7%A2%BC for future formatting
        if phone[0] == "0":
            return f"({phone[:2]}){phone[2:]}"
        else:
            return phone


class PurchaseCards(GridOfCards):
    def __init__(
        self,
        schemas: list[FieldSchema],
        data: list[dict],
        group_by: str,
        on_update: Callable[[int, list[dict]], None] = None,
        on_delete: Callable[[int], None] = None,
    ):
        super().__init__(schemas, data, group_by, on_update, on_delete)

    @override
    def _get_primary_ids(self):
        return sorted(super()._get_primary_ids(), reverse=True)

    @override
    def _create_header(self, rows: list[dict]):
        title = rows[0]["vendor_name"]
        purchase_date = rows[0]["purchase_date"].strftime("%Y/%m/%d")
        with ui.row().classes("w-full gap-1 pt-2 px-2 items-center justify-between"):
            ui.label(f"廠商：{title}").classes("font-extrabold")
            ui.label(purchase_date)


class RecipeCards(GridOfCards):
    def __init__(
        self,
        schemas: list[FieldSchema],
        data: list[dict],
        group_by: str,
        on_update: Callable[[int, dict], None] = None,
        on_delete: Callable[[int], None] = None,
    ):
        super().__init__(schemas, data, group_by, on_update, on_delete)

    @override
    def _create_header(self, rows: list[dict]):
        title = rows[0][f"product_name"]
        price = rows[0]["price"]
        with ui.row().classes("w-full gap-1 pt-2 px-2 items-center justify-between"):
            ui.label(title).classes("font-extrabold")
            ui.label(f"定價：{price}元")


class OrderCards(GridOfCards):
    def __init__(
        self,
        schemas: list[FieldSchema],
        data: list[dict],
        group_by: str,
        on_update: Callable[[int, list[dict]], None] = None,
        on_delete: Callable[[int], None] = None,
        on_status_change: Callable[[int, str], None] = None,
    ):
        self._footer_visible = True
        self._paid_visible = False
        self._status_visibility: dict[str, bool] = {
            "已完成": True,
            "已取消": True,
            "準備中": True,
        }
        super().__init__(schemas, data, group_by, on_update, on_delete)
        self.on_status_change = on_status_change

    @override
    def _create(self):
        cols = [
            {
                "label": s.header_name,
                "field": s.field,
                "align": "left" if s.field == "product_name" else "center",
                "style": "width:40%" if s.field == "product_name" else "width:20%",
            }
            for s in self.schemas
        ]

        if not self.data:
            with self:
                with ui.card().tight().classes("col-span-6"):
                    ui.label("請建立新訂單開始").classes("w-full text-xl p-5")
        else:
            primary_ids = self._get_primary_ids()
            for p_id in primary_ids:
                table_data = [i for i in self.data if i[f"{self.group_by}_id"] == p_id]
                with self.classes("w-full"):
                    with ui.card().tight() as card:
                        card.classes("col-span-6 sm:col-span-3 xl:col-span-2")
                        price, status = self._create_header(table_data)
                        table = self._create_table(cols, table_data)
                        paid = self._create_footer(p_id, table_data)
                    self._reference[p_id]["card_ref"] = card
                    self._reference[p_id]["price_ref"] = price
                    self._reference[p_id]["status_ref"] = status
                    self._reference[p_id]["table_ref"] = table
                    self._reference[p_id]["paid_ref"] = paid
                    self._change_status_display(p_id)
            self._filter_by_status()

    @override
    def _get_primary_ids(self):
        return sorted(super()._get_primary_ids())

    @override
    def _create_header(self, rows: list[dict]):
        timestamp: datetime = rows[0]["order_timestamp"]
        summed_price = rows[0]["order_total"]
        status = rows[0]["order_status"]
        with ui.row().classes("w-full gap-1 pt-2 px-2"):
            ui.label(timestamp.strftime("%Y/%m/%d %H:%M:%S"))
            price = ui.label(f"總金額：{summed_price}元").classes("ml-auto")
            status = ui.label(status).classes("font-semibold")
        return price, status

    @override
    def _create_footer(self, order_id: int, rows: list[dict]):
        note = rows[0]["note"]
        is_paid = rows[0]["is_paid"]
        if note:
            ui.label(f"備註：{note}").classes("px-2")
        with ui.row().classes(
            "w-full pb-1 px-1 mt-auto items-center justify-between"
        ) as footer:
            with ui.row().classes("gap-0.5"):
                # (Refresh to) preparing order button
                prepare = ui.button(icon="refresh")
                prepare.classes("text-black text-base md:text-lg")
                prepare.props("flat padding=none")
                prepare.on_click(lambda o=order_id: self._change_status(o, "準備中"))
                # Cancel order button
                cancel = ui.button(icon="delete_forever")
                cancel.classes("text-black text-base md:text-lg")
                cancel.props("flat padding=none")
                cancel.on_click(lambda o=order_id: self._change_status(o, "已取消"))

            with ui.row().classes("gap-0.5 items-center"):
                with ui.row().classes("gap-1") as modify:
                    update = ui.button("修改資料")
                    update.classes("!text-black").props("outline padding='none 4px'")
                    delete = ui.button("刪除資料")
                    delete.classes("!text-red-500").props("outline padding='none 4px'")

                # Paid button
                paid = ui.button().classes("font-semibold")
                paid.props("flat padding='none 2px'")
                paid.on_click(lambda o=order_id, p=paid: self._change_paid_status(o, p))
                paid.on_click(lambda o=order_id: self._change_paid_display(o))
                paid.text = "已付款" if is_paid else "未付款"
                paid.bind_visibility_from(self, "_paid_visible")
                # Complete order button
                complete = ui.button(icon="assignment_turned_in")
                complete.classes("text-black  text-base md:text-lg")
                complete.props("flat padding=none")
                complete.on_click(lambda o=order_id: self._change_status(o, "已完成"))
            # On update sent id and table data to update
            if self.on_update:
                update.on_click(lambda o=order_id, r=rows: self.on_update(o, r))
            # On delete sent id to delete
            if self.on_delete:
                delete.on_click(lambda o=order_id: self.on_delete(o))
            modify.bind_visibility_from(self, "_modify_visible")
            footer.bind_visibility_from(self, "_footer_visible")
            return paid

    def _change_status_display(self, order_id: int):
        card = self._reference[order_id]["card_ref"]
        price = self._reference[order_id]["price_ref"]
        status = self._reference[order_id]["status_ref"]
        table = self._reference[order_id]["table_ref"]
        if status.text == "已完成":
            card.classes("text-gray-400")
            table.classes("text-gray-400")
            price.classes("text-black")
            status.classes("text-green-600")
        elif status.text == "已取消":
            card.classes("text-gray-400")
            table.classes("text-gray-400")
            price.classes("line-through")
            status.classes("text-red-600")

    def _change_status(self, order_id: int, new_status: str):
        if self.on_status_change:
            self.on_status_change(order_id, new_status)
            self._change_status_display(order_id)

    # Today Order does not change is_paid status
    def _change_paid_status(self, order_id: int, button: ui.button):
        raise NotImplementedError("Today order default to paid")

    def _change_paid_display(self, order_id: int):
        paid = self._reference[order_id]["paid_ref"]
        if paid.text == "已付款":
            paid.classes("!text-green-600")
        elif paid.text == "未付款":
            paid.classes("!text-red-600")

    # Control the visiblity of cards based on status
    # _status_visibility example: {"準備中": True; "已完成": False}
    def _filter_by_status(self):
        cards_visibility = []
        cards = [self._reference[i]["card_ref"] for i in self._reference.keys()]
        for i in self._reference.keys():
            status = self._reference[i]["status_ref"]
            card = self._reference[i]["card_ref"]
            visible = self._status_visibility.get(status.text)
            card.set_visibility(visible)
            cards_visibility.append(card.visible)
        # Give user a warning that order cards still exists, they are just being hidden
        if any(cards) and not any(cards_visibility):
            ui.notify("提醒：目前所有訂單皆被隱藏，但仍然存在於列表中。")

    def update_status_visibility(self, stauts_visibilty: dict[str, bool]):
        self._status_visibility = stauts_visibilty
        self._filter_by_status()


class FutureOrderCards(OrderCards):
    def __init__(
        self,
        schemas: list[FieldSchema],
        data: list[dict],
        group_by: str,
        on_update: Callable[[int, list[dict]], None] = None,
        on_delete: Callable[[int], None] = None,
        on_status_change: Callable[[int, str], None] = None,
        on_paid_change: Callable[[int, bool], None] = None,
    ):
        self.on_paid_change = on_paid_change
        super().__init__(
            schemas, data, group_by, on_update, on_delete, on_status_change
        )
        self._paid_visible = True

    # Let id be sorted based on completion_timestamp
    # Because order_id does not have a direct relationship with completion_timestamp
    @override
    def _get_primary_ids(self):
        id_cpt = {(i["order_id"], i["completion_timestamp"]) for i in self.data}
        cp_based_ids = sorted(id_cpt, key=lambda x: x[1])
        cp_based_ids = [i[0] for i in cp_based_ids]
        return cp_based_ids

    @override
    def _create(self):
        super()._create()
        # Change is_paid button color, similar to _change_status_display being applied for every id
        if self.data:
            for i in self._get_primary_ids():
                self._change_paid_display(i)

    @override
    def _create_header(self, rows: list[dict]):
        timestamp: datetime = rows[0]["completion_timestamp"]
        summed_price = rows[0]["order_total"]
        status = rows[0]["order_status"]
        days_from_now = self._get_days_from_now(timestamp)
        with ui.row().classes("w-full gap-1 pt-1 pb-0.5 px-2 justify-between"):
            ui.label(f"{timestamp.strftime('%Y/%m/%d %H:%M')}交貨")
            warn_complete = ui.label().classes("font-bold")
            if days_from_now == 0:
                warn_complete.text = "今日交貨"
                warn_complete.classes("text-red-600")
            elif days_from_now < 0:
                warn_complete.text = "已過交貨期限"
                warn_complete.classes("text-red-600")
            elif days_from_now > 0:
                warn_complete.text = f"{days_from_now}天後交貨"
                warn_complete.classes("text-black")
            # Handle color change here instead of through _change_status_display to avoid having to rewrite _create for this small change
            if status == "已取消" or status == "已完成":
                warn_complete.classes("!text-gray-400")
        ui.separator().classes("mb-1.5")
        with ui.row().classes("w-full gap-1 px-2"):
            price = ui.label(f"總金額：{summed_price}元").classes("ml-auto")
            status = ui.label(status).classes("font-semibold")
        return price, status

    @staticmethod
    def _get_days_from_now(d: datetime):
        today = datetime.now()
        diff = (d - today).days
        return diff

    @override
    def _change_paid_status(self, order_id: int, button: ui.button):
        if self.on_paid_change:
            if button.text == "已付款":
                self.on_paid_change(order_id, False)
            elif button.text == "未付款":
                self.on_paid_change(order_id, True)


class PreviousOrderCards(OrderCards):
    def __init__(
        self,
        schemas: list[FieldSchema],
        data: list[dict] | None,
        group_by: str,
        on_update: Callable[[int, list[dict]], None] = None,
        on_delete: Callable[[int], None] = None,
        on_status_change: Callable[[int, str], None] = None,
        on_paid_change: Callable[[int, bool], None] = None,
    ):
        self._cost: ui.label | None = None
        self.on_paid_change = on_paid_change
        super().__init__(
            schemas, data, group_by, on_update, on_delete, on_status_change
        )
        self._paid_visible = True
        self._footer_visible = False

    # Let id be sorted based on order_timestamp
    # Because order_id does not have a direct relationship with order_timestamp when it can be changed on_complete (i.e., when future order becomes previous)
    @override
    def _get_primary_ids(self):
        id_ot = {(i["order_id"], i["order_timestamp"]) for i in self.data}
        cp_based_ids = sorted(id_ot, key=lambda x: x[1])
        cp_based_ids = [i[0] for i in cp_based_ids]
        return cp_based_ids

    @override
    def _create(self):
        if not self.data:
            self.clear()
        else:
            super()._create()
            for i in self._get_primary_ids():
                self._change_paid_display(i)

    @override
    def _create_table(self, cols: list[dict], rows: list[dict]):
        table = super()._create_table(cols, rows)
        with ui.row().classes("w-full gap-1 px-2 pb-1 items-center justify-end"):
            products_costs = [i["products_cost"] for i in rows]
            if "N/A" in products_costs:
                self._cost = ui.label(f"總成本：無法計算")
            else:
                summed_cost = round(sum([Decimal(i) for i in products_costs]), 2)
                self._cost = ui.label(f"總成本：{summed_cost}元")
        return table

    @override
    def _change_status_display(self, order_id: int):
        super()._change_status_display(order_id)
        status = self._reference[order_id]["status_ref"]
        if status.text == "已完成":
            self._cost.classes("text-black")
        elif status.text == "已取消":
            self._cost.classes("line-through")

    @override
    def select(self):
        raise NotImplementedError(
            "Disabled. PreviousOrderCards is now created on selection"
        )

    def create_on_select(self, details: list[dict]):
        self.data = details
        self.clear()
        self._create()

    def show_footer(self):
        if not self.data:
            pass
        else:
            if self._footer_visible:
                self._footer_visible = False
            else:
                ui.notify("請注意，此頁面之修改將影響過去收入與成本計算")
                self._footer_visible = True

    @override
    def _change_paid_status(self, order_id: int, button: ui.button):
        if self.on_paid_change:
            if button.text == "已付款":
                self.on_paid_change(order_id, False)
            elif button.text == "未付款":
                self.on_paid_change(order_id, True)
