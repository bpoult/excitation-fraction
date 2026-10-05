"""
launcher.py
-----------
Desktop entry point for the Sample & Laser Calculations app.

Serves the Dash app (src.app) on a free localhost port from a background
thread and shows it in a native window (pywebview / WebView2). Closing the
window shuts the server down and exits.

Run from source:   python launcher.py          (repo root)
Packaged build:    dist/ExcitationFraction/ExcitationFraction.exe

All diagnostics go to excitation_fraction.log next to the exe (or next to this
file when run from source), because the packaged build has no console.
"""

import ctypes
import logging
import os
import pathlib
import sys
import threading
import time
import traceback
import urllib.request

APP_TITLE = "Sample & Laser Calculations"
WINDOW_SIZE = (1400, 950)
MIN_WINDOW_SIZE = (1000, 700)
STARTUP_TIMEOUT_S = 20
LOG_NAME = "excitation_fraction.log"

FROZEN = bool(getattr(sys, "frozen", False))


def base_dir() -> pathlib.Path:
    if FROZEN:
        return pathlib.Path(sys.executable).resolve().parent
    return pathlib.Path(__file__).resolve().parent


def setup_logging(log_path: pathlib.Path) -> None:
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    # A windowed (no-console) build has sys.stdout/stderr == None; anything that
    # print()s would raise, so point both at the log file.
    if sys.stdout is None or sys.stderr is None:
        stream = open(log_path, "a", encoding="utf-8", buffering=1)
        sys.stdout = sys.stderr = stream


def show_error(message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, message, f"{APP_TITLE} - error", 0x10)
    except Exception:
        pass


def wait_until_ready(url: str, server_thread: threading.Thread, errors: list) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT_S
    while True:
        if errors:
            raise RuntimeError(f"Server failed to start: {errors[0]!r}")
        if not server_thread.is_alive():
            raise RuntimeError("Server thread exited before becoming ready")
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            pass
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"Server did not respond at {url} within {STARTUP_TIMEOUT_S}s"
            )
        time.sleep(0.1)


def main() -> int:
    base = base_dir()
    setup_logging(base / LOG_NAME)
    logging.info("Starting %s (frozen=%s, base=%s)", APP_TITLE, FROZEN, base)

    os.environ.setdefault("DASH_DISABLE_VERSION_CHECK", "true")

    # The layout lists configs at import time, so the folder must exist first.
    from src.config_io import CONFIGS_DIR, ensure_default_config

    ensure_default_config()
    logging.info("Configs dir: %s", CONFIGS_DIR)

    from src.app import app
    from werkzeug.serving import make_server

    # Port 0 -> the OS picks a free port, so several instances can run at once.
    srv = make_server("127.0.0.1", 0, app.server, threaded=True)
    url = f"http://127.0.0.1:{srv.port}/"
    errors: list = []

    def serve() -> None:
        try:
            srv.serve_forever()
        except BaseException as exc:  # noqa: BLE001 - report anything to the UI
            errors.append(exc)
            logging.exception("Server thread died")

    server_thread = threading.Thread(target=serve, name="dash-server", daemon=True)
    server_thread.start()
    wait_until_ready(url, server_thread, errors)
    logging.info("Server ready at %s", url)

    import webview

    webview.create_window(
        APP_TITLE,
        url,
        width=WINDOW_SIZE[0],
        height=WINDOW_SIZE[1],
        min_size=MIN_WINDOW_SIZE,
    )
    webview.start()  # blocks until the window is closed

    logging.info("Window closed; shutting down server")
    srv.shutdown()
    server_thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        tb = traceback.format_exc()
        logging.error(tb)
        show_error(
            "The application failed to start.\n\n"
            + tb[-1500:]
            + f"\n\nSee log: {base_dir() / LOG_NAME}"
        )
        sys.exit(1)
