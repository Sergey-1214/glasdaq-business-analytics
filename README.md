# Glasdaq Business Analytics

Дашборд для бизнес-аналитики с модульным интерфейсом, микросервисным бэкендом и встроенным AI-ассистентом.

## Стек

**Frontend** — React 19 + Vite, Zustand, dnd-kit, React Router, Canvas API (@chenglou/pretext)

**Backend** — Python, FastAPI, микросервисная архитектура

**Инфраструктура** — Docker Compose, PostgreSQL, Ollama (LLM)

## Архитектура

```
┌─────────────────────────────────────────────────┐
│                    Frontend                     │
│              React SPA  :5173                   │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│               API Gateway  :8000                │
└──┬──────┬──────┬──────┬──────┬──────┬───────────┘
   │      │      │      │      │      │
:8003  :8004  :8008  :8005  :8006  :8001  :8002
Orch  Prod  ProdImpl Team  Fin  Market  Parsers
                                   │
                              PostgreSQL :5432
                       
Ollama :11434  (Qwen и другие LLM)
```

### Сервисы

| Сервис | Порт | Описание |
|--------|------|----------|
| `api_gateway` | 8000 | Единая точка входа, маршрутизация запросов |
| `orchestrator` | 8003 | Оркестрация запросов между сервисами |
| `product_service` | 8004 | Анализ продуктов (использует Ollama) |
| `product_implementation` | 8008 | Реализация продуктовых функций |
| `team_service` | 8005 | Управление командой |
| `finance_service` | 8006 | Финансовые показатели |
| `market_service` | 8001 | Анализ рынка, PostgreSQL |
| `parsers` | 8002 | Парсинг внешних данных |
| `ollama` | 11434 | LLM-сервер (Qwen и другие модели) |

## Запуск

### Требования

- Docker Desktop (с включённым WSL2 или Hyper-V)
- Node.js 20+ (для локального запуска фронта без Docker)

### Через Docker

```bash
# Скопируй переменные окружения
cp env.example .env

# Только фронтенд
docker-compose up --build frontend

# Весь стек
docker-compose up --build
```

### После запуска применить миграции с помощью
```bash
docker-compose exec market_service python -m alembic upgrade head
```

Фронтенд открывается на `http://localhost:5173`

### Фронтенд локально (без Docker)

```bash
cd frontend
npm install
npm run dev
```

## Переменные окружения

Скопируй `env.example` в `.env` и при необходимости измени значения:

```env
GATEWAY_PORT=8000        # API Gateway
MARKET_DB_USER=postgres  # PostgreSQL
MARKET_DB_PASSWORD=postgres
OLLAMA_PORT=11434        # LLM сервер
FRONTEND_PORT=5173       # Фронтенд
```

## Интерфейс

Дашборд построен на зонах: **левый сайдбар**, **центр** (карта), **правый сайдбар**, **нижняя панель**. Блоки можно перетаскивать между зонами через drag-and-drop, добавлять и удалять через кнопку `+` в каждой зоне.

Доступные блоки:

- **Карта** — закреплена в центре, всегда активна
- **Ассистент** — AI-чат с анимацией текста на Canvas
- **Графики / Отчёты / Метрики** — аналитические блоки (нижняя панель)
- **Аккаунт / Быстрые действия** — левый сайдбар

Режим фокуса — двойной клик на заголовке блока разворачивает его на весь экран. Узкий левый сайдбар показывает иконки всех активных блоков для быстрого переключения.

## Структура проекта

```
glasdaq-business-analytics/
├── frontend/               # React-приложение
│   └── src/
│       ├── components/     # UI-компоненты
│       ├── store/          # Zustand (auth, dashboard)
│       └── main.jsx        # Точка входа, роутинг
├── api_gateway/            # FastAPI gateway
├── orchestrator/           # Оркестратор
├── market_service/         # Сервис рынка + БД
├── product_service/        # Сервис продуктов
├── product_implementation/ # Реализация продуктов
├── team_service/           # Сервис команды
├── finance_service/        # Финансовый сервис
├── parsers/                # Парсеры данных
├── ollama/                 # LLM конфигурация
├── docker-compose.yml
└── env.example
```
