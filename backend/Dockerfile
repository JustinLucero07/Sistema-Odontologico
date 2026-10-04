FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Sin privilegios de root: si alguien llegara a ejecutar código en el
# contenedor, no controlaría el sistema.
RUN useradd --create-home --uid 10001 odonto \
    && mkdir -p /app/storage && chown -R odonto:odonto /app/storage \
    && chmod +x /app/docker-entrypoint.sh
USER odonto

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
