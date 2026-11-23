# RTSP service on macOS

Этот профиль упаковывает один RTSP → VideoGrace connector как системную службу
macOS. Медиатракт, parser и внутренний reconnect остаются в Liza. Небольшой
нативный launcher отвечает только за дочерний процесс, логи и состояние.
Python нужен для сборки и административных команд; работающая служба его не
запускает. Linux/systemd пока не входит в этот профиль.

## Сборка артефакта

Нужны macOS, Xcode Command Line Tools/Clang, Python 3.9+ и OpenSSL 3.
Используйте чистый checkout выбранного commit:

```sh
git rev-parse HEAD
export LIZA_OPENSSL_PREFIX=/opt/homebrew/opt/openssl@3
python3 packaging/macos/rtsp/build.py /private/tmp/liza-rtsp-release
```

Для Intel Mac укажите соответствующий путь OpenSSL. Артефакт собирается под
архитектуру текущего Mac; universal binary не создаётся. `manifest.json`
содержит commit, O2, версии Python/Clang/SDK/OpenSSL, архитектуру и SHA-256
каждого файла. Dirty checkout отклоняется. `--allow-dirty` предназначен только
для разработки: такой артефакт установщик отвергает.

Библиотеки OpenSSL копируются в `lib`, ссылки заменяются на относительные;
Homebrew не нужен во время исполнения. Включены лицензии Liza и OpenSSL.
Mach-O файлы подписываются ad-hoc; это не Developer ID/notarization и не
готовая публичная поставка через Gatekeeper. SHA проверяет целостность,
но не подлинность источника: берите release из доверенной сборки.
Manifest и инструкция позволяют повторить сборку; побайтовая идентичность
результатов разных SDK/компиляторов не заявляется.

## Конфигурация и установка

Подготовьте конфигурацию по [контракту клиента](rtsp-client.md). Для службы
обязательно задайте `run_ms: 0` и актуальный `client_version`. Пароль хранится
только в файле; не передавайте JSON или пароль в shell-команде. Пример из
документации содержит только фиктивные значения.
Для исследованной камеры используется `rtp_pace_ms: 1`; диапазон 0..5 и
ограничение PPS описаны в контракте клиента. По умолчанию pacing отключён.

```sh
chmod 600 /private/path/rtsp.json
sudo python3 /private/tmp/liza-rtsp-release/rtspctl.py --instance camera \
  install /private/tmp/liza-rtsp-release --user YOUR_UNPRIVILEGED_USER \
  --config /private/path/rtsp.json
```

Выберите существующего непривилегированного пользователя. Установщик не создаёт
аккаунт и не запускает медиаклиент от root. Не устанавливайте службу параллельно
уже работающему CLI с тем же VideoGrace account/device.

Стабильные пути:

| Путь | Назначение |
| --- | --- |
| `/Library/Application Support/Liza/RTSP/camera/releases/<release>/` | root-owned бинарники, библиотеки и manifest |
| `…/camera/current` | активный release |
| `…/camera/previous` | предыдущий release для отката |
| `…/camera/config/config.json` | конфигурация, 0600, владелец — service user |
| `…/camera/state/` | приватные логи, lock, статус и attention marker |
| `/Library/LaunchDaemons/ru.liza.rtsp.camera.plist` | системный LaunchDaemon, root-owned 0644 |

Каталоги config/state имеют права 0700. Путь конфигурации виден в argv, её
содержимое — нет. Не включайте shell tracing и не публикуйте сам файл при
диагностике. Доступ к CA-файлу, если он задан, также должен иметь service user.

LaunchDaemon запускается при загрузке macOS без пользовательского login.
`KeepAlive.SuccessfulExit=false` восстанавливает аварийный выход launcher.
При signal-crash дочернего процесса launcher возвращает ненулевой статус;
при постоянной ошибке приложения сохраняет `attention` и возвращает 0.
Поэтому неверные credentials, версия, TLS/config/resource ошибки не вызывают
цикл перезапусков. Сохранённый attention запрещает новый запуск также после
перезагрузки, пока оператор явно не выполнит start/restart.

Временные сетевые отказы обслуживает **внутренний reconnect Liza**, без нового
процесса. launchd не заменяет этот механизм. Аварийные перезапуски ограничены
`ThrottleInterval=30`; гарантии непрерывного видео при отказах нет.
Политика launchd описана в [руководстве Apple](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)
и локальной `man launchd.plist`.

## Управление и диагностика

