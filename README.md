# Async Payment Processing Service

Асинхронный сервис обработки платежей. API принимает запрос и сразу возвращает `202 Accepted`; дальнейшая обработка выполняется воркером через RabbitMQ. Результат отправляется на `webhook_url` клиента.

## Стек

- Python 3.12+, FastAPI и Pydantic v2;
- PostgreSQL, async SQLAlchemy 2.0 и Alembic;
- RabbitMQ и FastStream;
- Docker Compose.

## Архитектура

```text
Client -> API -> PostgreSQL (payments + outbox)
                   |
                   v
            outbox publisher -> RabbitMQ payments.new -> worker
                                                     |
                                                     v
                                            payment gateway emulator
                                                     |
                                                     v
                                                  webhook
```

`POST /api/v1/payments` в одной транзакции записывает платёж и outbox-событие. Отдельный publisher читает зафиксированные события и публикует их в RabbitMQ. Запись outbox помечается опубликованной только после подтверждённой публикации. Поэтому недоступность RabbitMQ не приводит к потере уже принятого платежа.

Доставка через RabbitMQ имеет семантику at-least-once. Consumer проверяет состояние платежа перед обработкой: уже финальный платёж не отправляется повторно в платёжный шлюз. Получатель webhook также должен быть идемпотентным по `payment_id`, поскольку при аварийных сценариях сетевой протокол не может гарантировать exactly-once доставку.

## Быстрый старт

1. Скопируйте шаблон окружения и задайте безопасный ключ:

   ```powershell
   Copy-Item .env.example .env
   ```

2. В `.env` поменяйте `API_KEY`. Не публикуйте этот файл в Git.

3. Запустите сервисы:

   ```powershell
   docker compose up --build
   ```

4. Проверьте API:

   ```powershell
   curl http://localhost:8000/health
   ```

API доступен на `http://localhost:8000`, интерактивная документация — на `http://localhost:8000/docs`. RabbitMQ Management UI доступен на `http://localhost:15672` (по умолчанию `guest` / `guest`, только для локального запуска).

Для остановки выполните `docker compose down`. Чтобы вместе с контейнерами удалить локальные данные PostgreSQL, используйте `docker compose down -v`.

## API

Все endpoint'ы платежей требуют заголовок `X-API-Key`.

### Создание платежа

`POST /api/v1/payments` требует также непустой `Idempotency-Key`.

```powershell
$headers = @{
  "X-API-Key" = "change-me-before-production"
  "Idempotency-Key" = "order-1001"
}

$body = @{
  amount = "1500.00"
  currency = "RUB"
  description = "Оплата заказа №1001"
  metadata = @{ order_id = "1001" }
  webhook_url = "https://webhook.site/your-unique-url"
} | ConvertTo-Json -Depth 4

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/payments" `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

Ответ:

```json
{
  "payment_id": "2ee1c5c1-477b-4b7a-a0f7-1e3e90e07452",
  "status": "pending",
  "created_at": "2026-11-09T12:00:00+00:00"
}
```

Повторный запрос с тем же `Idempotency-Key` возвращает исходный платёж и не создаёт дубликат платежа или outbox-события. В текущем контракте body повторного запроса не сравнивается с исходным: ключ считается идентификатором операции клиента.

### Получение платежа

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/payments/<payment_id>" `
  -Headers @{ "X-API-Key" = "change-me-before-production" }
```

Поля `status` принимают значения `pending`, `succeeded` или `failed`. После обработки также возвращается `processed_at`.

## Очереди, retry и DLQ

- `payments.new` — durable рабочая очередь;
- `payments` — direct exchange для рабочих событий;
- `payments.dlx` и `payments.dlq` — durable dead-letter exchange и очередь;
- consumer делает до трёх попыток обработки сообщений, завершившихся исключением; исчерпанные сообщения направляются в DLQ;
- webhook получает до трёх HTTP-попыток с задержками из `RETRY_DELAYS_SECONDS` (по умолчанию 1 и 2 секунды между попытками). Состояние попыток хранится в записи платежа.

Смотрите очереди и сообщения DLQ в Management UI RabbitMQ. Ошибки webhook сохраняются в `webhook_last_error`; успешная доставка — в `webhook_delivered_at`.

## Конфигурация

| Переменная | Назначение |
| --- | --- |
| `API_KEY` | Статический ключ для HTTP API. |
| `DATABASE_URL` | Асинхронный SQLAlchemy URL PostgreSQL. |
| `RABBITMQ_URL` | URL RabbitMQ. |
| `WEBHOOK_TIMEOUT_SECONDS` | Таймаут HTTP webhook. |
| `OUTBOX_POLL_INTERVAL_SECONDS` | Интервал опроса pending outbox-событий. |
| `OUTBOX_BATCH_SIZE` | Максимум событий за одну публикацию. |
| `PROCESSING_MIN_DELAY_SECONDS` / `PROCESSING_MAX_DELAY_SECONDS` | Границы задержки эмулятора шлюза. |
| `PROCESSING_SUCCESS_RATE` | Вероятность успешной обработки. |
| `RETRY_DELAYS_SECONDS` | Экспоненциальные задержки retry в секундах. Количество значений равно числу попыток webhook. |

## Разработка и тесты

```powershell
python -m pip install -e ".[dev]"
python -m pytest
```

Перед изменением схемы БД создавайте новую миграцию Alembic и проверяйте её на чистой базе:

```powershell
alembic upgrade head
```

## Публикация на GitHub

В репозиторий безопасно добавлять `.env.example`, но не `.env`. Перед первым push проверьте:

```powershell
git status
git diff --cached
```

Убедитесь, что реальные API-ключи, DSN с паролями и данные webhook не попали в staging area.
