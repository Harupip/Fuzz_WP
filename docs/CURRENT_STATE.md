# Current State

## Active implementation

- Active bootstrap: `fuzzer-core/bootstrap/auto_prepend.php`
- Active runtime entry: `fuzzer-core/instrumentation/uopz_hook.php`
- Active UOPZ core: `fuzzer-core/instrumentation/uopz_hook.php`
- Retry install source: `fuzzer-core/bootstrap/uopz_mu_plugin.php`
- Active energy CLI watcher: `fuzzer-core/fuzzing/energy/cli_watch.py`
- Active fuzz entry for `shop-demo`: `fuzzer-core/fuzzing/cli_fuzz.py`
- Aggregate/energy package: `fuzzer-core/fuzzing/energy/`
- Fuzz orchestrator package: `fuzzer-core/fuzzing/orchestrator/`
- Campaign config: `fuzzer-core/fuzzing/campaigns/shop_demo_v1.json`

## Verified runtime state

- Docker config dang tro `auto_prepend_file` toi `/var/www/uopz/fuzzer-core/bootstrap/auto_prepend.php`
- UOPZ dang duoc enable voi `uopz.disable=0`
- UOPZ phai giu `uopz.exit=1` de REST request ket thuc dung semantics
- MU plugin bootstrap duoc sync vao `wp-content/mu-plugins/fuzzer-uopz-bootstrap.php`
- Current target app trong repo la `shop-demo`
- `contact-form-7` khong con nam trong repo nay
- Per-request JSON export dang hoat dong va giu full `hook_coverage`
- Callback identity da tach `stable_id`, `runtime_id`, va `callback_runtime_id`
- Moi callback entry da mang them `source_file` va `source_line`
- Request artifact co san feedback placeholders nhu `score`, `coverage_delta`, `new_callback_ids`
- Python scheduler da persist `processed_ids` de restart khong reprocess request cu
- `cli_watch.py` dang dung `enrich_request_files=False`, nen no phu hop cho watch/debug
- `ShopDemoFuzzer` da noi request execution, energy scoring, va mutation co ban vao mot loop v1
- Current readiness: `prototype-with-basic-loop`

## What is already done

- Theo doi registration cho `add_action` va `add_filter`
- Theo doi unregister qua `remove_action`, `remove_filter`, `remove_all_actions`, `remove_all_filters`
- Theo doi invocation thuc te qua `WP_Hook` runtime context cung `call_user_func` / `call_user_func_array`
- Request correlation co `request_id`, `endpoint`, `http_method`, va `input_signature`
- Blindspots duoc tinh tu callback dang active nhung chua execute
- Per-request export dung atomic write
- Aggregate coverage PHP co schema rieng trong `output/total_coverage.json`
- Energy system Python da tach thanh package rieng, co scheduler, state snapshot, va processed-id persistence
- Request artifact co the duoc enrich lai voi `energy_feedback` sau khi Python process
- Da co campaign, mutator, runner, va summary output cho `shop-demo`
- Da co unittest cover campaign loading va scheduler enrichment

## Verified blockers

- Fuzz loop moi o muc v1, chua co parallel worker hay queue manager ben ngoai
- `coverage_delta_weight` van la reserved knob, chua tham gia cong thuc score
- Van can benchmark overhead va verify them cac edge case nhu closure/object instance
- `cli_watch.py` va orchestrator co hanh vi enrich artifact khac nhau, can giu ro khi debug
- `__pycache__` dang xuat hien trong cac thu muc moi va nen duoc don de tranh noisy git status

## Six-axis status

- Hook registration monitoring: usable
- Actual callback execution monitoring: usable
- Remove/unregister tracking: usable
- Request correlation: usable per-request
- Persistence/export format: usable per-request, usable aggregate, co schema version
- Fuzzer feedback readiness: prototype, da co v1 loop cho `shop-demo`

## Next 3 priorities

1. Chay mot round fuzz thuc te va doi chieu `fuzz_summary.json`, `total_coverage.json`, va request artifacts de verify signal on dinh.
2. Dua them testing/runtime verification cho closure, object instance, same hook nhieu priority, va callback bi remove truoc khi execute.
3. Quy dinh ro che do watcher debug so voi che do orchestrator production-like, nhat la viec co enrich request artifact hay khong.

## Last doc refresh

- Date: `2026-04-09`
- Target plugin from `.env`: `shop-demo`
- Runtime chain: `bootstrap/auto_prepend.php -> instrumentation/uopz_hook.php`
- Active watcher: `fuzzer-core/fuzzing/energy/cli_watch.py`
- Active fuzz entry: `fuzzer-core/fuzzing/cli_fuzz.py`
