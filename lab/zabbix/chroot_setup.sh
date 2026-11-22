#!/usr/bin/env bash
# Zabbix lab ortamı (yalnızca Docker Hub ve resmi Zabbix depolarına erişimin olmadığı geçici ortamlar içindir).
# Ubuntu 22.04 (jammy) deposundaki Zabbix 5.0.17'yi bir chroot içinde çalıştırır.
# Ön koşul: /opt/zbx-jammy altında debootstrap ile jammy + zabbix-server-pgsql, zabbix-frontend-php,
#           zabbix-agent, postgresql, php8.1-fpm, nginx kurulu olmalı. Lab parolaları bilerek basittir.
set -euo pipefail
R="${ZBX_CHROOT:-/opt/zbx-jammy}"
DBPASS="zbxlab"
mountpoint -q "$R/proc" || mount -t proc proc "$R/proc"

in_chroot() { chroot "$R" bash -c "$1"; }

# 1) PostgreSQL
in_chroot "pg_ctlcluster 14 main start || true"
sleep 3
if ! in_chroot "su postgres -c \"psql -tAc \\\"select 1 from pg_roles where rolname='zabbix'\\\"\"" | grep -q 1; then
  in_chroot "su postgres -c \"psql -c \\\"create user zabbix password '$DBPASS'\\\"\""
  in_chroot "su postgres -c \"createdb -O zabbix -E Unicode -T template0 zabbix\""
  for f in schema images data; do
    in_chroot "zcat /usr/share/zabbix-server-pgsql/$f.sql.gz | PGPASSWORD=$DBPASS psql -q -h 127.0.0.1 -U zabbix zabbix" >/dev/null
  done
fi

# 2) Zabbix server ve agent
in_chroot "sed -i 's/^# DBHost=.*/DBHost=127.0.0.1/; s/^# DBPassword=.*/DBPassword=$DBPASS/' /etc/zabbix/zabbix_server.conf"
in_chroot "grep -q '^DBHost=' /etc/zabbix/zabbix_server.conf || echo 'DBHost=127.0.0.1' >> /etc/zabbix/zabbix_server.conf"
in_chroot "grep -q '^DBPassword=' /etc/zabbix/zabbix_server.conf || echo 'DBPassword=$DBPASS' >> /etc/zabbix/zabbix_server.conf"
in_chroot "mkdir -p /var/log/zabbix /run/zabbix && chown zabbix:zabbix /var/log/zabbix /run/zabbix"
in_chroot "pgrep zabbix_server >/dev/null || zabbix_server -c /etc/zabbix/zabbix_server.conf"
in_chroot "pgrep zabbix_agentd >/dev/null || zabbix_agentd -c /etc/zabbix/zabbix_agentd.conf"

# 3) Web arayüzü + API (nginx + php-fpm) 127.0.0.1:8081
in_chroot "cat > /etc/zabbix/zabbix.conf.php <<'PHP'
<?php
\$DB['TYPE'] = 'POSTGRESQL'; \$DB['SERVER'] = '127.0.0.1'; \$DB['PORT'] = '0'; \$DB['DATABASE'] = 'zabbix';
\$DB['USER'] = 'zabbix'; \$DB['PASSWORD'] = '$DBPASS'; \$DB['SCHEMA'] = '';
\$DB['ENCRYPTION'] = false; \$DB['KEY_FILE'] = ''; \$DB['CERT_FILE'] = ''; \$DB['CA_FILE'] = '';
\$DB['VERIFY_HOST'] = false; \$DB['CIPHER_LIST'] = '';
\$ZBX_SERVER = '127.0.0.1'; \$ZBX_SERVER_PORT = '10051'; \$ZBX_SERVER_NAME = 'lab';
\$IMAGE_FORMAT_DEFAULT = IMAGE_FORMAT_PNG;
PHP"
in_chroot "cat > /etc/nginx/conf.d/zabbix.conf <<'NGINX'
server {
    listen 127.0.0.1:8081;
    root /usr/share/zabbix;
    index index.php;
    location / { try_files \$uri \$uri/ =404; }
    location ~ \\.php\$ {
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        fastcgi_param PHP_VALUE \"post_max_size=16M\\nmax_execution_time=300\\nmax_input_time=300\\ndate.timezone=UTC\";
    }
}
NGINX"
in_chroot "rm -f /etc/nginx/sites-enabled/default; mkdir -p /run/php; pgrep php-fpm8.1 >/dev/null || php-fpm8.1 -D; pgrep nginx >/dev/null && nginx -s reload || nginx"
echo "Zabbix web/API: http://127.0.0.1:8081  (Admin / zabbix, yalnızca lab)"
