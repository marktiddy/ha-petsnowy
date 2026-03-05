# HACS Setup Guide

This guide covers installing and configuring [HACS](https://hacs.xyz/) (Home Assistant Community Store) so you can install PetSnowy and other custom integrations.

## Prerequisites

- Home Assistant OS or Supervised installation
- SSH access to your Home Assistant instance
- A GitHub account

## 1. Install the HACS Add-on

If HACS files are not already present:

1. In Home Assistant, go to **Settings** > **Add-ons** > **Add-on Store**
2. Search for **"Get HACS"** and install it
3. Start the add-on — it copies the HACS files to `/config/custom_components/hacs/`
4. Restart Home Assistant

## 2. Activate the HACS Integration

Having the files installed is not enough — HACS must be activated through the config flow.

### Via the UI

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **HACS**
3. Accept the terms (logs, add-ons, untested, disable)
4. Follow the GitHub device authorization:
   - Go to https://github.com/login/device
   - Enter the code shown in Home Assistant
   - Authorize the HACS GitHub App
5. HACS will appear under your integrations

### Via the API (headless / SSH)

If you have the **Advanced SSH & Web Terminal** add-on with `homeassistant_api: true`, you can activate HACS from the command line:

```bash
# Step 1: Start the config flow
curl -s -X POST \
  -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  -H "Content-Type: application/json" \
  "http://supervisor/core/api/config/config_entries/flow" \
  -d '{"handler":"hacs"}'
```

This returns a `flow_id` and the acceptance form. Accept the terms:

```bash
# Step 2: Accept terms (use the flow_id from step 1)
curl -s -X POST \
  -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  -H "Content-Type: application/json" \
  "http://supervisor/core/api/config/config_entries/flow/<flow_id>" \
  -d '{"acc_logs":true,"acc_addons":true,"acc_untested":true,"acc_disable":true}'
```

This returns a GitHub device code. Authorize at https://github.com/login/device, then complete the flow:

```bash
# Step 3: Complete after GitHub authorization
curl -s -X POST \
  -H "Authorization: Bearer $SUPERVISOR_TOKEN" \
  -H "Content-Type: application/json" \
  "http://supervisor/core/api/config/config_entries/flow/<flow_id>"
```

> **Note:** The basic **Terminal & SSH** add-on (`core_ssh`) does not have HA API access. You must use the **Advanced SSH & Web Terminal** add-on on port 2222 with `homeassistant_api: true`.

## 3. Install PetSnowy via HACS

Once HACS is active:

1. Open HACS in the sidebar
2. Go to **Integrations** > three-dot menu > **Custom repositories**
3. Add `https://github.com/hypercubian/ha-petsnowy` with category **Integration**
4. Search for **PetSnowy** and install
5. Restart Home Assistant

Or use the one-click button in the [README](../README.md).

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "You need the integration HACS to use this redirect" | HACS files present but integration not activated | Complete step 2 above |
| 401 Unauthorized on API calls | Using basic SSH add-on instead of Advanced | SSH to port 2222 with `-o MACs=hmac-sha2-256-etm@openssh.com` |
| GitHub device code expired | Took too long to authorize | Restart from step 1 — a new flow_id and code are generated |
| HACS not in "Add Integration" list | Files not installed or HA not restarted | Complete step 1, then restart HA |
