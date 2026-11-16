---
description: "TLS-A/B: move-only session, системная проверка сервера и HTTPS/WSS на Liza поверх Reactor и OpenSSL 3."
---

# TLS transport и HTTPS/WSS

TLS-A предоставляет OpenSSL 3 adapter, TLS-B — публичную move-only
`tls.Session`, системную проверку сервера и HTTPS/WSS-примеры на Liza.
HTTP parser и WebSocket framing остаются общими для plain и secure клиентов
в `examples/httpws`; TLS backend не знает HTTP и не владеет TCP socket.

OpenSSL 3 выполняет TLS 1.2/1.3. Он требуется только при сборке программы,
использующей `tls.*`, либо опциональной native-приёмки. Обычные HTTP/WS и
compiler tests не требуют установленного OpenSSL.

## Запуск HTTPS/WSS

```sh
export LIZA_OPENSSL_PREFIX=/opt/homebrew/opt/openssl@3
python3 -m liza build --project-root examples examples/apps/liza_https.liza -o /tmp/liza-https
python3 -m liza build --project-root examples examples/apps/liza_wss.liza -o /tmp/liza-wss
/tmp/liza-https 127.0.0.1:8443 / localhost ca.pem
```

Аргументы: числовой IPv4:port, target, проверяемый peer identity, необязательный
CA file. Без CA file используется системное доверие. CLI ограничивает каждый
аргумент 63 ASCII-байтами; библиотечный peer допускает до 253 байт, CA path —
до 4096 байт. DNS lookup отсутствует: имя для проверки/SNI и числовой адрес TCP
задаются независимо. Host header в примере содержит числовой адрес назначения.
Для WSS отправляется текст `Liza`; HTTP body/WS messages выводятся в stdout.

Коды завершения: 0 — протокол и graceful TLS/TCP close завершены; 2 — параметры;
3 — transport/output; 4 — protocol; 5 — deadline; 6 — configuration/resources;
7 — verification. Частичный HTTP body может быть выведен до поздней ошибки;
только код 0 подтверждает завершение. Нет insecure flag или plain fallback.

## Публичный ресурс

`tls.create(peer, managed_budget, now, deadline)` и
`tls.create_with_ca(peer, ca_file, managed_budget, now, deadline)` возвращают
`Result<tls.Session,TlsError>`. Session передаётся через `move`, не копируется
и требует `tls.destroy(move session)` на всех возвращающихся путях.
Компилятор отклоняет повторный destroy, use-after-move и потерянный ресурс.
Session остаётся привязанной к создавшему native thread; TLS не добавлен
в capabilities workers/channels/scoped groups.

`handshake`, `write`, `feed`, `eof`, `shutdown` заимствуют session и возвращают
`Result<TlsStep,TlsError>`. `read` и `drain` потребляют Buffer и возвращают
`TlsRead` с тем же owned Buffer и Result; storage origin сохраняется.
`TlsStep` содержит count, wants, state и outcome (`Progress`, `Want`, `Closed`).
`TlsError` различает `Verification(code)`, `Deadline`, `Protocol(reason)`,
`Transport(ReactorError)`, `Output`, параметры, бюджет, allocation и контекст.
Нормальное TLS-закрытие не кодируется как ошибка транспорта.

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

TCP `WouldBlock`/`Interrupted` снимает разрешение на запись независимо от
входного progress. Повторная запись разрешена после writable/error readiness.
Пока есть полезная обработка input, readiness проверяется с timeout 0
не чаще чем после 256 шагов обработки;
без progress используется блокирующее ожидание оставшегося deadline.
После WANT с OUTPUT и нулевым plaintext progress исходный plaintext сохраняется
и повторяется только после успешного `tls.drain`, освободившего BIO.

## Authentication без публичного небезопасного режима

Каждая session требует непустой peer identity и аутентификацию сервера.
Проверяются цепочка, сроки, назначение serverAuth и DNS/IP SAN. DNS peer
задаёт SNI, literal IP не отправляется как SNI. CN fallback и partial wildcards
отключены. Проверка имени и SNI — отдельные операции
([OpenSSL](https://docs.openssl.org/3.5/man3/SSL_set1_host/)).

| Платформа | Default trust policy |
| --- | --- |
| Linux | OpenSSL default verify paths дистрибутива |
| macOS | SecTrust с SSL server policy и системными trust settings |
| Windows | CertGetCertificateChain и SSL chain policy |

Это проверка политикой ОС, а не экспорт списка корней в OpenSSL.
Явный CA file задаёт корни только данной session; macOS/Windows также проверяют
эту цепочку своей SSL policy. OS trust store никогда не меняется, в том числе
в тестах. Проверка закрывается отказом при недоступной policy или roots.

Network fetching отключён: недостающий intermediate не скачивается; online
OCSP/CRL и гарантия свежего revocation status не заявляются. Синхронные вызовы
политики ОС не имеют вытесняющего deadline. Ограничения: verify depth 8,
certificate list 64 КиБ; platform conversion — максимум 9 certificates,
custom anchors — 256 certificates / 2 МиБ DER. Native allocations OpenSSL и
политики ОС не входят в managed budget.

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
вызов отклоняется. После destroy C pointer недействителен; внутренний C caller обязан соблюдать
этот контракт. Публичный Liza resource дополнительно защищён статическим
move-only анализом. Backend не создаёт worker threads и не
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
  python3.12 -m unittest discover -s tests -p "test_tls*.py" -v
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
На Windows TLS-linker flags задают reserve основного стека PE-программы 8 МиБ,
чтобы O0-сборки протокольных клиентов с ограниченными агрегатами не упирались
в стандартный reserve 1 МиБ. Commit страниц происходит по необходимости.
Этот reserve не входит в `tls.managed_bytes()`. Явные stack budgets SG2 задаются
отдельно; legacy native threads, использующие default stack, наследуют PE reserve.

Workflow `TLS transport and clients` проверяет Linux/macOS/Windows.

TLS-B дополнительно проверяет ownership, сохранение Buffer origin, HTTPS с
TLS 1.2/1.3 и DNS/IP SAN, WSS с coalesced input/fragments/ping/close,
обязательную проверку CA/имени/срока, короткие ciphertext I/O и WouldBlock,
deadline и преждевременное HTTP body EOF. Сервер проверяет получение финального
close_notify; реальные OpenSSL данные обрабатываются до следующего poll.
Локальные test CA не устанавливаются в системное доверие. Default trust
отвергает fixture CA; положительные детерминированные тесты задают per-session
корни, сохраняя платформенный verifier.

DNS, chunked, CAN, TLS server, session pooling, HTTP/2 и интеграция со scoped
ролями остаются отдельными задачами. Это bounded экспериментальный клиент,
а не универсальная production HTTPS-библиотека.

Adversarial backpressure-приёмка использует реальные TLS/TCP и управляемую
инъекцию неготовности записи: 800 различных ping одновременно заполняют BIO
исходящими pong. Проверяются точное содержимое и порядок всех ответов,
сохранение ciphertext при partial writes, два периода `WouldBlock` (включая
shutdown), входной TLS progress во время блокировки и отсутствие TCP retry
без writable readiness / plaintext retry без BIO drain. При заполненном
входном BIO и удерживаемом TCP input ожидание readable отключается; отдельная
мутация проверяет отсутствие spin на этом уровне. Все три отрицательные
мутации отклоняются при O0/O2. Это детерминированная проверка контракта I/O,
а не измерение физической пропускной способности TCP.
