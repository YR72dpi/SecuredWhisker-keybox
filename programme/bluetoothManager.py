import sys
import os
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
    
import asyncio
import json
from typing import Callable, Optional
import dataManager
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, dbus_property
from dbus_next.constants import PropertyAccess, BusType, MessageType
from dbus_next import Message
from dbus_next import Variant

import logging

BLUEZ = 'org.bluez'
ADAPTER = '/org/bluez/hci0'
GATT_MANAGER = 'org.bluez.GattManager1'
LE_ADV_MANAGER = 'org.bluez.LEAdvertisingManager1'
AGENT_MANAGER = 'org.bluez.AgentManager1'

APP_PATH = '/com/example'
SERVICE_PATH = f'{APP_PATH}/service0'
CHAR_PATH = f'{SERVICE_PATH}/char0'
ADV_PATH = f'{APP_PATH}/advertisement0'
AGENT_PATH = f'{APP_PATH}/agent0'
LOCAL_NAME = 'SW-Keybox'
SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0'
CHAR_UUID = '12345678-1234-5678-1234-56789abcdef1'

# ======================
# PROTOCOLE BLE
# ======================
# ReadValue : retourne toujours {"initialized", "iv", "public", "private"}
#
# WriteValue — écriture (JSON brut) :
#   {"iv": "...", "public": "...", "private": "..."}  → écriture des secrets (seulement si initialized == false)

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

    @method()
    def ReadValue(self, options: 'a{sv}') -> 'ay':
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
            # return
        
        payload = json.loads(self.value.decode('utf-8'))
        logging.debug(payload)

        # write iv, private & public keys
        if 'action' in payload and str(payload.get('action', '')) == "set_iv": 
            print("Write iv:", list(payload.keys()))
            dataManager.set_iv(iv=str(payload.get('set_iv', '')))

        if 'action' in payload and str(payload.get('action', '')) == "set_public": 
            print("Write public:", list(payload.keys()))
            dataManager.set_public(str(payload.get('set_public', '')))
        
        if 'action' in payload and str(payload.get('action', '')) == "set_private": 
            print("Write private:", list(payload.keys()))
            dataManager.set_private(private=str(payload.get('set_private', '')))

        if 'action' in payload and str(payload.get('action', '')) == "set_hash_iv":
            print("Write hash iv:", list(payload.keys()))
            dataManager.set_hash_iv(iv=str(payload.get('set_hash_iv', '')))

        if 'action' in payload and str(payload.get('action', '')) == "set_hash_public":
            print("Write hash public:", list(payload.keys()))
            dataManager.set_hash_public(public=str(payload.get('set_hash_public', '')))

        if 'action' in payload and str(payload.get('action', '')) == "set_hash_private":
            print("Write hash private:", list(payload.keys()))
            dataManager.set_hash_private(private=str(payload.get('set_hash_private', '')))

        # shutdown the pi
        if 'action' in payload and str(payload.get('action', '')) == "shutdown": 
            print("shutdown")
            self.shutdown_cb()

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
        # Les flags encrypt-* forcent un lien chiffré, donc un pairing/bonding côté client.
        return ['read', 'write']
        # return ['read', 'write', 'notify', 'encrypt-read', 'encrypt-write']

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
    def UUID(self) -> 's': # type: ignore[name-defined]  # noqa: F821
        return SERVICE_UUID

    @dbus_property(access=PropertyAccess.READ)
    def Primary(self) -> 'b': # type: ignore[name-defined]  # noqa: F821
        return True

    @dbus_property(access=PropertyAccess.READ)
    def Includes(self) -> 'ao': # type: ignore[name-defined]  # noqa: F821
        return []


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
                    'UUID': Variant('s', self._service.UUID),
                    'Primary': Variant('b', self._service.Primary),
                    'Includes': Variant('ao', self._service.Includes),
                }
            },
            CHAR_PATH: {
                'org.bluez.GattCharacteristic1': {
                    'UUID': Variant('s', self._characteristic.UUID),
                    'Service': Variant('o', self._characteristic.Service),
                    'Flags': Variant('as', self._characteristic.Flags),
                    'Value': Variant('ay', self._characteristic.Value),
                    'Notifying': Variant('b', self._characteristic.Notifying),
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
    def Type(self) -> 's': # type: ignore[name-defined]  # noqa: F821
        return 'peripheral'

    @dbus_property(access=PropertyAccess.READ)
    def ServiceUUIDs(self) -> 'as': # type: ignore[name-defined]  # noqa: F821
        return [SERVICE_UUID]

    @dbus_property(access=PropertyAccess.READ)
    def LocalName(self) -> 's': # type: ignore[name-defined]  # noqa: F821
        return LOCAL_NAME

    @dbus_property(access=PropertyAccess.READ)
    def Includes(self) -> 'as':  # type: ignore[name-defined]  # noqa: F821
        return ['tx-power']

    @method()
    def Release(self):
        print('Advertisement released')


# ======================
# PAIRING AGENT
# ======================

class PairingAgent(ServiceInterface):
    def __init__(self, display_cb: Optional[Callable[[str], None]] = None):
        super().__init__('org.bluez.Agent1')
        self._display_cb = display_cb

    def _display(self, message: str):
        if self._display_cb is not None:
            try:
                self._display_cb(message)
            except Exception:
                pass

    @method()
    def Release(self):
        print('Agent released')

    @method()
    def DisplayPasskey(self, device: 'o', passkey: 'u', entered: 'q'):  # type: ignore[name-defined]  # noqa: F821
        print('DisplayPasskey', device, passkey, entered)
        # Le passkey est généralement un entier (0..999999). On l'affiche sur 6 chiffres.
        self._display(f"Code BLE: {int(passkey):06d}")

    @method()
    def RequestConfirmation(self, device: 'o', passkey: 'u'):  # type: ignore[name-defined]  # noqa: F821
        # Si BlueZ utilise le mode "numeric comparison", accepter automatiquement.
        print('RequestConfirmation', device, passkey)
        try:
            self._display(f"Code BLE: {int(passkey):06d}")
        except Exception:
            pass
        return

    @method()
    def AuthorizeService(self, device: 'o', uuid: 's'):  # type: ignore[name-defined]  # noqa: F821
        print('AuthorizeService', device, uuid)
        return

    @method()
    def Cancel(self):
        print('Agent request cancelled')


async def register_pairing_agent(
    bus: MessageBus,
    capability: str = 'DisplayYesNo',
    display_cb: Optional[Callable[[str], None]] = None,
):
    """Enregistre un agent BlueZ (affichage du code de vérification sur le device).

    capability (BlueZ): 'DisplayOnly' | 'DisplayYesNo' | 'KeyboardOnly' | 'NoInputNoOutput' | 'KeyboardDisplay'
    """
    agent = PairingAgent(display_cb=display_cb)
    bus.export(AGENT_PATH, agent)

    introspection = await bus.introspect(BLUEZ, '/org/bluez')
    obj = bus.get_proxy_object(BLUEZ, '/org/bluez', introspection)
    agent_mgr = obj.get_interface(AGENT_MANAGER)

    print(f"Registering Agent (capability={capability}) at {AGENT_PATH}...")
    await agent_mgr.call_register_agent(AGENT_PATH, capability)
    await agent_mgr.call_request_default_agent(AGENT_PATH)
    print("Pairing Agent ready")


def _device_path_to_mac(device_path: str) -> Optional[str]:
    # /org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX -> XX:XX:XX:XX:XX:XX
    if not device_path:
        return None
    marker = '/dev_'
    if marker not in device_path:
        return None
    tail = device_path.split(marker, 1)[1]
    mac = tail.replace('_', ':')
    return mac


async def _install_connection_watcher(bus: MessageBus, status_cb: Optional[Callable[[str], None]]):
    if status_cb is None:
        return

    # S'abonner aux signaux PropertiesChanged de BlueZ (Device1)
    match_rule = "type='signal',sender='org.bluez',interface='org.freedesktop.DBus.Properties',member='PropertiesChanged'"
    await bus.call(
        Message(
            destination='org.freedesktop.DBus',
            path='/org/freedesktop/DBus',
            interface='org.freedesktop.DBus',
            member='AddMatch',
            signature='s',
            body=[match_rule],
        )
    )

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
                connected = bool(changed_props['Connected'].value)
                if connected:
                    status_cb(f"CONN: connected {mac or ''}".strip())
                else:
                    status_cb(f"CONN: disconnected {mac or ''}".strip())

            # Bonded passe à True une fois le pairing/bonding complètement validé
            if 'Bonded' in changed_props:
                bonded = bool(changed_props['Bonded'].value)
                if bonded:
                    status_cb(f"BONDED: {mac or ''}".strip())
        except Exception:
            # Ne jamais casser la boucle DBus
            return

    bus.add_message_handler(handler)


async def start_ble_server(
    *,
    status_cb: Optional[Callable[[str], None]] = None,
    display_cb: Optional[Callable[[str], None]] = None,
    shutdown_cb: Optional[Callable[[], None]] = None,
):
    """Démarre le serveur BLE (GATT + advertisement) et reste actif.

    - `status_cb`: messages d'étape (utile pour l'écran)
    - `display_cb`: affichage du code de pairing (DisplayPasskey/RequestConfirmation)
    """

    def status(message: str):
        print(message)
        if status_cb is not None:
            try:
                status_cb(message)
            except Exception:
                pass

    await initRaspberryPiBluetooth()
    status("BLE: bus système…")
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    await _install_connection_watcher(bus, status_cb)
    await register_pairing_agent(bus, display_cb=display_cb)

    service = Service()
    char = Characteristic(SERVICE_PATH, shutdown_cb=shutdown_cb)
    adv = Advertisement()
    app = Application(service, char)

    bus.export(APP_PATH, app)
    bus.export(SERVICE_PATH, service)
    bus.export(CHAR_PATH, char)
    bus.export(ADV_PATH, adv)

    status("BLE: introspection adapter…")
    introspection = await bus.introspect(BLUEZ, ADAPTER)
    obj = bus.get_proxy_object(BLUEZ, ADAPTER, introspection)

    gatt = obj.get_interface(GATT_MANAGER)
    adv_manager = obj.get_interface(LE_ADV_MANAGER)

    status("BLE: RegisterApplication…")
    await asyncio.wait_for(gatt.call_register_application(APP_PATH, {}), timeout=15.0)
    await asyncio.sleep(1)
    status("BLE: RegisterAdvertisement…")
    await asyncio.wait_for(adv_manager.call_register_advertisement(ADV_PATH, {}), timeout=15.0)

    status(f"BLE: prêt ({LOCAL_NAME})")
    await asyncio.get_running_loop().create_future()


# ======================
# MAIN
# ======================

async def initRaspberryPiBluetooth ():
    os.system("systemctl stop bluetooth")
    os.system("pkill bluetoothd")
    os.system("btmgmt power off")
    os.system("btmgmt bredr off")

    # Best effort: capacité d'E/S correspondant à DisplayYesNo
    os.system("btmgmt bondable on")
    os.system("btmgmt io-cap 1")  # DisplayYesNo

    os.system("btmgmt le on")
    os.system("btmgmt power on")
    os.system("systemctl start bluetooth")
    os.system("bluetoothctl power on")
    os.system("bluetoothctl discoverable on")
    os.system("bluetoothctl pairable on")

async def main():
    # Important: sur téléphone, le code affiché lors du pairing peut être généré par la procédure BLE.
    # display_cb permet d'afficher le même code côté Raspberry (console / écran).
    await start_ble_server(status_cb=None, display_cb=print)


if __name__ == '__main__':
    asyncio.run(main())
