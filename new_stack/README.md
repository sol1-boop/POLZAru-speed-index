# 🚀 Monitor App v2.0 - Полный Рефакторинг

## Новый Стек Технологий

### Backend
- **FastAPI** - современный асинхронный фреймворк
- **SQLAlchemy 2.0 (Async)** - асинхронная ORM
- **PostgreSQL** - надежная реляционная БД
- **Celery + Redis** - очередь задач для Lighthouse
- **Pydantic v2** - валидация данных
- **JWT Auth** - безопасная аутентификация
- **Loguru** - продвинутое логирование

### Frontend
- **React 18** - компонентный UI
- **TypeScript** - строгая типизация
- **Vite** - быстрая сборка
- **TanStack Query** - кэширование и синхронизация
- **Tailwind CSS** - утилитарные стили
- **React Router v6** - навигация
- **Axios** - HTTP клиент

### Infrastructure
- **Docker Compose** - оркестрация контейнеров
- **Nginx** - раздача статики
- **GitHub Actions** - CI/CD

---

## 📁 Структура Проекта

```
new_stack/
├── backend/
│   ├── app/
│   │   ├── api/          # API роуты
│   │   │   ├── auth.py
│   │   │   ├── domains.py
│   │   │   └── dashboard.py
│   │   ├── core/         # Конфигурация, БД, безопасность
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/       # SQLAlchemy модели
│   │   ├── schemas/      # Pydantic схемы
│   │   ├── services/     # Бизнес-логика
│   │   │   ├── auth.py
│   │   │   └── lighthouse.py
│   │   ├── workers/      # Celery задачи
│   │   │   ├── celery_app.py
│   │   │   └── tasks.py
│   │   └── main.py       # Точка входа
│   ├── alembic/          # Миграции БД
│   ├── logs/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/          # API клиенты
│   │   ├── components/   # React компоненты
│   │   ├── pages/        # Страницы
│   │   ├── hooks/        # Кастомные хуки
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🏃 Быстрый Старт

### 1. Клонирование и настройка
```bash
cd new_stack
cp .env.example .env
# Отредактируйте .env (особенно пароли!)
```

### 2. Запуск через Docker Compose
```bash
docker-compose up --build
```

Сервисы будут доступны:
- **Frontend**: http://localhost:80
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Flower (Celery UI)**: http://localhost:5555

### 3. Первый вход
- Email: `admin@example.com` (изменийте в .env!)
- Пароль: `change_me_immediately` (смените немедленно!)

---

## 🔑 Ключевые Улучшения

### Безопасность
✅ Хеширование паролей (bcrypt)  
✅ JWT токены с expiration  
✅ Переменные окружения для секретов  
✅ CORS настройка  
✅ Валидация всех входных данных  

### Производительность
✅ Асинхронные запросы к БД  
✅ Celery для тяжелых задач Lighthouse  
✅ Кэширование через Redis  
✅ Оптимизированная сборка фронтенда  

### Надежность
✅ Health check эндпоинты  
✅ Graceful shutdown  
✅ Ретраи для Celery задач  
✅ Логирование с ротацией  

### Developer Experience
✅ Auto-generated API docs (/docs)  
✅ TypeScript на фронтенде  
✅ Hot reload в разработке  
✅ Docker для консистентной среды  

---

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Регистрация
- `POST /api/v1/auth/login` - Логин
- `GET /api/v1/auth/me` - Текущий пользователь

### Domains
- `GET /api/v1/domains/` - Список доменов
- `POST /api/v1/domains/` - Создать домен
- `GET /api/v1/domains/{id}` - Детали домена
- `PUT /api/v1/domains/{id}` - Обновить домен
- `DELETE /api/v1/domains/{id}` - Удалить домен
- `GET /api/v1/domains/{id}/metrics` - Метрики Lighthouse
- `POST /api/v1/domains/{id}/check` - Запустить проверку

### Dashboard
- `GET /api/v1/dashboard` - Сводка дашборда
- `GET /api/v1/alerts` - Список алертов

---

## 🔧 Разработка

### Backend (локально)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend (локально)
```bash
cd frontend
npm install
npm run dev
```

---

## 📊 Миграция со Старой Версии

1. **Экспорт данных** из старой SQLite БД
2. **Настройка** нового PostgreSQL
3. **Запуск миграций** (Alembic)
4. **Импорт данных** (скрипт в разработке)
5. **Тестирование** нового стека
6. **Переключение трафика**

---

## ⚠️ Важные Замечания

🔴 **Измените пароль администратора** после первого входа!  
🔴 **Настройте CORS** для продакшена (сейчас разрешено все)  
🔴 **Используйте HTTPS** в продакшене  
🟡 Настройте Alembic миграции вместо авто-создания таблиц  
🟢 Добавьте мониторинг (Prometheus/Grafana)  

---

## 📈 Следующие Шаги

1. Реализовать полноценные страницы (Login, Dashboard, Domain Details)
2. Добавить графики (Recharts) для метрик
3. WebSocket для real-time обновлений
4. Telegram уведомления об алертах
5. Покрыть тестами (pytest + React Testing Library)
6. Настроить CI/CD pipeline

---

## 📝 Лицензия

MIT
