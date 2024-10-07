from typing import Callable

from nicegui import ui


class DropdownNavigate(ui.dropdown_button):
    def __init__(self, name: str, path_name: dict[str, str]) -> None:
        super().__init__(text=name)
        self.path_name = path_name
        self._create()

    def _create(self):
        with self.classes("text-lg md:text-xl"):
            for key, val in self.path_name.items():
                item = ui.item(val).classes("text-lg md:text-xl")
                item.on_click(lambda x=key: ui.navigate.to(x))
                if val == self.text:
                    item.disable()
                else:
                    item.classes("hover:font-bold")


class VisibilityMenu(ui.menu):
    def __init__(
        self, to_filter: list[str], on_change: Callable[[dict], None] = None
    ) -> None:
        super().__init__()
        self.visibility_results = {i: True for i in to_filter}
        self.on_change = on_change
        self.switch_reference: dict[str, ui.switch] = {}
        self._create()

    def _create(self):
        def change_visibility(key, value):
            self.visibility_results[key] = value
            if self.on_change:
                self.on_change(self.visibility_results)

        # niceGUI event handler pass in sender as an argument (? not sure)
        # so ui.switch of which value changes would be pass in as x
        # see _handle_value_change for more details, but I am still unsure as to where it stated sender is passed as argument
        with self, ui.column().classes("gap-0 p-2"):
            for name, visible in self.visibility_results.items():
                switch = ui.switch(name, value=visible).on_value_change(
                    lambda x, key=name: change_visibility(key, x.value)
                )
                self.switch_reference[name] = switch

    def manual_switch(self, name: str, value: bool):
        switch = self.switch_reference.get(name)
        switch.set_value(value)
