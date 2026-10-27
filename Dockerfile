FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    WHATPCT_DATA=/data

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY products.yaml /app/products.yaml
RUN adduser --disabled-password --gecos "" --uid 10001 app \
    && mkdir -p /data \
    && chown app:app /data

USER app
ENTRYPOINT ["python", "-m", "whatpercent"]
CMD ["collect"]
