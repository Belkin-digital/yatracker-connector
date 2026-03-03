# YaTracker Connector — точка входа для AI-агентов

## Структура проекта

```
.
├── AGENTS.md                        # ← ты здесь
├── CLAUDE.md                        # Подробная инструкция для AI (команды, API, примеры)
├── DOCKER.md                        # ⚠️ MCP живёт в Docker — читать обязательно
├── QUICKSTART.md                    # Быстрый старт для новых пользователей
├── CHANGELOG.md                     # История изменений — обновлять после каждого изменения
├── docker-compose.yml               # Конфигурация контейнера
├── Dockerfile                       # Сборка образа
├── .mcp.json                        # Подключение MCP к Cursor (через docker exec)
├── .env                             # Токен и org_id (не коммитить!)
├── config/sample.env                # Пример .env для коллег
├── requirements.txt                 # Python-зависимости
├── scripts/
│   ├── mcp_server.py                # MCP-сервер (инструменты yatracker_*)
│   └── cli.py                       # CLI-интерфейс
└── src/yatracker_connector/
    ├── __init__.py                  # Публичный API библиотеки
    ├── operations.py                # Все операции с Трекером (бизнес-логика)
    ├── client.py                    # Фабрика TrackerClient
    └── config.py                    # Настройки (токен, org_id, base_url)
```

---

## Архитектура

```
Claude / Cursor
      │  MCP (stdio через docker exec)
      ▼
scripts/mcp_server.py
      │  Python API
      ▼
src/yatracker_connector/operations.py
      │  HTTP (OAuth)
      ▼
Yandex Tracker API (v2)
```

---

## Правила для агента

После каждого изменения в коде или документации:

1. **Обновить [CHANGELOG.md](CHANGELOG.md)** — добавить запись с датой, что добавлено/изменено/исправлено.
2. **Обновить затронутые документы** — если изменился MCP-инструмент, обновить [CLAUDE.md](CLAUDE.md); если деплой — [DOCKER.md](DOCKER.md) и т.д.

---

## Доступные очереди

| Ключ | Название |
|------|----------|
| CRM | Лиды и клиенты |
| DEV | Разработка |
| MGT | Управление |
| ISTRA / ISTR / ISTRATEST | Истра |

Конфиг: `.env` → `YATRACKER_TOKEN`, `YATRACKER_ORG_ID=7579907`. Пример — [config/sample.env](config/sample.env).
