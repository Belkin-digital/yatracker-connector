# Инструкция для Claude по работе с YaTracker Connector

## Настройка окружения

Файл `.env` должен содержать:
```bash
YATRACKER_TOKEN=your_oauth_token_here
YATRACKER_ORG_ID=your_organization_id
# Необязательно: Client ID приложения на oauth.yandex.ru (если хранишь рядом с токеном)
# YATRACKER_OAUTH_CLIENT_ID=your_client_id
```

Секреты не коммитить; шаблон — [config/sample.env](config/sample.env).

## Доступные очереди

- **CRM** - Lead (лиды и клиенты)
- **DEV** - Разработка
- **MGT** - Управление
- **ISTRA** - Истра
- **ISTRATEST** - Istratest
- **ISTR** - Istra

## Как запускать команды

### Базовая команда
```bash
cd "/Users/aleksejbelkin/Git/YaTracker Connector" && \
PYTHONPATH=src python3.11 -m scripts.cli <команда>
```

### Примеры команд

#### 1. Получить список задач из очереди
```bash
PYTHONPATH=src python3.11 -m scripts.cli issues list --queue CRM --limit 50
```

#### 2. Просмотреть комментарии к задаче
```bash
PYTHONPATH=src python3.11 -m scripts.cli comments list CRM-19
```

#### 3. Добавить комментарий к задаче
```bash
PYTHONPATH=src python3.11 -m scripts.cli comments add CRM-19 "Текст комментария"
```

#### 4. Посмотреть доступные переходы (смена статуса)
```bash
PYTHONPATH=src python3.11 -m scripts.cli transitions list CRM-19
```

#### 5. Выполнить переход статуса
```bash
PYTHONPATH=src python3.11 -m scripts.cli transitions execute CRM-19 <transition_id>
```

#### 6. Обновить поля задачи
```bash
PYTHONPATH=src python3.11 -m scripts.cli issues update CRM-19 --field "summary=Новое название"
```

#### 7. Скачать вложения
```bash
PYTHONPATH=src python3.11 -m scripts.cli attachments download CRM-19 --target ./downloads
```

#### 8. Добавить вложение
```bash
PYTHONPATH=src python3.11 -m scripts.cli attachments add CRM-19 --path ./file.pdf
```

## Использование через Python API напрямую

```python
import sys
sys.path.insert(0, 'src')

from yatracker_connector import (
    build_tracker_client,
    get_issue,
    add_comment,
    list_comments,
    search_issues
)

# Создать клиент
client = build_tracker_client()

# Получить задачу
issue = get_issue(client, 'CRM-19')

# Добавить комментарий
add_comment(issue, 'Текст комментария')

# Получить список комментариев
comments = list_comments(issue)
for comment in comments:
    print(f"{comment.id}: {comment.text}")

# Поиск задач
issues = search_issues(client, filter_payload={'queue': 'CRM'}, limit=100)
for issue in issues:
    print(f"{issue.key}: {issue.summary}")
```

## Важные замечания

1. **Всегда указывай PYTHONPATH=src** при запуске команд
2. **Используй python3.11**, не python или python3 (может быть другая версия)
3. **Пути с пробелами** нужно экранировать или брать в кавычки
4. **Многострочные комментарии** можно добавлять, используя `\n` или многострочные строки в Python

## Исправленные баги

1. В `config.py` используется `base_url` вместо `url` (совместимость с yandex-tracker-client)
2. В `operations.py` параметры передаются в `client.issues.find()` как именованные аргументы
3. В `cli.py` статус отображается через `status.display` вместо прямого вывода объекта

## MCP Server (Model Context Protocol)

### Что это?

MCP сервер делает YaTracker доступным для Claude Code через специальный протокол. Это позволяет Claude автоматически работать с задачами, комментариями и вложениями.

### Как работает?

