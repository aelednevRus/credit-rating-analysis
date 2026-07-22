FROM python:3.12-slim

ENV TZ=Europe/Moscow \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends cron tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Только код методики и представления — реальные данные (data/) в образ
# не попадают, монтируются как volume (см. .dockerignore и docker-compose.yml)
COPY credit_analysis/ credit_analysis/
COPY dashboard/ dashboard/

# Каждый час с 9:00 до 18:00 (по TZ контейнера) перечитать data/input и
# пересобрать статический HTML-дашборд в data/output/report.html.
# cron запускает задачи с минимальным PATH (без /usr/local/bin, где лежит
# python в этом образе) — поэтому PATH задан явно и python вызван по
# полному пути, иначе задача молча падает с "python: not found".
RUN echo "PATH=/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin" > /etc/cron.d/dashboard-cron \
    && echo "0 9-18 * * * cd /app && /usr/local/bin/python dashboard/html_report.py /app/data/input /app/data/output/report.html >> /var/log/cron.log 2>&1" >> /etc/cron.d/dashboard-cron \
    && chmod 0644 /etc/cron.d/dashboard-cron \
    && crontab /etc/cron.d/dashboard-cron \
    && touch /var/log/cron.log

COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
