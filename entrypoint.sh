#!/bin/bash
set -e

wpf() {
    php -d memory_limit=512M /usr/local/bin/wp "$@"
}

# Doi MySQL container san sang
RET=1
while [[ RET -ne 0 ]]; do
    echo "=> Dang cho MySQL service khoi dong..."
    sleep 3
    mysql -uroot -prootpass -h mysql -e "status" > /dev/null 2>&1
    RET=$?
done
echo "=> MySQL da san sang!"

# Chuan hoa quyen ghi cho output tren bind mount Windows.
mkdir -p /var/www/uopz/output/requests
chmod -R 0777 /var/www/uopz/output 2>/dev/null || true
chown -R www-data:www-data /var/www/uopz/output 2>/dev/null || true

# Kiem tra xem WordPress da duoc cai dat chua.
if ! wpf core is-installed --path=/var/www/html --allow-root 2>/dev/null; then
    echo "=> Chua cai dat WordPress core, dang tien hanh cai dat..."
    if [ ! -f /var/www/html/wp-includes/version.php ]; then
        wpf core download --path=/var/www/html --allow-root
    fi
    if [ ! -f /var/www/html/wp-config.php ]; then
        wpf config create --dbname=wordpress --dbuser=wp_user --dbpass=wp_password --dbhost=mysql --path=/var/www/html --allow-root
    fi
    wpf core install --url="http://localhost:8088" --title="Fuzzer target" --admin_user=admin --admin_email=admin@localhost.local --admin_password=admin --path=/var/www/html --allow-root
    echo "=> Cai dat WordPress core hoan tat!"
fi

# Tat tu dong update
wpf plugin auto-updates disable --all --path=/var/www/html --allow-root || true

# Doc tu bien moi truong TARGET_APP_NAME va cau hinh plugin do
if [ ! -z "${TARGET_APP_NAME}" ]; then
    echo "=> Dang xu ly plugin muc tieu: ${TARGET_APP_NAME}"

    # Kiem tra plugin local bang cach tim file PHP co header "Plugin Name:".
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
        echo "=> Nhan dien plugin cuc bo tai ${PLUGIN_BASENAME}. Tien hanh kich hoat..."
        wpf plugin activate "${PLUGIN_BASENAME}" --path=/var/www/html --allow-root \
            || wpf plugin activate "${TARGET_APP_NAME}" --path=/var/www/html --allow-root \
            || true
    else
        echo "=> Khong tim thay ma plugin cuc bo hop le trong ${PLUGIN_DIR}, dang tai va cai dat ${TARGET_APP_NAME} tu internet..."
        wpf plugin install "${TARGET_APP_NAME}" --activate --force --path=/var/www/html --allow-root || echo "Canh bao: Loi cai dat plugin ${TARGET_APP_NAME} tu WP registry."
    fi
fi

echo "=> Khoi tao Fuzzing environment OK!"

# Goi Entrypoint mac dinh cua hinh anh apache de khoi dong web server
exec "$@"
