FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN groupadd --system collector && useradd --system --gid collector --home-dir /app collector
COPY services/collector/pyproject.toml ./pyproject.toml
COPY services/collector/src ./src
RUN python -m pip install --no-cache-dir .
USER collector:collector
ENTRYPOINT ["eye-collector"]
CMD ["worker", "--once"]
