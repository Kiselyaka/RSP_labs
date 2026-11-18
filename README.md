# Лабораторные работы по разработке серверных приложений

Репозиторий содержит материалы лабораторных работ по дисциплине
«Разработка серверных приложений».

## Лабораторная работа №1

**Тема:** проектирование архитектуры серверного приложения и предметной области.

**Вариант 13:** платформа проведения опросов и голосований (Survey Tool).

Материалы по архитектуре находятся в [ARCHITECTURE.md](ARCHITECTURE.md).

## Лабораторная работа №2

В ЛР 2 спроектирована спецификация REST API Survey Tool по OpenAPI 3.0.
В текущей ветке [openapi.yaml](openapi.yaml) синхронизирован с реализованным
API ЛР 7 и использует OpenAPI 3.1. Исходный контракт сохранён в ветке ЛР 2.

## Лабораторная работа №3

Создан базовый сервер на Python и FastAPI с Layered Architecture,
конфигурацией из переменных окружения и health-check эндпоинтом.

### Запуск

1. Скопировать `.env.example` в `.env` или использовать подготовленный локальный `.env`.
2. Создать и активировать окружение: `python -m venv .venv`, затем `.venv\Scripts\activate`.
3. Установить зависимости: `pip install -r requirements.txt`.
4. Запустить сервер: `python -m cmd.app.main`.
5. Открыть `http://localhost:8080/api/v1/health` или Swagger UI: `http://localhost:8080/docs`.

В текущей ветке Swagger UI строится из реализованных маршрутов и DTO.
Его схема проверяется на совпадение с [openapi.yaml](openapi.yaml).

## Лабораторная работа №4

Приложение контейнеризировано с помощью Docker. В [.dockerignore](.dockerignore)
перечислены файлы, которые не должны попадать в контекст сборки, а [Dockerfile](Dockerfile)
создаёт минимальный образ Python, запускаемый от непривилегированного пользователя.

### Сборка и запуск контейнера

