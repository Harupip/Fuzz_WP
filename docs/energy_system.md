# Energy-Based Scheduling System

Tai lieu nay mo ta he thong energy hien tai trong repo `UOPZ_demo`, doi chieu voi implementation dang active trong:

- `fuzzer-core/bootstrap/auto_prepend.php`
- `fuzzer-core/instrumentation/uopz_hook_runtime.php`
- `fuzzer-core/uopz_hook_v2.php`
- `fuzzer-core/fuzzing/energy/`
- `fuzzer-core/fuzzing/orchestrator/`

## 1. Muc tieu cua energy system

Energy system la lop feedback dung de uu tien request seed/candidate nao nen duoc mutate tiep. Y tuong chinh:

- request nao mo ra callback moi thi duoc score cao hon
- request nao cham vao callback hiem thi van duoc uu tien
- request nao danh trung blindspot da biet thi duoc cong bonus
- request nao mo ra hook moi thi duoc tang priority them

Trong repo nay, energy khong con chi la watcher debug. Hien da co:

- watcher de quan sat artifact va state
- scheduler de score request artifact
- fuzz loop v1 cho `shop-demo` de dung score trong candidate scheduling

## 2. Kien truc tong the

Flow active hien tai:

```text
HTTP request
  -> PHP auto_prepend bootstrap
  -> UOPZ runtime hook instrumentation
  -> per-request JSON trong output/requests/
  -> Python EnergyScheduler doc artifact moi
  -> EnergyCalculator tinh score dua tren aggregate state hien co
  -> scheduler enrich artifact neu dang chay qua orchestrator
  -> GlobalCoverageState cap nhat snapshot rieng
  -> output/energy_state.json + output/energy_state.json.processed_ids.json
```

Khi chay qua `cli_fuzz.py`, flow con them:

```text
campaign seed
  -> candidate queue
  -> HTTP execution
  -> wait for request artifact
  -> energy feedback
  -> spawn mutations
  -> output/fuzz_summary.json
```

## 3. Vai tro cua PHP runtime

### 3.1 Bootstrap

Docker image cau hinh:

```ini
auto_prepend_file = /var/www/uopz/fuzzer-core/bootstrap/auto_prepend.php
```

Bootstrap hien tai:

1. Doc `FUZZER_ENABLE_UOPZ` va `FUZZER_ENABLE_PCOV`
2. Neu bat UOPZ thi load `instrumentation/uopz_hook_runtime.php`
3. Dong bo MU plugin bootstrap vao `wp-content/mu-plugins/`
4. Neu bat PCOV thi load them exporter cho line coverage

### 3.2 Runtime instrumentation

`fuzzer-core/instrumentation/uopz_hook_runtime.php` chi la compatibility entry va `require_once` vao:

- `fuzzer-core/uopz_hook_v2.php`

File `uopz_hook_v2.php` la noi:

- theo doi registration cua `add_action` / `add_filter`
- theo doi unregister qua `remove_action` / `remove_filter` / `remove_all_*`
- theo doi callback dispatch qua `WP_Hook::apply_filters`, `WP_Hook::do_action`, `WP_Hook::do_all_hook`
- theo doi invocation thuc te qua `call_user_func` va `call_user_func_array`
- xuat per-request JSON va merge aggregate coverage

### 3.3 Target filtering

Target duoc quyet dinh boi:

```ini
TARGET_APP_PATH=/wp-content/plugins/shop-demo/
```

Runtime uu tien:

- reflection de tim file goc cua callback
- cache ket qua origin
- chi danh dau callback la target neu file callback nam trong `TARGET_APP_PATH`

## 4. Dinh dang du lieu dau vao cho energy

Energy layer doc cac file JSON trong:

- `output/requests/`

Moi request hop le tao 1 file schema `uopz-request-v3`.

### 4.1 Truong thong tin trong per-request JSON

Mot request artifact hien tai chua:

- `schema_version`
- `request_id`
- `timestamp`
- `http_method`
- `http_target`
- `endpoint`
- `input_signature`
- `request_params`
- `errors`
- `response`
- `hook_coverage`
- `hook_coverage_summary`
- `executed_callback_ids`
- `new_callback_ids`
- `rare_callback_ids`
- `frequent_callback_ids`
- `blindspot_callback_ids`
- `new_hook_names`
- `coverage_delta`
- `score`

Neu artifact da duoc Python scheduler enrich, no con co:

- `energy_feedback`

### 4.2 Hook coverage Python dang doc

Khac voi phien ban cu, artifact hien giu full:

- `hook_coverage.registered_callbacks`
- `hook_coverage.executed_callbacks`
- `hook_coverage.blindspot_callbacks`

