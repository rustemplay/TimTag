# TimTag
# На ПК — пересобрать
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t rustam21/timtag:latest \
  --push .

# На Orange Pi — обновить
docker compose pull && docker compose up -d