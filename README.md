# YaTracker Connector

Python библиотека и MCP сервер для работы с API Яндекс Трекера.

## 🚀 Быстрый старт

### Вариант 1: Docker (Рекомендуется)

Самый простой способ для использования MCP сервера:

```bash
# 1. Создайте .env файл
cp config/sample.env .env
# Отредактируйте .env и добавьте свои credentials

# 2. Запустите
docker-compose up -d

# Готово! MCP сервер работает на порту 8080
```

**Преимущества Docker:**
- ✅ Никаких абсолютных путей
- ✅ Работает везде одинаково
- ✅ Легко передать коллегам
- ✅ Не конфликтует с другими проектами

📖 Подробнее: [DOCKER.md](DOCKER.md)

### Вариант 2: Локальная установка

```bash
# 1. Установите зависимости
pip install -r requirements.txt

# 2. Создайте .env
cp config/sample.env .env
# Добавьте YATRACKER_TOKEN и YATRACKER_ORG_ID

# 3. Используйте CLI
PYTHONPATH=src python3.11 -m scripts.cli issues list --queue CRM
```

📖 Подробнее: [QUICKSTART.md](QUICKSTART.md)

## 📚 Документация

- **[QUICKSTART.md](QUICKSTART.md)** - Быстрый справочник команд CLI
- **[CLAUDE.md](CLAUDE.md)** - Полная инструкция для работы с проектом
- **[DOCKER.md](DOCKER.md)** - Развертывание через Docker

## 🔧 Возможности

### CLI (Command Line Interface)

```bash
# Список задач
PYTHONPATH=src python3.11 -m scripts.cli issues list --queue CRM --limit 50

# Комментарии
PYTHONPATH=src python3.11 -m scripts.cli comments list CRM-19
PYTHONPATH=src python3.11 -m scripts.cli comments add CRM-19 "Текст"

# Переходы статусов
PYTHONPATH=src python3.11 -m scripts.cli transitions list CRM-19

# Вложения
PYTHONPATH=src python3.11 -m scripts.cli attachments download CRM-19
```

### Python API

```python
from yatracker_connector import (
    build_tracker_client,
    get_issue,
    add_comment,
    search_issues
)

client = build_tracker_client()
issue = get_issue(client, 'CRM-19')
add_comment(issue, 'Текст комментария')
```

### MCP Server для Claude Code

Запустите через Docker и настройте в `.mcp.json`:

```json
{
  "mcpServers": {
    "yatracker": {
      "transport": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

## MCP Инструменты

### Работа с задачами
- `yatracker_search_issues` - поиск и список задач
- `yatracker_get_issue` - детали задачи
- `yatracker_create_issue` - создать задачу/лид
- `yatracker_update_issue` - обновить поля

### Комментарии
- `yatracker_list_comments` - список комментариев
- `yatracker_add_comment` - добавить комментарий
- `yatracker_add_comment_with_attachment` - комментарий с файлом

### Переходы и статусы
- `yatracker_list_transitions` - доступные переходы
- `yatracker_execute_transition` - выполнить переход

### Вложения
- `yatracker_download_attachments` - скачать вложения
- `yatracker_attach_file` - прикрепить файл

### Метаданные
- `yatracker_list_queues` - список очередей
- `yatracker_list_queue_fields` - поля очереди
- `yatracker_list_all_fields` - все поля системы
- `yatracker_list_queue_issue_types` - типы задач
- `yatracker_get_queue_workflows` - бизнес-процесс/граф статусов

## 🤝 Для команды

### Передача проекта коллегам (Docker):

```bash
# 1. Коллега клонирует репозиторий
git clone <url>
cd "YaTracker Connector"

# 2. Создает свой .env
cp config/sample.env .env
# Добавляет свои credentials

# 3. Запускает
docker-compose up -d
```

**Вот и всё!** Никаких настроек путей, версий Python и прочего.

## 🔐 Настройка

Создайте файл `.env` в корне проекта:

```bash
YATRACKER_TOKEN=your_oauth_token_here
YATRACKER_ORG_ID=your_organization_id
# опционально, если ведёшь учёт приложения: YATRACKER_OAUTH_CLIENT_ID=...
```

### Как получить credentials:

1. **Токен OAuth**: [Яндекс OAuth](https://oauth.yandex.ru/)
2. **Org ID**: В Трекере → Администрирование → Организации → идентификатор
3. **Client ID** (необязательно): в том же кабинете OAuth — идентификатор приложения; для вызовов API Трекера достаточно токена

## 📦 Структура проекта

```
.
├── Dockerfile              # Docker образ
├── docker-compose.yml      # Простой запуск
├── .env                    # Credentials (НЕ коммитить!)
├── src/yatracker_connector/
│   ├── config.py          # Настройки
│   ├── client.py          # Клиент API
│   └── operations.py      # Операции с задачами
└── scripts/
    ├── cli.py             # CLI интерфейс
    └── mcp_server.py      # MCP сервер
```

## Доступные очереди

- **CRM** - Lead (лиды и клиенты)
- **DEV** - Разработка
- **MGT** - Управление
- **ISTRA** - Истра
- **ISTRATEST** - Istratest
- **ISTR** - Istra

## Требования

- Python 3.11+
- Yandex Tracker API token
- Organization ID

## Лицензия

MIT
