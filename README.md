```
Todo :
    - secure reset of the keybox
    - Get back private key on browser form keybox
```


# Secured Whisker KeyBox (SW-KeyBox)

> A hardware key vault for [SecuredWhisker](https://github.com/YR72dpi/SecuredWhisker) — your RSA private key belongs in your hands, not in your browser.

SW-KeyBox is a compact, offline hardware security device built as a physical companion to **SecuredWhisker**, the self-hosted end-to-end encrypted messaging platform. Built on a Raspberry Pi Zero 2W and communicating over Bluetooth Low Energy, it physically extracts your RSA private key from the browser and locks it inside a device only you possess — no cloud, no server middleman, no exposure.

---

## The Problem

SecuredWhisker uses **RSA + AES hybrid encryption**: a unique RSA keypair is generated for each user at sign-up. The RSA private key is the single point of trust — every message you receive is decrypted with it.

By default, that key lives in your browser's **IndexedDB**. As SecuredWhisker's own documentation warns:

> *"The RSA private key is stored in your browser. If you clean up 'Cookies and site data', this key, which is used to decrypt messages, will be lost."*

Beyond the risk of accidental loss, this also means:
- Any malicious script running in the browser context can read it
- Anyone with physical or remote access to your machine can extract it
- Logging in from an untrusted device immediately exposes your key

**If your browser is compromised, every message you've ever received is compromised.**

## The Solution

**SW-KeyBox physically removes the RSA private key from SecuredWhisker's IndexedDB** and locks it inside a dedicated hardware device that only you carry.

- The RSA private key is **AES-encrypted** client-side before leaving the browser
- It is **transferred over Bluetooth Low Energy** directly to the SW-KeyBox
- Once received, the key is **locked on the device** — it can never be overwritten
- Every decryption request in SecuredWhisker fetches the key **locally via BLE**, never over the network
- The key is **deleted from IndexedDB** after successful transfer — the browser holds nothing

---

## Hardware

| Component | Details |
|---|---|
| **SBC** | Raspberry Pi Zero 2W(H) |
| **OS** | Debian (Raspberry Pi OS Lite) |
| **Display** | [2.13" Touch e-Paper HAT](https://www.waveshare.com/wiki/2.13inch_Touch_e-Paper_HAT_Manual#Python_.28Used_for_Raspberry_Pi.29) (Waveshare) |
| **Connectivity** | Bluetooth 4.2 / BLE (GATT server) |

![SW-KeyBox e-Paper display](image-1.png)

---

## Key Features

- **Removes the browser's key exposure** — SecuredWhisker's RSA private key no longer lives in IndexedDB
- **Hardware isolation** — the private key resides only on a physical device you control
- **Immutable key store** — once initialized, no key material can be overwritten (enforced in firmware)
- **BLE pairing with PIN** — only your explicitly paired device can connect and read key material
- **AES encryption in transit** — the key is encrypted before leaving the browser, decrypted only on the device
- **Low-power e-Paper UI** — always-visible status display with no backlight power draw
- **Self-hosted & open** — no cloud dependency, no subscription, no telemetry

---

## How It Works

1. Install SW-KeyBox on your Raspberry Pi Zero 2W
2. Pair your phone or computer via Bluetooth PIN
3. SecuredWhisker encrypts your RSA private key with AES and transfers it to the SW-KeyBox over BLE
4. The device locks the key store — no further writes are accepted
5. The RSA private key is **deleted from SecuredWhisker's IndexedDB**

From that point forward, every time SecuredWhisker needs to decrypt a message, it fetches the RSA private key directly from the SW-KeyBox over Bluetooth — your key never touches the network.

---

## Documentation

- [Technical Documentation & Architecture](TECHNICAL.md) — stack, module breakdown, BLE protocol, data flow