1. **Для Claude Code**: MCP сервер автоматически запускается и предоставляет инструменты для работы с YaTracker
2. **Для Python скриптов**: Используй обычный API из `yatracker_connector` (MCP сервер только для Claude)

### Настройка

MCP сервер уже настроен в [.mcp.json](.mcp.json). При открытии проекта в Claude Code он автоматически станет доступен.

### Доступные инструменты в Claude Code

Когда MCP сервер активен, у Claude появляются следующие инструменты:

#### Работа с задачами
- `yatracker_search_issues` - поиск и список задач из очереди
- `yatracker_get_issue` - получить детали задачи
- `yatracker_create_issue` - создать новую задачу/лид
- `yatracker_update_issue` - обновить поля задачи

#### Комментарии
- `yatracker_list_comments` - список комментариев
- `yatracker_add_comment` - добавить комментарий
- `yatracker_add_comment_with_attachment` - добавить комментарий с файлом-вложением

#### Переходы и статусы
- `yatracker_list_transitions` - доступные переходы статусов для конкретной задачи
- `yatracker_execute_transition` - выполнить переход статуса

#### Вложения
- `yatracker_download_attachments` - скачать вложения
- `yatracker_attach_file` - прикрепить файл

#### Метаданные и конфигурация
- `yatracker_list_queues` - список всех доступных очередей в системе
- `yatracker_list_queue_fields` - список полей конкретной очереди
- `yatracker_list_all_fields` - список всех полей в системе
- `yatracker_list_queue_issue_types` - список типов задач в очереди
- `yatracker_get_queue_workflows` - полный бизнес-процесс/граф статусов с переходами для очереди

### Примеры использования MCP инструментов

#### Получить список очередей
```
Используй yatracker_list_queues для просмотра всех доступных очередей в системе
```

#### Посмотреть бизнес-процесс очереди
```
Используй yatracker_get_queue_workflows с параметром queue="CRM"
Получишь полный граф переходов статусов для лидов
```

#### Добавить комментарий с вложением
```
Используй yatracker_add_comment_with_attachment:
- issue_key: "CRM-24"
- text: "Отправляю договор"
- file_path: "./contract.pdf"
```

#### Узнать доступные поля очереди
```
Используй yatracker_list_queue_fields с параметром queue="CRM"
Посмотришь какие поля можно заполнять в задачах
```

#### Проверить типы задач в очереди
```
Используй yatracker_list_queue_issue_types с параметром queue="CRM"
Увидишь доступные типы (например, "Лид", "Задача", и т.д.)
```

### Проверка статуса MCP сервера

В Claude Code используй команду `/mcp` для проверки статуса сервера.

### Глобальная конфигурация

Чтобы сделать MCP сервер доступным во всех проектах на компьютере:

1. Скопируй содержимое [.mcp.json](.mcp.json)
2. Добавь его в `~/.claude.json`
3. Измени путь к проекту в `env.PYTHONPATH` на абсолютный

Пример для `~/.claude.json`:
```json
{
  "mcpServers": {
    "yatracker": {
      "command": "python3.11",
      "args": ["-m", "scripts.mcp_server"],
      "env": {
        "PYTHONPATH": "/Users/aleksejbelkin/Git/YaTracker Connector/src",
        "YATRACKER_TOKEN": "${YATRACKER_TOKEN}",
        "YATRACKER_ORG_ID": "${YATRACKER_ORG_ID}"
      }
    }
  }
}
```

## Структура проекта

```
.
├── .env                        # Конфигурация (токен, org_id)
├── .mcp.json                   # Конфигурация MCP сервера
├── config/sample.env           # Пример конфигурации
├── requirements.txt            # Python зависимости
├── src/yatracker_connector/
│   ├── __init__.py            # Экспорт API
│   ├── config.py              # Настройки
│   ├── client.py              # Фабрика клиента
│   └── operations.py          # Операции с задачами
└── scripts/
    ├── cli.py                 # CLI интерфейс
    └── mcp_server.py          # MCP сервер для Claude Code
```
