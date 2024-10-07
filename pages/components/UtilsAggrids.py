from typing import Callable, override

from nicegui import ui

from database.FieldSchema import FieldSchema


class RefreshableAggrid(ui.aggrid):
    def __init__(self, schemas: list[FieldSchema], data: list[dict]):
        self.schemas = schemas
        self.data = data
        self._header = self._customize_header()
        self._default_setting = self._customize_general()
        self._create()

    # Putting super__init__ in _create to handle refreshable logic
    @ui.refreshable
    def _create(self):
        super().__init__(self._default_setting, auto_size_columns=False)

    def _customize_general(self) -> dict:
        default_setting = {
            "defaultColDef": {"flex": 1},
            "columnDefs": self._header,
            "rowData": self.data,
            "rowSelection": "multiple",
            "localeText": {"contains": "包含", "inRange": "範圍", "reset": "重置"},
        }
        return default_setting

    def _customize_header(self) -> list[dict]:
        header = []
        for s in self.schemas:
            if "date" in s.field:
                header.append(
                    {
                        "headerName": s.header_name,
                        "field": s.field,
                        "filter": "agDateColumnFilter",
                        "filterParams": {
                            "filterOptions": [
                                "inRange",
                            ],
                            "buttons": ["reset"],
                            "suppressAndOrCondition": True,
                            "inRangeInclusive": True,
                        },
                    }
                )
            elif "name" in s.field and s.field != "uom_name":
                header.append(
                    {
                        "headerName": s.header_name,
                        "field": s.field,
                        "filter": "agTextColumnFilter",
                        "filterParams": {
                            "filterOptions": [
                                "contains",
                            ],
                            "buttons": ["reset"],
                            "suppressAndOrCondition": True,
                        },
                    }
                )
            else:
                header.append({"headerName": s.header_name, "field": s.field})
        return header

    def refresh(self, new_data: list[dict]) -> None:
        self._default_setting["rowData"] = new_data
        self._create.refresh()


class SelectableAggrid(RefreshableAggrid):
    def __init__(
        self,
        schemas: list[FieldSchema],
        data: list[dict],
        select_cards: Callable[[int | bool], None] = None,
    ):
        super().__init__(schemas, data)
        self.select_cards = select_cards
        # Make the checkbox align to left, not sure why but justify center has the best result
        ui.add_css(".checkboxLeft .ag-cell-wrapper {justify-content: center;}")

    @override
    @ui.refreshable
    def _create(self):
        super()._create()
        self.on("selectionChanged", lambda: self._get_selected_ids())

    @override
    def _customize_general(self) -> dict:
        default_setting = super()._customize_general()
        default_setting["rowMultiSelectWithClick"] = True
        return default_setting

    @override
    def _customize_header(self) -> list[dict]:
        header = super()._customize_header()
        for idx, _ in enumerate(header):
            if idx == 0:
                header[idx]["flex"] = 5
            else:
                header[idx]["flex"] = 4
        header.append(
            {
                "checkboxSelection": True,
                "maxWidth": 30,
                "suppressSizeToFit": True,
                "cellClass": "checkboxLeft",
            }
        )
        return header

    def uncheck_all(self):
        self.run_grid_method("deselectAll")

    # Currently the select_cards takes in the select method in GridOfCards
    # Beware of this coupling when changing in the future
    async def _get_selected_ids(self):
        rows: list[dict] = await self.get_selected_rows()
        if rows:
            selected_ids = [val for r in rows for key, val in r.items() if "id" in key]
            self.select_cards(ids=selected_ids)
        else:
            self.select_cards(all=False)


class PreviousOrderGrid(SelectableAggrid):
    def __init__(
        self,
        schemas: list[FieldSchema],
        data: list[dict],
        get_selected_details: Callable[[list[int]], list[dict]] = None,
        create_select_cards: Callable[[list[int], list[dict]], None] = None,
    ):
        super().__init__(schemas, data, None)
        self.get_selected_details = get_selected_details
        self.create_select_cards = create_select_cards
        self._ids_to_created: list[str] | None = None

    @override
    @ui.refreshable
    def _create(self):
        super()._create()
        # Pop the previous on_selection_change in the parent class
        self._event_listeners.popitem()
        self.on("selectionChanged", lambda: self._create_selected_order_cards())

    @override
    async def _get_selected_ids(self):
        raise NotImplementedError(
            "Disabled. Select rows now instead call _create_selected_order_cards"
        )

    async def _create_selected_order_cards(self):
        rows: list[dict] = await self.get_selected_rows()
        if rows:
            id_list_strs: list[str] = []
            for i in rows:
                id_list: str = i["total_id_list"]
                if len(id_list) == 1:
                    id_list_strs.append(id_list)
                else:
                    id_list_strs.extend(id_list.split(","))
            self._ids_to_created = id_list_strs
            details = self.get_selected_details(id_list_strs)
            self.create_select_cards(details)
        else:
            self.create_select_cards(None)

    def recreate_selected(self, deleted_id: str | None = None):
        if self._ids_to_created:
            id_list_strs = self._ids_to_created.copy()
            if deleted_id:
                id_list_strs.remove(deleted_id)
            details = self.get_selected_details(id_list_strs)
            self.create_select_cards(details)
        else:
            self.create_select_cards(None)
