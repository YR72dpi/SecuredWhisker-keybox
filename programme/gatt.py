import sys
import os
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import asyncio
import json
import struct
import logging

import dataManager
import display
from constants import (
    CHAR_UUID, CHAR_PATH, SERVICE_UUID, SERVICE_PATH,
    CHUNK_SIZE, LOCAL_NAME,
)
from dbus_next.service import ServiceInterface, method, dbus_property
from dbus_next.constants import PropertyAccess, MessageType
from dbus_next import Message, Variant
import display

# ======================
# GATT CHARACTERISTIC
# ======================

class Characteristic(ServiceInterface):
    def __init__(self, service_path: str, shutdown_cb=None):
        super().__init__('org.bluez.GattCharacteristic1')
        self._service_path = service_path
        self.value = b'Hello BLE'
        self.notifying = False
        self.shutdown_cb = shutdown_cb
        self._bus = None
        self._transfer_in_progress = False  # évite les rafraîchissements répétés
        self.connected_mac: str = ""  # MAC de l'appareil connecté

    @method()
    def ReadValue(self, options: 'a{sv}') -> 'ay':  # type: ignore[override, name-defined]  # noqa: F821
        data = json.dumps(dataManager.get_secrets()).encode()
        offset = options.get('offset')
        if offset is not None:
            data = data[offset.value:]
        return data

    @method()
    def WriteValue(self, value: 'ay', options: 'a{sv}'):  # type: ignore[override, name-defined]  # noqa: F821
        self.value = bytes(value)
        if not self.value:
            print("WriteValue: payload vide")

        payload = json.loads(self.value.decode('utf-8'))
        logging.debug(payload)
        action = str(payload.get('action', ''))

        # --- Étapes intermédiaires : pas de mise à jour écran à chaque chunk ---
        if action.startswith("set_") or action.startswith("concat_"):
            _dispatch = {
                "set_iv":           lambda: dataManager.set_iv(payload.get('data', '')),
                "concat_public":    lambda: dataManager.concat_public(payload.get('data', '')),
                "concat_private":   lambda: dataManager.concat_private(payload.get('data', '')),
                "set_hash_iv":      lambda: dataManager.set_hash_iv(payload.get('data', '')),
                "set_hash_public":  lambda: dataManager.set_hash_public(payload.get('data', '')),
                "set_hash_private": lambda: dataManager.set_hash_private(payload.get('data', '')),
            }
            if action in _dispatch:
                print(f"Write [{action}]:", payload.get('data', list(payload.keys())))
                _dispatch[action]()
                if not self._transfer_in_progress:
                    self._transfer_in_progress = True
                    display.show_message("Transfer in progress...")

        # --- Étapes finales : mise à jour écran une seule fois ---
        elif action == "validate":
            print("Validate hash")
            self._transfer_in_progress = False
            if dataManager.verify_iv() and dataManager.verify_private() and dataManager.verify_public():
                dataManager.set_hash_all_corresponding(True)
                display.show_key_status()
                display.show_connected(self.connected_mac)
                self._schedule_notify_all()
            else:
                display.show_message("Validation failed!")

        elif action == "fix":
            print("Fix data")
            self._transfer_in_progress = False
            dataManager.set_initialized(True)
            display.show_key_status()
            display.show_connected(self.connected_mac)
            self._schedule_notify_all()

        elif action == "read":
            print("Read requested via notify")
            display.show_message("Sending data...")
            self._schedule_notify_all()

        elif action == "shutdown":
            print("shutdown")
            display.show_message("Shutdown...")
            if self.shutdown_cb:
                self.shutdown_cb()

        elif action == "reset":
            print("Reset data")
            self._transfer_in_progress = False
            dataManager.reset()
            display.show_waiting_screen()

    def _schedule_notify_all(self):
        if self.notifying and self._bus is not None:
            asyncio.ensure_future(self._notify_all_data())

    async def _notify_all_data(self):
        if not self.notifying or self._bus is None:
            return
        raw = json.dumps(dataManager.get_all_data(), ensure_ascii=False).encode('utf-8')
        chunks = [raw[i:i + CHUNK_SIZE] for i in range(0, len(raw), CHUNK_SIZE)]
        total = len(chunks)
        print(f"Notify: envoi de {len(raw)} octets en {total} chunk(s)")
        for i, chunk in enumerate(chunks):
            if not self.notifying:
                break
            packet = struct.pack('>HH', i, total) + chunk
            print(f"Notify: chunk {i + 1}/{total} ({len(packet)} octets)")
            self._send_notify(packet)
            await asyncio.sleep(0.05)

        print("Notify: transfert terminé")
        display.show_connected(self.connected_mac)

    def _send_notify(self, data: bytes):
        self.value = bytes(data)
        msg = Message(
            message_type=MessageType.SIGNAL,
            path=CHAR_PATH,
            interface='org.freedesktop.DBus.Properties',
            member='PropertiesChanged',
            signature='sa{sv}as',
            body=[
                'org.bluez.GattCharacteristic1',
                {'Value': Variant('ay', bytes(data))},
                [],
            ],
        )
        self._bus.send(msg)

    @method()
    def StartNotify(self):
        self.notifying = True
        print("Notifications enabled")

    @method()
    def StopNotify(self):
        self.notifying = False
        print("Notifications disabled")

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> 's':  # type: ignore[name-defined]  # noqa: F821
        return CHAR_UUID

    @dbus_property(access=PropertyAccess.READ)
    def Service(self) -> 'o':  # type: ignore[name-defined]  # noqa: F821
        return self._service_path

    @dbus_property(access=PropertyAccess.READ)
    def Value(self) -> 'ay':  # type: ignore[name-defined]  # noqa: F821
        return self.value

    @dbus_property(access=PropertyAccess.READ)
    def Notifying(self) -> 'b':  # type: ignore[name-defined]  # noqa: F821
        return self.notifying

    @dbus_property(access=PropertyAccess.READ)
    def Flags(self) -> 'as':  # type: ignore[name-defined]  # noqa: F821
        return ['read', 'write', 'notify']

    @dbus_property(access=PropertyAccess.READ)
    def Descriptors(self) -> 'ao':  # type: ignore[name-defined]  # noqa: F821
        return []


