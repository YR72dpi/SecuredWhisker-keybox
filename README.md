# Secured Whisker KeyBox (SW-KeyBox)

> A hardware key vault for [SecuredWhisker](https://github.com/YR72dpi/SecuredWhisker) — your encryption keys belong to you, not your browser.

SW-KeyBox is a compact, offline hardware security device that keeps your cryptographic keys physically in your hands. Built on a Raspberry Pi Zero 2W and communicating over Bluetooth Low Energy, it acts as a personal hardware key vault for end-to-end encrypted messaging — no cloud, no server middleman, no exposure.

---

## The Problem

Today, encryption keys generated during sign-up are typically stored in plain text inside the browser's **IndexedDB** — readable by any malicious script or anyone with access to your machine.

Transferring keys to a new browser requires routing them through a server, or copying sensitive data via QR codes and clipboard. **If your PC is compromised, your keys are compromised.**

Worse, you may sometimes need to log in from a device you don't own or fully trust.

## The Solution

**SW-KeyBox physically removes your private keys from the browser** and locks them inside a dedicated hardware device that only you possess.

- Your keys are **AES-encrypted** before leaving the browser
- They are **transferred over Bluetooth** directly to the SW-KeyBox
- Decryption happens on **your terms** — unlock via a PIN + a 10-word mnemonic recovery phrase
- Once stored, keys are **deleted from IndexedDB** — they can never be read from the browser again
- When a message needs to be decrypted, the key is fetched **locally via Bluetooth**, never exposed to the network

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

- **Zero-trust browser model** — keys never live in your browser permanently
- **Hardware isolation** — private keys reside only on a physical, air-gapped device you control
- **Bluetooth pairing with PIN** — a secure pairing step ensures only your authorized device can connect
- **AES encryption in transit** — keys are encrypted before leaving the browser, decrypted only on the device
- **Mnemonic recovery system** — a 10-word recovery phrase protects your numeric password as a second factor
- **Low-power e-Paper UI** — always-visible status display with no backlight power draw
- **Self-hosted & open** — no cloud dependency, no subscription, no telemetry

---

## How It Works

1. Install SW-KeyBox on your Raspberry Pi Zero 2W
2. Pair your phone or computer via Bluetooth PIN
3. Set a numeric password (A) to protect your private key
4. Your browser encrypts the private key with A (AES) and sends it to the SW-KeyBox
5. A 10-word mnemonic phrase is generated and shown to you — the phrase encrypts A
6. Confirm the mnemonic, and your key is secured on the device
7. The private key is **deleted from the browser's localStorage**

From that point forward, every decryption request pulls the key directly from the SW-KeyBox over Bluetooth — your keys never touch the internet.

---

## Documentation

- [Technical Documentation & Architecture](TECHNICAL.md) — stack, module breakdown, BLE protocol, data flow
