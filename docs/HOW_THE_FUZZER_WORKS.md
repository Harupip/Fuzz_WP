# Fuzzer Hook Engine - How it works

Tai lieu nay mo ta flow hien tai cua he thong fuzzing, tap trung vao UOPZ runtime hook coverage va lop energy scoring bang Python.

## 1. Muc tieu kien truc

Muc tieu la theo doi duoc callback registration, callback execution, va cac blindspot trong WordPress target app ma khong sua source code cua plugin muc tieu.

Thanh phan chinh:

- `fuzzer-core/bootstrap/auto_prepend.php`: diem vao som nhat cua PHP
- `fuzzer-core/instrumentation/uopz_hook_runtime.php`: runtime entry giu tuong thich
- `fuzzer-core/uopz_hook_v2.php`: implementation UOPZ chinh
- `fuzzer-core/fuzzing/energy/`: package Python tinh energy va luu aggregate state

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
- callback bi go qua `remove_action` / `remove_filter`
- callback thuc su duoc chay qua `WP_Hook` runtime context
- metadata cua request hien tai nhu `request_id`, `endpoint`, `http_method`, `input_signature`

Output chinh cua PHP side la per-request JSON tai `output/requests/`.

## 4. Tai sao runtime moi nhanh hon

Runtime hien tai khong con dua vao `debug_backtrace()` tren hot path dang ky hook de xac dinh callback co thuoc target app hay khong. Thay vao do:

- resolve source tu callback reflection
- cache ket qua ownership
- chi giu callback ma source file nam trong `TARGET_APP_PATH`

Tradeoff:

- bootstrap nhanh hon khi WordPress dang ky nhieu hook
- giam noise trong hook coverage
- callback internal nhu `__return_true` se khong duoc tinh la callback cua target neu source file nam ngoai target app

## 5. Per-request artifact

Moi request hop le se tao 1 JSON file, thuong bao gom:

- `request_id`
- `endpoint`
- `http_method`
- `input_signature`
- `hook_coverage.executed_callbacks`
- `hook_coverage_summary`
- thong tin response, timing, va PHP errors

Request artifact hien tai khong con export full `hook_coverage`. No chi giu `executed_callbacks` toi thieu cho energy layer:

- `callback_id`
- `hook_name`
- `callback_repr`
- `executed_count`

PHP side van tu merge aggregate coverage vao `output/total_coverage.json`. Python side doc request-level artifact de tinh energy va giu state rieng.

## 6. Energy layer bang Python

`fuzzer-core/fuzzing/watch_energy.py` la utility watcher doc request artifacts moi va goi `EnergyScheduler`.

`fuzzer-core/fuzzing/energy/` chua:

- `calculator.py`: tinh score cho tung request
- `scheduler.py`: xu ly batch request moi
- `state.py`: aggregate state va snapshot
- `request_store.py`: quan ly file request artifacts
- `models.py`: data models cho result/state
- `config.py`: doc env config
- `cli_watch.py`: CLI helper

Watcher doc `output/requests/`, tinh energy score, va ghi state rieng vao `output/energy_state.json`.

`output/total_coverage.json` duoc PHP runtime merge tren moi request va khong con bi Python watcher ghi de.

## 7. PCOV status

PCOV da co scaffold qua `fuzzer-core/instrumentation/pcov_exporter.php`, nhung hien tai chua phai feedback signal chinh. He thong active van la UOPZ hook coverage + Python energy.

## 8. Limitations hien tai

- Chua tach `stable_id` va `runtime_id`
- Chua co branch scoring hoac line coverage feedback tu PCOV
- Chua co live mutation loop noi truc tiep vao `EnergyScheduler`
- Can them runtime verification cho closure/object instance edge cases
