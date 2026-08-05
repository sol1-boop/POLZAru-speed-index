# 🚀 Changelog Monitor App v2.0

## [2.1.0] - 2024-XX-XX - Аналитика и Умные алерты

### ✨ Новые возможности
- **Графики трендов** — визуализация метрик за период (AreaChart, LineChart)
- **Умные алерты** — обнаружение деградации по серии ухудшений (3+ раза подряд)
- **Аналитическая страница домена** — отдельный дашборд с графиками и статистикой
- **Core Web Vitals детально** — раздельные графики для LCP, FID, CLS

### 🔧 Технические улучшения
- Добавлен сервис `TrendAnalyzer` для анализа временных рядов
- Новый API endpoint `/api/analytics/domains/{id}/trends`
- Новый API endpoint `/api/analytics/domains/{id}/anomalies`
- Компоненты Recharts для графиков
- Интеграция TanStack Query для кэширования данных аналитики

### 📦 Обновленные зависимости
- `recharts` (frontend)
- `pylighthouse` (опционально, backend)

---

## [2.0.0] - 2024-XX-XX - Миграция на FastAPI + React

### 🎉 Полный перезапуск стека
- **Backend:** FastAPI + SQLAlchemy 2.0 (Async) + PostgreSQL
- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS
- **Task Queue:** Celery + Redis
- **Infrastructure:** Docker Compose

### ✨ Ключевые фичи
- JWT аутентификация
- CRUD доменов и метрик
- Автоматические проверки Lighthouse через Celery Beat
- Telegram уведомления
- Бюджеты производительности

### 📁 Структура проекта
```
new_stack/
├── backend/          # FastAPI приложение
├── frontend/         # React приложение
├── docker-compose.yml
└── README.md
```

---

## [1.0.0] - Legacy (Flask)
- Монолитное Flask приложение
- SQLite база данных
- Синхронные проверки Lighthouse
- Простая система сессий
