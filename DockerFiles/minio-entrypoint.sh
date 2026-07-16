#!/bin/sh
set -e

minio server /data --console-address ":9001" &

echo "Waiting for MinIO to start..."
until mc ready local; do
  sleep 1
done
echo "MinIO is ready!"

mc alias set myminio http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc mb --ignore-existing "myminio/${MINIO_BUCKET}"
mc anonymous set download "myminio/${MINIO_BUCKET}"

wait