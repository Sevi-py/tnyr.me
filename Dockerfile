FROM node:20-alpine AS frontend-build

WORKDIR /src

# Copy only what the Vite build needs first (better layer caching)
COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci

COPY frontend ./frontend
COPY backend ./backend

RUN cd frontend && npm run build


FROM python:3.10-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY --from=frontend-build /src/backend/dist /app/backend/dist

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default DB location inside the container; mount a volume at /data and set TNYR_DB_PATH=/data/urls.db
VOLUME ["/data"]

EXPOSE 5502

ENTRYPOINT ["/entrypoint.sh"]


