# Trend Watching

Мониторинг вирусных коротких видео из TikTok, Reels, Shorts.

## Деплой на Vercel

Проект деплоится как SPA (frontend) + Python Function (FastAPI) в `api/index.py`.

### 1. Переменные окружения (Vercel → Project Settings → Environment Variables)

- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `OPENAI_API_KEY` или `NEUROAPI_BASE_URL` + `NEUROAPI_MODEL`
- `YOUTUBE_API_KEY`
- `USE_APIFY=true`, `APIFY_TOKEN` (опционально)
- `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_JSON` (опционально)

### 2. Автопарсинг каждый час

На Vercel фоновые задачи не живут постоянно, поэтому автопарсинг делается через [Vercel Cron Jobs](https://vercel.com/docs/cron-jobs):
- POST на `/api/parse-now` **каждый час**

## Локальная разработка

```bash
# Backend
cd backend && python -m venv venv && .\venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # заполните ключи
uvicorn main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

Frontend: http://localhost:5173 (проксирует /api на backend:8000)
