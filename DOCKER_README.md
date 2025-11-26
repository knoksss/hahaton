# VIbeCode Jam - AI Interview System

## 🚀 Запуск с Docker

### Предварительные требования
- Docker Desktop (для Windows/Mac) или Docker Engine (для Linux)
- Docker Compose

### 🐳 Быстрый старт

1. **Клонируйте репозиторий**
```bash
git clone https://github.com/knoksss/hahaton.git
cd hahaton
```

2. **Запустите приложение**
```bash
docker-compose up -d
```

3. **Откройте в браузере**
```
http://localhost:5000
```

### 📦 Команды Docker

**Запуск контейнера**
```bash
docker-compose up -d
```

**Остановка контейнера**
```bash
docker-compose down
```

**Просмотр логов**
```bash
docker-compose logs -f
```

**Пересборка образа**
```bash
docker-compose build --no-cache
docker-compose up -d
```

**Перезапуск**
```bash
docker-compose restart
```

### 🔧 Альтернативный запуск (без docker-compose)

**Сборка образа**
```bash
docker build -t vibecodejam-interview .
```

**Запуск контейнера**
```bash
docker run -d \
  --name vibecodejam \
  -p 5000:5000 \
  -e LLM_BASE_URL=https://llm.t1v.scibox.tech/v1 \
  -e LLM_MODEL=qwen3-coder-30b-a3b-instruct-fp8 \
  -e LLM_TOKEN=sk--hwyMZDmxjPMm50_5LXTiA \
  vibecodejam-interview
```

### 🛠️ Настройка окружения

Создайте файл `.env` в корне проекта:
```env
LLM_BASE_URL=https://llm.t1v.scibox.tech/v1
LLM_MODEL=qwen3-coder-30b-a3b-instruct-fp8
LLM_TOKEN=your_token_here
FLASK_ENV=production
```

Затем обновите `docker-compose.yml`:
```yaml
environment:
  - FLASK_APP=app.py
env_file:
  - .env
```

### 📊 Мониторинг

**Проверка статуса**
```bash
docker ps
```

**Использование ресурсов**
```bash
docker stats vibecodejam_interview
```

**Вход в контейнер**
```bash
docker exec -it vibecodejam_interview /bin/bash
```

### 🔍 Отладка

**Просмотр всех логов**
```bash
docker-compose logs
```

**Логи в реальном времени**
```bash
docker-compose logs -f web
```

**Очистка всего**
```bash
docker-compose down -v
docker system prune -a
```

### 📝 Особенности

- **Порт**: Приложение доступно на порту 5000
- **Автоперезапуск**: Контейнер автоматически перезапускается при падении
- **Volumes**: Код монтируется для разработки (можно убрать в продакшене)

### 🚢 Деплой в продакшен

Для продакшена рекомендуется:

1. Убрать volume монтирование в `docker-compose.yml`
2. Использовать `.env` файл вместо hardcoded переменных
3. Добавить nginx как reverse proxy
4. Использовать Gunicorn вместо Flask dev server

**Обновленный Dockerfile для продакшена:**
```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
```

### 🎯 Возможности системы

- ✅ 10 задач по программированию
- ✅ Прогрессивная сложность (easy → medium → hard)
- ✅ Специализация по должностям (Frontend, Backend, Data Scientist и др.)
- ✅ Автоматическое тестирование кода
- ✅ Анализ качества кода
- ✅ Адаптация под уровень (Junior/Middle/Senior)

---
Сделано с ❤️ для VIbeCode Jam Hackathon
