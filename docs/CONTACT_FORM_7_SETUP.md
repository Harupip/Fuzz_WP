# Contact Form 7 setup in UOPZ_demo

This workspace is now preconfigured to mount the sibling repo
`../contact-form-7` into WordPress as the target plugin.

## Active settings

The file `C:\Users\chuda\OneDrive\Desktop\LVTS\UOPZ_demo\.env` now points to:

- `TARGET_APP_NAME=contact-form-7`
- `TARGET_APP_PATH=/wp-content/plugins/contact-form-7/`
- `TARGET_APP_HOST_PATH=../contact-form-7`
- `FUZZER_ENABLE_UOPZ=1`
- `FUZZER_ENABLE_PCOV=1`

## What gets exported

UOPZ hook coverage:

- `C:\Users\chuda\OneDrive\Desktop\LVTS\UOPZ_demo\output\requests\*.json`
- `C:\Users\chuda\OneDrive\Desktop\LVTS\UOPZ_demo\output\total_coverage.json`

PCOV line/file coverage:

- `C:\Users\chuda\OneDrive\Desktop\LVTS\UOPZ_demo\output\pcov\requests\*.json`
- `C:\Users\chuda\OneDrive\Desktop\LVTS\UOPZ_demo\output\pcov_total_coverage.json`

## Run flow

1. From `C:\Users\chuda\OneDrive\Desktop\LVTS\UOPZ_demo`, run `docker compose up -d --build`.
2. Open `http://localhost:8088` and finish the WordPress install if this is the first boot.
3. In wp-admin, activate `Contact Form 7`.
4. Visit pages or submit forms that hit the plugin.
5. Inspect the JSON reports under `output/`.

## Switching to another plugin later

Update only these `.env` values:

- `TARGET_APP_NAME`
- `TARGET_APP_PATH`
- `TARGET_APP_HOST_PATH`

No copy into `target-app/` is required unless you prefer that workflow.