# ======================
# GATT SERVICE
# ======================

class Service(ServiceInterface):
    def __init__(self):
        super().__init__('org.bluez.GattService1')

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> 's':  # type: ignore[name-defined]  # noqa: F821
        return SERVICE_UUID

    @dbus_property(access=PropertyAccess.READ)
    def Primary(self) -> 'b':  # type: ignore[name-defined]  # noqa: F821
        return True

    @dbus_property(access=PropertyAccess.READ)
    def Includes(self) -> 'ao':  # type: ignore[name-defined]  # noqa: F821
        return []


# ======================
# APPLICATION (ObjectManager)
# ======================

class Application(ServiceInterface):
    def __init__(self, service: Service, characteristic: Characteristic):
        super().__init__('org.freedesktop.DBus.ObjectManager')
        self._service = service
        self._characteristic = characteristic

    @method()
    def GetManagedObjects(self) -> 'a{oa{sa{sv}}}':  # type: ignore[name-defined]  # noqa: F821
        return {
            SERVICE_PATH: {
                'org.bluez.GattService1': {
                    'UUID':    Variant('s',  self._service.UUID),
                    'Primary': Variant('b',  self._service.Primary),
                    'Includes': Variant('ao', self._service.Includes),
                }
            },
            CHAR_PATH: {
                'org.bluez.GattCharacteristic1': {
                    'UUID':        Variant('s',  self._characteristic.UUID),
                    'Service':     Variant('o',  self._characteristic.Service),
                    'Flags':       Variant('as', self._characteristic.Flags),
                    'Value':       Variant('ay', self._characteristic.Value),
                    'Notifying':   Variant('b',  self._characteristic.Notifying),
                    'Descriptors': Variant('ao', self._characteristic.Descriptors),
                }
            },
        }


# ======================
# ADVERTISEMENT
# ======================

class Advertisement(ServiceInterface):
    def __init__(self):
        super().__init__('org.bluez.LEAdvertisement1')

    @dbus_property(access=PropertyAccess.READ)
    def Type(self) -> 's':  # type: ignore[name-defined]  # noqa: F821
        return 'peripheral'

    @dbus_property(access=PropertyAccess.READ)
    def ServiceUUIDs(self) -> 'as':  # type: ignore[name-defined]  # noqa: F821
        return [SERVICE_UUID]

    @dbus_property(access=PropertyAccess.READ)
    def LocalName(self) -> 's':  # type: ignore[name-defined]  # noqa: F821
        return LOCAL_NAME

    @dbus_property(access=PropertyAccess.READ)
    def Includes(self) -> 'as':  # type: ignore[name-defined]  # noqa: F821
        return ['tx-power']

    @method()
    def Release(self):
        print('Advertisement released')
