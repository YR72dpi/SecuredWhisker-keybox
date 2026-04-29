import sys
import os
import time
import logging
import threading

libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "lib")
if os.path.exists(libdir):
    sys.path.append(libdir)

import screenManager
from JsonManager import get_all_json
from TP_lib import gt1151
from TP_lib import epd2in13_V4

# ─── Hardware state ───────────────────────────────────────────────────────────
# All globals are set by init_hardware() before any display function is called.

_epd:    epd2in13_V4.EPD       = None
_gt:     gt1151.GT1151         = None
_gt_dev: gt1151.GT_Development = None
_touch_active                  = True
_touch_thread: threading.Thread = None

# Header line shown at the top of every screen.
HEADER = "---------------- SW Keybox ----------------"


# ─── Touch polling thread ─────────────────────────────────────────────────────

def _touch_poll() -> None:
    """Background thread: continuously samples the touch-controller IRQ pin."""
    logging.info("Touch polling thread started")
    while _touch_active:
        _gt_dev.Touch = 1 if _gt.digital_read(_gt.INT) == 0 else 0
        time.sleep(0.01)
    logging.info("Touch polling thread stopped")


# ─── Hardware lifecycle ───────────────────────────────────────────────────────

def init_hardware() -> None:
    """Initialise e-Paper, touch controller, and start the touch polling thread."""
    global _epd, _gt, _gt_dev, _touch_thread, _touch_active

    logging.info("Initialising display hardware")
    _epd    = epd2in13_V4.EPD()
    _gt     = gt1151.GT1151()
    _gt_dev = gt1151.GT_Development()

    _epd.init(_epd.FULL_UPDATE)
    _epd.Clear(0xFF)
    _gt.GT_Init()

    _touch_active = True
    _touch_thread = threading.Thread(target=_touch_poll, daemon=True)
    _touch_thread.start()


def teardown() -> None:
    """Gracefully stop all hardware: show logo, sleep display, release GPIO."""
    global _touch_active
    _touch_active = False
    if _touch_thread:
        _touch_thread.join(timeout=1.0)

    # Silence a benign gpiozero race: its IRQ callback may fire one last time
    # after Dev_exit() clears the internal _hold_thread reference.
    _orig = threading.excepthook
    def _suppress_gpiozero(args):
        msg = args.exc_value.args[0] if args.exc_value.args else ""
        if args.exc_type is AttributeError and (
            "_hold_thread" in msg or "NoneType" in str(args.exc_value)
        ):
            return
        _orig(args)
    threading.excepthook = _suppress_gpiozero

    if _epd:
        screenManager.clear_and_sleep(_epd)
        _epd.Dev_exit()

    threading.excepthook = _orig


# ─── Internal render helper ───────────────────────────────────────────────────

def _show(lines, *, force: bool = False, hold_extra: float = 0.0) -> None:
    """Render lines on the display.

    When force=True (or hold_extra > 0), the render runs in a worker thread so
    the asyncio event-loop is never blocked while waiting for the e-Paper.
    """
    def _render():
        screenManager.print_lines(_epd, lines, force=force, hold_extra=hold_extra)

    if force or hold_extra > 0:
        threading.Thread(target=_render, daemon=True).start()
    else:
        _render()


# ─── Public display API ───────────────────────────────────────────────────────

def show_waiting_screen() -> None:
    _show([HEADER, "Prêt pour apairage", "(pairing BLE)"])


def show_pairing_code(code: str) -> None:
    _show(["SW-Keybox", "Code BLE :", str(code)], force=True)


def show_connected(mac: str = "") -> None:
    lines = [HEADER, "Appareil connecté"]
    if mac:
        lines.append(mac)
    _show(lines, force=True)


def show_key_status() -> None:
    """Show whether key pairs are stored.

    Holds the screen for 3 s (hold_extra) so the user can read it before
    show_connected() can overwrite it. Runs in a worker thread — asyncio safe.
    """
    try:
        initialized = bool(get_all_json().get("initialized", False))
    except Exception:
        initialized = False
    msg = "Clés présentes" if initialized else "Aucune paire de clé"
    _show([HEADER, msg], force=True, hold_extra=3.0)


def show_launching() -> None:
    _show([HEADER, "Launching… Please wait…"])


def show_message(text: str) -> None:
    _show([HEADER, text])


def shutdown() -> None:
    """Display the logo, sleep the panel, then power off the Raspberry Pi."""
    screenManager.clear_and_sleep(_epd)
    time.sleep(1)
    os.system("shutdown -h now")