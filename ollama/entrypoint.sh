#!/bin/bash
set -e

echo "🚀 Starting Ollama server..."
ollama serve &

# Ждем запуска Ollama
sleep 5

echo "📦 Checking and pulling models..."

# Функция для проверки и загрузки модели
pull_model() {
    local model=$1
    echo "Checking model: $model"
    
    if ollama list | grep -q "$model"; then
        echo "✅ Model $model already exists"
    else
        echo "⬇️  Pulling model $model..."
        ollama pull $model
        echo "✅ Model $model pulled successfully"
    fi
}

# Загрузка необходимых моделей
pull_model "phi"              # Для SWOT и аудитории (2.7B)
pull_model "qwen2.5:7b"       # Для ценностного предложения (7B)
pull_model "llama2:7b"        # Для команды (7B)
pull_model "mistral:7b"       # Для технического стека (7B)

echo "🎉 All models are ready!"

# Показываем список загруженных моделей
ollama list

# Держим процесс запущенным
wait