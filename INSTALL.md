# Installation

## Requirements

- Raspberry Pi Zero 2W with Raspberry Pi OS Lite (64-bit)
- Internet access (for initial package installation)
- SPI and I2C enabled (`sudo raspi-config` → Interface Options)

## Steps

```bash
git clone https://github.com/YR72dpi/SecuredWhisker-keybox.git
cd SecuredWhisker-keybox
sudo chmod +x setup.sh
./setup.sh
```

`setup.sh` performs the following automatically:

1. Installs system dependencies (`git`, `python3-pip`, `python3-pil`, `python3-numpy`, `python3-gpiozero`, `python3-smbus`, `spidev`)
2. Copies `data.example.json` → `data.json` and sets restrictive permissions (`chmod 700`)
3. Installs and enables the systemd service (`sw-keybox.service`) so the BLE GATT server starts at boot

## Managing the service

```bash
sudo systemctl status sw-keybox
sudo systemctl restart sw-keybox
sudo journalctl -u sw-keybox -f   # live logs
```
