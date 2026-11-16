# RTSP → VideoGrace client

Экспериментальный CLI-клиент передаёт видео H.264 с RTSP-камеры в конференцию
VideoGrace. Вход на сервер выполняется как обычный пользователь через WSS,
без CAN. Протокольный код и медиатракт написаны на Liza; внешние ffmpeg,
Python и декодер не запускаются. OpenSSL обеспечивает TLS и HMAC-SHA256.

## Сборка и запуск

Нужны Clang и OpenSSL 3, как для [HTTPS/WSS](tls-transport.md).
На macOS при необходимости задайте `LIZA_OPENSSL_PREFIX` путём установки
OpenSSL, например `/opt/homebrew/opt/openssl@3`.

```sh
python3 -m liza build --project-root examples \
  examples/apps/liza_rtsp.liza -O 2 -o liza-rtsp
./liza-rtsp /private/path/rtsp.json
```

Рекомендуется `O2`. На `O0` фиксированные агрегаты создают крупные кадры
стека: в исследованном Windows x64 lowering около 3,05 МиБ у основного
цикла и 2,28 МиБ у вложенного WSS step. Сохраняется существующий TLS PE stack
reserve 8 МиБ; это отдельная величина от Region и `tls.managed_bytes()`.

Конфигурация — JSON до 4096 байт. Храните её с ограниченными правами: пароль
читается из файла, а не из argv. Реальные пароли и ответы с ключами не следует
сохранять в репозиторий.

```json
{
  "camera_ip": "192.0.2.20",
  "camera_port": 554,
  "camera_url": "rtsp://192.0.2.20/stream1",
  "vg_ip": "192.0.2.10",
  "vg_port": 443,
  "vg_peer": "demo.example.org",
  "login": "camera-user",
  "password": "replace-locally",
  "conference": "radio",
  "client_version": 617,
  "run_ms": 60000
}
```

`camera_ip` и `vg_ip` — числовые IPv4; DNS resolver не используется.
`camera_url` задаёт RTSP resource, а TCP подключается к `camera_ip:camera_port`.
`vg_peer` задаёт TLS identity/SNI и HTTP Host независимо от TCP IP.
Системное доверие обязательно; необязательный `ca_file` выбирает явный CA
для этой session. Переключения на небезопасный транспорт при TLS-ошибке нет.
`run_ms` — 100..3600000 мс. Без аргумента или при неверной конфигурации код
выхода 2. Нормальное завершение — 0; ошибки транспорта/протокола — ненулевой код.

## Протокол и владение

Один Reactor владеет UDP endpoint и двумя исходящими TCP-соединениями:
RTSP камеры и WSS сервера. UDP endpoint исключает TCP listener, но не
исходящие TCP slots. Числовой socket handle приложению не выдаётся.

RTSP выполняет `OPTIONS → DESCRIBE → SETUP → PLAY`, затем `GET_PARAMETER`
каждые 15 секунд. В первой версии используется RTP/RTCP interleaved TCP,
каналы 0/1; RTCP извлекается из framing и пропускается. Парсер сохраняет
частичные заголовки, body и `$` records, проверяет CSeq и границы размеров.
Остановка по сроку работы или SIGINT/SIGTERM отправляет `TEARDOWN` при живой
session, удаляет VG camera device, покидает конференцию и закрывает WSS/TLS.
Ожидание остановки ограничено 5 секундами, затем локальные ресурсы закрываются.
Это не гарантия получения последнего control-сообщения удалённой стороной.

Обычный VG control loop выполняет login, join, `device_params` и
`device_connect`. Device ID, SSRC, UDP port и binding key назначает сервер.
Объявленный сервером `0.0.0.0` или пустой RTP address означает IP текущего
WSS peer; числовой IPv4 используется явно. Другой hostname отвергается.
VGB1 Author handshake проверяет HMAC, SSRC, роли и nonce. Ключ — ровно
64 ASCII hex-байта, а не декодированные 32 байта. Без подтверждения handshake
за 5 секунд публикация завершается ошибкой. Binding обновляется каждые 5 секунд.

`net.reactor_udp_receive` возвращает тот же owned Buffer также при ошибке,
сохраняя его Region origin. Публичные UDP wrappers используют существующий
нативный endpoint. `hmac.sha256` принимает синхронные views, ключ 1..1024 байт
и сообщение до 4096 байт, возвращает 32 байта либо `HmacError`.
Эти лимиты не являются полным пределом внутренних allocations OpenSSL.

## H.264 и ограничения

Поддерживается один video track `H264/90000`, `packetization-mode=1`, SDP с
`sprop-parameter-sets`, `control` и `framesize`. Поддерживаются single NAL,
STAP-A и FU-A. Кадры не собираются и не декодируются. H.264 payload и RTP
timestamp/marker сохраняются; выходной PT — 102, SSRC назначен VG, sequence
ведётся локально, поскольку перед первым IDR вставляются SDP SPS/PPS.

До первого IDR пакеты отбрасываются. Разрыв sequence или некорректная
пакетизация закрывают gate до следующего IDR и повторной отправки SPS/PPS.
Уже отправленные части повреждённого access unit отозвать невозможно:
это не атомарная доставка кадров и не гарантия декодирования после потери.

Пределы: WS message 64 КиБ, исходящий WS payload 4 КиБ, RTSP header/body
фиксированы, interleaved record до 4096 байт, SPS/PPS до 256 байт каждый.
Входящие большие WS сообщения не расширяют CAN-профиль с его лимитом 4 КиБ.
Нет RTSP authentication, аудио, UDP-транспорта со стороны камеры, DNS,
автоматического reconnect, обработки смены SPS/PPS/разрешения и CAN lifecycle.
Камера должна поддерживать указанный профиль и keepalive.

## Приёмка

Независимый локальный стенд проверяет O0/O2: RTSP fragmentation/CSeq,
обычный WSS login/join, фрагментированный control message больше 32 КиБ,
VGB1 с Python HMAC oracle, точный RTP payload, SPS/PPS, PT/SSRC/sequence,
а также `TEARDOWN`, удаление устройства и WSS/TLS close. Дополнительные
тесты проверяют RFC 4231, изменение MAC, SDP/Base64, IDR recovery,
truncation, нулевой datagram и сохранение Buffer.
Обрыв камеры при активной передаче проверяется отдельно: ненулевой выход,
удаление VG-устройства и закрытие WSS без автоматического reconnect.

```sh
LIZA_TEST_TLS=1 python3 -m unittest discover -s tests -p 'test_rtsp*.py' -v
```

Live-приёмка 16 ноября 2026: H.264 High 4.0, 1920×1080, 25 fps с камеры
по RTSP/TCP опубликован в `radio` на `demo.videograce.ru`. Пользователь
подтвердил движущееся видео в веб-клиенте. Минутный прогон завершился кодом 0:
12 329 пакетов обработано bridge, 1 075 отброшено до IDR, 11 256 отправок
приняты ОС (включая два SPS/PPS), sequence discontinuities — 0.
Счётчик успешных send не измеряет полную доставку и не является benchmark.
