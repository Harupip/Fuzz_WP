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

## 3. Registration monitoring

- [x] Theo doi `add_action`
- [x] Theo doi `add_filter`
- [x] Luu `hook_name`
- [x] Luu `hook_type`
- [x] Luu `priority`
- [x] Luu `accepted_args`
- [x] Luu `callback_repr`
- [ ] Luu `callback_runtime_id`
- [ ] Luu `callback_stable_id`
- [ ] Luu `source_file` / `source_line`
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
- [ ] Theo doi hook `"all"`
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
- [ ] Object method co runtime identity rieng
- [ ] Closure khong collision
- [x] Invokable object parse dung
- [ ] Co tach `runtime_id` vs `stable_id`

## 7. Coverage state

- [x] Co state `registered_only`
- [x] Co state `covered`
- [x] Co state `removed`
- [x] Blindspot = registered_active - covered
- [x] Aggregate khong chi union set tho

## 8. Persistence

- [x] Per-request JSON ghi thanh cong
- [x] Aggregate JSON co the duoc Python layer cap nhat
- [x] Khong con `Permission denied`
- [x] Co lock/atomic write hop ly cho request artifacts
- [ ] File format co version/schema ro rang

## 9. Fuzzer feedback readiness

- [ ] Per-request co `executed_callback_ids`
- [ ] Co `new_callback_ids`
- [ ] Co `rare_callback_ids`
- [ ] Co `new_hook_names`
- [ ] Co `score`
- [x] Aggregate co execution histogram
- [ ] Co map `request_id -> coverage delta`
- [ ] Re-run cung input khong bi bao new sai

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

## 13. Semantic verification

- [x] `add_action` khong bi overwrite thanh `filter`
- [x] `do_action` khong bi export thanh `apply_filters`
- [x] `add_filter` van giu semantic `filter`
