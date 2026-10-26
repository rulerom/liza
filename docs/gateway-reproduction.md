# Gateway R0 — функциональное воспроизведение

R0 проверяет воспроизводимость процедуры сборки и эксплуатационных тестов.
Он не переносит доказательства Relay на новый event loop и не заменяет VN0.
Текущий срез: опубликованный macOS pilot и отдельный Linux CI. Независимая приёмка
сторонним инженером **остаётся pending**; CI достаточен для этого этапа разработки,
но не объявляется внешним ревью или публичным релизом Gateway.

## Зафиксированная база

- Snapshot: `90c9c2f0eab565397db00ceb4a89cf27116c5bc2`, затем включённый в main через PR #36.
- Приложение: `examples/apps/liza_proxy_ops.liza`.
- SHA-256 приложения: `e6bd206d02112d50a549900395b378010772031c702aff90d5d65ed71b84ee41`.
- Pilot: macOS ARM64, Homebrew Clang 23.1.4, Python 3.9.6, target и flags в отчёте.
- 18 тестов на O0/O2, один платформенный skip. Сборки и тесты успешны.

[Исходный отчёт](https://github.com/rulerom/liza/blob/gateway-r0-baseline/maintenance/gateway-r0/macos-pilot/report.json),
[IR, бинарники, исходники приложения и журналы](https://github.com/rulerom/liza/blob/gateway-r0-baseline/maintenance/gateway-r0/macos-pilot/evidence.tar.gz),
[manifest SHA-256](https://github.com/rulerom/liza/blob/gateway-r0-baseline/maintenance/gateway-r0/macos-pilot/manifest.json).
Абсолютные пути в исходном отчёте описывают исторический прогон, а не требуемую
структуру каталогов другой машины. Теперь отчёт доступен без доступа к машине автора.

## Linux CI

`Gateway R0 reproduction` использует Ubuntu 24.04, Python **3.11.17** и проверяет
точную строку Clang **`Ubuntu clang version 18.1.3 (1ubuntu1)`**. При изменении версии
компилятора job завершается ошибкой, а baseline не обновляется молча. Clang взят
из уже прошедшей Linux-приёмки проекта; это другой toolchain, чем macOS pilot.

Хеши исполняемых файлов Python/Clang, полный version output, ОС, target и flags
сохраняются. Hosted image, linker и системные библиотеки не закреплены целиком:
это ещё **не герметичная toolchain**. Совпадение SHA бинарников между Linux/macOS
или разными системными библиотеками не требуется и не обещается.

Workflow запускается только при изменениях R0 runner, документа/артефактов R0 или
самого workflow; также доступен manual dispatch. Он не добавляет полный Gateway
прогон на каждое изменение языка. Snapshot фиксирован, поэтому успех этого workflow
не является проверкой произвольного нового HEAD компилятора или приложения.

## Процедура для инженера

Нужны Git, Python 3.9+, Clang и доступ к loopback-сокетам. Для сопоставимого Linux
прогона используйте указанные версии Python/Clang; PATH должен выбирать нужный Clang.
Возьмите чистый clone проекта с историей, включая указанный commit, и выполните:

```sh
python tools/gateway_r0/verify.py maintenance/gateway-r0/macos-pilot
python tools/gateway_r0/run.py \
  --commit 90c9c2f0eab565397db00ceb4a89cf27116c5bc2 \
  --expect-clang 'Ubuntu clang version 18.1.3 (1ubuntu1)' \
  --output /tmp/liza-gateway-r0
python tools/gateway_r0/verify.py /tmp/liza-gateway-r0
```

Выходной каталог должен быть новым. Для macOS pilot используется проверка строки
`Homebrew clang version 23.1.4`; на иной платформе задайте свою ожидаемую строку и
публикуйте результат отдельно. Windows/macOS CI этого R0-среза пока не заявляются.

Runner:

1. Получает полный commit ID и `git archive`, не копирует текущие/untracked файлы.
2. Проверяет пути архива, запрещает links и извлекает отдельный source tree.
3. Задаёт PYTHONPATH на snapshot, отключает user site и очищает внешние `LIZA_*`.
4. Собирает фактическое приложение O0/O2, сохраняет SIR, LLVM и команды linking.
5. Запускает `test_proxy_ops.py` и `test_proxy_lifecycle.py` из snapshot; ожидает
   соответственно 7 и 11 тестов. Изменение числа или падение — ошибка, не успех.
6. Сохраняет stdout/stderr, return codes, skips, версии и хеши исходников/артефактов.

Тесты поднимают реальные upstream/proxy на loopback и отдельно fault-injection
варианты с управляемыми часами. Проверяются connect deadline, idle, fixed drain,
half-close, full queue/WouldBlock, метрики потерь, clock regression и повторное
использование слотов. Сохранённые обычные бинарники собираются отдельно; тестовые
бинарники собираются из того же snapshot с необходимыми адаптерами и временными
портами. Нельзя выдавать тестовый fault-injection runtime за production runtime.

CI artifact `gateway-r0-linux` содержит report, source.tar, build, bootstrap и логи.
После скачивания его можно проверить той же командой `verify.py` без исполнения
бинарников и без распаковки source.tar. Проверка целостности не удостоверяет автора
результата: доверенный commit/workflow и происхождение manifest проверяются отдельно.

Внешний инженер должен приложить report, логи, manifest/артефакты, описание своей
машины и инструментов, имя/дату исполнителя и перечень отклонений. Только затем
можно отдельно отметить independent engineer acceptance как выполненную.

## Что здесь не измерено и не доказано

RSS, CPU, throughput и wall time завершения drain имеют статус **not_measured**.
Время выполнения unittest не является ни latency прокси, ни временем drain.
Для следующего измерительного среза нужны отдельные обычные прогоны без fault
injection, фиксированные нагрузки/число пар, сырые серии, платформа измерения RSS/CPU
и timestamp от запроса остановки до завершения процесса. Детерминированные часы
в функциональном тесте не заменяют такого измерения.

VN0 не выполнялся. R1/R2-A/B/C сохраняют собственные области, включая старый
baseline `liza_proxy.liza`; актуальный операционный event loop ими автоматически
не покрыт. Следующий шаг VN0 — отдельная проверка выбранных lifecycle-переходов
`liza_proxy_ops.liza` с явными контрактами clock, socket I/O и cleanup.
