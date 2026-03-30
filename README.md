# 🛍️ Bộ Khung Fuzzer Cho WordPress (Sử dụng UOPZ & PCOV)

Dự án này là môi trường kiểm thử bảo mật (Fuzzing) dành cho WordPress. Mục tiêu ở giai đoạn này là sử dụng kỹ thuật **UOPZ Hooking** để theo dõi mọi luồng thực thi bên trong bất kỳ Plugin / Theme nào mà không cần phải chạm vào hoặc sửa đổi mã nguồn gốc của chúng.

Trong tương lai (Giai đoạn 2), dự án sẽ tích hợp thêm **PCOV** để đo lường tỷ lệ bao phủ mã lệnh (Code Coverage).

## 📂 Tổ chức phân mục (Kiến trúc chuẩn bị cho Mở rộng)

Nhằm mục đích dễ dàng tái sử dụng cho nhiều ứng dụng WordPress khác nhau, thư mục được cấu trúc như sau:

```text
UOPZ_demo/
├── .env                    # (QUAN TRỌNG) Nơi bạn cấu hình Tên Plugin và Bật/Tắt module theo dõi
├── docker-compose.yml      # Cấu hình Mount volume và chạy Database + WordPress
├── Dockerfile              # Bản Build chứa sẵn PHP 8.2 + Apache + UOPZ + PCOV
├── docs/                   
│   └── HOW_THE_FUZZER_WORKS.md # Tài liệu nguyên lý hoạt động nội bộ
├── fuzzer-core/            # CHỨA CÁC ĐOẠN CODE THEO DÕI
│   ├── auto_prepend.php    # Điểm xuất phát (Router) của Fuzzer gọi bởi php.ini
│   └── uopz_hooks.php      # Mã nguồn sử dụng thư viện UOPZ để Hook
├── output/                 # KẾT QUẢ ĐƯỢC XUẤT RA Ở ĐÂY
│   ├── requests/           # Files JSON dòng thời gian của từng request API
│   └── total_coverage.json # Tổng kết chung độ nhận diện Hook
└── target-app/             # ỨNG DỤNG BẠN MUỐN TEST (Paste folder code vào đây)
    └── shop-demo/          # (Ví dụ mẫu có sẵn)
```
*Lưu ý: Mọi thư mục như `target-app` hay `fuzzer-core` đều được Mount trực tiếp vào Docker bằng Volume, do đó nếu bạn sửa code ở máy tính (Windows), nó sẽ ăn ngay lập tức vào Docker mà không cần script copy rườm rà.*

---

## ⚙️ Hướng dẫn sử dụng (Nhanh và Đơn giản)

### 1. Chuẩn bị ứng dụng để test
Dán thư mục Plugin WordPress mà bạn muốn đánh giá bảo mật vào trong `target-app/`. 
*(Ví dụ nếu plugin tên là `elementor`, đường dẫn sẽ là `target-app/elementor/`)*

### 2. Cấu hình file `.env`
Mở file `.env` ở thư mục gốc và đổi tên ứng dụng cho khớp:
```ini
TARGET_APP_NAME=tên_thư_mục_plugin_của_bạn
TARGET_APP_PATH=/wp-content/plugins/tên_thư_mục_plugin_của_bạn/
```
*(Nếu là app mẫu có sẵn, bạn giữ nguyên).*

### 3. Chạy hệ thống
Mở terminal ở thư mục gốc của dự án (`UOPZ_demo/`) và gõ:

```bash
# Build hệ thống một lần duy nhất (hoặc khi đổi cấu hình Dockerfile)
docker-compose build

# Khởi động Fuzzer
docker-compose up -d
```

### 4. Thiết lập lần đầu (Chỉ làm 1 lần)
Truy cập `http://localhost:8088` hoàn thành việc cài đặt tài khoản admin WordPress mặc định. Sau đó kích hoạt plugin mục tiêu trực tiếp trong Admin Dashboard.

### 5. Kiểm tra kết quả
Mỗi khi bạn (hoặc công cụ Fuzzer) tương tác với API của máy chủ, một file JSON cực chi tiết sẽ tự động rơi vào thư mục `output/requests/<id>.json`. 
Dữ liệu bao gồm: 
- Params đầu vào.
- Dòng thời gian thứ tự các hàm WordPress Hook được gọi đến.
- Bất cứ lỗi PHP nào sinh ra trong quá trình đó.

---

📖 **Đọc thêm:** Bí kíp công nghệ đằng sau bộ theo dõi này nằm ở file `docs/HOW_THE_FUZZER_WORKS.md`.
