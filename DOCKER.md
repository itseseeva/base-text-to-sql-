# 🐳 Docker Quick Start

## Быстрый старт

1. **Создайте `.env` файл** с необходимыми переменными:
```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=Kohkau11999
POSTGRES_DB=tg_bot
DB_PORT=5432
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id
API_ID=your_api_id
API_HASH=your_api_hash
```

2. **Убедитесь, что папка `model/` содержит файлы модели**

3. **Запустите все сервисы:**
```bash
docker-compose up -d
```

4. **Проверьте логи:**
```bash
docker-compose logs -f bot
```

5. **Загрузите данные (если нужно):**
```bash
docker-compose exec bot python load_data.py videos.json
```

## Структура Docker

- **postgres** - PostgreSQL база данных
- **bot** - Telegram бот с LLM моделью

## Полезные команды

```bash
# Остановка
docker-compose stop

# Запуск
docker-compose start

# Перезапуск
docker-compose restart

# Удаление всего (включая данные БД)
docker-compose down -v

# Пересборка образа бота
docker-compose build --no-cache bot
```

## Troubleshooting

### Бот не запускается
```bash
docker-compose logs bot
```

### PostgreSQL не запускается
```bash
docker-compose logs postgres
```

### Проверка состояния контейнеров
```bash
docker-compose ps
```

