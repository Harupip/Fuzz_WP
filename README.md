# 🛍️ WordPress Shop Demo + UOPZ Hook Coverage

Dự án mô phỏng luồng gọi API CRUD trong WordPress, kết hợp với **UOPZ instrumentation** để xuất ra báo cáo JSON chi tiết cho từng Request (Input params, Error log, Hook Execution Timeline, ...).

## 🚀 Tính năng nổi bật

- **Shop Demo Plugin**: Plugin mô phỏng bán hàng với đầy đủ 7 đầu API REST (Products & Orders).
- **UOPZ Instrumentation**: Tự động capture toàn bộ các Hook (`add_action`, `add_filter`, `do_action`, `apply_filters`) của WordPress mà plugin mục tiêu sử dụng.
- **Detailed JSON Report**: Xuất báo cáo chi tiết cho mỗi Request bao gồm metadata, input từ query/body/headers, và dòng thời gian thực thi Hook.
- **Interactive Test UI**: Trang giao diện điều khiển mạnh mẽ tại `/?test-shop=1` giúp test API bằng nút bấm trực quan.

## 🛠️ Yêu cầu hệ thống

- Docker & Docker Compose.
- PHP với module `uopz` (Đã được cấu hình sẵn trong Dockerfile).

## ⚙️ Hướng dẫn cài đặt & Chạy

### 1. Khởi động môi trường Docker

```bash
cd docker-env
docker-compose up -d
```

### 2. Cài đặt các file Hook và Plugin vào Container

Sử dụng script Python để giải quyết vấn đề mapping folder trên Windows (OneDrive/Spaces):

```bash
# Trong folder docker-env
python inject_files.py
```

### 3. Cấu hình ban đầu cho WordPress (One-time)

Truy cập `http://localhost:8088` để hoàn tất setup WordPress Wizard. 
Sau đó, chạy lệnh sau để cài đặt WP-CLI và kích hoạt plugin:

```bash
docker exec shop_demo_wp bash -c "curl -sO https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && chmod +x wp-cli.phar && mv wp-cli.phar /usr/local/bin/wp"
docker exec shop_demo_wp bash -c "wp --allow-root --path=/var/www/html plugin activate shop-demo"
```

### 4. Kiểm tra thành quả

- **Giao diện Test API**: [http://localhost:8088/?test-shop=1](http://localhost:8088/?test-shop=1)
- **Log Request**: `docker-env/hook-coverage/requests/*.json`
- **Báo cáo tổng hợp**: `docker-env/hook-coverage/total_coverage.json`

## 📂 Cấu trúc thư mục

```text
UOPZ_demo/
├── uopz_hooks.php          # Core instrumentation dùng UOPZ
├── docker-env/
│   ├── Dockerfile          # Build image với UOPZ & MySQL support
│   ├── docker-compose.yml  # Định nghĩa dịch vụ (WP 6.4 + MySQL 8.0)
│   ├── inject_files.py     # Script helper để copy code vào container
│   ├── hook-coverage/      # Folder chứa báo cáo (được mount vào docker)
│   └── plugins/
│       └── shop-demo/      # Mã nguồn chính của Shop Plugin
└── .gitignore              # Loại bỏ các file log rác
```

## 🧠 Cách thức hoạt động của UOPZ Instrumentation

File `uopz_hooks.php` được load qua `auto_prepend_file` trong PHP, nó ghi đè:
1. `add_filter` / `add_action`: Đánh dấu các hook được khai báo bởi plugin mục tiêu.
2. `apply_filters` / `do_action`: Ghi lại mỗi khi hook đó thực sự được gọi.
3. `register_shutdown_function`: Thu thập thông tin cuối cùng (HTTP code, response time) và ghi file JSON.

---
Phát triển bởi **LVTS Researcher**.
