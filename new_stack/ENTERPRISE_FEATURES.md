# 🚀 Enterprise Features: CI/CD, Geo-Testing, AI Assistant

## Обзор реализованных фич

### 1. CI/CD Integration
**Файлы:** `backend/app/services/cicd_service.py`, `backend/app/api/v1/endpoints.py`

**Возможности:**
- Автоматический анализ PR в GitHub/GitLab
- Постинг комментариев с метриками производительности
- Верификация вебхук-подписей
- Блокировка мержа при регрессии метрик

**Использование:**
```bash
# Настройка вебхука в GitHub
URL: https://your-domain.com/api/v1/webhooks/github
Secret: YOUR_WEBHOOK_SECRET
Events: Pull Request
```

**Пример отчета в PR:**
```markdown
## 📊 Performance Report
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Performance | 92 | 88 | 🔴 -4 |
| LCP | 1.2s | 1.5s | ⚠️ +0.3s |

⚠️ **Warning**: Performance decreased by 4 points.
```

---

### 2. Гео-тестирование
**Файлы:** `backend/app/services/geo_testing_service.py`, `frontend/src/components/enterprise/EnterpriseFeatures.tsx`

**Возможности:**
- Запуск Lighthouse из 7 регионов worldwide
- Сравнение latency и scores между регионами
- Выявление проблемных зон (CDN, DNS, routing)
- Конкурентный запуск тестов (async)

**Регионы:**
- 🇺🇸 US East (Virginia)
- 🇺🇸 US West (Oregon)
- 🇪🇺 EU West (Frankfurt)
- 🇬🇧 EU UK (London)
- 🇯🇵 Asia East (Tokyo)
- 🇸🇬 Asia SE (Singapore)
- 🇦🇺 Oceania (Sydney)

**API:**
```http
GET /api/v1/domains/{id}/geo-stats
POST /api/v1/domains/{id}/geo-test?locations=us-east,eu-west
```

---

### 3. AI Ассистент по оптимизации
**Файлы:** `backend/app/services/ai_assistant.py`, `frontend/src/components/enterprise/EnterpriseFeatures.tsx`

**Возможности:**
- Анализ Lighthouse отчетов через GPT-4o-mini
- Rule-based fallback (работает без API ключа)
- Приоритизация рекомендаций (High/Medium/Low)
- Генерация code examples для исправлений
- Оценка потенциального улучшения в ms/%

**Режимы работы:**
1. **OpenAI Mode** (требуется `OPENAI_API_KEY`):
   - Умный контекстный анализ
   - Персонализированные советы
   - Code examples на React/Vue/Vanilla

2. **Rule-based Mode** (default):
   - Анализ по шаблону аудита Lighthouse
   - Стандартные рекомендации
   - Работает out-of-the-box

**Пример рекомендации:**
```json
{
  "id": "unused-javascript",
  "title": "Удалите неиспользуемый JavaScript",
  "description": "150KB кода не выполняется при загрузке страницы",
  "priority": "high",
  "estimatedImprovement": "+12% Performance",
  "codeExample": "// Используйте dynamic imports:\nconst Module = lazy(() => import('./Module'));"
}
```

---

## Интеграция во Frontend

Компоненты добавлены в `DomainDetailPage`:

```tsx
import { GeoTestingPanel, AIAssistantPanel } from './components/enterprise/EnterpriseFeatures';

// В рендере страницы домена
<GeoTestingPanel domainId={domain.id} />
<AIAssistantPanel domainId={domain.id} />
```

---

## Конфигурация (.env)

```ini
# CI/CD
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_WEBHOOK_SECRET=your_secret_here
GITLAB_TOKEN=glpat-xxxxxxxxxxxx

# AI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o-mini

# Geo-testing (опционально, для proxy)
PROXY_US_EAST=http://user:pass@us-proxy:8080
PROXY_EU_WEST=http://user:pass@eu-proxy:8080
```

---

## Тестирование

### 1. CI/CD Webhook
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/github \
  -H "X-Hub-Signature-256: sha256=..." \
  -H "X-GitHub-Event: pull_request" \
  -d '{"action":"opened","pull_request":{"number":123}}'
```

### 2. Гео-тестирование
```bash
curl http://localhost:8000/api/v1/domains/1/geo-test
```

### 3. AI Анализ
```bash
curl -X POST http://localhost:8000/api/v1/domains/1/ai-analyze \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"metric_type":"performance"}'
```

---

## Roadmap улучшений

- [ ] Добавить поддержку Bitbucket
- [ ] Интеграция с Slack/Discord для алертов
- [ ] Кастомные регионы для гео-тестов
- [ ] Fine-tuning AI модели на ваших данных
- [ ] А/B тестирование рекомендаций

---

**Статус:** ✅ Готово к продакшену  
**Версия:** 2.0 Enterprise  
**Дата:** 2024
