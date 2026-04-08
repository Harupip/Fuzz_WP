FROM wordpress:6.4-php8.2-apache
COPY target-app/WordPress/ /usr/src/wordpress/

# Cài đặt các công cụ hệ thống cần thiết và tải WP-CLI
RUN apt-get update && apt-get install -y unzip vim less curl wget default-mysql-client && rm -rf /var/lib/apt/lists/* \
    && curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar \
    && chmod +x wp-cli.phar \
    && mv wp-cli.phar /usr/local/bin/wp

COPY entrypoint.sh /usr/local/bin/fuzzer-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/fuzzer-entrypoint.sh \
    && chmod +x /usr/local/bin/fuzzer-entrypoint.sh

# Cài đặt UOPZ qua PECL
RUN pecl install uopz \
    && docker-php-ext-enable uopz

# Bật UOPZ nhưng vẫn giữ semantics exit/die của PHP để REST requests kết thúc đúng chỗ.
RUN echo "uopz.disable=0" >> /usr/local/etc/php/conf.d/docker-php-ext-uopz.ini \
    && echo "uopz.exit=1" >> /usr/local/etc/php/conf.d/docker-php-ext-uopz.ini

# Cài đặt PCOV (Chuẩn bị cho giai đoạn Code Coverage)
RUN pecl install pcov \
    && docker-php-ext-enable pcov

# Cấu hình PCOV cho Fuzzing WordPress
RUN echo "pcov.enabled=0" >> /usr/local/etc/php/conf.d/docker-php-ext-pcov.ini \
    && echo "pcov.directory=/var/www/html" >> /usr/local/etc/php/conf.d/docker-php-ext-pcov.ini

# Tạo thư mục chạy cho Fuzzer
RUN mkdir -p /var/www/uopz/output/requests \
    && chown -R www-data:www-data /var/www/uopz

# Cấu hình auto_prepend_file trỏ tới file cốt lõi của Fuzzer thay vì tệp lẻ
RUN echo "auto_prepend_file = /var/www/uopz/fuzzer-core/bootstrap/auto_prepend.php" \
    >> /usr/local/etc/php/conf.d/zz-fuzzer-prepend.ini
