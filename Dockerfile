FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app appuser

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:app cmd ./cmd
COPY --chown=appuser:app internal ./internal
COPY --chown=appuser:app openapi.yaml ./

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "from os import getenv; from urllib.request import urlopen; urlopen('http://127.0.0.1:' + getenv('HTTP_PORT', '8080') + '/api/v1/health', timeout=2.5)" || exit 1

CMD ["python", "-m", "cmd.app.main"]

FROM runtime AS test
USER root
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY --chown=appuser:app tests ./tests
USER appuser
CMD ["python", "-P", "tests/run_unit.py"]
