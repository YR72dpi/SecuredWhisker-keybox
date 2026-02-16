import sys
import os
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
    
import asyncio
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method, dbus_property
from dbus_next.constants import PropertyAccess, BusType
from dbus_next import Variant

BLUEZ = 'org.bluez'
ADAPTER = '/org/bluez/hci0'
GATT_MANAGER = 'org.bluez.GattManager1'
LE_ADV_MANAGER = 'org.bluez.LEAdvertisingManager1'

APP_PATH = '/com/example'
SERVICE_PATH = f'{APP_PATH}/service0'
CHAR_PATH = f'{SERVICE_PATH}/char0'
ADV_PATH = f'{APP_PATH}/advertisement0'
LOCAL_NAME = 'RaspberryBLE'

SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0'
CHAR_UUID = '12345678-1234-5678-1234-56789abcdef1'


# ======================
# GATT CHARACTERISTIC
# ======================

class Characteristic(ServiceInterface):
    def __init__(self, service_path: str):
        super().__init__('org.bluez.GattCharacteristic1')
        self._service_path = service_path
        self.value = b'Hello BLE'
        self.notifying = False

    @method()
    def ReadValue(self, options: 'a{sv}') -> 'ay':
        print("Read request")
        return self.value

    @method()
    def WriteValue(self, value: 'ay', options: 'a{sv}'):
        self.value = bytes(value)
        print("Write:", self.value)

    @method()
    def StartNotify(self):
        self.notifying = True
        print("Notifications enabled")

    @method()
    def StopNotify(self):
        self.notifying = False
        print("Notifications disabled")

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> 's':
        return CHAR_UUID

    @dbus_property(access=PropertyAccess.READ)
    def Service(self) -> 'o':
        return self._service_path

    @dbus_property(access=PropertyAccess.READ)
    def Value(self) -> 'ay':
        return self.value

    @dbus_property(access=PropertyAccess.READ)
    def Notifying(self) -> 'b':
        return self.notifying

    @dbus_property(access=PropertyAccess.READ)
    def Flags(self) -> 'as':
        return ['read', 'write', 'notify']

    @dbus_property(access=PropertyAccess.READ)
    def Descriptors(self) -> 'ao':
        return []


# ======================
# GATT SERVICE
# ======================

class Service(ServiceInterface):
    def __init__(self):
        super().__init__('org.bluez.GattService1')

    @dbus_property(access=PropertyAccess.READ)
    def UUID(self) -> 's':
        return SERVICE_UUID

    @dbus_property(access=PropertyAccess.READ)
    def Primary(self) -> 'b':
        return True

    @dbus_property(access=PropertyAccess.READ)
    def Includes(self) -> 'ao':
        return []


class Application(ServiceInterface):
    def __init__(self, service: Service, characteristic: Characteristic):
        super().__init__('org.freedesktop.DBus.ObjectManager')
        self._service = service
        self._characteristic = characteristic

    @method()
    def GetManagedObjects(self) -> 'a{oa{sa{sv}}}':
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
    def Type(self) -> 's':
        return 'peripheral'

    @dbus_property(access=PropertyAccess.READ)
    def ServiceUUIDs(self) -> 'as':
        return [SERVICE_UUID]

    @dbus_property(access=PropertyAccess.READ)
    def LocalName(self) -> 's':
        return LOCAL_NAME

    @dbus_property(access=PropertyAccess.READ)
    def Includes(self) -> 'as':
        return ['tx-power']

    @method()
    def Release(self):
        print('Advertisement released')


# ======================
# MAIN
# ======================

async def initRaspberryPiBluetooth ():
    os.system("systemctl stop bluetooth")
    os.system("pkill bluetoothd")
    os.system("btmgmt power off")
    os.system("btmgmt bredr off")

    os.system("btmgmt le on")
    os.system("btmgmt power on")
    os.system("systemctl start bluetooth")
    os.system("bluetoothctl power on")
    os.system("bluetoothctl discoverable on")
    os.system("bluetoothctl pairable on")

async def main():

    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    service = Service()
    char = Characteristic(SERVICE_PATH)
    adv = Advertisement()
    app = Application(service, char)

    bus.export(APP_PATH, app)
    bus.export(SERVICE_PATH, service)
    bus.export(CHAR_PATH, char)
    bus.export(ADV_PATH, adv)

    introspection = await bus.introspect(BLUEZ, ADAPTER)
    obj = bus.get_proxy_object(BLUEZ, ADAPTER, introspection)

    gatt = obj.get_interface(GATT_MANAGER)
    adv_manager = obj.get_interface(LE_ADV_MANAGER)

    print("Registering GATT...")
    await asyncio.wait_for(gatt.call_register_application(APP_PATH, {}), timeout=15.0)
    await asyncio.sleep(1)
    print("Registering Advertisement...")
    await asyncio.wait_for(adv_manager.call_register_advertisement(ADV_PATH, {}), timeout=15.0)

    print(f"BLE Server running. Advertising as '{LOCAL_NAME}'.")
    await asyncio.get_running_loop().create_future()

asyncio.run(main())
