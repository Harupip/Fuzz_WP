#!/bin/bash
set -e

# Đợi MySQL container sẵn sàng
RET=1
while [[ RET -ne 0 ]]; do
    echo "=> Đang chờ MySQL service khởi động..."
    sleep 3
    mysql -uroot -prootpass -h mysql -e "status" > /dev/null 2>&1
    RET=$?
done
echo "=> MySQL đã sẵn sàng!"

# Chuẩn hóa quyền ghi cho output trên bind mount Windows.
mkdir -p /var/www/uopz/output/requests
chmod -R 0777 /var/www/uopz/output 2>/dev/null || true
chown -R www-data:www-data /var/www/uopz/output 2>/dev/null || true

# Kiểm tra xem WordPress đã được cài đặt chưa (cần thiết nếu chưa có database schema)
if ! wp core is-installed --path=/var/www/html --allow-root 2>/dev/null; then
    echo "=> Chưa cài đặt WordPress core, đang tiến hành cài đặt..."
    if [ ! -f /var/www/html/wp-includes/version.php ]; then
        wp core download --path=/var/www/html --allow-root
    fi
    if [ ! -f /var/www/html/wp-config.php ]; then
        wp config create --dbname=wordpress --dbuser=wp_user --dbpass=wp_password --dbhost=mysql --path=/var/www/html --allow-root
    fi
    wp core install --url="http://localhost:8088" --title="Fuzzer target" --admin_user=admin --admin_email=admin@localhost.local --admin_password=admin --path=/var/www/html --allow-root
    echo "=> Cài đặt WordPress core hoàn tất!"
fi

# Tắt tự động update
wp plugin auto-updates disable --all --path=/var/www/html --allow-root || true

# Đọc từ biến môi trường TARGET_APP_NAME và cấu hình plugin đó
if [ ! -z "${TARGET_APP_NAME}" ]; then
    echo "=> Đang xử lý plugin mục tiêu: ${TARGET_APP_NAME}"
    
    # Kiểm tra plugin local bằng cách tìm file PHP có header "Plugin Name".
    PLUGIN_DIR="/var/www/html/wp-content/plugins/${TARGET_APP_NAME}"
    PLUGIN_MAIN_FILE=""

    if [ -d "$PLUGIN_DIR" ]; then
        while IFS= read -r -d '' PHP_FILE; do
            if grep -q "Plugin Name:" "$PHP_FILE"; then
                PLUGIN_MAIN_FILE="$PHP_FILE"
                break
            fi
        done < <(find "$PLUGIN_DIR" -maxdepth 2 -type f -name '*.php' -print0)
    fi

    if [ -n "$PLUGIN_MAIN_FILE" ]; then
        PLUGIN_BASENAME="${PLUGIN_MAIN_FILE#/var/www/html/wp-content/plugins/}"
        echo "=> Nhận diện plugin cục bộ tại ${PLUGIN_BASENAME}. Tiến hành kích hoạt..."
        wp plugin activate "${PLUGIN_BASENAME}" --path=/var/www/html --allow-root \
            || wp plugin activate "${TARGET_APP_NAME}" --path=/var/www/html --allow-root \
            || true
    else
        echo "=> Không tìm thấy mã plugin cục bộ hợp lệ trong ${PLUGIN_DIR}, đang tải và cài đặt ${TARGET_APP_NAME} từ internet..."
        wp plugin install "${TARGET_APP_NAME}" --activate --force --path=/var/www/html --allow-root || echo "Cảnh báo: Lỗi cài đặt plugin ${TARGET_APP_NAME} từ WP registry."
    fi
    
fi

echo "=> Khởi tạo Fuzzing environment OK!"

# Gọi Entrypoint mặc định của hình ảnh apache để khởi động web server
exec "$@"
