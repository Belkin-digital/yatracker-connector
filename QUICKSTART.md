# Быстрый старт - YaTracker Connector

## Все команды запускаются из корня проекта

### 📋 Просмотр задач

```bash
# Показать задачи из очереди CRM
PYTHONPATH=src python3.11 -m scripts.cli issues list --queue CRM --limit 50

# Показать задачи из очереди DEV
PYTHONPATH=src python3.11 -m scripts.cli issues list --queue DEV --limit 20
```

### 💬 Работа с комментариями

```bash
# Показать комментарии к задаче
PYTHONPATH=src python3.11 -m scripts.cli comments list CRM-19

# Добавить комментарий
PYTHONPATH=src python3.11 -m scripts.cli comments add CRM-19 "Ваш комментарий"
```

### 🔄 Переходы (смена статусов)

```bash
# Посмотреть доступные переходы
PYTHONPATH=src python3.11 -m scripts.cli transitions list CRM-19

# Выполнить переход
PYTHONPATH=src python3.11 -m scripts.cli transitions execute CRM-19 <ID>
```

### 📎 Вложения

```bash
# Скачать все вложения
PYTHONPATH=src python3.11 -m scripts.cli attachments download CRM-19

# Добавить файл
PYTHONPATH=src python3.11 -m scripts.cli attachments add CRM-19 --path ./file.pdf
```

### ✏️ Обновление полей

```bash
# Обновить название задачи
PYTHONPATH=src python3.11 -m scripts.cli issues update CRM-19 --field "summary=Новое название"
```

## Доступные очереди

- **CRM** - Лиды и клиенты
- **DEV** - Разработка
- **MGT** - Управление
- **ISTRA**, **ISTRATEST**, **ISTR** - Истра

## Настройка

Файл `.env` в корне проекта содержит:
```
YATRACKER_TOKEN=<ваш_токен>
YATRACKER_ORG_ID=7579907
```

## Подробности

См. [CLAUDE.md](CLAUDE.md) для полной документации и примеров использования через Python API.
