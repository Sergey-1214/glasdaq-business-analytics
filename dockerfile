FROM python:3.11-slim

WORKDIR /app

ARG SERVICE_NAME
ARG PORT

COPY services/${SERVICE_NAME}/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/${SERVICE_NAME}/ .
COPY shared/ ./shared/ 2>/dev/null || true

ENV PYTHONPATH=/app
ENV PORT=${PORT}

EXPOSE ${PORT}

CMD python main.py