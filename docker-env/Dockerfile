FROM wordpress:6.4-php8.2-apache

# Cài đặt dependencies
RUN apt-get update && apt-get install -y unzip && rm -rf /var/lib/apt/lists/*

# Cài UOPZ qua PECL
RUN pecl install uopz \
    && docker-php-ext-enable uopz

# Bật UOPZ (bắt buộc)
RUN echo "uopz.disable=0" >> /usr/local/etc/php/conf.d/docker-php-ext-uopz.ini

# Tạo thư mục instrumentation và log
RUN mkdir -p /var/www/uopz/hook-coverage/requests \
    && chown -R www-data:www-data /var/www/uopz

# Auto-prepend: chạy uopz_hooks.php trước MỌI file PHP
RUN echo "auto_prepend_file = /var/www/uopz/uopz_hooks.php" \
    >> /usr/local/etc/php/conf.d/zz-uopz-prepend.ini
