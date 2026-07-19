# Changelog

All notable changes to this integration are documented here.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
and the format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.5.2] - 2026-07-12

Adds support for the **OilClear AI Water Fountain (PS-120)**, polled through the
Tuya Cloud.

### Added
- **OilClear AI Water Fountain (PS-120)** as a new device type, polled via the
  Tuya Cloud API. Unlike the other devices it is power-managed and drops its LAN
  listener between syncs, so local polling can't reach it. Setup asks for your
  Tuya IoT project's Access ID, Access Secret, and data-centre region instead of
  an IP address and local key.
- Entities: water weight (g), water temperature (°C), battery (%), filter days
  remaining, water consumed today (ml/oz), charge status (diagnostic), a heating
  switch, reset-filter and calibrate-weight buttons, and a work-mode select
  (normal/intelligent).
- Options dialog to choose the volume unit (millilitres or fluid ounces) for the
  water-consumed sensor.
- Command confirmation: a value you set is held and re-applied on every poll
  until the device reports it, or until a 5-minute timeout elapses. This stops
  the UI snapping back while the device catches up.

### Fixed
- Read the device shadow (`/v2.0/cloud/thing/{id}/shadow/properties`) and issue
  commands to `.../shadow/properties/issue`. The legacy `iot-03/devices`
  endpoints return nothing for this device, which left every entity empty.
- Correct the OilClear work modes to `normal`/`intelligent` (they are not the
  PS-010 fountain's `normal`/`night`).
- Read the indicator light from its own data point rather than the battery
  charge status.
- Entities removed in earlier versions (power, indicator light, reset pump, pump
  time, drinks today, filter reminder) are now deleted from the entity registry
  instead of lingering under Controls.

### Notes
- There is a **delay between changing a control and it taking effect**, because
  the device only applies queued cloud commands when it next wakes.
