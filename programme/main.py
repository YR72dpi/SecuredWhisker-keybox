#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
fontdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'font')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
    
from TP_lib import gt1151
from TP_lib import epd2in13_V4
import time
import logging
import traceback
import threading
import asyncio
import queue

import screenManager
import bluetoothManager

logging.basicConfig(level=logging.DEBUG)
flag_t = 1

def pthread_irq():
    print("pthread running")
    while flag_t == 1:
        if(gt.digital_read(gt.INT) == 0):
            GT_Dev.Touch = 1
        else:
            GT_Dev.Touch = 0
        time.sleep(0.01)
    print("thread:exit")

try:
    logging.info("epd2in13_V4 Touch Demo")
    
    epd = epd2in13_V4.EPD()
    gt = gt1151.GT1151()
    GT_Dev = gt1151.GT_Development()
    GT_Old = gt1151.GT_Development()
    
    logging.info("init and Clear")
    
    epd.init(epd.FULL_UPDATE)
    epd.Clear(0xff)
    gt.GT_Init()
    
    t = threading.Thread(target=pthread_irq)
    t.daemon = True
    t.start()

    def show_waiting_screen():
        screenManager.printLines(epd, [
            "---------------- SW Keybox ----------------",
            "Prêt pour apairage",
            "En attente du code…",
            "(pairing BLE)"
            ], 5, 5)

    def show_pairing_code(code: str):
        screenManager.printLines(epd, ["SW-Keybox","Code BLE:",str(code)],5,5)

    def show_connected(mac: str = ""):
        lines = [
            "---------------- SW Keybox ----------------",
            "Appareil connecté",
        ]
        if mac:
            lines.append(mac)
        screenManager.printLines(epd, lines, 5, 5)

    show_waiting_screen()

    ble_queue: "queue.Queue[str]" = queue.Queue()

    def ble_status_cb(msg: str):
        # On n'affiche que les événements de connexion/déconnexion
        if isinstance(msg, str) and msg.startswith("CONN:"):
            ble_queue.put(msg)

    def ble_display_cb(msg: str):
        # msg sera par ex: "Code BLE: 384921"
        if isinstance(msg, str) and msg.startswith("Code BLE:"):
            ble_queue.put(msg)

    def run_ble():
        try:
            asyncio.run(
                bluetoothManager.start_ble_server(
                    status_cb=ble_status_cb,
                    display_cb=ble_display_cb,
                )
            )
        except Exception as e:
            # Ne pas spammer l'écran. On peut au moins réafficher l'écran d'attente.
            print(f"[ERREUR] BLE: {e}")
            show_waiting_screen()
    
    ble_thread = threading.Thread(target=run_ble, daemon=True)
    ble_thread.start()

    # À la fin
    # screenManager.clearAndSleep(epd)

    # Garder le programme actif + afficher les messages BLE
    while True:
        try:
            msg = ble_queue.get(timeout=1.0)
            if isinstance(msg, str) and msg.startswith("Code BLE:"):
                code = msg.split(":", 1)[1].strip() if ":" in msg else msg.strip()
                show_pairing_code(code)
            elif isinstance(msg, str) and msg.startswith("CONN:"):
                parts = msg.split()
                state = parts[1] if len(parts) > 1 else ""
                mac = parts[2] if len(parts) > 2 else ""
                if state == "connected":
                    show_connected(mac)
                elif state == "disconnected":
                    show_waiting_screen()
        except queue.Empty:
            pass
    
except IOError as e:
    logging.info(e)
    
except KeyboardInterrupt:    
    logging.info("ctrl + c:")
    flag_t = 0
    t.join()
    time.sleep(1)
    screenManager.clearAndSleep(epd)
    epd.Dev_exit()
    exit()