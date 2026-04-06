# Hook-Coverage Status Checklist

Legend:
- `[x]` = Verified from current code or runtime
- `[ ]` = Missing, incorrect, or still needs runtime verification

## 0. Source of truth
- [x] Active file da xac dinh ro (`uopz_hook_v2.php` hay file khac)
- [x] `auto_prepend.php` dang load dung file active
- [x] MU plugin retry install dang tro dung installer
- [x] `.env` / php.ini / docker compose dong bo voi target plugin dang test

Note:
Current runtime target is `shop-demo`. `contact-form-7` is also active in WordPress, but it is not the current `TARGET_APP_PATH`.

## 1. Bootstrap & install
- [x] Hook coverage duoc bootstrap som truoc WordPress/plugin target
- [ ] UOPZ hooks duoc cai dung 1 lan
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
- [ ] Khong danh dau executed sai khi callback truoc `wp_die()/exit/fatal`

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
- [ ] Aggregate JSON merge thanh cong
- [x] Khong con `Permission denied`
- [x] Co lock/atomic write hop ly
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
- [ ] Backtrace/filtering co cache
- [ ] Co benchmark overhead
- [ ] Request JSON khong phinh vo ich

## 11. Runtime verification
- [x] Co test request that trong container
- [x] Co request tao duoc file output
- [x] Co case register-but-not-executed
- [ ] Co case callback bi removed
- [ ] Co case same hook nhieu priority
- [ ] Co case closure/object instance edge cases

## 12. Documentation hygiene
- [x] README mo ta dung ban active
- [x] Co so do flow cap nhat
- [x] Co danh sach known limitations
- [x] Co next steps ro rang
- [x] Co test plan ro rang

## 13. Semantic verification
- [x] `add_action` khong con bi overwrite thanh `filter`
- [x] `do_action` khong con bi export thanh `apply_filters`
- [x] `add_filter` van giu semantic `filter`
