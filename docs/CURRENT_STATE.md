# Current State

## Active implementation
- Active file: `fuzzer-core/uopz_hook_v2.php`
- Bootstrap path: `Dockerfile` -> `auto_prepend_file=/var/www/uopz/fuzzer-core/auto_prepend.php` -> `fuzzer-core/auto_prepend.php` -> `fuzzer-core/uopz_hook_v2.php`
- Retry install path: `fuzzer-core/auto_prepend.php` syncs `fuzzer-core/uopz_mu_plugin.php` into `wp-content/mu-plugins/fuzzer-uopz-bootstrap.php`
- Install hook entry: `__uopz_install_wp_hooks()`
- Shutdown/export entry: `register_shutdown_function(...)` in `fuzzer-core/uopz_hook_v2.php`
- Aggregate/energy entry: `fuzzer-core/fuzzing/energy.py`
- Aggregate status: Python module exists, but no production caller was found in this repo

## Verified runtime state
- `auto_prepend_file` is active and points to `/var/www/uopz/fuzzer-core/auto_prepend.php`
- UOPZ is enabled at runtime with `uopz.disable=0`
- MU plugin bootstrap exists in the container and matches the source file by MD5
- Current `.env` target is `shop-demo`, not `contact-form-7`
- Active WordPress plugins currently include both `shop-demo` and `contact-form-7`
- Per-request JSON export is working and now includes full `hook_coverage`
- Action/filter semantics have been re-verified after patch: action callbacks now stay `type=action` and execute with `source=do_action`
- Current readiness: `prototype`

## What is already done
- Registration monitoring exists for `add_action` and `add_filter`
- Actual callback invocation is tracked via `WP_Hook` runtime context plus `call_user_func` / `call_user_func_array`
- Request correlation exists at both request level and callback-entry level through `request_id`, `endpoint`, and `input_signature`
- Blindspots are computed as active registered callbacks minus executed callbacks
- Per-request export uses atomic write and no longer strips `hook_coverage`
- Action/filter alias corruption has been fixed for current runtime artifacts

## Verified blockers
- Callback identity is still too weak for closures and object-method instances; `stable_id` and `runtime_id` are not separated
- `install_failures` remains noisy after successful retry install because early failures are kept in request debug state
- Aggregate state does not keep callback-to-request history or per-request coverage deltas
- No live fuzzer loop in this repo currently consumes `energy.py`

## Six-axis status
- Hook registration monitoring: partial-usable
- Actual callback execution monitoring: partial-usable
- Remove/unregister tracking: partial
- Request correlation: usable per-request
- Persistence/export format: usable per-request, partial aggregate
- Fuzzer feedback readiness: prototype

## Next 3 priorities
1. Add `stable_id` and `runtime_id`, then emit normalized feedback fields such as `executed_callback_ids`, `new_callback_ids`, `rare_callback_ids`, and `score`.
2. Re-run verification with only the intended target plugin active so coverage reflects the real audit target.
3. Wire Python aggregate/energy into a real fuzzer loop so `total_coverage.json` and scheduling feedback are regenerated automatically.

## Last runtime verification
- Date: `2026-04-06`
- Target plugin from `.env`: `shop-demo`
- Also active in WordPress: `contact-form-7`
- Requests used: `GET /?rest_route=/shop/v1/products`, `POST /?rest_route=/shop/v1/products`
- New request files observed: `output/requests/084014_GET_index_a0c0.json`, `output/requests/084014_POST_index_d3d7.json`
- Result: request export works; hook coverage is present; action/filter semantics are correct in current artifacts; aggregate feedback is still not wired into a real fuzzer loop
