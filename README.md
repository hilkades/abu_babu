# AntiSpam Telegram Bot (aiogram 3)

Production-ready каркас Telegram-бота для антиспама в группах:
- гибридная детекция (rules + scoring),
- подтверждение человека через inline-кнопку,
- таймауты и временные состояния в Redis,
- постоянные данные/аудит в PostgreSQL,
- настраиваемость по чатам и режимам строгости.

## Быстрый старт (Docker)

1) Скопируйте переменные окружения:

```bash
cp .env.example .env
```

2) Запустите зависимости и бота:

```bash
docker compose up -d --build
```

3) Примените миграции:

```bash
docker compose exec bot alembic upgrade head
```

4) Логи:

```bash
docker compose logs -f bot
```

## Локальный запуск (без Docker)

1) Создайте venv и установите зависимости:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

2) Поднимите PostgreSQL и Redis (удобнее через Docker):

```bash
docker compose up -d postgres redis
```

3) Примените миграции:

```bash
alembic upgrade head
```

4) Запуск бота:

```bash
export $(cat .env | xargs)  # или используйте direnv
python -m bot.main
```

## Команды

- **Публичные**: `/start`, `/help`, `/status`
- **Только админы чата**:
  - `/settings` (показывает inline-меню)
  - `/enable`, `/disable`
  - `/setmode strict|balanced|lenient`
  - `/settimeout <sec>`
  - `/setaction delete|mute|kick|ban`
  - `/setthreshold <suspicious> <spam> <critical>`
  - `/setflood <window_sec> <max_messages> <mute_sec>`
  - `/adddomain <domain>`, `/removedomain <domain>`
  - `/addbadword <phrase>`, `/removebadword <phrase>`
  - `/addwhitelist <user_id> [ttl_sec]`, `/removewhitelist <user_id>`
  - `/audit`, `/stats`

`/addbadword` и `/removebadword` работают с общим для всех чатов списком в файле `badwords.txt` (в корне проекта).  
Формат файла: одна фраза на строку, строки с `#` считаются комментариями.

## Тесты

Локально (с dev-зависимостями):

```bash
pip install -e ".[dev]"
pytest -q
```

## Требования

- Python 3.11+ (локально) или Docker
- PostgreSQL 15+
- Redis 7+

## Важно

Бот должен быть **администратором** чата с правами:
- удаление сообщений,
- бан/кик/ограничение пользователей,
- чтение сообщений (в группах доступно по умолчанию).

