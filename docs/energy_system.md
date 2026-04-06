# Energy-Based Scheduling System

## Tổng quan

Energy quyết định **số lần mutate** cho mỗi candidate. Score cao → mutate nhiều lần → khám phá sâu hơn.

```
PHP (thu thập raw data) → per-request JSON → Python (tính energy in-memory) → mutation loop
```

## Luồng dữ liệu

```
┌─────────────────────────────────────────────────────────────────┐
│ WordPress Container (PHP)                                       │
│                                                                 │
│  Request đến → uopz_hook_v2.php theo dõi callbacks              │
│             → shutdown: ghi per-request JSON                    │
│               (chỉ raw data, KHÔNG tính energy, KHÔNG merge)   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ per-request JSON file
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Python Fuzzer                                                   │
│                                                                 │
│  Đọc per-request JSON → EnergyCalculator.process_request()      │
│                        → trả về score (int >= 1)                │
│                        → for i in range(score): mutate(...)     │
└─────────────────────────────────────────────────────────────────┘
```

## Công thức tính Energy

### Input

Từ per-request JSON, lấy `hook_coverage.executed_callbacks` — danh sách callbacks đã thực thi trong request đó.

### Tier classification

Mỗi callback được phân loại dựa trên **số lần đã thấy trước đó** (historical count):

| Historical Count | Tier | Weight mặc định | Ý nghĩa |
|-----------------|------|-----------------|----------|
| = 0 | `first_seen` | 12 | Callback chưa bao giờ chạy → rất quý |
| 1 → 3 | `rare` | 5 | Callback hiếm khi chạy → vẫn đáng khám phá |
| > 3 | `frequent` | 1 | Callback chạy thường xuyên → ít giá trị mới |

### Bonuses

| Bonus | Giá trị mặc định | Điều kiện |
|-------|-------------------|-----------|
| `blindspot_bonus` | +8 | Callback đã register nhưng chưa bao giờ executed |
| `new_hook_bonus` | +10 | Hook name chưa từng xuất hiện trong lịch sử |

### Công thức

```
energy = 0

for mỗi callback đã executed trong request:
    energy += tier_weight(callback)

    if callback là blindspot:
        energy += blindspot_bonus

    if hook_name chưa từng thấy:
        energy += new_hook_bonus

score = clamp(energy, min=1, max=max_energy)
```

### Ví dụ

Request trigger 3 callbacks:
- `shop_register_endpoints` — đã chạy 5 lần trước → frequent → +1
- `shop_secret_admin_export` — chưa chạy bao giờ + là blindspot → first_seen (12) + blindspot (8) = +20
- `shop_new_feature` — hook mới + chưa chạy → first_seen (12) + new_hook (10) = +22

**Total energy = 1 + 20 + 22 = 43** → fuzzer sẽ mutate candidate này 43 lần.

## Cấu hình qua Environment Variables

| Variable | Mặc định | Mô tả |
|----------|----------|-------|
| `FUZZER_ENERGY_CALLBACK_FIRST` | 12 | Weight cho tier first_seen |
| `FUZZER_ENERGY_CALLBACK_RARE` | 5 | Weight cho tier rare |
| `FUZZER_ENERGY_CALLBACK_FREQUENT` | 1 | Weight cho tier frequent |
| `FUZZER_ENERGY_RARE_CALLBACK_MAX` | 3 | Ngưỡng tối đa để còn là "rare" |
| `FUZZER_ENERGY_BLINDSPOT_BONUS` | 8 | Bonus khi trigger blindspot |
| `FUZZER_ENERGY_NEW_HOOK_BONUS` | 10 | Bonus khi trigger hook mới |
| `FUZZER_ENERGY_MAX` | 200 | Giới hạn trên của energy score |

## Cấu trúc code (energy.py)

```
energy.py
├── EnergyConfig          # Đọc config từ env vars
├── EnergyResult          # Kết quả: score, tier, chi tiết
├── GlobalCoverageState   # Lưu historical data in-memory (thay total_coverage.json)
│   ├── executed_counts   # callback_id → tổng lần executed
│   ├── registered_callbacks
│   ├── seen_hooks
│   ├── blindspot_ids     # = registered - executed
│   ├── save_snapshot()   # Ghi ra file JSON (periodic)
│   └── load_snapshot()   # Đọc lại (warm restart)
├── EnergyCalculator      # Tính energy
│   ├── calculate()       # Tính từ request data (core ~30 dòng)
│   └── process_request() # calculate() + update state
└── EnergyScheduler       # Wrapper cao cấp cho fuzzer loop
    ├── process_new_requests()  # Scan thư mục, tính energy cho files mới
    └── save_state()             # Periodic snapshot
```

