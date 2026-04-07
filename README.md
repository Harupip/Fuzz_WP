# Bo khung fuzzer cho WordPress

Repo nay la moi truong fuzzing cho WordPress, tap trung vao hook coverage bang UOPZ va lop energy scoring viet bang Python. Source of truth hien tai la code trong repo, dac biet:

- `fuzzer-core/bootstrap/auto_prepend.php`
- `fuzzer-core/instrumentation/uopz_hook_runtime.php`
- `fuzzer-core/uopz_hook_v2.php`
- `fuzzer-core/fuzzing/energy/`

Trang thai hien tai: `prototype`

## Kien truc active

- PHP bootstrap som qua `auto_prepend_file`
- `bootstrap/auto_prepend.php` nap runtime UOPZ va dong bo MU plugin bootstrap
- `instrumentation/uopz_hook_runtime.php` la compatibility entry, hien tro den `uopz_hook_v2.php`
- PHP ghi per-request JSON vao `output/requests/`
- Python energy layer doc request artifacts, tinh score, va co the ghi snapshot aggregate ra `output/total_coverage.json`
- PCOV da co scaffold rieng, chua phai feedback channel chinh

## Cau truc thu muc

```text
Fuzz_WP/
|-- .env
|-- docker-compose.yml
|-- Dockerfile
|-- docs/
|   |-- CURRENT_STATE.md
|   |-- HOW_THE_FUZZER_WORKS.md
|   |-- energy_system.md
|   `-- hook-coverage-status.md
|-- fuzzer-core/
|   |-- auto_prepend.php                  # wrapper cu, giu tuong thich
|   |-- uopz_hook_v2.php                  # UOPZ runtime chinh
|   |-- uopz_mu_plugin.php                # wrapper cu, giu tuong thich
|   |-- bootstrap/
|   |   |-- auto_prepend.php
|   |   `-- uopz_mu_plugin.php
|   |-- instrumentation/
|   |   |-- pcov_exporter.php
|   |   `-- uopz_hook_runtime.php
|   `-- fuzzing/
|       |-- energy.py                     # compatibility wrapper
|       |-- watch_energy.py
|       `-- energy/
|           |-- __init__.py
|           |-- calculator.py
|           |-- cli_watch.py
|           |-- config.py
|           |-- models.py
|           |-- request_store.py
|           |-- scheduler.py
|           `-- state.py
|-- output/
|   |-- requests/
|   `-- total_coverage.json
`-- target-app/
    |-- WordPress/
    `-- shop-demo/
```

## Trang thai da verify

- Docker dang tro `auto_prepend_file` toi `fuzzer-core/bootstrap/auto_prepend.php`
- UOPZ runtime active qua chuoi `bootstrap/auto_prepend.php -> instrumentation/uopz_hook_runtime.php -> uopz_hook_v2.php`
- MU plugin bootstrap duoc dong bo tu `fuzzer-core/bootstrap/uopz_mu_plugin.php`
- `uopz.exit=1` la bat buoc de giu semantics `exit()/die()` goc cua PHP trong flow REST
- Per-request JSON giu lai `hook_coverage`
- Action callbacks da duoc verify lai va khong bi sai semantic thanh `filter`
- Ownership cua target callback hien duoc xac dinh bang reflection + cache, khong con quet `debug_backtrace()` tren hot path dang ky hook
- `contact-form-7` khong con nam trong repo nay; target app duoc giu lai la `shop-demo`
- Energy runtime da duoc tach thanh package trong `fuzzer-core/fuzzing/energy/`

## Su dung nhanh

### 1. Cau hinh target

Cap nhat `.env` cho plugin/app muon fuzz:

```ini
TARGET_APP_NAME=shop-demo
TARGET_APP_PATH=/wp-content/plugins/shop-demo/
TARGET_APP_HOST_PATH=./target-app/shop-demo
FUZZER_ENABLE_UOPZ=1
FUZZER_ENABLE_PCOV=0
```

### 2. Khoi dong moi truong

```bash
docker compose up -d --build
```

### 3. Theo doi artifacts

Moi request hop le se tao 1 file trong `output/requests/<request_id>.json`.

Per-request JSON hien co:

- `request_id`, `endpoint`, `http_method`, `input_signature`
- `hook_coverage.registered_callbacks`
- `hook_coverage.executed_callbacks`
- `hook_coverage.blindspot_callbacks`
- response status, response time, va PHP errors neu co

### 4. Chay energy watcher

```bash
python fuzzer-core/fuzzing/watch_energy.py
```

Watcher se quet `output/requests/`, tinh energy score cho cac request moi, va cap nhat `output/total_coverage.json` theo chu ky.

## Gioi han hien tai

- Chua tach ro `stable_id` va `runtime_id` cho callback identity
- Chua co live fuzzer loop day du trong repo; watcher hien tai la utility de demo va debug
- `output/total_coverage.json` duoc Python aggregate layer ghi lai, khong phai moi request PHP deu merge truc tiep
- Internal/core callbacks ma target plugin dang ky se bi loai neu reflection khong tro ve file ben trong `TARGET_APP_PATH`

## Tai lieu lien quan

- `docs/CURRENT_STATE.md`
- `docs/HOW_THE_FUZZER_WORKS.md`
- `docs/energy_system.md`
- `docs/hook-coverage-status.md`
