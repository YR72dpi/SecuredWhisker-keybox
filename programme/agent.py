import sys
import os
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

import display
from constants import BLUEZ, AGENT_PATH, AGENT_MANAGER
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method


# ======================
# PAIRING AGENT
# ======================

class PairingAgent(ServiceInterface):
    def __init__(self):
        super().__init__('org.bluez.Agent1')

    @method()
    def Release(self):
        print('Agent released')

    @method()
    def DisplayPasskey(self, device: 'o', passkey: 'u', entered: 'q'):  # type: ignore[name-defined]  # noqa: F821
        print('DisplayPasskey', device, passkey, entered)
        display.show_pairing_code(f"{int(passkey):06d}")

    @method()
    def RequestConfirmation(self, device: 'o', passkey: 'u'):  # type: ignore[name-defined]  # noqa: F821
        print('RequestConfirmation', device, passkey)
        try:
            display.show_pairing_code(f"{int(passkey):06d}")
        except Exception:
            pass

    @method()
    def AuthorizeService(self, device: 'o', uuid: 's'):  # type: ignore[name-defined]  # noqa: F821
        print('AuthorizeService', device, uuid)

    @method()
    def Cancel(self):
        print('Agent request cancelled')


async def register_pairing_agent(bus: MessageBus, capability: str = 'DisplayYesNo'):
    """
    capability (BlueZ): 'DisplayOnly' | 'DisplayYesNo' | 'KeyboardOnly' |
                        'NoInputNoOutput' | 'KeyboardDisplay'
    """
    agent = PairingAgent()
    bus.export(AGENT_PATH, agent)

    introspection = await bus.introspect(BLUEZ, '/org/bluez')
    obj = bus.get_proxy_object(BLUEZ, '/org/bluez', introspection)
    agent_mgr = obj.get_interface(AGENT_MANAGER)

    print(f"Registering Agent (capability={capability}) at {AGENT_PATH}...")
    await agent_mgr.call_register_agent(AGENT_PATH, capability)
    await agent_mgr.call_request_default_agent(AGENT_PATH)
    print("Pairing Agent ready")
