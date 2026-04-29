import sys
import os
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import time
import logging
import threading

import screenManager
from JsonManager import get_all_json
from TP_lib import gt1151
from TP_lib import epd2in13_V4

# ======================
# HARDWARE GLOBALS
# ======================

epd          = None
gt           = None
GT_Dev       = None
GT_Old       = None
flag_t       = 1
_touch_thread = None

def _pthread_irq():
    print("pthread running")
    while flag_t == 1:
        if gt.digital_read(gt.INT) == 0:
            GT_Dev.Touch = 1
        else:
            GT_Dev.Touch = 0
        time.sleep(0.01)
    print("thread:exit")

# ======================
# HARDWARE LIFECYCLE
# ======================

def init_hardware():
    global epd, gt, GT_Dev, GT_Old, _touch_thread
    logging.info("epd2in13_V4 Touch Demo")
    epd    = epd2in13_V4.EPD()
    gt     = gt1151.GT1151()
    GT_Dev = gt1151.GT_Development()
    GT_Old = gt1151.GT_Development()

    logging.info("init and Clear")
    epd.init(epd.FULL_UPDATE)
    epd.Clear(0xff)
    gt.GT_Init()

    _touch_thread = threading.Thread(target=_pthread_irq, daemon=True)
    _touch_thread.start()

def teardown():
    global flag_t
    flag_t = 0
    if _touch_thread:
        _touch_thread.join(timeout=1.0)

    # Silences a benign gpiozero race condition: the lgpio interrupt callback
    # fires one last time after Dev_exit() clears _hold_thread to None.
    _orig_excepthook = threading.excepthook
    def _suppress_gpiozero_cleanup(args):
        if args.exc_type is AttributeError and "_hold_thread" in (args.exc_value.args[0] if args.exc_value.args else ""):
            return
        if args.exc_type is AttributeError and "NoneType" in str(args.exc_value) and "holding" in str(args.exc_value):
            return
        _orig_excepthook(args)
    threading.excepthook = _suppress_gpiozero_cleanup

    if epd:
        screenManager.clearAndSleep(epd)  # affiche logo.bmp + sleep
        epd.Dev_exit()

    threading.excepthook = _orig_excepthook

# ======================
# DISPLAY FUNCTIONS
# ======================

def show_waiting_screen():
    screenManager.printLines(epd, [
        "---------------- SW Keybox ----------------",
        "Prêt pour apairage",
        "(pairing BLE)"
    ], 5, 5)

def show_pairing_code(code: str):
    screenManager.printLines(epd, ["SW-Keybox", "Code BLE:", str(code)], 5, 5)

def show_connected(mac: str = ""):
    lines = [
        "---------------- SW Keybox ----------------",
        "Appareil connecté",
    ]
    if mac:
        lines.append(mac)
    screenManager.printLines(epd, lines, 5, 5)

def show_key_status():
    try:
        data = get_all_json()
        initialized = bool(data.get("initialized", False))
    except Exception:
        initialized = False
    msg = "Clés présentes" if initialized else "Aucune paire de clé présente"
    screenManager.printLines(epd, [
        "---------------- SW Keybox ----------------",
        msg,
    ], 5, 5)
    time.sleep(3)

def shutdown():
    screenManager.clearAndSleep(epd)
    time.sleep(1)
    os.system("shutdown -h now")

def launchingPleaseWait():
    screenManager.printLines(epd, [
        "---------------- SW Keybox ----------------",
        "Launching... Please wait...",
    ], 5, 5)

def showMessage(text: str):
    screenManager.printLines(epd, [
        "---------------- SW Keybox ----------------",
        text,
    ], 5, 5)