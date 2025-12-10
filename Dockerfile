FROM python:3.11-bullseye

ENV DEBIAN_FRONTEND=noninteractive
ENV ACCEPT_EULA=Y
ENV PYTHONUNBUFFERED=1

# System deps + Microsoft ODBC Driver 17
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg2 apt-transport-https software-properties-common unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends msodbcsql17 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# App
WORKDIR /app
COPY api.py wsgi.py .env requirements.txt ./

# Python deps
RUN pip install --no-cache-dir -r requirements.txt

# App listens on 8000
EXPOSE 8000

# Set environment variables for the application
ENV FLASK_APP=api.py
ENV FLASK_ENV=production

# Run with Gunicorn
CMD ["gunicorn", "--workers", "3", "--threads", "8", "--bind", "0.0.0.0:8000", "wsgi:app"]