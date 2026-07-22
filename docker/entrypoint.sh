#!/bin/sh
set -e

mkdir -p /app/data/input /app/data/output

echo "[entrypoint] $(date '+%Y-%m-%d %H:%M:%S %Z'): первичная генерация дашборда"
python dashboard/html_report.py /app/data/input /app/data/output/report.html || true

echo "[entrypoint] запуск cron (расписание: 0 9-18 * * * — каждый час с 9:00 до 18:00)"
cron

# держим контейнер живым и выводим лог cron в stdout (docker logs)
tail -F /var/log/cron.log
