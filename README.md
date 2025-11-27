# VibeCodeJam Interview System

AI-powered система для проведения технических собеседований с автоматической генерацией задач и проверкой кода.

## Быстрый запуск приложения

### Docker

```powershell
# 1. Скачайте образ с Docker Hub
docker pull knoksss/vibecodejam-interview:latest

# 2. Запустите контейнер
docker run -d -p 5000:5000 -e LLM_TOKEN=sk--hwyMZDmxjPMm50_5LXTiA --name vibecodejam knoksss/vibecodejam-interview:latest

# 3. Откройте браузер
start http://localhost:5000
```

** ВАЖНО:** После запуска подождите 10-15 секунд, пока приложение полностью загрузится. LLM модель требует времени на инициализацию.

## Особенности работы

- **Первый запуск**: Может занять 15-20 секунд
- **Генерация задач**: AI модель работает 5-10 секунд на задачу
- **Оценка ответов**: Обработка занимает 3-7 секунд
- **Не перезагружайте страницу** во время генерации - дождитесь ответа

##  Возможности

-  AI-генерация задач по программированию (на базе LLM qwen3-coder-30b)
-  Автоматическая проверка кода с тестами
-  Анализ качества кода
-  Технические вопросы с оценкой
-  Итоговый отчет по собеседованию
-  Поддержка Python и JavaScript
-  Docker контейнеризация

##  Как пользоваться

1. **Откройте** http://localhost:5000
2. **Выберите** позицию и уровень (Frontend/Backend, Junior/Middle/Senior)
3. **Начните** собеседование
4. **Решайте** задачи по программированию (10 задач)
5. **Получите** детальный отчет с оценкой

##  Технологии

- **Backend:** Flask (Python 3.13)
- **AI/LLM:** OpenAI API (SciBox)
- **Code Runner:** subprocess с изоляцией
- **Frontend:** HTML/CSS/JavaScript
- **Deployment:** Docker, Docker Compose

##  Структура проекта

```
hahaton/
├── app.py                      # Flask приложение
├── code_runner.py              # Запуск и проверка кода
├── coding_tasks.py             # Генератор задач
├── requirements.txt            # Python зависимости
├── Dockerfile                  # Docker образ
├── docker-compose.yml          # Локальная разработка
├── docker-compose.prod.yml     # Production запуск
├── docker-publish.ps1          # Скрипт публикации (PowerShell)
├── docker-publish.bat          # Скрипт публикации (BAT)
├── templates/                  # HTML шаблоны
│   ├── index.html
│   ├── setup.html
│   ├── chat.html
│   └── coding.html
└── docs/
    ├── DOCKER_QUICKSTART.md    # Быстрый старт
    ├── DOCKER_INSTRUCTIONS.md  # Полная инструкция
    └── DOCKER_CHEATSHEET.md    # Шпаргалка команд
```

## Авторы

Команда Без лаб
- Китаева Дарья
- Галанова Екатерина
- Иващенко Юлия


 Docker Hub: [@knoksss](https://hub.docker.com/u/knoksss)
 GitHub: [@knoksss](https://github.com/knoksss)




