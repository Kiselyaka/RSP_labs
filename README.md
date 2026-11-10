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

## Лабораторная работа №5. PostgreSQL и Docker Compose

Запусти Docker Desktop. Если `.env` отсутствует, выполни в CMD
`copy .env.example .env`. Для существующего `.env` добавь недостающие
параметры PostgreSQL из шаблона. Задай `DB_PASSWORD` латинскими буквами
и цифрами, поскольку мигратор использует пароль в URL подключения.

```cmd
docker compose up --build -d
docker compose ps -a
curl.exe -i http://localhost:8080/api/v1/health
```

Ожидаемый результат: `db` и `app` имеют статус `healthy`, одноразовый
сервис `migrate` завершается с кодом 0, HTTP-запрос возвращает `200 OK`.
Для другого свободного порта измени `HTTP_PORT` в `.env` и URL запроса.

После запуска останови только БД командой `docker compose stop db`.
Повторный HTTP-запрос должен вернуть `503 Service Unavailable`. Восстанови
БД командой `docker compose start db` и дождись ответа `200 OK`.

Команды проверки миграций на пустой учебной базе:

```cmd
docker compose stop app
docker compose run --rm migrate version
docker compose run --rm migrate down 1
docker compose run --rm migrate up
docker compose up -d app
```

Команда `down 1` удаляет таблицы первой миграции вместе с их данными.
Для проверки тома создай тестовую запись, выполни `docker compose down`
и снова `docker compose up -d`. Запись должна остаться в PostgreSQL.

Открыть `psql` внутри контейнера с настройками из `.env` можно командой:

```cmd
docker compose exec db sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB"
```
