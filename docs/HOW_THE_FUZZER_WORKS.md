# Fuzzer Hook Engine - How it works

Tai lieu nay mo ta flow hien tai cua he thong fuzzing, tap trung vao UOPZ runtime hook coverage, energy scoring bang Python, va fuzz orchestrator v1 cho `shop-demo`.

## 1. Muc tieu kien truc

Muc tieu la:

- theo doi callback registration, callback execution, va blindspot trong WordPress target app
- giu request-level artifact du de energy layer va orchestrator ra quyet dinh
- uu tien lai candidate dua tren signal nhu callback moi, hook moi, blindspot, va rare callback

Thanh phan chinh:

- `fuzzer-core/bootstrap/auto_prepend.php`: diem vao som nhat cua PHP
- `fuzzer-core/instrumentation/uopz_hook_runtime.php`: runtime entry giu tuong thich
- `fuzzer-core/uopz_hook_v2.php`: implementation UOPZ chinh
- `fuzzer-core/fuzzing/energy/`: package Python tinh energy va luu aggregate state
- `fuzzer-core/fuzzing/orchestrator/`: campaign loader, mutator, candidate runner, va scheduler loop
- `fuzzer-core/fuzzing/cli_fuzz.py`: CLI chay fuzz session cho `shop-demo`

## 2. Bootstrap som qua auto_prepend_file

Trong `Dockerfile`, PHP duoc cau hinh:

```ini
auto_prepend_file = /var/www/uopz/fuzzer-core/bootstrap/auto_prepend.php
```

Dieu nay dam bao moi request deu di qua bootstrap cua fuzzer truoc khi WordPress xu ly request chinh.

Bootstrap hien tai se:

1. Doc `FUZZER_ENABLE_UOPZ` va `FUZZER_ENABLE_PCOV`
2. Neu UOPZ duoc bat, nap `instrumentation/uopz_hook_runtime.php`
3. Dong bo `bootstrap/uopz_mu_plugin.php` vao `wp-content/mu-plugins/`
4. Neu PCOV duoc bat, nap `instrumentation/pcov_exporter.php`

## 3. UOPZ runtime lam gi

`uopz_hook_v2.php` hook vao cac diem quan trong cua WordPress hook system de ghi nhan:

- callback duoc dang ky qua `add_action` / `add_filter`
- callback bi go qua `remove_action` / `remove_filter` / `remove_all_*`
- callback thuc su duoc chay qua `WP_Hook::apply_filters`, `WP_Hook::do_action`, `WP_Hook::do_all_hook`
- invocation thuc te qua `call_user_func` va `call_user_func_array`
- metadata cua request hien tai nhu `request_id`, `endpoint`, `http_method`, `input_signature`

Runtime moi khong con dua vao `debug_backtrace()` tren hot path dang ky hook de xac dinh callback co thuoc target app hay khong. Thay vao do:

- resolve source tu callback reflection
- cache ket qua ownership
- chi giu callback ma source file nam trong `TARGET_APP_PATH`

## 4. Dinh danh callback hien tai

Moi callback duoc tach identity thanh:

- `stable_id`: identity on dinh theo loai callback va origin
- `runtime_id`: identity co them runtime-specific data cho closure/object instance
- `callback_runtime_id`: identity da duoc scope them theo `hook_name` va `priority`
- `callback_id`: key chinh lich su ma coverage va energy dang dung

Moi entry dang ky/execution hien co them:

- `callback_repr`
- `source_file`
- `source_line`
- `registered_from` hoac `executed_from`

Muc tieu cua cach tach nay la giam collision va de kiem chung edge case tot hon, nhat la voi closure va object method.

## 5. Per-request artifact

Moi request hop le se tao 1 JSON file trong `output/requests/`. Schema hien tai la `uopz-request-v3`.

Artifact nay bao gom:

- `request_id`
- `endpoint`
- `http_method`
- `input_signature`
- `hook_coverage.registered_callbacks`
- `hook_coverage.executed_callbacks`
- `hook_coverage.blindspot_callbacks`
- `hook_coverage_summary`
- `executed_callback_ids`
- `new_callback_ids`
- `rare_callback_ids`
- `frequent_callback_ids`
- `blindspot_callback_ids`
- `new_hook_names`
- `coverage_delta`
- `score`

