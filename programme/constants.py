# ======================
# BLE / D-Bus CONSTANTS
# ======================

BLUEZ         = 'org.bluez'
ADAPTER       = '/org/bluez/hci0'
GATT_MANAGER  = 'org.bluez.GattManager1'
LE_ADV_MANAGER = 'org.bluez.LEAdvertisingManager1'
AGENT_MANAGER = 'org.bluez.AgentManager1'

APP_PATH      = '/com/example'
SERVICE_PATH  = f'{APP_PATH}/service0'
CHAR_PATH     = f'{SERVICE_PATH}/char0'
ADV_PATH      = f'{APP_PATH}/advertisement0'
AGENT_PATH    = f'{APP_PATH}/agent0'

LOCAL_NAME    = 'SW-Keybox'
CHUNK_SIZE    = 490  # bytes de données utiles par paquet BLE

SERVICE_UUID  = '12345678-1234-5678-1234-56789abcdef0'
CHAR_UUID     = '12345678-1234-5678-1234-56789abcdef1'
