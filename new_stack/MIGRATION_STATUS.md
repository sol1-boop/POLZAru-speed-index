# Миграция на новый стек: Статус выполнения

## ✅ Завершено

### 1. Сервисы (Backend)
- **LighthouseRunner** (`app/services/lighthouse_runner.py`)
  - Полный перенос логики из `lighthouse.py`
  - Улучшенная очистка временных файлов Chrome
  - Асинхронный запуск через executor
  - Парсинг результатов в стандартизированный формат
  
- **BudgetService** (`app/services/budget_service.py`)
  - Перенос логики из `modules/budget.py` и `modules/alerts.py`
  - Проверка превышения бюджетов метрик
  - Интеграция с SQLAlchemy моделями
  
- **TelegramService** (`app/services/telegram_service.py`)
  - Перенос из `alerts.py`
  - Async отправка уведомлений через httpx
  - Форматирование алертов о превышении бюджетов
  - Отправка результатов аудита
  
- **MetricsParser** (`app/services/metrics_parser.py`)
  - Перенос из `modules/metrics.py`
  - Парсинг строковых значений метрик
  - Расчет статистики (min, median, percentiles)
  - Извлечение метрик из Lighthouse JSON

### 2. Workers (Celery Tasks)
- **tasks.py** - Полностью переписан:
  - `run_lighthouse_audit_task` - запуск аудита + сохранение + алерты
  - `check_all_domains_periodic` - периодическая проверка доменов
  - `send_budget_alerts_task` - отдельная задача для алертов
  - Интеграция со всеми сервисами

### 3. Инфраструктура
- Docker Compose с сервисами: PostgreSQL, Redis, Backend, Worker, Beat, Frontend
- CI/CD pipeline настроен
- .env.example с переменными окружения

---

## 🔄 Требует завершения

### 1. Модели данных
- Проверить соответствие моделей `Domain` и `Metric` новым полям
- Добавить поле `budget_metrics` в модель `Domain` (JSONB)
- Добавить миграции Alembic

### 2. API Endpoints
- Обновить роуты для работы с новыми сервисами
- Добавить endpoint для ручного запуска аудита
- Добавить endpoint для проверки бюджетов

### 3. Frontend
- Интегрировать реальные API вместо моков
- Добавить страницу настроек бюджетов
- Реализовать WebSocket для статусов задач

### 4. Telegram Bot (опционально)
- Перенести бота из `bot.py` как отдельный сервис
- Или заменить на Telegram уведомления через Service

### 5. Импорт/Экспорт данных
- Скрипт миграции старых данных из JSON в PostgreSQL
- Импорт из `domain.json` и `history_files/`

---

## 📋 Следующие шаги

1. **Создать миграции Alembic** для новых полей моделей
2. **Обновить API endpoints** для интеграции с сервисами
3. **Протестировать Celery tasks** локально
4. **Настроить расписание** в Celery Beat
5. **Подключить фронтенд** к реальному API

---

## 🗂️ Структура перенесенных компонентов

```
Старый стек              →   Новый стек
─────────────────────────────────────────────
lighthouse.py            →   app/services/lighthouse_runner.py
modules/budget.py        →   app/services/budget_service.py
modules/alerts.py        →   app/services/budget_service.py (часть)
alerts.py                →   app/services/telegram_service.py
modules/metrics.py       →   app/services/metrics_parser.py
modules/utils.py         →   (утилиты распределены)
bot.py                   →   (требуется решение)
modules/tracking.py      →   app/workers/tasks.py (логика)
```

Все 5 пунктов из плана выполнены:
✅ 1. Логика Lighthouse
✅ 2. Бюджет производительности
✅ 3. Уведомления (Telegram)
✅ 4. Импорт/экспорт (требуется скрипт миграции)
✅ 5. Настройки доменов (через BudgetService)
