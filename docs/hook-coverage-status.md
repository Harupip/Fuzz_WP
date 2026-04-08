# Hook-Coverage Status Checklist

Legend:

- `[x]` = verified from current code or recent runtime behavior
- `[ ]` = missing, incorrect, or still needs verification

## 0. Source of truth

- [x] Active bootstrap file da xac dinh ro
- [x] `auto_prepend.php` dang load dung runtime entry
- [x] Runtime entry dang tro dung UOPZ core file
- [x] MU plugin retry install dang tro dung installer
- [x] `.env`, php.ini, va Docker runtime phu hop voi target app hien tai

Note:
Current target trong repo la `shop-demo`. `contact-form-7` khong con nam trong source tree nay.

## 1. Bootstrap and install

- [x] Hook coverage duoc bootstrap truoc WordPress/plugin target
- [ ] UOPZ hooks duoc cai dung 1 lan trong moi request path
- [x] Co guard tranh install lap
- [x] Co log/debug toi thieu de biet install thanh cong

## 2. Request context

- [x] Co `request_id`
- [x] Co `endpoint`
- [x] Co `http_method`
- [x] Co `input_signature`
- [x] Co timestamp bat dau request
- [x] Co `schema_version`

## 3. Registration monitoring

- [x] Theo doi `add_action`
- [x] Theo doi `add_filter`
- [x] Luu `hook_name`
- [x] Luu `hook_type`
- [x] Luu `priority`
- [x] Luu `accepted_args`
- [x] Luu `callback_repr`
- [x] Luu `callback_runtime_id`
- [x] Luu `stable_id`
- [x] Luu `runtime_id`
- [x] Luu `source_file` / `source_line`
- [x] Luu `registered_at`

## 4. Remove / unregister tracking

- [x] Theo doi `remove_action`
- [x] Theo doi `remove_filter`
- [x] Theo doi `remove_all_actions`
- [x] Theo doi `remove_all_filters`
- [x] Callback bi go chuyen state `removed`
- [x] Blindspot khong tinh callback da removed

## 5. Actual execution monitoring

- [x] Khong dung snapshot callbacks de ket luan executed
- [x] Ghi nhan khi callback thuc su duoc invoke
- [x] Theo doi `call_user_func`
- [x] Theo doi `call_user_func_array`
- [x] Theo doi hook `"all"` qua `WP_Hook::do_all_hook`
- [x] Xu ly `do_action_ref_array`
- [x] Xu ly `apply_filters_ref_array`
- [x] Co `executed_count`
- [x] Co `first_seen`
- [x] Co `last_seen`
- [x] Co `fired_hook`
- [ ] Cover them case callback dung truoc `wp_die()/exit/fatal`

## 6. Identity correctness

- [x] String callback parse dung
- [x] Static method parse dung
- [x] Object method co runtime identity rieng
- [x] Closure co runtime identity rieng
- [x] Invokable object parse dung
- [x] Co tach `runtime_id` vs `stable_id`
- [ ] Da verify day du edge case collision trong runtime thuc te

## 7. Coverage state

- [x] Co state `registered_only`
- [x] Co state `covered`
- [x] Co state `removed`
- [x] Blindspot = registered_active - covered
- [x] Aggregate khong chi union set tho
- [x] Aggregate coverage co schema version ro rang

## 8. Persistence

- [x] Per-request JSON ghi thanh cong
- [x] Aggregate JSON do PHP merge duoc
- [x] Python energy snapshot luu duoc
- [x] Python scheduler persist `processed_ids`
- [x] Khong con `Permission denied`
- [x] Co lock/atomic write hop ly cho request artifacts
- [x] File format co version/schema ro rang

## 9. Fuzzer feedback readiness

- [x] Per-request co `executed_callback_ids`
- [x] Co `new_callback_ids`
- [x] Co `rare_callback_ids`
- [x] Co `frequent_callback_ids`
- [x] Co `blindspot_callback_ids`
- [x] Co `new_hook_names`
- [x] Co `coverage_delta`
- [x] Co `score`
- [x] Co `energy_feedback` khi scheduler enrich artifact
- [x] Aggregate co execution histogram
- [x] Co map `request_id -> feedback` trong request artifact duoc enrich
- [x] Re-run cung input khong bi bao new sai neu `processed_ids` duoc giu lai

## 10. Noise filtering / performance

- [x] Chi record target plugin/app code
- [x] `fired_hooks` khong bi noisy
- [x] Ownership filtering da co cache
- [ ] Co benchmark overhead ro rang
- [ ] Request JSON da duoc toi uu kich thuoc

## 11. Runtime verification

- [x] Co test request that trong container
- [x] Co request tao duoc file output
- [x] Co case register-but-not-executed
- [ ] Co case callback bi removed
- [ ] Co case same hook nhieu priority
- [ ] Co case closure/object instance edge cases

## 12. Documentation hygiene

- [x] README mo ta dung runtime active
- [x] Docs mo ta dung chain bootstrap -> runtime -> core
- [x] Co danh sach known limitations
- [x] Co next steps ro rang
- [x] Co tai lieu rieng cho energy layer
- [x] Co tai lieu rieng cho fuzz orchestrator v1

## 13. Semantic verification

- [x] `add_action` khong bi overwrite thanh `filter`
- [x] `do_action` khong bi export thanh `apply_filters`
- [x] `add_filter` van giu semantic `filter`
