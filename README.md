[![GitHub Release](https://img.shields.io/github/v/release/hypercubian/ha-petsnowy?style=for-the-badge)](https://github.com/hypercubian/ha-petsnowy/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge)](https://hacs.xyz/)
[![License: MIT](https://img.shields.io/github/license/hypercubian/ha-petsnowy?style=for-the-badge)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000?style=for-the-badge)](https://github.com/psf/black)
[![Type checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue?style=for-the-badge)](https://mypy-lang.org/)

# PetSnowy for Home Assistant

Custom [Home Assistant](https://www.home-assistant.io/) integration for local-network control of [PetSnowy](https://www.petsnowy.com/) smart pet devices via the Tuya protocol. No cloud dependency — all communication stays on your LAN.

## Supported Devices

| Device | Model | Entities |
|--------|-------|----------|
| **Snow+ Litterbox** | PS-001 | Cat weight, excretion stats, filter life, status, auto-clean, sleep mode, light, child lock, auto-deodorize, clean delay, manual clean/deodorize/empty, fault alerts |
| **Water Fountain** | PS-010 | Filter days, pump time, power, light, work mode, filter reminder, reset filter/pump |
| **Air Purifier** | — | TVOC, filter days, countdown timer, power, ionizer, mode, fan speed, auto-off, fault alerts |
| **Pet Feeder** | PS-020 | Food status, cover sensor, quick feed |

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Go to **Integrations** > three-dot menu > **Custom repositories**
3. Add `https://github.com/hypercubian/ha-petsnowy` with category **Integration**
4. Search for "PetSnowy" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/petsnowy` directory into your Home Assistant `config/custom_components/` folder
2. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **PetSnowy**
3. Select your device type (Litterbox, Fountain, Purifier, or Feeder)
4. Enter the Tuya credentials for your device:
   - **Device ID** — Tuya device identifier
   - **IP Address** — local network address of the device
   - **Local Key** — Tuya local encryption key
   - **Protocol Version** — auto-filled based on device type (3.3 or 3.4)

The integration validates connectivity before completing setup.

### Obtaining Tuya Credentials

You need the Device ID, IP address, and Local Key for each device. These can be obtained using the [tinytuya](https://github.com/jasonacox/tinytuya) wizard:

```bash
pip install tinytuya
python -m tinytuya wizard
```

Follow the wizard prompts — you'll need a [Tuya IoT Platform](https://iot.tuya.com/) account linked to your PetSnowy app account.

## Entities

### Litterbox (PS-001)

| Platform | Entities |
|----------|----------|
| **Sensor** | Cat weight (g), excretion count today, excretion duration today (s), filter days remaining, status (standby/cleaning/deodorization/sleep) |
| **Binary Sensor** | Top cover fault, drawer fault, drawer full, cat stuck, check fault, cat stayed too long, trouble removal |
| **Switch** | Auto clean, sleep mode, indicator light, child lock, auto deodorize |
| **Button** | Clean, deodorize, empty litter, cancel empty, pause, resume, reset filter, calibrate weight |
| **Number** | Clean delay (2–60 min, step 2) |

### Water Fountain (PS-010)

| Platform | Entities |
|----------|----------|
| **Sensor** | Filter days, pump cleaning days |
| **Switch** | Power, indicator light |
| **Button** | Reset filter, reset pump |
| **Number** | Filter reminder (0–90 days) |
| **Select** | Work mode (normal/night) |

### Air Purifier

| Platform | Entities |
|----------|----------|
| **Sensor** | TVOC (µg/m³), filter days, countdown remaining (min) |
| **Binary Sensor** | Hall sensor fault, toppled over, fan fault, filter missing |
| **Switch** | Power, ionizer |
| **Select** | Mode (auto/sleep), fan speed (1–6), auto-off countdown (off/1h–5h) |

### Pet Feeder (PS-020)

| Platform | Entities |
|----------|----------|
| **Sensor** | Food status (enough/insufficient) |
| **Binary Sensor** | Cover (opening detection) |
| **Button** | Quick feed (1 portion) |

## Technical Details

- **Communication:** Local Tuya protocol via [tinytuya](https://github.com/jasonacox/tinytuya) — no cloud polling
- **Connection:** Persistent TCP with automatic reconnection on errors
- **Polling:** 30-second update interval via `DataUpdateCoordinator`
- **Library:** [petsnowy-py](https://github.com/hypercubian/petsnowy-py) — async Python library for PetSnowy devices

## Contributing

1. Clone the repo
2. Install dependencies: `poetry install`
3. Install pre-commit hooks: `poetry run pre-commit install`
4. Run tests: `poetry run pytest tests/unit/`

## License

[MIT](LICENSE)
