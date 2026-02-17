# Trend Watching

Мониторинг вирусных коротких видео из TikTok, Reels, Shorts.

## Деплой на Vercel

1. Подключите репозиторий к Vercel
2. Добавьте переменные окружения в Project Settings → Environment Variables:
   - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
   - `OPENAI_API_KEY` или `NEUROAPI_BASE_URL` + `NEUROAPI_MODEL`
   - `YOUTUBE_API_KEY`
   - `USE_APIFY=true`, `APIFY_TOKEN` (для TikTok/Reels через Apify)
   - `GOOGLE_SHEET_ID` (опционально, для выгрузки)
3. Для Google Sheets: загрузите JSON сервисного аккаунта как `GOOGLE_CREDENTIALS_JSON` (содержимое файла)

**Примечание:** на Vercel не запускается фоновый воркер. Для автопарсинга настройте [Vercel Cron](https://vercel.com/docs/cron-jobs): POST на `/api/parse-now` по расписанию.

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