```bash
docker build --target runtime -t survey-tool-api:lab4 .
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

## Лабораторная работа №6

Репозитории пользователей, опросов и вопросов используют PostgreSQL и пул
соединений из ЛР №5. Контракты, реализация и ответы на вопросы описаны в
[ARCHITECTURE.md](ARCHITECTURE.md#лабораторная-работа-6-слой-доступа-к-данным).

Запуск интеграционных тестов из корня проекта в CMD. Команда создаёт отдельный
проект Compose с собственной базой и применяет миграцию перед тестами.

```cmd
docker compose -p rsp-lab6-check up -d db
docker compose -p rsp-lab6-check run --rm migrate
docker compose -p rsp-lab6-check build app
docker compose -p rsp-lab6-check run --rm --no-deps -e RUN_POSTGRES_TESTS=1 -v "%CD%\tests:/app/tests:ro" -v "%CD%\requirements-dev.txt:/tmp/requirements-dev.txt:ro" app sh -c "pip -q install --no-cache-dir --target /tmp/test-deps -r /tmp/requirements-dev.txt && PYTHONPATH=/tmp/test-deps python -P tests/run_integration.py"
docker compose -p rsp-lab6-check down
```

## Лабораторная работа №7

В ветке ЛР 8 формат ошибок ЛР 7 расширен, актуальный контракт описан в [LAB8.md](LAB8.md).

Реализованы сервисы пользователей и опросов, DTO, единая обработка ошибок,
CRUD пользователей, создание и публикация опросов. Ручные сценарии,
бизнес-правила и объяснение кода находятся в [LAB7.md](LAB7.md).

Запуск из основной папки репозитория в CMD с существующим `.env`:

```cmd
set "HTTP_PORT=8080"
docker compose -p rsp-lab6-demo up --build -d --wait
```

Swagger — http://127.0.0.1:8080/docs. Используется тот же проект и том,
что при демонстрации ЛР 5–6. Изменение схемы PostgreSQL не требуется.
На чистом клоне сначала выполни `copy .env.example .env` и заполни `DB_PASSWORD`.
Обычный запуск из папки проекта также работает через `docker compose up --build -d`.

Все модульные проверки ЛР 7 одной командой, без запуска БД и HTTP-сервера:

```cmd
docker compose -p rsp-lab6-demo run --build --rm unit
```

Локальный запуск после установки `requirements-dev.txt`:
`python -P tests/run_unit.py`. Тесты сервисов используют заглушки репозиториев,
HTTP-тесты — TestClient с подменой сервисов. Для приёмочных проверок на
отдельной учебной базе можно вызвать `python tests/check_lab7.py`.
Этот сценарий создаёт демонстрационные данные, часть из которых остаётся в БД.

В этой учебной версии доступ не требует JWT. Пользователь создаётся через
`POST /api/v1/users`, его UUID явно передаётся как `creatorId` при создании опроса.
Пароль хешируется scrypt и вместе с хешем исключён из DTO ответов. Вход и проверка
прав владельца потребуют отдельного механизма аутентификации. Прежние запланированные
маршруты регистрации, входа, изменения опросов и отправки ответов исключены из
активной схемы этой ветки, поскольку ещё не реализованы. Снимок схемы и Swagger
отражают одинаковые работающие операции.

## Резервная копия общей базы перед показом отката

Из CMD в папке репозитория выполни `backup-db.cmd`. Скрипт создаёт новый
файл `backups/survey_tool-ДАТА-ВРЕМЯ-СУФФИКС.dump` и контрольную сумму SHA256.
Архив содержит всю схему, данные всех таблиц и состояние `schema_migrations`.
Для последующего восстановления сохрани путь, напечатанный командой.
После добавления новых нужных записей создай новую копию.

После демонстрации `migrate down 1` и `migrate up` восстанови нужную копию:

```cmd
restore-db.cmd backups\ИМЯ_СОХРАНЕННОЙ_КОПИИ.dump
docker compose -p rsp-lab6-demo start app
```

Восстановление заменяет таблицы и записи состоянием из выбранного архива.
Скрипт проверяет контрольную сумму, временно останавливает работающий app
и выполняет восстановление одной транзакцией. Если app был остановлен
до вызова скрипта, запусти его сам командой выше. Перед восстановлением
заверши открытые транзакции DBeaver, чтобы они не удерживали блокировки.
Для восстановления достаточно работающего db, повторный migrate up
перед восстановлением не обязателен, поскольку архив содержит схему.

Команды `down -v` и `migrate down 1` удаляют данные разными способами.
Файл копии находится на Windows вне тома PostgreSQL и переживает эти операции.
Папка backups исключена из Git. Архив также содержит хеши паролей пользователей.


## Лабораторная работа №8

Валидация DTO реализована декларативно через Pydantic. Неверные поля
возвращаются списком в error.details, проверяется связь type и options,
параметры limit/offset и UUID, запрещены неизвестные поля и неверный JSON.
Схема, таблица правил и П1–П9 приведены в [LAB8.md](LAB8.md).

Новый формат ошибок:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [{"field": "displayName", "issue": "Minimum length is 2."}],
    "requestId": "e7f31c2d-3b41-4dd4-8136-1dc0634d48e1",
    "timestamp": "2026-11-18T12:00:00Z"
  }
}
```

X-Request-ID возвращается во всех ответах и совпадает с error.requestId
и идентификатором журнала. Неизвестное поле, неверный тип тела и неверный
JSON дают MALFORMED_JSON; нарушение ограничений DTO — VALIDATION_ERROR;
отказ бизнес-правила — INVALID_INPUT. Дубликат теперь имеет код CONFLICT.
При 500 полный текст и стек сохраняются в журнале, клиент получает общее сообщение.

Запуск использует ту же базу ЛР 5–7 и порт 8080:

```cmd
set "HTTP_PORT=8080"
docker compose -p rsp-lab6-demo up --build -d --wait
docker compose -p rsp-lab6-demo run --build --rm unit
```

Модульные и HTTP-тесты работают без запуска БД. Локальный вариант —
`python -P tests/run_unit.py` после установки requirements-dev.txt.
Для проверки 500 при отключённой БД вызывай GET /api/v1/users.
Health сохраняет 503, как в ЛР 5. Журнал можно прочитать через
`docker compose -p rsp-lab6-demo logs --tail 30 app`.
