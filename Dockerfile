# Build frontend
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Backend + serve
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./
COPY --from=frontend /app/frontend/dist ./frontend_dist

ENV PORT=8000
EXPOSE $PORT

CMD uvicorn main:app --host 0.0.0.0 --port $PORT
