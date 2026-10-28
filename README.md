# Лабораторные работы по разработке серверных приложений

Репозиторий содержит материалы лабораторных работ по дисциплине
«Разработка серверных приложений».

## Лабораторная работа №1

**Тема:** проектирование архитектуры серверного приложения и предметной области.

**Вариант 13:** платформа проведения опросов и голосований (Survey Tool).

Материалы по архитектуре находятся в [ARCHITECTURE.md](ARCHITECTURE.md).

## Лабораторная работа №2

В [openapi.yaml](openapi.yaml) находится спецификация REST API Survey Tool
по стандарту OpenAPI 3.0.

## Лабораторная работа №3

Создан базовый сервер на Python и FastAPI с Layered Architecture,
конфигурацией из переменных окружения и health-check эндпоинтом.

### Запуск

1. Скопировать `.env.example` в `.env` или использовать подготовленный локальный `.env`.
2. Создать и активировать окружение: `python -m venv .venv`, затем `.venv\Scripts\activate`.
3. Установить зависимости: `pip install -r requirements.txt`.
4. Запустить сервер: `python -m cmd.app.main`.
5. Открыть `http://localhost:8080/api/v1/health` или Swagger UI: `http://localhost:8080/docs`.

Swagger UI использует [openapi.yaml](openapi.yaml) из второй лабораторной и
показывает полный спроектированный контракт API.

## Лабораторная работа №4

Приложение контейнеризировано с помощью Docker. В [.dockerignore](.dockerignore)
перечислены файлы, которые не должны попадать в контекст сборки, а [Dockerfile](Dockerfile)
создаёт минимальный образ Python, запускаемый от непривилегированного пользователя.

### Сборка и запуск контейнера

```bash
docker build -t survey-tool-api:lab4 .
docker run --name survey-tool-api -d -p 8080:8080 --env-file .env survey-tool-api:lab4
curl http://localhost:8080/api/v1/health
```

Просмотреть логи: `docker logs survey-tool-api`.

Остановить и удалить контейнер: `docker stop survey-tool-api` и `docker rm survey-tool-api`.
