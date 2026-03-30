FROM wordpress:6.4-php8.2-apache

# Cài đặt các công cụ hệ thống cần thiết
RUN apt-get update && apt-get install -y unzip vim && rm -rf /var/lib/apt/lists/*

# Cài đặt UOPZ qua PECL
RUN pecl install uopz \
    && docker-php-ext-enable uopz

# Bật UOPZ bằng cách sửa file cấu hình tự tạo của extension
RUN echo "uopz.disable=0" >> /usr/local/etc/php/conf.d/docker-php-ext-uopz.ini

# Cài đặt PCOV (Chuẩn bị cho giai đoạn Code Coverage)
RUN pecl install pcov \
    && docker-php-ext-enable pcov

# Cấu hình PCOV cho Fuzzing WordPress
RUN echo "pcov.enabled=1" >> /usr/local/etc/php/conf.d/docker-php-ext-pcov.ini \
    && echo "pcov.directory=/var/www/html" >> /usr/local/etc/php/conf.d/docker-php-ext-pcov.ini

# Tạo thư mục chạy cho Fuzzer
RUN mkdir -p /var/www/uopz/output/requests \
    && chown -R www-data:www-data /var/www/uopz

# Cấu hình auto_prepend_file trỏ tới file cốt lõi của Fuzzer thay vì tệp lẻ
RUN echo "auto_prepend_file = /var/www/uopz/fuzzer-core/auto_prepend.php" \
    >> /usr/local/etc/php/conf.d/zz-fuzzer-prepend.ini
