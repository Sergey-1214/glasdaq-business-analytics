#!/bin/bash

# Скрипт для ручной инициализации моделей

echo "🔧 Startup Analyzer - Model Initialization"
echo "=========================================="

# Проверка наличия Ollama
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed locally"
    echo "Please run: docker-compose up -d ollama"
    exit 1
fi

# Функция для загрузки модели
pull_model() {
    local model=$1
    local description=$2
    
    echo ""
    echo "📦 Model: $model"
    echo "   Description: $description"
    
    if ollama list | grep -q "$model"; then
        echo "   ✅ Already exists"
    else
        echo "   ⬇️  Pulling..."
        ollama pull $model
        echo "   ✅ Done"
    fi
}

# Загрузка всех моделей
pull_model "phi" "Microsoft Phi-2 - SWOT & Audience"
pull_model "qwen2.5:7b" "Alibaba Qwen 2.5 - Value Proposition"
pull_model "llama2:7b" "Meta Llama 2 - Team Recommendations"
pull_model "mistral:7b" "Mistral - Technical Stack"

echo ""
echo "=========================================="
echo "🎉 All models are ready!"
echo ""
echo "📊 Model sizes:"
ollama list