Nghia la Python khong con bi gioi han boi payload executed-toi-thieu nhu truoc do.

### 4.3 Callback identity trong artifact

Moi callback entry hien co the chua:

- `callback_id`
- `callback_runtime_id`
- `stable_id`
- `runtime_id`
- `hook_name`
- `callback_repr`
- `source_file`
- `source_line`
- `priority`
- `accepted_args`
- `executed_count`

Trong do:

- `callback_id` van la key lich su chinh ma energy dang dung
- `stable_id` va `runtime_id` duoc export de giam mo ho doi voi closure/object instance

## 5. Cau truc Python energy package

```text
fuzzer-core/fuzzing/
|-- cli_fuzz.py
|-- energy.py
|-- campaigns/
|   `-- shop_demo_v1.json
|-- energy/
|   |-- calculator.py
|   |-- cli_watch.py
|   |-- config.py
|   |-- models.py
|   |-- request_store.py
|   |-- scheduler.py
|   `-- state.py
`-- orchestrator/
    |-- campaign.py
    |-- models.py
    |-- mutator.py
    `-- runner.py
```

## 6. Vai tro cua tung module energy

### 6.1 `config.py`

`EnergyConfig` dinh nghia cac he so score va doc env vars:

- `callback_first_seen`
- `callback_rare`
- `callback_frequent`
- `rare_max_count`
- `blindspot_bonus`
- `new_hook_bonus`
- `coverage_delta_weight`
- `max_energy`

Luu y:

- `coverage_delta_weight` da co trong config nhung hien chua duoc dung trong cong thuc score

### 6.2 `models.py`

`EnergyResult` la object tra ve sau khi tinh score cho 1 request, gom:

- `request_id`
- `endpoint`
- `score`
- `coverage_delta`
- `dominant_tier`
- `first_seen_count`
- `rare_count`
- `frequent_count`
- `blindspot_hits`
- `new_hooks_discovered`
- `executed_callback_ids`
- `new_callback_ids`
- `rare_callback_ids`
- `frequent_callback_ids`
- `blindspot_callback_ids`
- `new_hook_names`
- `components`

### 6.3 `state.py`

`GlobalCoverageState` la aggregate state in-memory cua Python. No giu:

- `executed_counts`
- `registered_callbacks`
- `executed_callbacks`
- `seen_hooks`
- `total_requests`
- `start_time`

Snapshot cua state duoc ghi ra `output/energy_state.json` voi schema `uopz-energy-state-v2`.

Ngoai state snapshot, scheduler con persist:

- `output/energy_state.json.processed_ids.json`

de tranh reprocess request cu sau khi restart.

### 6.4 `calculator.py`

`EnergyCalculator` tinh score cho 1 request.

No co hai buoc logic:

1. `calculate(request_data)`
2. `state.update_from_request(request_data)`

Thu tu nay rat quan trong, vi score cua request hien tai luon duoc tinh dua tren lich su truoc khi request do duoc merge vao state.

### 6.5 `scheduler.py`

`EnergyScheduler` la lop dieu phoi:

- doc request files moi
- bo qua request da co trong `processed_ids`
- goi `EnergyCalculator`
- dinh ky save snapshot
- co the enrich lai request artifact

Hai mode quan trong:

- `enrich_request_files=False`
  Dung cho `cli_watch.py`, phu hop debug/watch

- `enrich_request_files=True`
  Mac dinh khi orchestrator dung scheduler, de ghi feedback vao chinh request file

### 6.6 `request_store.py`

Module nay cung cap:

- `read_request_file(filepath)`
- `write_request_file(filepath, payload)`
- `find_new_request_files(requests_dir, processed_ids)`

## 7. Cong thuc scoring hien tai

### 7.1 Tier classification

Moi callback executed trong request duoc xep tier theo historical execution count trong aggregate state:

| Historical count | Tier | Y nghia |
|---|---|---|
| `0` | `first_seen` | callback nay chua tung execute trong lich su Python state |
| `1..rare_max_count` | `rare` | callback da xuat hien, nhung van hiem |
| `> rare_max_count` | `frequent` | callback quen thuoc |

Mac dinh `rare_max_count = 3`.

### 7.2 Weight mac dinh

| Tier | Default weight |
|---|---|
| `first_seen` | `12` |
| `rare` | `5` |
| `frequent` | `1` |

### 7.3 Bonus

| Bonus | Default | Dieu kien |
|---|---|---|
| `blindspot_bonus` | `8` | callback dang la blindspot trong state cu |
| `new_hook_bonus` | `10` | `hook_name` chua tung xuat hien trong `seen_hooks` |

### 7.4 Cong thuc tong quat

Cong thuc thuc te trong `EnergyCalculator.calculate()` la:

