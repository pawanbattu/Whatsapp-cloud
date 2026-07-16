#!/bin/bash
set -e

mkdir -p /app/logs
touch /app/logs/access_gunicorn.log /app/logs/error_gunicorn.log /app/logs/application.log /app/logs/celery_worker.log
chmod 664 /app/logs/*.log

echo "Waiting for MySQL..."
until python -c "
import MySQLdb, os, sys
try:
    MySQLdb.connect(host=os.environ.get('DB_HOST','mysql'), user=os.environ.get('DB_USER','root'),
                     passwd=os.environ.get('DB_PASSWORD',''), port=int(os.environ.get('DB_PORT',3306)))
except Exception as e:
    sys.exit(1)
"; do
  sleep 2
done
echo "MySQL is up."

echo "Waiting for RabbitMQ..."
until curl -s -u guest:guest "${CELERY_BROKER_URL_DOCKER:-http://rabbitmq:15672/api/overview}" > /dev/null; do
  sleep 2
done
echo "RabbitMQ is up."

echo "Running database migrations..."
python manage.py migrate

exec "$@"