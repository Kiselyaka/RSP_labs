# Лабораторная работа 8

## Результат

На основе ЛР 7 добавлены декларативная валидация всех входных DTO, проверка
связи type/options, единый JSON ошибок и X-Request-ID во всех HTTP-ответах.
Операции и база данных ЛР 5–7 сохраняются. Новая миграция не требуется.
Код находится в ветке feature/lab8-validation, Compose-проект — rsp-lab6-demo.

## Формат ошибки

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

requestId совпадает с заголовком X-Request-ID и идентификатором записи журнала.
details всегда присутствует как массив, при отсутствии полевых ошибок он пустой.
Имена вложенных полей имеют вид questions[0].options. Неизвестный путь получает
тот же формат с NOT_FOUND. Неожиданный сбой возвращает только общее сообщение.

| Код | HTTP | Причина |
| --- | --- | --- |
| VALIDATION_ERROR | 400 | Нарушение ограничений DTO, формата UUID и query |
| MALFORMED_JSON | 400 | Неверный JSON, неизвестное поле, неправильный тип значения тела |
| INVALID_INPUT | 400 | Нарушение бизнес-правила сервиса |
| NOT_FOUND | 404 | Ресурс или путь отсутствует |
| CONFLICT | 409 | Дубликат, ограничение связи или конфликт состояния |
| INTERNAL_ERROR | 500 | Непредвиденный сбой приложения или хранилища |
| METHOD_NOT_ALLOWED | 405 | Метод не поддерживается, сохраняется заголовок Allow |
| SERVICE_UNAVAILABLE | 503 | Проверка health обнаружила недоступную БД |

Проверку П9 задания выполняй через GET /api/v1/users, поскольку health
сохраняет специальное поведение 503 из ЛР 5. В ЛР 8 ошибки пользователей и
опросов имеют новый контракт вместо плоского формата ЛР 7.

## Декларативные правила

| DTO или поле | Правило | Соответствие PostgreSQL |
| --- | --- | --- |
| CreateUserRequest.email, UpdateUserRequest.email | Обязательная строка, trim, формат email, 3–255 | users.email NOT NULL, VARCHAR(255), UNIQUE |
| CreateUserRequest.password | Обязательная строка, 8–128 без trim | В БД хранится вычисленный хеш |
| CreateUserRequest.displayName, UpdateUserRequest.displayName | Обязательно, trim, 2–100 | users.display_name NOT NULL, VARCHAR(100) |
| CreateSurveyRequest.creatorId | Обязательный UUID | surveys.creator_id, внешний ключ |
| CreateSurveyRequest.title | Обязательно, trim, 3–200 | NOT NULL, VARCHAR(200), CHECK непустой строки |
| CreateSurveyRequest.description | Необязательная строка или null, максимум 2000 | TEXT, допускается NULL |
| CreateSurveyRequest.questions | Массив, максимум 100, по умолчанию пустой черновик | Таблица questions |
| QuestionInput.text | Обязательная строка, trim, 1–1000 | NOT NULL, CHECK непустого текста |
| QuestionInput.type | text, single_choice, multiple_choice | CHECK типа |
| QuestionInput.position, OptionInput.position | Обязательное строгое целое, 1–2147483647 | INTEGER, CHECK position > 0 |
| QuestionInput.isRequired | Строгий bool, по умолчанию true | BOOLEAN NOT NULL DEFAULT true |
| QuestionInput.options | Массив до 50, для type=text пустой | Связь таблиц и правило сервиса |
| OptionInput.text | Обязательная строка, trim, 1–500 | NOT NULL, CHECK непустого текста |
| GET users.limit, offset | limit 1–100, offset >= 0 | Параметры LIMIT/OFFSET |
| UUID в пути | Правильный формат UUID | Тип UUID |

Все DTO наследуют extra="forbid", включая вложенные вопросы и варианты.
Строка "1", дробное число и bool не приводятся к position. Отсутствующий
position отличается от явно переданного 0. Неверные типы в теле относятся к
MALFORMED_JSON, неверная строка UUID и query — к VALIDATION_ERROR.

Проверка options_match_type получает соседнее поле type через ValidationInfo.
Пустой черновик и вопрос выбора с одним вариантом разрешены для сохранения,
а готовность к публикации по-прежнему проверяет SurveyService. При прямом
вызове сервиса сохраняются его прежние проверки.

## Как работает обработка

RequestContextMiddleware выполняется до HTTP-обработчиков. Он создаёт UUID,
сохраняет его в request.state и ContextVar, добавляет X-Request-ID к ответу
и пишет строку о методе, пути и статусе. Контекст сбрасывается в finally.
Входной заголовок клиента не используется как серверный идентификатор.

Обработчики в controller/errors.py централизованно преобразуют исключения.
Для RequestValidationError собираются все ошибки Pydantic без input и ctx,
с отдельными безопасными сообщениями. Domain errors сохраняют смысл причин.
Неожиданные исключения и RepositoryError записываются с полным стеком и
requestId, а наружу возвращается INTERNAL_ERROR.

Внешний ASGI middleware направляет неожиданные исключения до начала ответа
в тот же центральный обработчик. Это позволяет сохранить заголовок и
контекст для 500. Уже начатый поток ответа не заменяется другим HTTP-ответом.
В обычных JSON-операциях проекта ошибка обрабатывается до отправки заголовков.

