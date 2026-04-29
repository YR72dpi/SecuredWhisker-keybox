#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import asyncio
import logging
import time
from typing import Optional

import display
import gatt
import agent
from constants import (
    BLUEZ, ADAPTER, GATT_MANAGER, LE_ADV_MANAGER,
    APP_PATH, SERVICE_PATH, CHAR_PATH, ADV_PATH,
    LOCAL_NAME,
)
from dbus_next.aio import MessageBus
from dbus_next.constants import BusType, MessageType
from dbus_next import Message


logging.basicConfig(level=logging.DEBUG)


# ======================
# CONNECTION WATCHER
# ======================

def _device_path_to_mac(device_path: str) -> Optional[str]:
    if not device_path:
        return None
    marker = '/dev_'
    if marker not in device_path:
        return None
    return device_path.split(marker, 1)[1].replace('_', ':')


async def _install_connection_watcher(bus: MessageBus, char=None):
    match_rule = (
        "type='signal',sender='org.bluez',"
        "interface='org.freedesktop.DBus.Properties',"
        "member='PropertiesChanged'"
    )
    await bus.call(Message(
        destination='org.freedesktop.DBus',
        path='/org/freedesktop/DBus',
        interface='org.freedesktop.DBus',
        member='AddMatch',
        signature='s',
        body=[match_rule],
    ))

    def handler(msg: Message):
        try:
            if msg.message_type != MessageType.SIGNAL:
                return
            if msg.interface != 'org.freedesktop.DBus.Properties' or msg.member != 'PropertiesChanged':
                return
            iface_name, changed_props, _invalidated = msg.body
            if iface_name != 'org.bluez.Device1':
                return

            mac = _device_path_to_mac(msg.path)

            if 'Connected' in changed_props:
                if bool(changed_props['Connected'].value):
                    if char is not None:
                        char.connected_mac = mac or ""
                    display.show_connected(mac or "")
                else:
                    if char is not None:
                        char.connected_mac = ""
                    display.show_waiting_screen()

            if 'Bonded' in changed_props:
                if bool(changed_props['Bonded'].value):
                    display.show_key_status()
                    display.show_connected(mac or "")

        except Exception:
            return

    bus.add_message_handler(handler)


# ======================
# BLUETOOTH INIT
# ======================

async def _init_bluetooth():
    os.system("systemctl stop bluetooth")
    os.system("pkill bluetoothd")
    os.system("btmgmt power off")
    os.system("btmgmt bredr off")
    os.system("btmgmt bondable on")
    os.system("btmgmt io-cap 1")  # DisplayYesNo
    os.system("btmgmt le on")
    os.system("btmgmt power on")
    os.system("systemctl start bluetooth")
    os.system("bluetoothctl power on")
    os.system("bluetoothctl discoverable on")
    os.system("bluetoothctl pairable on")


# ======================
# BLE SERVER
# ======================

async def start_ble_server():
    display.launchingPleaseWait()
    await _init_bluetooth()

    print("BLE: bus système…")
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    await agent.register_pairing_agent(bus)

    service  = gatt.Service()
    char     = gatt.Characteristic(SERVICE_PATH, shutdown_cb=display.shutdown)
    await _install_connection_watcher(bus, char)
    char._bus = bus
    adv      = gatt.Advertisement()
    app      = gatt.Application(service, char)

    bus.export(APP_PATH,     app)
    bus.export(SERVICE_PATH, service)
    bus.export(CHAR_PATH,    char)
    bus.export(ADV_PATH,     adv)

    print("BLE: introspection adapter…")
    introspection = await bus.introspect(BLUEZ, ADAPTER)
    obj = bus.get_proxy_object(BLUEZ, ADAPTER, introspection)

    gatt_mgr    = obj.get_interface(GATT_MANAGER)
    adv_manager = obj.get_interface(LE_ADV_MANAGER)

    print("BLE: RegisterApplication…")
    await asyncio.wait_for(gatt_mgr.call_register_application(APP_PATH, {}), timeout=15.0)
    await asyncio.sleep(1)
    print("BLE: RegisterAdvertisement…")
    await asyncio.wait_for(adv_manager.call_register_advertisement(ADV_PATH, {}), timeout=15.0)

    print(f"BLE: prêt ({LOCAL_NAME})")
    display.show_waiting_screen()
    await asyncio.get_running_loop().create_future()


# ======================
# ENTRY POINT
# ======================

async def main():
    display.init_hardware()
    try:
        await start_ble_server()
    finally:
        # S'exécute que ce soit un Ctrl+C (CancelledError) ou une erreur
        display.teardown()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
