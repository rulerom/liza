---
description: "TLS-A: внутренний OpenSSL 3 transport adapter, ограниченный ciphertext pump, явный deadline и проверка ресурсов перед публичным HTTPS/WSS API."
---

# TLS transport: TLS-A и граница TLS-B

TLS-A реализует **внутренний C-адаптер транспорта**, а не готовый HTTPS/WSS
клиент Liza. Он находится в `liza/runtime/tls.h` и `tls_openssl.c`; сейчас
вызывается native acceptance harness. Language binding, move-only TLS resource
в Semantic IR, trust store ОС и подключение к клиентам из
[HTTP/WebSocket](http-websocket.md) остаются задачами TLS-B.

OpenSSL 3 выполняет TLS 1.2/1.3. HTTP parser, WebSocket framing и управление
приложением остаются на Liza; TLS backend не содержит HTTP/WebSocket и не
получает socket descriptor. Обычная сборка Liza не получает зависимости от
OpenSSL: этот backend пока собирается только явно выбранной приёмкой TLS-A.

## Владение и результаты

| Объект | Владелец |
| --- | --- |
| TCP socket, Reactor, readiness и ciphertext offsets | Вызывающая сторона |
| SSL/SSL_CTX, пара BIO и staging buffers | TLS session, один native thread |
| Входной plaintext/ciphertext и буфер результата | Caller; указатель не сохраняется |
| CA file и peer name | Caller; создание синхронно загружает/копирует настройки |
| Монотонные часы и абсолютный deadline | Caller задаёт время; session проверяет срок |

Результат содержит status, count, wants и state. Успешная plaintext-запись
подтверждает приём TLS engine, а не доставку по TCP или приложению сервера.
WANT не подтверждает plaintext progress. INPUT/OUTPUT относятся к ciphertext:
это не готовая маска `poll` и не разрешение постоянно ждать writable socket.

`feed` и `drain` обслуживают ограниченные BIO rings и могут продвинуть только
часть данных. Caller сохраняет offsets. При заполненном входном BIO нужно
дать TLS engine потребить уже принятые данные. При pending output сначала
нужно сохранить/отправить ciphertext, затем продолжать операцию.

TLS может произвести plaintext или завершить handshake без нового события ОС.
После успешного шага caller должен выполнить следующий доступный шаг, а не
сразу уходить в `poll`. Непрочитанные данные OpenSSL также не требуют нового
kernel readiness. Реальный Reactor harness проверяет этот переход.

При WANT во время write caller повторяет те же байты и длину. Адаптер хранит
собственную копию до завершения: физический адрес caller buffer может измениться,
но другое содержимое отвергается. Одновременно допускается одна незавершённая
plaintext-запись; переключение на read/shutdown до её завершения отклоняется.
Правило повторения следует
[контракту SSL_write](https://docs.openssl.org/3.5/man3/SSL_write/).

## Authentication без публичного небезопасного режима

TLS-A требует **явный CA file и непустой peer identity**. Нет `verify_none`,
insecure flag или перехода на plain TCP после ошибки TLS. Даже тестовый
адаптер не принимает application data до успешной проверки handshake.

Проверяются цепочка и время сертификата, DNS hostname либо IP SAN. DNS peer
также задаёт SNI; literal IP не отправляется как SNI. CN fallback и partial
wildcards отключены. Применяются verify depth 8 и лимит certificate list
64 КиБ. Ключи и тестовые сертификаты генерируются локально для каждого прогона;
в репозиторий они не записываются.

**Это ещё не TLS-B:** тестовый/явный CA file не заменяет trust store ОС.
Импорт доверенных корней Linux/macOS/Windows, политика конфигурации и публичное
представление ошибок должны пройти самостоятельную приёмку до объявления
HTTPS/WSS клиента. Проверка имени и SNI — разные операции;
[документация OpenSSL](https://docs.openssl.org/3.5/man3/SSL_set1_host/)
описывает их отдельно.

## Deadline и завершение

Состояния: Handshake → Open → Closing → Done; ошибка или deadline переводят
session в Dead. Первый срез использует один абсолютный срок ограниченной сессии,
который не сдвигается при progress. Время проверяется на каждой операции;
обратный ход часов отвергается. Это кооперативные проверки, без прерывания
одного вызова OpenSSL или вытесняющего ограничения CPU.

Нормальный close требует обмена `close_notify` **и отправки оставшегося
ciphertext**. TCP EOF без TLS close_notify — ошибка, а не успешный пустой read.
Plaintext read/write после закрытия отвергаются. Destroy без завершённого
shutdown — явный abort локальной TLS session; он ничего не утверждает о
доставке и никогда не закрывает чужой socket.

Все обращения и destroy выполняет создавший session thread. Foreign-thread
вызов отклоняется. После destroy C pointer недействителен: текущий внутренний
caller обязан соблюдать это правило; статическая move-only проверка будущего
Liza resource в этот PR не входит. Backend не создаёт worker threads и не
передаёт операции в background.

## Память

Ciphertext rings имеют ёмкость по 32768 байт в каждом направлении; plaintext
staging buffers — по 4096 байт для read/write. `liza_tls_managed_bytes()`
отчитывается о размере структуры адаптера и суммарной ёмкости rings.

Это **не предел RSS или всех OpenSSL allocations**: внутренние TLS buffers,
сертификаты, provider state, BIO metadata, allocator overhead, стеки и OS socket
buffers учитываются отдельно. Приёмка намеренно заполняет ring, проверяет
backpressure, отсутствие ложного plaintext progress и корректный retry.

## Приёмка

На macOS с установленным OpenSSL 3:

```sh
LIZA_TEST_TLS=1 LIZA_OPENSSL_PREFIX=/opt/homebrew/opt/openssl@3 \
  python3.12 -m unittest discover -s tests -p test_tls_transport.py -v
```

В Linux используются development files и `pkg-config openssl`; Windows workflow
использует vcpkg `openssl:x64-windows`. Без `LIZA_TEST_TLS=1` опциональная
приёмка пропускается и не требует OpenSSL для обычных compiler tests.

Три test methods выполняют 24 native сценария при O0/O2: boundary/thread affinity,
memory-pair TLS 1.2/1.3, насыщение output ring, retry с изменённым/перемещённым
caller buffer, TLS 1.3 key update, close, реальный TCP Reactor echo с однобайтовыми
ciphertext writes и семибайтовыми reads, DNS/IP identity, неизвестный CA,
просроченный сертификат, hostname/IP mismatch, deadline и abrupt EOF.
Принудительно маленькие I/O — приёмка корректности, не benchmark эффективности.
Workflow `TLS-A transport` содержит Linux/macOS/Windows matrix.

TLS-B должен добавить публичный owned TLS transport, системные trust roots и
композицию с HTTP/WS без переписывания parser. DNS, chunked, CAN и scoped groups
не являются частью TLS-A.

Обязательные свойства TLS-B:

- Resource budget отдельно отражает управляемую память и native allocations;
  `liza_tls_managed_bytes()` не становится полным лимитом памяти сессии.
- Move-only session запрещает copy, double destroy и use-after-move на уровне
  языка; для этого нужны отрицательные compiler tests, а не только C contract.
- Typed Result различает transport failure, verification failure, deadline и
  штатное TLS-закрытие. WANT отражает требуемый прогресс, а не безусловный poll.
- Внутренние данные TLS обрабатываются до ожидания нового kernel event.
- Graceful close подтверждается только после завершения TLS shutdown и передачи
  последних ciphertext bytes в TCP. Это две отдельные стадии; они не обещают
  прикладного подтверждения получения сервером.
