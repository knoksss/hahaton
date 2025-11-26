#!/bin/bash

# Скрипт для запуска приложения в Docker

echo "🚀 Запуск VIbeCode Jam Interview System..."

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Проверка наличия Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен."
    exit 1
fi

echo "✅ Docker и Docker Compose найдены"

# Остановка существующих контейнеров
echo "🛑 Остановка существующих контейнеров..."
docker-compose down

# Сборка образа
echo "🔨 Сборка Docker образа..."
docker-compose build

# Запуск контейнеров
echo "🐳 Запуск контейнеров..."
docker-compose up -d

# Ожидание запуска
echo "⏳ Ожидание запуска приложения..."
sleep 5

# Проверка статуса
if docker ps | grep -q vibecodejam_interview; then
    echo "✅ Приложение успешно запущено!"
    echo "🌐 Откройте в браузере: http://localhost:5000"
    echo ""
    echo "📊 Для просмотра логов: docker-compose logs -f"
    echo "🛑 Для остановки: docker-compose down"
else
    echo "❌ Ошибка запуска. Проверьте логи: docker-compose logs"
    exit 1
fi
