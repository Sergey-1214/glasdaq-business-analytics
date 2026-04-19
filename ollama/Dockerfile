FROM ollama/ollama:latest

# Установка дополнительных инструментов
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Создание скрипта инициализации
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# Создание директории для моделей
RUN mkdir -p /root/.ollama/models

EXPOSE 11434

ENTRYPOINT ["/entrypoint.sh"]
