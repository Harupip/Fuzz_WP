# Current State

## Active implementation

- Active bootstrap: `fuzzer-core/bootstrap/auto_prepend.php`
- Active runtime entry: `fuzzer-core/instrumentation/uopz_hook_runtime.php`
- Active UOPZ core: `fuzzer-core/uopz_hook_v2.php`
- Retry install source: `fuzzer-core/bootstrap/uopz_mu_plugin.php`
- Aggregate/energy entry: `fuzzer-core/fuzzing/watch_energy.py`
- Aggregate/energy package: `fuzzer-core/fuzzing/energy/`

## Verified runtime state

- Docker config dang tro `auto_prepend_file` toi `/var/www/uopz/fuzzer-core/bootstrap/auto_prepend.php`
- UOPZ dang duoc enable voi `uopz.disable=0`
- UOPZ phai giu `uopz.exit=1` de REST request ket thuc dung semantics
- MU plugin bootstrap duoc sync vao `wp-content/mu-plugins/fuzzer-uopz-bootstrap.php`
- Current target app trong repo la `shop-demo`
- `contact-form-7` khong con nam trong repo nay
- Per-request JSON export dang hoat dong va giu day du `hook_coverage`
- Action/filter semantics da duoc verify lai sau patch
- Callback ownership da chuyen sang reflection + cache thay vi stack walking tren registration hot path
- Current readiness: `prototype`

## What is already done

- Theo doi registration cho `add_action` va `add_filter`
- Theo doi invocation thuc te qua `WP_Hook` runtime context cung `call_user_func` / `call_user_func_array`
- Request correlation co `request_id`, `endpoint`, `http_method`, va `input_signature`
- Blindspots duoc tinh tu callback dang active nhung chua execute
- Per-request export dung atomic write
- Energy system Python da tach thanh package rieng, co scheduler va state snapshot
- Co watcher de xu ly request artifacts moi va cap nhat aggregate snapshot

## Verified blockers

- Callback identity van chua tach ro `stable_id` va `runtime_id`
- Chua co full fuzzer loop production noi truc tiep vao `EnergyScheduler`
- Van can benchmark overhead va verify them cac edge case nhu closure/object instance
- `install_failures` debug state van co the noisy neu co retry som trong bootstrap

## Six-axis status

- Hook registration monitoring: partial-usable
- Actual callback execution monitoring: partial-usable
- Remove/unregister tracking: partial
- Request correlation: usable per-request
- Persistence/export format: usable per-request, usable aggregate via Python snapshot
- Fuzzer feedback readiness: prototype

## Next 3 priorities

1. Them `stable_id` va `runtime_id`, sau do emit normalized feedback fields nhu `executed_callback_ids`, `new_callback_ids`, `rare_callback_ids`, va `score`.
2. Noi `EnergyScheduler` vao loop fuzzer that de aggregate state va scheduling khong con la utility chay rieng.
3. Re-verify runtime chi voi plugin muc tieu dang bat de coverage phan anh dung audit target.

## Last doc refresh

- Date: `2026-04-08`
- Target plugin from `.env`: `shop-demo`
- Runtime chain: `bootstrap/auto_prepend.php -> instrumentation/uopz_hook_runtime.php -> uopz_hook_v2.php`
- Aggregate path: `fuzzer-core/fuzzing/watch_energy.py` + `fuzzer-core/fuzzing/energy/`
