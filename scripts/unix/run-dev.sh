mkdir -p logs
docker compose -f docker-compose.hot-dev.yml up "$@"
