from nicegui import ui


class NotifyAwaitInput:
    def __init__(
        self,
        message,
    ) -> None:
        self.message = message
        self._notification: ui.notification | None = None

    def notify_if_null_data(self, check_input: list | None):
        if not check_input:
            self._notification = ui.notification(
                self.message, timeout=None, type="warning"
            )
        elif check_input and self._notification:
            self._notification.dismiss()