```text
total_energy = 0

for moi executed callback:
  tier = classify(historical_count)
  total_energy += tier_weight(tier)

  neu callback dang la blindspot trong state cu:
    total_energy += blindspot_bonus

  neu hook_name la moi trong request nay va chua tung thay truoc do:
    total_energy += new_hook_bonus

score = clamp(total_energy, min=1, max=max_energy)
coverage_delta = so callback moi trong request hien tai
```

Neu request khong co callback nao execute, score cuoi cung van la `1`.

## 8. Thu tu update state va y nghia cua no

Mot nuance rat quan trong:

- `calculate()` chay truoc
- `update_from_request()` chay sau

Vi vay:

- callback vua execute lan dau trong request hien tai se duoc tinh la `first_seen`
- hook vua gap lan dau trong request hien tai se an `new_hook_bonus`
- request hien tai khong tu lam giam gia tri cua chinh no

Day la hanh vi dung cho scheduling, vi ta muon score phan anh "gia tri moi" ma request vua mo ra.

## 9. Phan biet `total_coverage.json` va `energy_state.json`

### 9.1 `output/total_coverage.json`

File nay do PHP runtime merge tren moi request. Schema hien tai la `uopz-total-coverage-v3`.

Day la source aggregate coverage phu hop de xem:

- tong callback da register
- callback nao da execute
- callback nao dang la blindspot
- coverage percent tong quan cua target app

### 9.2 `output/energy_state.json`

File nay do Python watcher hoac orchestrator ghi.

No la snapshot state rieng cua `GlobalCoverageState`, dung cho:

- phuc hoi aggregate state sau khi restart
- giu thong ke Python da tich luy
- track `seen_hooks`

### 9.3 `output/energy_state.json.processed_ids.json`

File nay ghi `request_id` da duoc xu ly. Day la thay doi quan trong cua hom nay vi no giam tinh trang restart watcher roi process lai artifact cu.

## 10. Energy da duoc noi vao fuzz loop den dau

Repo hien da co mot fuzz loop v1 cho `shop-demo`:

- load campaign
- tao candidate seed
- gui HTTP request
- doi artifact moi
- score bang `EnergyScheduler`
- gan feedback vao candidate
- spawn mutation moi
- dung khi dat `max_requests` hoac `stagnation_limit`

No chua phai production loop day du, nhung da vuot qua muc "watcher debug only".

## 11. Command dung de chay

### 11.1 Watcher debug

```bash
python fuzzer-core/fuzzing/energy/cli_watch.py
```

### 11.2 Fuzz loop v1

```bash
python fuzzer-core/fuzzing/cli_fuzz.py --reset-output --max-requests 40 --stagnation-limit 10
```

## 12. Bien moi truong co the tuning

Energy layer doc cac env var sau:

| Variable | Default | Mo ta |
|---|---|---|
| `FUZZER_ENERGY_CALLBACK_FIRST` | `12` | weight cho callback `first_seen` |
| `FUZZER_ENERGY_CALLBACK_RARE` | `5` | weight cho callback `rare` |
| `FUZZER_ENERGY_CALLBACK_FREQUENT` | `1` | weight cho callback `frequent` |
| `FUZZER_ENERGY_RARE_CALLBACK_MAX` | `3` | nguong callback van con duoc xem la rare |
| `FUZZER_ENERGY_BLINDSPOT_BONUS` | `8` | bonus khi cham vao blindspot |
| `FUZZER_ENERGY_NEW_HOOK_BONUS` | `10` | bonus khi hook name la moi |
| `FUZZER_ENERGY_COVERAGE_DELTA_WEIGHT` | `2.0` | da co trong config, hien chua duoc dung |
| `FUZZER_ENERGY_MAX` | `200` | tran tren cua score |

## 13. Gioi han va rui ro hien tai

- Fuzz loop moi o muc v1, single-node
- `coverage_delta_weight` chua active trong cong thuc score
- Van can verify them edge case runtime cho closure/object instance
- Van chua co benchmark overhead ro rang
- `callback_id` van la key lich su chinh; `stable_id` va `runtime_id` dang duoc export de tiep tuc kiem chung

## 14. Tom tat ngan

Energy system hien tai duoc hieu tot nhat nhu sau:

- PHP la ben quan sat WordPress hooks va xuat artifact day du
- Python la ben tinh score, giu aggregate state rieng, va co the enrich artifact
- `total_coverage.json` la aggregate coverage cua runtime PHP
- `energy_state.json` la aggregate state cua Python scheduler
- `energy_state.json.processed_ids.json` giup restart an toan hon
- `cli_watch.py` la watcher debug
- `cli_fuzz.py` la fuzz loop v1 cho `shop-demo`
