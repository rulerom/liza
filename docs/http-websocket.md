---
description: "Экспериментальные HTTP/1.1 GET и ws:// клиенты: протокол на Liza, bounded buffers, системное ожидание Reactor и OS entropy."
---

# HTTP и WebSocket: первый клиент

HTTP parsing, Upgrade, WebSocket framing, masking и проверка сообщения написаны
на Liza в `examples/httpws`. Это обычные source modules, а не обёртка над curl
или готовым HTTP/WebSocket-клиентом. Runtime предоставляет TCP/Reactor, часы
и новый узкий вызов `net.random_u32()` для nonce и масок.

Это первый экспериментальный клиент. Он работает с числовым IPv4 endpoint,
без DNS и TLS; `https://` и `wss://` пока не поддерживаются. Приложения используют
явный Reactor в одном потоке, а не scoped-группу. CAN ещё не реализован.

## Сборка

Из корня репозитория:

```sh
python3 -m liza build examples/liza_http.liza -o build/liza-http
python3 -m liza build examples/liza_ws.liza -o build/liza-ws
```

Примеры запуска с уже работающими локальными серверами:

```sh
./build/liza-http 127.0.0.1:8080 /hello.txt
./build/liza-ws 127.0.0.1:9000 /echo
```

Первый клиент выводит тело HTTP-ответа. Второй отправляет текст `hello Liza`,
выводит законченные входящие text/binary messages без добавления разделителей,
отвечает на ping и ожидает close от сервера. Это конечный demonstration client,
а не интерактивный CAN-сеанс. Обе программы имеют общий сетевой deadline 10 секунд;
непрерывный входящий трафик не перезапускает его. Синхронный вывод в stdout
не входит в гарантию прерываемого сетевого ожидания.

CLI принимает два ASCII-аргумента: `IPv4:port` и origin-form request target.
Текущий CLI ограничивает аргумент 63 символами; библиотечные функции допускают
authority до 255 и target до 1024 байт. Target уже должен быть percent-encoded;
CR/LF, пробелы, fragment и обратная косая черта отвергаются.

Коды завершения: 0 — успешное HTTP framing или WS close; 2 — неверная
конфигурация; 3 — transport/entropy/output error; 4 — protocol error,
неподдерживаемый профиль или превышенный лимит; 5 — сетевой deadline.

## HTTP GET

Реализован ограниченный HTTP/1.1 GET с `Connection: close` и
`Accept-Encoding: identity`. Response-head parser отделяет заголовки от тела,
включая случай их совместного прихода одним TCP read.

Поддерживаются тело по единственному `Content-Length` и тело до EOF.
Для 204/304 тело отсутствует. Дублирующийся или некорректный Content-Length,
ранний EOF и любой Transfer-Encoding отвергаются. Chunked decoding, redirects,
interim 1xx, HTTP/2, decompression и connection reuse не входят в этот срез.
Тело выводится как байты; статус 404 сам по себе не является транспортной ошибкой.

## WebSocket

Клиент создаёт случайный 16-байтовый nonce, формирует GET Upgrade и проверяет
HTTP 101, Upgrade, Connection и точный Sec-WebSocket-Accept. SHA-1 и Base64
для accept proof реализованы на Liza; SHA-1 здесь не является механизмом
аутентификации. Незапрошенные subprotocols и extensions отвергаются.

Кадры сервера должны быть немаскированными, с нулевыми RSV bits, допустимым
opcode и канонической длиной. Принимаются text/binary, continuation, ping/pong
и close. Проверяются порядок fragmentation, aggregate message size и UTF-8
через границы фрагментов. Control frames не нарушают сборку data message.
Close payload проверяется по коду и UTF-8 reason; профиль не принимает 1010
в close ни в одном направлении. EOF без close считается abnormal closure.
После протокольной ошибки соединение закрывается без попытки продолжить parsing.

Исходящие data frames в первом срезе не фрагментируются. Каждый клиентский кадр,
включая pong и close, получает свежую маску из ОС. Генератор не подменяется
счётчиком, часами или фиксированным тестовым seed. При ошибке entropy отправка
не продолжается. Это соответствует требованиям nonce/masking
[RFC 6455](https://www.rfc-editor.org/rfc/rfc6455).

## Память, ожидание и владение

| Ресурс | Лимит |
| --- | --- |
| HTTP response head | 8192 байта |
| HTTP body / собранное WS data message | 4096 байт |
| WS control payload | 125 байт |
| Входной heap buffer | 4096 байт в Region |
| Исходящие данные | Один pending Wire, без растущей очереди |

Wire имеет фиксированное хранилище 8192 байта; parser и вспомогательные массивы
занимают отдельную память, включая стек. Лимит Region не является пределом RSS.
Header и data message имеют независимые лимиты. Даже при разбиении на множество
WS fragments суммарный message limit не сбрасывается.

Частичные writes сохраняют offset. WouldBlock/Interrupted возвращают исполнение
к системному ожиданию с оставшимся deadline. Пока pending frame не отправлен,
приложение сохраняет непрочитанный остаток входного чанка. Поэтому ping/close,
пришедшие вместе с Upgrade или другим кадром, не теряются при смене фаз.
Reactor закрывает соединение; input Buffer освобождается до закрытия Region.

`net.random_u32()` использует `arc4random_buf` на macOS, `getrandom` на Linux и
`BCryptGenRandom` на Windows. Это effect `io`; разрешения scoped-ролей этим
изменением не расширяются.

## Проверка

```sh
python3 -m unittest discover -s tests -p test_httpws.py -v
```

Тесты используют независимый Python socket server и hashlib/Base64 oracle,
собирают Liza при O0/O2. Проверяются HTTP bodies, некорректный Upgrade,
дробление HTTP/TCP, coalesced input, extended frame length, fragmented UTF-8,
ping/pong/close, abnormal EOF, malformed frame vectors, deadline и принудительные
однобайтовые writes с WouldBlock. Инъекция отказа entropy отдельно проверяет,
что вместо свежей маски не отправляется подставное значение.
Workflow `HTTP and WebSocket client` запускает
эти проверки на Linux/macOS/Windows; локальный запуск не заменяет результаты CI.

Следующие самостоятельные задачи — DNS, TLS transport с проверкой имени и
сертификата, затем JSON/CAN и композиция с RTP owner. Текущий пример не заявляет
готовность production CAN или полного HTTP/WebSocket API.