Luu y:

- PHP tao artifact goc va dat san cac feedback field mac dinh
- Python co the enrich lai chinh artifact voi `energy_feedback` va cac field feedback cap nhat sau khi score xong

## 6. Hai file aggregate khac nhau

He thong hien co 2 lop aggregate tach biet:

- `output/total_coverage.json`
  File do PHP runtime merge tren moi request. Day la source tot nhat de xem tong registered, executed, blindspot, va coverage percent cua target app.

- `output/energy_state.json`
  File do Python energy layer ghi. Day la snapshot state rieng cua scheduler, gom executed histogram, seen hooks, va thong ke request da xu ly.

Ngoai ra con co:

- `output/energy_state.json.processed_ids.json`
  Danh sach `request_id` da duoc scheduler xu ly de watcher/orchestrator restart khong reprocess request cu.

## 7. Energy layer bang Python

`fuzzer-core/fuzzing/energy/` hien chua:

- `calculator.py`: tinh score cho tung request
- `scheduler.py`: xu ly request moi, persist state, va enrich artifact
- `state.py`: aggregate state va snapshot schema `uopz-energy-state-v2`
- `request_store.py`: doc/ghi request artifacts bang atomic write
- `models.py`: `EnergyResult`
- `config.py`: doc env config
- `cli_watch.py`: watcher debug

`EnergyResult` hien giu:

- `request_id`
- `endpoint`
- `score`
- `coverage_delta`
- `executed_callback_ids`
- `new_callback_ids`
- `rare_callback_ids`
- `frequent_callback_ids`
- `blindspot_callback_ids`
- `new_hook_names`

Cong thuc uu tien hien dua tren:

- callback moi
- rare callback
- blindspot callback
- hook moi

`coverage_delta_weight` da co trong config, nhung chua duoc dua vao cong thuc score.

## 8. Watcher debug va orchestrator khac nhau o dau

`cli_watch.py` la utility watcher de theo doi artifact va snapshot state. No tao `EnergyScheduler` voi:

- `snapshot_interval=5`
- `enrich_request_files=False`

Nghia la watcher debug se tinh score va luu snapshot, nhung khong rewrite request artifact.

Nguoc lai, `ShopDemoFuzzer` trong `orchestrator/runner.py` tao `EnergyScheduler` voi che do enrich mac dinh, nen sau moi request artifact co the duoc ghi them:

- `score`
- `coverage_delta`
- `new_callback_ids`
- `rare_callback_ids`
- `frequent_callback_ids`
- `blindspot_callback_ids`
- `new_hook_names`
- `energy_feedback`

## 9. Fuzz orchestrator v1 cho `shop-demo`

`fuzzer-core/fuzzing/cli_fuzz.py` la entry point de chay mot fuzz session co ban.

Flow tong quat:

1. Load campaign `campaigns/shop_demo_v1.json`
2. Tao initial candidate tu 8 request seed cua `shop-demo`
3. Gui request HTTP vao `target_template`
4. Cho artifact moi xuat hien trong `output/requests/`
5. Dua artifact qua `EnergyScheduler.process_request_file()`
6. Gan feedback vao candidate:
   `score`, `coverage_delta`, `new_callback_ids`, `blindspot_callback_ids`, `new_hook_names`
7. Spawn mutation moi qua `ShopDemoMutator`
8. Sap xep lai queue theo priority va tiep tuc cho toi khi dat stop condition
9. Ghi tong ket session vao `output/fuzz_summary.json`

Stop conditions hien co:

- `max_requests`
- `max_iterations_without_new_coverage`

## 10. Testing hien co

`fuzzer-core/fuzzing/tests/test_fuzzing.py` hien cover:

- campaign `shop_demo_v1.json` bao phu du 8 endpoint
- initial candidate generation khop campaign
- `EnergyScheduler` enrich request artifact va persist `processed_ids`

## 11. Gioi han hien tai

- Fuzz loop moi o muc v1, single-node
- Chua co benchmark overhead ro rang cho runtime UOPZ moi
- Van can verify them edge case runtime nhu closure/object instance, callback removed, va same hook nhieu priority
- PCOV da co scaffold, nhung chua duoc noi thanh feedback signal chinh