RequestLogFormatter формирует по одной JSON-строке на запись, включая стек
как строковое поле exception. Пароли, Authorization и тела запросов в access
журнал не записываются. Полный текст системного исключения остаётся в журнале
для диагностики и не включается в ответ клиенту.

## Запуск и тесты

В CMD из C:\Users\MSI\Desktop\rsp_labs:

```cmd
set "HTTP_PORT=8080"
docker compose -p rsp-lab6-demo up --build -d --wait
docker compose -p rsp-lab6-demo run --build --rm unit
```

Swagger — http://127.0.0.1:8080/docs. Локальная команда после установки
requirements-dev.txt — python -P tests/run_unit.py. Набор unit включает
сервисы ЛР 7, транспортные проверки и новый test_validation.py. PostgreSQL
для этих тестов не запускается, зависимости подменяются.

Схема Error и X-Request-ID описаны в openapi.yaml. Снимок OpenAPI проверяется
на равенство схеме работающих маршрутов отдельным тестом.

## Ручные проверки П1–П9

### П1 Несколько неправильных полей

В Swagger отправь POST /api/v1/users:

```json
{"email":"wrong","password":"short","displayName":" "}
```

Ожидается 400 VALIDATION_ERROR. В details должны быть email, password,
displayName. Значение короткого пароля в ошибке не повторяется.

### П2 Связь полей

POST /api/v1/surveys, UUID здесь нужен только в корректном формате:

```json
{
  "creatorId":"00000000-0000-0000-0000-000000000001",
  "title":"Проверка связи полей",
  "questions":[{
    "text":"Текстовый вопрос", "type":"text", "position":1,
    "options":[{"text":"Недопустимый вариант", "position":1}]
  }]
}
```

Ожидается 400 VALIDATION_ERROR с questions[0].options. Сервис не вызывается,
поэтому существование этого пользователя для проверки формы запроса не требуется.

### П3 Неизвестное поле

Добавь role="admin" к корректному телу POST /api/v1/users. Ожидается
400 MALFORMED_JSON, поле role и сообщение Unknown field. Создания записи не будет.

### П4 Неверный JSON

В CMD:

```cmd
curl.exe -i -X POST http://127.0.0.1:8080/api/v1/users -H "Content-Type: application/json" -d "{"
```

Ожидается 400 MALFORMED_JSON.

### П5 и П6 Параметры

```cmd
curl.exe -i "http://127.0.0.1:8080/api/v1/users?limit=1000"
curl.exe -i http://127.0.0.1:8080/api/v1/users/abc
```

Ожидается 400 VALIDATION_ERROR с limit и user_id соответственно.

### П7 Правило сервиса

Создай пользователя и пустой черновик через Swagger, затем вызови
POST /api/v1/surveys/{id}/publish. Ожидается 400 INVALID_INPUT, details пустой.
Это отличается от отказа DTO: форма запроса подходит, публикация нарушает правило.
Демонстрационные пользователь и опрос останутся в общей базе.

### П8 Отсутствующий ресурс

```cmd
curl.exe -i http://127.0.0.1:8080/api/v1/users/00000000-0000-0000-0000-000000000000
curl.exe -i http://127.0.0.1:8080/api/v1/unknown
```

Ожидается 404 NOT_FOUND с тем же форматом и X-Request-ID.

### П9 Отключённая база и связь с журналом

```cmd
docker compose -p rsp-lab6-demo stop db
curl.exe -i http://127.0.0.1:8080/api/v1/users
docker compose -p rsp-lab6-demo logs --tail 30 app
docker compose -p rsp-lab6-demo start db
```

Покажи 500 INTERNAL_ERROR с общим сообщением и requestId. В журнале найди
этот UUID: там будет полный текст исключения. Запусти базу даже если проверка
закончилась ошибкой. После восстановления пула health снова вернёт 200.
Сохранность данных при этой остановке обеспечивается существующим томом.

## Отчёт и контрольные вопросы

По заданию отчёт PDF на 4–6 страниц содержит таблицу правил DTO, коды ошибок,
ключевой код обработчика и middleware, результат тестов и П1–П9. Сохрани снимки
П1, П3 и П9, для последнего — ответ и запись журнала с одинаковым requestId.
ФИО, группа и ссылка на репозиторий добавляются при оформлении отчёта.

Для устной подготовки:

1. Вход может поступить от любого клиента, поэтому проверяются форма и смысл.
2. DTO проверяет формат; сервис — состояние и сценарий; БД — целостность.
3. Отсутствующее обязательное поле даёт missing; 0 проверяется как заданное значение.
4. extra="forbid" блокирует массовое присваивание лишних полей вроде role.
5. Общий обработчик обеспечивает одинаковые коды и структуру во всём API.
6. 4xx объясняет ошибку запроса, 5xx сообщает о сбое без раскрытия устройства сервера.
7. code подходит для программы, requestId связывает ответ с диагностикой журнала.
8. Middleware создаёт контекст до контроллера и добавляет заголовок при отправке ответа.

## Результаты выполненной проверки

Модульная команда из README завершилась с результатом 44 passed. На запущенном API проверены П1–П9, включая 500 при остановленной PostgreSQL и совпадение requestId с записью полного исключения в журнале. После запуска БД health вернулся к 200. Временные пользователь и опрос проверки удалены.

Перед запуском сохранена свежая копия общей базы. В скриптах backup-db.ps1 и restore-db.ps1 расчёт SHA256 переведён на .NET для совместимости с запуском из CMD без Get-FileHash.
