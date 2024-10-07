from nicegui import app

from logging_setup.setup import LOGGER


@app.get("/ping")
def ping() -> dict[str, str]:
    try:
        LOGGER.debug("Ping received, all systems operational")
        return {"status": "ok", "message": "All systems operational"}
    except Exception as e:
        LOGGER.error(f"Ping received, system check failed: {str(e)}")
        return {"status": "error", "message": str(e)}, 500
