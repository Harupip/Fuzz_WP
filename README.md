# Bo Khung Fuzzer Cho WordPress (UOPZ hook coverage + PCOV scaffold)

Du an nay la moi truong fuzzing cho WordPress. Nguon su that hien tai la code trong repo, dac biet la `fuzzer-core/instrumentation/uopz_hook_runtime.php`, khong phai cac note cu.

Kien truc active hien tai:
- PHP bootstrap som qua `auto_prepend_file`
- UOPZ theo doi callback registration va callback invocation o muc WordPress hook runtime
- PHP chi ghi **per-request JSON**
- Aggregate merge va energy scoring nam o `fuzzer-core/fuzzing/energy/`
- PCOV van la scaffold rieng, chua phai feedback chinh

Trang thai hien tai: `prototype`

## Cau truc thu muc

```text
Fuzz_WP/
|-- .env
|-- docker-compose.yml
|-- Dockerfile
|-- docs/
|   |-- CURRENT_STATE.md
|   |-- HOW_THE_FUZZER_WORKS.md
|   `-- hook-coverage-status.md
|-- fuzzer-core/
|   |-- auto_prepend.php                  # wrapper tuong thich
|   |-- bootstrap/
|   |   |-- auto_prepend.php
|   |   `-- uopz_mu_plugin.php
|   |-- instrumentation/
|   |   |-- pcov_exporter.php
|   |   `-- uopz_hook_runtime.php
|   `-- fuzzing/
|       |-- energy.py                     # compatibility wrapper
|       |-- watch_energy.py
|       |-- energy/
|       |   |-- calculator.py
|       |   |-- config.py
|       |   |-- models.py
|       |   |-- request_store.py
|       |   |-- scheduler.py
|       |   `-- state.py
|-- output/
|   |-- requests/
|   `-- total_coverage.json
`-- target-app/
    |-- WordPress/
    |-- shop-demo/
    `-- contact-form-7/
```

## Current Verified Notes

- Active bootstrap file: `fuzzer-core/bootstrap/auto_prepend.php`
- Active hook implementation: `fuzzer-core/instrumentation/uopz_hook_runtime.php`
- Retry installer: `fuzzer-core/bootstrap/uopz_mu_plugin.php`
- Current `.env` target mac dinh trong repo: `shop-demo`
- Runtime da verify rang `contact-form-7` cung dang active trong WordPress, nhung current target filter van la `shop-demo`
- Runtime UOPZ can `uopz.exit=1` de giu semantics `exit()/die()` goc cua PHP, tranh REST request roi xuong theme render
- Per-request export hien da giu nguyen `hook_coverage`
- Action callbacks da duoc verify lai la giu dung semantic `action` trong artifact moi
- Target callback ownership nay duoc xac dinh bang callback reflection + cache, khong con quet `debug_backtrace()` tren hot path dang ky hook
- Energy package da duoc tach module trong `fuzzer-core/fuzzing/energy/`, con `energy_modules/` chi la lop tuong thich tam thoi

## Su dung nhanh

### 1. Cau hinh target
Sua `.env` cho khop plugin/app muon fuzz:

```ini
TARGET_APP_NAME=shop-demo
TARGET_APP_PATH=/wp-content/plugins/shop-demo/
TARGET_APP_HOST_PATH=./target-app/shop-demo
FUZZER_ENABLE_UOPZ=1
FUZZER_ENABLE_PCOV=0
```

### 2. Khoi dong moi truong

```bash
docker compose up -d
```

### 3. Kiem tra ket qua
Moi request co gia tri phan tich se tao mot file trong `output/requests/<request_id>.json`.

Per-request JSON hien bao gom:
- `request_id`, `endpoint`, `input_signature`
- `hook_coverage.registered_callbacks`
- `hook_coverage.executed_callbacks`
- `hook_coverage.blindspot_callbacks`
- response status, response time, va PHP errors

Luu y:
- PHP side hien **khong** merge aggregate coverage moi request
- `output/total_coverage.json` chi la snapshot aggregate neu Python energy layer chu dong ghi ra
- Target filter uu tien "callback thuoc file nao" hon "add_action/add_filter duoc goi tu dau", de giam overhead nhung van giu coverage tap trung vao code cua app muc tieu
- Neu docs nao mo ta active file la `uopz_hooks.php`, coi do la tai lieu cu

## Known Limitations

- Chua co tach `stable_id` va `runtime_id` cho callback identity
- Chua co normalized fuzzer feedback fields nhu `new_callback_ids`, `rare_callback_ids`, `score`
- Chua co production wiring tu request export sang `EnergyScheduler`
- Internal/core callbacks duoc target plugin dang ky se khong duoc tinh la target callback neu reflection khong tro vao file cua target app
- Neu xoa `output/total_coverage.json`, file nay se khong tu tao lai cho den khi co Python aggregate layer goi `save_state()` / `save_snapshot()`

## Next Steps

1. Them `stable_id` va `runtime_id`
2. Noi `energy.py` vao loop fuzzer that
3. Re-verify runtime voi dung target plugin duy nhat
4. Bo sung script hoac loop aggregate de tao lai `total_coverage.json` tu `output/requests/`

## Tai lieu lien quan

- `docs/CURRENT_STATE.md`
- `docs/hook-coverage-status.md`
- `docs/HOW_THE_FUZZER_WORKS.md`
