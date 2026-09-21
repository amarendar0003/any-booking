FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# System deps needed for psycopg2 and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files (needs a dummy SECRET_KEY at build time)
RUN SECRET_KEY=build-time-placeholder \
    DATABASE_URL=sqlite:////tmp/build.sqlite3 \
    python manage.py collectstatic --noinput

EXPOSE 8080

# Run migrations then start gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120"]