## So sánh với PHP cũ (hook_energy.php)

| Hạng mục | PHP cũ | Python mới |
|----------|--------|------------|
| Tính energy ở đâu | Trong PHP shutdown handler | Trong Python fuzzer process |
| Historical state | Đọc/ghi `total_coverage.json` mỗi request | In-memory dict, snapshot periodic |
| File lock | `flock(LOCK_EX)` mỗi request | Không cần |
| File I/O per request | Đọc + ghi file lớn (~14KB+) | Chỉ ghi 1 file nhỏ per-request |
| Tốc độ tính energy | ~5-50ms (file I/O) | ~0.01ms (dict lookup) |
| Blindspot bonus | Không có | Có (+8) |
| New hook bonus | Không có | Có (+10) |
| Max energy clamp | Không có | Có (200) |

## Trạng thái hiện tại phía PHP (uopz_hook_v2.php)

Đã sửa:
1. **Bỏ** `require_once hook_energy.php` — không load module energy PHP nữa
2. **Bỏ** field `energy` trong `$GLOBALS['__uopz_request']` — Python sẽ tính
3. **Bỏ** lời gọi `__uopz_fuzz_calculate_request_energy()` trong `__uopz_update_total_coverage()`
4. **Bỏ** 2 field `last_request_energy` và `last_request_energy_tier` trong metadata của `total_coverage.json`
5. **Giữ nguyên** `hook_coverage` trong per-request export JSON (trước đó bị `unset()`)

**Vẫn giữ tạm:**
- `__uopz_update_total_coverage()` — hàm merge aggregate vào `total_coverage.json` vẫn chạy mỗi request
- Lý do: Python fuzzer loop chưa tồn tại, cần `total_coverage.json` để debug/xem trực tiếp

## Khi nào có Python Fuzzer: những gì có thể bỏ

Khi Python fuzzer loop đã hoạt động và tự quản lý aggregate state (qua `GlobalCoverageState`), có thể loại bỏ phần PHP aggregate để tăng hiệu năng:

### Checklist migration

```
[ ] Python fuzzer loop đã chạy ổn định
[ ] EnergyCalculator.process_request() được gọi cho mỗi request
[ ] GlobalCoverageState.save_snapshot() ghi total_coverage.json periodic
[ ] Xác nhận total_coverage.json từ Python đúng format
```

### Khi checklist hoàn thành, bỏ trong uopz_hook_v2.php:

1. **Bỏ toàn bộ hàm `__uopz_update_total_coverage()`** (~120 dòng)
   - Bao gồm: file lock, json_decode, merge logic, json_encode, atomic write
   - Đây là bottleneck lớn nhất (đọc + ghi file mỗi request)

2. **Bỏ lời gọi trong shutdown handler:**
   ```php
   // BỎ dòng này:
   __uopz_update_total_coverage();
   ```

3. **Giữ nguyên trong shutdown handler:**
   ```php
   // GIỮ — vẫn cần per-request JSON cho Python đọc:
   $requestFile = $requestsDir . '/' . $GLOBALS['__uopz_request']['request_id'] . '.json';
   __uopz_write_json_atomic($requestFile, __uopz_build_request_export());
   ```

4. **Có thể bỏ `fuzzer-core/fuzzing/hook_energy.php`** — không còn ai gọi

### Hiệu quả khi bỏ

| Metric | Hiện tại (giữ PHP aggregate) | Sau khi bỏ |
|--------|------------------------------|------------|
| File I/O per request | Đọc + ghi `total_coverage.json` + ghi per-request | Chỉ ghi per-request |
| File lock | `flock(LOCK_EX)` mỗi request | Không cần |
| JSON encode/decode | Toàn bộ aggregate mỗi request | Không |
| Thời gian shutdown | ~5-50ms (tùy file size) | ~1-2ms |

## Sử dụng trong fuzzer loop (tương lai)

```python
from energy import EnergyCalculator

calc = EnergyCalculator()

# Optional: khôi phục state từ session trước
calc.state.load_snapshot("output/total_coverage.json")

while True:
    # Gửi request fuzz
    response = send_request(candidate)

    # Đọc per-request JSON mà PHP vừa ghi
    request_data = json.load(open(f"requests/{request_id}.json"))

    # Tính energy
    result = calc.process_request(request_data)

    # Dùng energy cho mutation
    for i in range(result.score):
        mutated = mutate(candidate)
        queue.put(mutated)

    # Periodic: ghi snapshot
    if counter % 50 == 0:
        calc.state.save_snapshot("output/total_coverage.json")
```
