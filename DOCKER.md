# Docker Deployment Guide для YaTracker MCP Server

## Зачем Docker?

Docker решает проблемы:
- ✅ **Портативность** - не нужны абсолютные пути, работает везде одинаково
- ✅ **Изоляция** - не конфликтует с другими проектами
- ✅ **Простота передачи** - коллеги могут просто запустить `docker-compose up`
- ✅ **Независимость от системы** - работает на любой ОС с Docker

## Быстрый старт

### 1. Убедитесь, что Docker установлен

```bash
docker --version
docker-compose --version
```

Если нет - установите [Docker Desktop](https://www.docker.com/products/docker-desktop)

### 2. Проверьте файл .env

Убедитесь, что `.env` содержит ваши credentials:

```bash
YATRACKER_TOKEN=your_token_here
YATRACKER_ORG_ID=7579907
```

### 3. Запустите контейнер

```bash
# Из корня проекта
docker-compose up -d
```

Готово! MCP сервер запущен на порту 8080.

## Команды управления

### Запуск сервера
```bash
docker-compose up -d        # Запустить в фоне
docker-compose up           # Запустить с выводом логов
```

### Остановка сервера
```bash
docker-compose down         # Остановить и удалить контейнер
docker-compose stop         # Просто остановить (сохранить контейнер)
```

### Просмотр логов
```bash
docker-compose logs -f      # Следить за логами в реальном времени
docker-compose logs         # Показать все логи
```

### Перезапуск после изменений
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Подключение из Claude Code

### Вариант 1: SSE Transport (рекомендуется)

В `.mcp.json` или `~/.claude.json`:

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

### Вариант 2: Stdio Transport

Если MCP сервер использует stdio:

```json
{
  "mcpServers": {
    "yatracker": {
      "command": "docker",
      "args": ["exec", "-i", "yatracker-mcp-server", "python3.11", "-m", "scripts.mcp_server"],
      "env": {}
    }
  }
}
```

## Для команды / коллег

### Шаг 1: Получить проект
```bash
git clone <repository-url>
cd "YaTracker Connector"
```

### Шаг 2: Создать .env файл
```bash
cp config/sample.env .env
# Отредактировать .env и добавить свои credentials
```

### Шаг 3: Запустить
```bash
docker-compose up -d
```

Всё! Никаких абсолютных путей, никаких проблем с Python версиями.

## Отладка

### Проверить статус контейнера
```bash
docker-compose ps
```

### Зайти внутрь контейнера
```bash
docker-compose exec yatracker-mcp /bin/bash
```

### Проверить переменные окружения
```bash
docker-compose exec yatracker-mcp env | grep YATRACKER
```

### Перестроить образ (после изменений кода)
```bash
docker-compose build --no-cache
docker-compose up -d
```

## Структура файлов Docker

```
.
├── Dockerfile              # Описание образа
├── docker-compose.yml      # Конфигурация запуска
├── .dockerignore          # Что не копировать в образ
└── .env                   # Credentials (НЕ коммитить в git!)
```

## Безопасность

⚠️ **ВАЖНО**:
- Файл `.env` с токенами НЕ должен попадать в git
- Добавьте `.env` в `.gitignore`
- Для команды создайте `config/sample.env` с примером структуры

## Альтернатива: Docker без docker-compose

Если не хотите использовать docker-compose:

```bash
# Собрать образ
docker build -t yatracker-mcp .

# Запустить с передачей переменных
docker run -d \
  -p 8080:8080 \
  -e YATRACKER_TOKEN=your_token \
  -e YATRACKER_ORG_ID=7579907 \
  --name yatracker-mcp-server \
  yatracker-mcp
```

## Публикация образа (опционально)

Если хотите поделиться готовым образом:

```bash
# Залогиниться в Docker Hub
docker login

# Пометить образ
docker tag yatracker-mcp yourusername/yatracker-mcp:latest

# Загрузить
docker push yourusername/yatracker-mcp:latest
```

Тогда коллеги смогут просто:
```bash
docker pull yourusername/yatracker-mcp:latest
docker run -d -p 8080:8080 --env-file .env yourusername/yatracker-mcp:latest
```
