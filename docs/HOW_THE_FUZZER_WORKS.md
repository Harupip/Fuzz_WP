# Fuzzer Hook Engine - Hướng dẫn Cách hoạt động

Tài liệu này giải thích cấu trúc và nguyên lý hoạt động của hệ thống Fuzzer đang được sử dụng, tập trung vào công nghệ **UOPZ Hooking** (Giai đoạn 1) và chuẩn bị cho **PCOV Coverage** (Giai đoạn 2).

## 1. Mục tiêu kiến trúc
Mục tiêu là tạo ra một hệ thống theo dõi **mọi thứ** xảy ra bên trong một ứng dụng / plugin mục tiêu (*Target App*) mà **không cần sửa mã nguồn gốc** của ứng dụng đó.

### Kiến trúc thư mục mới:
*   `fuzzer-core/`: Chứa kịch bản instrumentation (code theo dõi) như UOPZ, PCOV.
*   `target-app/`: Bạn sẽ thả `thư mục code` của các ứng dụng / plugin cần test (ví dụ WooCommerce, Elementor...) vào đây.
*   `output/`: Mọi kết quả phân tích JSON của các Requests, độ phủ Coverage sẽ sinh ra tự động ở đây.
*   `.env`: Nơi bạn cấu hình nhắm mục tiêu (Nhắm vào Plugin tên gì? Bật/Tắt module theo dõi nào?).

## 2. Kích hoạt tự động (Auto-Prepend)
Bí quyết để theo dõi được ứng dụng PHP mà không cần chạm vào code là tính năng `auto_prepend_file` của `php.ini`.

Trong file `Dockerfile`, chúng ta có dòng cấu hình:
```ini
auto_prepend_file = /var/www/uopz/fuzzer-core/auto_prepend.php
```
Điều này buộc PHP engine: **"Trước khi chạy /index.php hay bất cứ script gọi API nào, HÃY CHẠY file `auto_prepend.php` của Fuzzer trước đã"**. Xuyên suốt vòng đời của Server, `auto_prepend.php` đóng vai trò là "Tổng Cổng Giao Giao", kiểm tra trong cấu hình `.env` xem bạn có muốn bật `UOPZ` hay `PCOV` không và tải các file tương ứng.

## 3. Cơ chế hoạt động của UOPZ Hooking (Giai đoạn 1)
File `fuzzer-core/uopz_hooks.php` dùng Extension **UOPZ** (Zend Engine User Operations) để "chiếm quyền điều khiển" (Hijack) các hàm lõi của WordPress (`add_action`, `apply_filters`, etc.).

**Cấu trúc một lần Hook:**
```php
uopz_set_return('apply_filters', function(...$args) {
    // 1. NGĂN CHẶN: Khi một framework gọi apply_filters(), hàm ẩn danh này sẽ chạy thay thế.
    $hook_name = $args[0];

    // 2. GIÁM SÁT: Chỉ ghi nhận (Log) nếu đó là Hook của Plugin Mục Tiêu (.env) 
    if (__is_target_app_code()) {
        Ghi_Nhan_Thoi_Gian_Cho_Request_Hien_Tai();
    }

    // 3. THẢ ĐI: Gọi lại hàm gốc chuẩn của WordPress để app vẫn chạy bình thường (Tránh crash ứng dụng)
    return \apply_filters(...$args);
}, true); // <- `true` báo hiệu cho UOPZ biết là được phép gọi lại hàm gốc (backslash `\`)
```

### Tại sao lại cần UOPZ cho Fuzzing WordPress?
Kiến trúc WordPress quá phụ thuộc vào Hook. Nếu Fuzzer (Bộ tạo dữ liệu mù) tự sinh dữ liệu và gọi API, Fuzzer không thể biết liệu Request đó *đã chạm được vào code nhạy cảm* hay chưa.
*   **Registered Hooks:** Những Hook mà Plugin đã "đăng ký" sẵn (Khai báo tồn tại).
*   **Executed Hooks:** Những Hook mà thực tế đã CHẠY trong vòng đời của Request.
=> **Fuzzer Blindspots (Điểm mù của Fuzzer)**: Chính là phép trừ `Registered - Executed`. Đây là những luồng code nguy hiểm mà Request Fuzzer *chưa với tới được*. Ghi nhận chúng (trong file JSON) giúp thuật toán AI của Fuzzer sinh ra các payload API tinh vi hơn cho các lần chạy tiếp theo.

## 4. Bắt lỗi tự động (Error Handler)
Trong `uopz_hooks.php`, hàm `set_error_handler` được đăng ký:
Bất cứ **Warning**, **Notice**, **Exception**, hay lỗi mãng rỗng (Null Pointer) nào sinh ra trong quá trình chạy sẽ bị Fuzzer "tóm lại" và đính thẳng vào file Report JSON của riêng Request đó. 
=> Fuzzer sẽ dựa vào dấu hiệu *sinh ra lỗi mới / cảnh báo mới* để kết luận Request đó có phải là Bug hay không.

## 5. (Tương lai) Cơ chế của PCOV (Giai đoạn 2)
PCOV nhẹ hơn và chuyên biệt hơn so với Xdebug. Nó hoạt động bằng cách đo lường **Lines of Code (LoC) đã chạy** so với tổng số dòng. PCOV sẽ được kích hoạt tại `auto_prepend.php` và sử dụng hàm `pcov_collect()` trong lúc request đang xử lý (Runtime) và `pcov_clear()` khi request hoàn thành để xuất báo cáo coverage LCOV. PCOV giúp nhận biết Fuzzer có chạm đến 1 nhánh `if` hay `else` bảo mật cụ thể trong Controller hay không.
