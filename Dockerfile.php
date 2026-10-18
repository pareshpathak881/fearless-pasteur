# Project Atlas: CodeIgniter 3 Apache Frontend Dockerfile
FROM php:7.4-apache

# Install mysqli, pdo, curl extensions for CI3
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcurl4-openssl-dev \
    && docker-php-ext-install mysqli pdo pdo_mysql curl \
    && a2enmod rewrite \
    && rm -rf /var/lib/apt/lists/*

# Copy frontend-ci3 codebase into webroot
COPY frontend-ci3/ /var/www/html/

# Set file permissions
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 755 /var/www/html

EXPOSE 80

CMD ["apache2-foreground"]
