from datetime import datetime, timedelta

import bcrypt
from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app
from starlette.middleware.base import BaseHTTPMiddleware

from logging_setup.setup import LOGGER

EXPIRATION_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
SESSION_LENGTH = timedelta(days=30)


# See also https://github.com/zauberzeug/nicegui/blob/main/examples/authentication/main.py
class AuthMiddleware(BaseHTTPMiddleware):
    """This middleware restricts access to all NiceGUI pages.
    It redirects the user to the login page if they are not authenticated.
    """

    # Grant access to internal, font, favicon, and login pages
    def grant_access(self, path: str):
        if (
            path.startswith("/_nicegui")
            or path.startswith("/fonts")
            or path.endswith(".ico")
            or path.endswith(".png")
            or path in {"/login", "/ping"}
        ):
            return True
        return False

    # Check user expiration date against now
    def check_expiration(self, expiration: str | None):
        if expiration is None:
            return True
        else:
            now = datetime.now()
            expiration = datetime.strptime(expiration, EXPIRATION_FORMAT)
            if expiration < now:
                return True
        return False

    async def dispatch(self, request: Request, call_next):
        # Set autheticated to False if session expired (see SESSION_LENGTH)
        user_expiration = app.storage.user.get("expiration", None)
        is_expired = self.check_expiration(user_expiration)
        if is_expired:
            app.storage.user.update({"authenticated": False})

        # Check authentication. Allow access to internal pages
        is_accessible = self.grant_access(request.url.path)
        is_authenticated = app.storage.user.get("authenticated", False)
        if not is_authenticated:
            if not is_accessible:
                # remember where the user wanted to go
                app.storage.user["referrer_path"] = request.url.path
                LOGGER.info("Unauthenticated access, redirect to /login")
                return RedirectResponse("/login")
        return await call_next(request)


# Check the provided password against store hashed
def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
