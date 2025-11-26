@echo off
REM Скрипт для запуска приложения в Docker на Windows

echo 🚀 Запуск VIbeCode Jam Interview System...

REM Проверка наличия Docker
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Docker не установлен. Установите Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Проверка наличия Docker Compose
where docker-compose >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Docker Compose не установлен.
    pause
    exit /b 1
)

echo ✅ Docker и Docker Compose найдены

REM Остановка существующих контейнеров
echo 🛑 Остановка существующих контейнеров...
docker-compose down

REM Сборка образа
echo 🔨 Сборка Docker образа...
docker-compose build

REM Запуск контейнеров
echo 🐳 Запуск контейнеров...
docker-compose up -d

REM Ожидание запуска
echo ⏳ Ожидание запуска приложения...
timeout /t 5 /nobreak >nul

REM Проверка статуса
docker ps | find "vibecodejam_interview" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✅ Приложение успешно запущено!
    echo 🌐 Откройте в браузере: http://localhost:5000
    echo.
    echo 📊 Для просмотра логов: docker-compose logs -f
    echo 🛑 Для остановки: docker-compose down
) else (
    echo ❌ Ошибка запуска. Проверьте логи: docker-compose logs
    pause
    exit /b 1
)

pause