В командах ниже замените RELEASE на реальное имя установленного release и
используйте доступный администратору Python 3.9+:

```sh
sudo python3 '/Library/Application Support/Liza/RTSP/camera/releases/RELEASE/rtspctl.py' --instance camera status
sudo launchctl print system/ru.liza.rtsp.camera
sudo tail -n 50 '/Library/Application Support/Liza/RTSP/camera/state/service.log'
```

Для того же `rtspctl.py` доступны команды `stop`, `start` и `restart`.
`stop` выгружает job и передаёт SIGTERM. Liza получает до 5 секунд на штатное
завершение; launcher через 8 секунд останавливает зависшего child принудительно
и получает exit status. `ExitTimeOut=12` ограничивает ожидание launchd.
Child остаётся в process group launchd, чтобы не пережить аварийное завершение
launcher. Сам connector не создаёт дочерних процессов.

`status.json` обновляется атомарным rename примерно раз в секунду. Размер
фиксирован. Поля включают release, PID, generation, локальные counters,
возраст последнего RTP/успешной отправки ОС и код последнего reconnect.
Протокол telemetry приложения сообщает только числовые поля каждые 5 секунд,
вне побайтового media parser; пароли, URLs и ответы сервера туда не попадают.

| Состояние | Смысл |
| --- | --- |
| Running | свежая telemetry, подтверждённый binding, недавний RTP и принятые ОС отправки |
| Recovering | процесс запускается, восстанавливает сеть или ждёт активное медиа |
| Attention required | постоянная ошибка; исправить причину и явно перезапустить |
| Stopping / Stopped | запрошена остановка / приложение завершено |
| Unknown | нет статуса или последнее активное состояние устарело; проверить launchctl |

Running не подтверждает доставку зрителю. Порог свежести — 7 секунд;
`status` признаёт активный status устаревшим через 10 секунд. В начале новой
generation counters/признаки активности сбрасываются. Нулевые данные не
подменяются признаком живого PID. Серверный `UpdateRequired` требует изменения
`client_version`, а не ожидания reconnect; уточнение причины находится в логе.

Логи: `service.log` и три архива, каждый не более 1 МиБ, всего до 4 МиБ.
Неполные/чрезмерно длинные диагностические строки не накапливаются в памяти.
При отказе записи launcher останавливает child и не просит launchd о рестарте.
Если диск не позволяет сохранить даже attention/status, прежний файл может
остаться устаревшим: проверяйте launchctl и свободное место. Это не durable
journal и не доказательство успешного 24-часового медиапрогона.

Если служба не смогла открыть даже state/log, фиксированная причина startup
также пишется в системный журнал macOS (Console, сообщение `Liza RTSP service
startup failed`). Эти редкие сообщения не содержат конфигурацию; хранением
системного журнала управляет macOS, отдельно от четырёх файлов службы.

## Обновление, откат и удаление

Соберите новый release в другом каталоге, затем выполните `install` с ним,
**без** `--user` и `--config`. Сначала проверяются файлы, SHA и архитектура,
затем останавливается служба, атомарно переключается `current` и запускается
новая версия. Конфигурация, логи и state сохраняются. После изменения секретов
или версии в защищённом конфигурационном файле выполните `restart`.

`rollback` переключает на сохранённый `previous`, не изменяя конфигурацию.
Хранятся максимум два release. Перед третьей установкой оператор может выполнить
`prune`: он явно удаляет неактивный rollback artifact и отменяет возможность
отката к нему. Автоматического rollback при ошибке login нет: Attention остаётся
видимым, чтобы не скрыть проблему конфигурации.

`uninstall` выгружает job, удаляет plist, бинарники и ссылки. Config и state
**сохраняются**; после проверки их можно архивировать/удалить вручную. Для
повторной установки используйте `install` без --user/--config — сохранённая
конфигурация продолжит использоваться.

## Приёмка и границы

```sh
python3 -m unittest discover -s tests -p test_rtsp_service.py -v
```

Проверяются реальные дочерние процессы: активное медиа/восстановление,
fatal latch, signal-crash, SIGTERM с принудительным reap, ограничение логов,
права, контроль SHA, staged install/update/rollback/uninstall.
`--staging DIRECTORY` у административной команды создаёт изолированное дерево
и никогда не вызывает launchctl; это тест, а не установка службы.
Перезагрузка хоста и 24-часовой прогон — отдельная эксплуатационная приёмка;
staged-тесты не доказывают её прохождение.
