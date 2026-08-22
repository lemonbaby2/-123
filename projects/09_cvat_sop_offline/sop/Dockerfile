FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOP_HOST=0.0.0.0 \
    SOP_PORT=8096 \
    SOP_DESKTOP_DIR=/app/runtime/desktop

WORKDIR /app
COPY source/server.py ./
COPY source/web ./web
COPY source/config ./config
RUN mkdir -p runtime models datasets

EXPOSE 8096
CMD ["python", "server.py"]
