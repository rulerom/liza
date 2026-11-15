---
description: "Bounded VideoGrace CAN example.echo worker на Liza: WSS, typed JSON, heartbeat, assignment fencing и cleanup."
---

# CAN Echo Worker

`examples/apps/liza_can.liza` — однопоточный worker для
[опубликованного CAN-протокола](https://videograce.ru/doc/developer/protocol/can/).
JSON и машина назначений написаны на Liza; TLS использует существующий backend.
Изменений compiler, production runtime и общей JSON-библиотеки нет.

## Запуск

```sh
python -m liza build --project-root examples examples/apps/liza_can.liza -o liza-can
./liza-can 192.0.2.1:443 server.example example-worker-01 /path/to/private-token - 120000
```

OpenSSL development files и параметры сборки описаны в [TLS](tls-transport.md).
Аргументы: числовой IPv4:port, проверяемый TLS peer, node ID, файл CAN service
token, необязательный CA file (`-` — системное доверие), длительность в миллисекундах.
По умолчанию — 120 секунд; допустимо 100–3600000 мс. Peer и node — до 63 ASCII
байт; CA path через CLI — до 63 ASCII байт. Token file использует platform Path,
token — до 512 байт без пробелов, разрешён завершающий CR/LF.

Token передаётся только в `hello` внутри аутентифицированного WSS. Не кладите
секрет в исходники, аргументы как значение token или репозиторий. Ограничьте
доступ к файлу средствами ОС. Диагностика не печатает token или payload.
CAN service token не предоставляет права администратора на постановку заданий.

## Профиль приложения

- WSS `/can`, role `worker`, capability `example.echo`, assignment protocol 1.
- Один активный assignment; `payload.text` — Unicode-строка до 512 UTF-8 байт.
- `job_ack` со статусом `accepted`, затем `job_event` со статусом `completed`
  и `data.echo`. Пустая строка допустима. Общего ACK от сервера нет.
- Идентичность: `(connection generation, job_id, assignment_id)`. IDs до 128 байт
  копируются в отдельные bounded значения; JsonDocument не переживает обработку.
- `job_cancel` отменяет только совпавшее назначение текущего соединения.
  Уже завершённое назначение не отменяется задним числом.
- Новое соединение получает новую generation и чистую очередь исходящих
  сообщений. Результаты предыдущего соединения не пересылаются.
- Неизвестный `job_type` получает `failed`; неподдерживаемый control с
  `expects_reply: true` получает отрицательный `control_result` с исходным
  `request_id`. Исходящих control-запросов приложение не создаёт.

Документ ограничен 4096 байтами и глубиной 16; строковое декодирование —
1024 байтами. Дубликаты JSON-ключей, неверные типы обязательных полей и Unicode
отклоняются. Это bounded профиль, а не поддержка общего серверного лимита 8 МиБ.
Четыре исходящих снимка имеют собственные IDs и payload; переполнение завершает
сеанс ошибкой, сообщения не теряются молча.

## Таймеры и завершение

Подключение/TLS/Upgrade, ожидание `hello_ok`, передача одного сообщения,
heartbeat-ответ и задание имеют отдельные сроки по 5 секунд. Heartbeat использует
согласованный интервал. Отправка следующего heartbeat не продлевает срок уже
ожидаемого ответа. Минимальный deadline ограничивает следующий Reactor poll.
При завершении общего времени worker отправляет WebSocket Close, затем TLS
close_notify и дренирует последний ciphertext; shutdown ограничен 3 секундами.

После транспортного разрыва разрешены две повторные попытки с паузой 500 мс
в пределах общего времени. Ошибки проверки сертификата, JSON/CAN, авторизации и
deadline автоматически не повторяются. Успех процесса означает локальное
graceful завершение; не является подтверждением хранения результата сервером.
Счётчики `completed/cancelled` относятся к последнему успешному сеансу.

Region содержит 21504 байта четырёх Buffer в бюджете 24576. Отдельно существуют
копируемые bounded структуры состояния и TLS managed budget. Эти числа не
являются полным пределом RSS: OpenSSL и ОС выделяют дополнительную память.
Deadline кооперативный, протокольный разбор и вывод не вытесняются таймером.

## Проверка

```sh
python -m unittest discover -s tests -p 'test_can_codec.py' -v
LIZA_TEST_TLS=1 python -m unittest discover -s tests -p 'test_can_worker.py' -v
```

Typed decoder проверяет 20 опубликованных примеров, мутации обязательных полей,
дубликаты и Unicode. Машина назначений проверяет generation, оба ID, повторное
завершение и heartbeat deadline. Независимый Python WSS-сервер проверяет wire
при O0/O2: hello, Unicode echo, heartbeat, ping/pong, отмену, повторное
использование слота, control correlation, policy error и переподключение.
Сертификаты тестового CA действуют только в данном тестовом сеансе.

Live-приёмка на demo.videograce.ru: 15 ноября 2026 администратор подтвердил
в интерфейсе сервера задание `1a1dfcfd939bce`, назначенное узлу
`liza-can-echo-acceptance`: `job_ack: accepted`, затем `job_event: completed`,
`data.echo: "hello from admin"`. Это подтверждение полного положительного
обмена с настоящим CAN-сервисом, а не только регистрации или локальной записи.
Отмена и переподключение проверены отдельным локальным WSS-стендом; данное
live-задание не является доказательством всех сценариев отказа или нагрузки.
