# Bo khung fuzzer cho WordPress

Repo nay la moi truong fuzzing cho WordPress, tap trung vao hook coverage bang UOPZ va feedback scheduling bang Python. Source of truth hien tai la code trong:

- `fuzzer-core/bootstrap/auto_prepend.php`
- `fuzzer-core/instrumentation/uopz_hook_runtime.php`
- `fuzzer-core/uopz_hook_v2.php`
- `fuzzer-core/fuzzing/energy/`
- `fuzzer-core/fuzzing/orchestrator/`

Trang thai hien tai: `prototype`, nhung da co mot fuzz loop v1 cho `shop-demo`.

## Kien truc active

- PHP bootstrap som qua `auto_prepend_file`
- `bootstrap/auto_prepend.php` nap runtime UOPZ va dong bo MU plugin bootstrap
- `instrumentation/uopz_hook_runtime.php` la compatibility entry, hien tro den `uopz_hook_v2.php`
- PHP ghi per-request JSON vao `output/requests/`
- PHP cung merge aggregate coverage vao `output/total_coverage.json`
- Python energy layer doc request artifacts, tinh score, va ghi snapshot rieng vao `output/energy_state.json`
- Python orchestrator da co the gui request, cho artifact xuat hien, feed qua `EnergyScheduler`, va sinh mutation tiep theo
- PCOV da co scaffold rieng, nhung chua phai feedback channel chinh

## Cau truc thu muc

```text
UOPZ_demo/
|-- .env
|-- docker-compose.yml
|-- Dockerfile
|-- docs/
|   |-- CURRENT_STATE.md
|   |-- FUZZ_PREPARATION_PLAN.md
|   |-- HOW_THE_FUZZER_WORKS.md
|   |-- energy_system.md
|   `-- hook-coverage-status.md
|-- fuzzer-core/
|   |-- bootstrap/
|   |   |-- auto_prepend.php
|   |   `-- uopz_mu_plugin.php
|   |-- instrumentation/
|   |   |-- pcov_exporter.php
|   |   `-- uopz_hook_runtime.php
|   |-- uopz_hook_v2.php
|   `-- fuzzing/
|       |-- campaigns/
|       |   `-- shop_demo_v1.json
|       |-- cli_fuzz.py
|       |-- energy.py
|       |-- energy/
|       |   |-- calculator.py
|       |   |-- cli_watch.py
|       |   |-- config.py
|       |   |-- models.py
|       |   |-- request_store.py
|       |   |-- scheduler.py
|       |   `-- state.py
|       |-- orchestrator/
|       |   |-- campaign.py
|       |   |-- models.py
|       |   |-- mutator.py
|       |   `-- runner.py
|       `-- tests/
|           `-- test_fuzzing.py
|-- output/
|   |-- requests/
|   |-- energy_state.json
|   |-- energy_state.json.processed_ids.json
|   |-- fuzz_summary.json
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
- Per-request JSON hien giu full `hook_coverage` va cac feedback field de Python co the enrich lai artifact
- Callback identity da tach `stable_id`, `runtime_id`, va `callback_runtime_id`
- Moi callback co them `source_file` va `source_line`
- `EnergyScheduler` da persist `processed_ids` ra `output/energy_state.json.processed_ids.json`
- `cli_watch.py` la watcher debug hien tai; no mac dinh khong rewrite request artifact
- `cli_fuzz.py` + `orchestrator/` da noi energy vao mot fuzz loop co ban cho `shop-demo`
- `contact-form-7` khong con nam trong repo nay; target app duoc giu lai la `shop-demo`

## Su dung nhanh

### 1. Cau hinh target

Cap nhat `.env` cho plugin/app muon fuzz:

```ini
TARGET_APP_NAME=shop-demo
TARGET_APP_PATH=/wp-content/plugins/shop-demo/
TARGET_APP_HOST_PATH=./target-app/shop-demo
FUZZER_ENABLE_UOPZ=1
FUZZER_ENABLE_PCOV=0

FUZZER_ENERGY_CALLBACK_FIRST=12
FUZZER_ENERGY_CALLBACK_RARE=5
FUZZER_ENERGY_CALLBACK_FREQUENT=1
FUZZER_ENERGY_RARE_CALLBACK_MAX=3
FUZZER_ENERGY_BLINDSPOT_BONUS=8
FUZZER_ENERGY_NEW_HOOK_BONUS=10
FUZZER_ENERGY_COVERAGE_DELTA_WEIGHT=2.0
FUZZER_ENERGY_MAX=200
```

### 2. Khoi dong moi truong

```bash
docker compose up -d --build
```

### 3. Theo doi artifact va energy

```bash
python fuzzer-core/fuzzing/energy/cli_watch.py
```

Watcher se quet `output/requests/`, tinh energy score cho cac request moi, va ghi snapshot rieng vao `output/energy_state.json`.

### 4. Chay fuzz loop v1 cho `shop-demo`

```bash
python fuzzer-core/fuzzing/cli_fuzz.py --reset-output --max-requests 40 --stagnation-limit 10
```

Lenh nay se:

- load campaign `shop_demo_v1.json`
- gui cac request seed dau tien
- cho artifact moi xuat hien trong `output/requests/`
- goi `EnergyScheduler` de score va enrich artifact
- spawn mutation moi dua tren feedback
- ghi tong ket vao `output/fuzz_summary.json`

## Dinh dang artifact can nho

Per-request JSON hien tai co:

- `schema_version`
- `request_id`, `endpoint`, `http_method`, `input_signature`
- `hook_coverage.registered_callbacks`
- `hook_coverage.executed_callbacks`
- `hook_coverage.blindspot_callbacks`
- `executed_callback_ids`
- `new_callback_ids`
- `rare_callback_ids`
- `frequent_callback_ids`
- `blindspot_callback_ids`
- `new_hook_names`
- `coverage_delta`
- `score`
- `energy_feedback`

Hai file aggregate khac nhau:

- `output/total_coverage.json`: aggregate coverage do PHP merge tren moi request
- `output/energy_state.json`: snapshot state rieng cua Python energy layer

## Gioi han hien tai

- Fuzz loop moi hien o muc v1, single-node, chua co queue phan tan hay multi-worker
- `cli_watch.py` mac dinh khong enrich request artifact, trong khi orchestrator thi co
- `coverage_delta_weight` da co trong config nhung chua duoc dua vao cong thuc score
- Van can verify them cac edge case closure/object instance trong runtime thuc te
- Chua co benchmark overhead ro rang cho runtime UOPZ moi

## Tai lieu lien quan

- `docs/CURRENT_STATE.md`
- `docs/FUZZ_PREPARATION_PLAN.md`
- `docs/HOW_THE_FUZZER_WORKS.md`
- `docs/energy_system.md`
- `docs/hook-coverage-status.md`
