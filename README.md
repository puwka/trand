# Trend Watching

Мониторинг вирусных коротких видео из TikTok, Reels, Shorts.

## Деплой на Railway

### 1. Создайте проект

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Выберите репозиторий и подключите

### 2. Переменные окружения

Settings → Variables:

- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `OPENAI_API_KEY` или `NEUROAPI_BASE_URL` + `NEUROAPI_MODEL`
- `YOUTUBE_API_KEY`
- `USE_APIFY=true`, `APIFY_TOKEN` (опционально)
- `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_JSON` (опционально)

### 3. Домен

Settings → Networking → Generate Domain

### 4. Автопарсинг

Фоновый парсер запускается при старте и вызывает POST `/api/parse-now` каждый час.

## Локальная разработка

```bash
# Backend
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env    # заполните ключи
uvicorn main:app --reload

# Frontend (в отдельном терминале)
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173 (проксирует /api на backend:8000)
