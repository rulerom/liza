# Liza

*Founded October 18, 2026 · Основан 18 октября 2026 года.*

[Документация](https://liza.rulerom.com/) · [Быстрый старт](https://liza.rulerom.com/getting-started.html)

**Liza — системный язык программирования для переносимых вычислений с определённой семантикой и контролируемой стоимостью операций.**

*Liza — a systems programming language for portable computation with well-defined semantics and explicit control over execution costs.*

Контролируемая стоимость — пока проектная цель, а не реализованная гарантия. Она означает возможность управлять аллокациями, копированием и другими затратами, а не одинаковую производительность на всех процессорах.

Проект экспериментальный. Программа описывает значения, зависимости
вычислений, права на изменение состояния и эффекты. Физическое размещение данных
и машинные инструкции выбирает реализация в пределах этих контрактов.

Цель — лаконичный язык для сложных систем, включая HA-мессенджеры и ВКС,
с нативной компиляцией, без универсальных указателей и обязательного GC.
Это цель проекта, а не описание уже готовых возможностей.

## Что работает сейчас

Первый вертикальный срез: исходник → AST → типизированный Liza IR → LLVM IR
→ нативный исполняемый файл через Clang. Компилятор-прототип написан на Python
без сторонних зависимостей. Скомпилированной программе Python не нужен.
Поддерживаются `i8/i16/i32/i64`, `u8/u16/u32/u64`, `bool`, контекстные литералы,
неизменяемые привязки, локальные `var` и присваивание, явные `copy`/`move` с проверкой use-after-move, структуры-значения, обновление полей и элементов у `var`, фиксированные массивы и readonly views, `Text`, проверяемые `pure/io`, консоль, ограниченное чтение файлов и move-only `File` с чтением чанками, `enum`, исчерпывающий `match`, `Option<T>` и `Result<T,E>`, функции, `if/else`, `while`, `break`, `continue`, сравнения, короткозамкнутые `&&`/`||`,
побитовые операции, проверяемые сдвиги, checked/wrapping/saturating-арифметика,
деление, остаток и явные преобразования `T(x)`, `T.wrap(x)`, `T.saturate(x)`.
Пример выделения полей двух байтов RTP-заголовка: `examples/rtp_fields.liza`.

```liza
fn twice(value: u32) -> u32 : pure {
    return value * 2
}

fn main() -> u32 {
    answer = twice(20) + 2
    return answer
}
```

Пользовательские модули: `import`, `pub`, квалифицированные имена и приватные
поля. Вся программа компилируется в общий IR. [Контракт модулей](https://liza.rulerom.com/modules.html).

## Редактор

Для Zed есть подсветка `.liza`, скобки, отступы и Outline. Выполните
`zed: install dev extension` и выберите `editors/zed`.
[Инструкция установки](https://liza.rulerom.com/editor.html).

## Запуск

Нужны Python 3.9+ и Clang в PATH; проверено локально на macOS ARM64
с Python 3.9.6 и Apple Clang 21. Команды выполняются из корня репозитория.

```sh
python3 -m liza run examples/connection_table.liza -O 2
python3 -m liza run examples/hello.liza
python3 -m liza run examples/rtp_file.liza -O 2
python3 -m liza check examples/answer.liza
python3 -m liza emit-ir examples/answer.liza
python3 -m liza emit-llvm examples/answer.liza
python3 -m liza build examples/answer.liza
./build/answer
echo $?  # 42
python3 -m liza run examples/wrapping.liza
python3 -m unittest discover -s tests -v
```

`run` возвращает код завершения программы; `answer.liza` возвращает 42,
а не печатает текст. На POSIX оболочка видит младшие 8 бит результата `main`.
`build` принимает `-o PATH`, `-O 0` или `-O 2`, `--clang PATH`.
`emit-ir` и `emit-llvm` принимают `-o PATH`; без него пишут в stdout.
`check` и `emit-*` не требуют Clang. Нативные тесты пропускаются без Clang.

## Границы прототипа

Реализованы чтение и запись файлов, региональные буферы, `Vec<T>` с явным
`reserve`, блокирующий TCP и ограниченный неблокирующий reactor на IPv4 loopback. Вызов `file.read` ограничен
2 КиБ; `file.read_chunk` позволяет читать файлы произвольного размера чанками.

Пока нет пользовательских ресурсных типов, задач и многопоточности.
Коллекции не растут автоматически: `push` не
выделяет память, рост запрашивается через `vec.reserve`. Старое размещение
остаётся занятым до закрытия региона. TCP echo обслуживает одного клиента
за раз; новый `liza-reactor` — до восьми в одном потоке. Есть тайм-аут poll,
но пока нет idle deadlines и управляемого завершения по сигналу.

Нет обещания оптимального исполнения на любой архитектуре. Поддерживается
нативная сборка для хоста на Linux, macOS и Windows. Параметр `--target`
задаёт целевое окружение LLVM, но полноценная кросс-сборка с подбором runtime,
SDK и системных библиотек не гарантируется. Freestanding-сборка ещё не
реализована: Clang связывает программу с системным startup-кодом.

Liza Verified V0–V4 проверяют выбранные программы и преобразования IR.
Верификация произвольных пользовательских программ, сетевого runtime и
конечного машинного кода пока не предоставляется.

- [Модель вычислений и памяти](docs/design.md)
- [Точная семантика работающего подмножества](docs/core.md)
- [Этапы и критерии готовности](docs/roadmap.md)

## Generics · 0.0.18

Generic-функции и структуры поддерживают параметры типов и вместимости `N: u32`,
вывод аргументов и мономорфизацию. Владение, эффекты и приватность проверяются
после подстановки. Пример: `python3 -m liza run examples/generic_table.liza`.
[Контракт](https://liza.rulerom.com/generics.html).

## Регионы · 0.0.19

`memory.Region` и move-only `memory.Buffer<T>` отделяют владение значением
от владения хранилищем. Создание и выделение требуют эффекта `alloc`;
зависимости сохраняются через `Result`, функции и CFG.
Пример: `python3 -m liza run examples/region_buffer.liza`.
[Контракт](https://liza.rulerom.com/regions.html).

## Линейные результаты и bounded Vec · 0.0.20

`(next, item) = vec.pop(move current)` целиком потребляет составной результат
и переносит обязанности владения каждому компоненту. `vec.Vec<T>` хранит
инициализированный префикс в регионе; `push/pop/get/set` не выделяют память.
Вместимость фиксирована, readonly views защищают владельца.

```sh
python3 -m liza run examples/bounded_vec.liza
```

[Контракт и ограничения](https://liza.rulerom.com/bounded-vec.html).

## Явный рост Vec · 0.0.21

`vec.reserve(move current, region, capacity)` увеличивает вместимость в исходном
регионе и возвращает владельца со статусом операции. Отказ сохраняет состояние;
рост копирует только инициализированный префикс. Старое размещение остаётся
занятым до закрытия региона. `push` сам не растёт.

```sh
python3 -m liza run examples/vec_reserve.liza
```

[Контракт и стоимость](https://liza.rulerom.com/vec-reserve.html).

## UTF-8 · 0.0.22

Проверка и декодирование `View<u8>`, подсчёт кодовых точек и проверка
текстовых диапазонов — чистые функции на Liza без аллокаций и копирования
входа. Некорректный UTF-8 возвращает `Result` с байтовым смещением ошибки.

```sh
python3 -m liza run examples/utf8_file.liza
```

[Контракт и разбор примера](https://liza.rulerom.com/utf8.html).

## Потоковый UTF-8 · 0.0.23

Проверка файлов до EOF через `file.read_chunk`, независимо от разбиения
кодировок между чанками. Малое копируемое состояние, абсолютные `u64`
смещения ошибок, без аллокаций и копирования входных чанков.

```sh
python3 -m liza run examples/utf8_stream_file.liza
```

[Контракт и пример](https://liza.rulerom.com/utf8-stream.html).

## Владеющий UTF-8 · T1

[Ресурсные структуры](https://liza.rulerom.com/resource-structures.html) позволяют
собрать String обычным модулем Liza поверх `memory.Buffer<u8>`. Append проверяет
UTF-8 и вместимость до записи; ошибка сохраняет прежнюю строку. Память выделяется
явно, автоматического роста нет. [T2-A](https://liza.rulerom.com/readonly-access.html)
добавляет readonly-параметры и непотребляющие length/capacity/byte_at.
Subviews и StringBuilder остаются следующими этапами.

```sh
python3 -m liza run examples/owned_string.liza
```

[Контракт и ограничения API](https://liza.rulerom.com/owned-string.html).

## liza-json · Text & Compiler Foundations

Потоковая проверка JSON на самой Liza: UTF-8, escapes и surrogate pairs,
лексические числа, точные байтовые смещения ошибок. Стек ограничен 64 уровнями,
память не зависит от размера файла; `format` и дерево объектов пока не реализованы.

```sh
python3 -m liza build examples/apps/liza_json.liza -o build/liza-json
./build/liza-json check config.json
```

[Контракт и ограничения](https://liza.rulerom.com/json.html).

## liza-text · 0.0.24

Первое CLI-приложение: `check`, `count`, `info` для произвольного пути к файлу.
Платформенные `Arg`/`Path`, потоковая проверка UTF-8, stdout/stderr и коды ошибок.

```sh
python3 -m liza build examples/apps/liza_text.liza -o build/liza-text
./build/liza-text info examples/data/utf8.txt
```

На Windows запускайте `build/liza-text.exe`.
[Команды и контракт](https://liza.rulerom.com/cli.html).

## liza-copy · 0.0.25

Бинарное копирование чанками: создание без перезаписи, частичные результаты
записи, явные flush и close. При отказе destination сохраняется для проверки.

```sh
python3 -m liza build examples/apps/liza_copy.liza -o build/liza-copy
./build/liza-copy source.bin destination.bin
```

На Windows запускайте `build/liza-copy.exe`.
[Контракт записи и исходник](https://liza.rulerom.com/file-output.html).

## Liza Verified (experimental)

An optional Z3 experiment checks ten fixed `u8`/`i8` functions against independent
contracts at Semantic IR and LLVM IR (generated, O0, O2) levels. It preserves
mandatory traps and requires counterexamples for deliberately broken lowerings.
This is not whole-compiler or binary verification; Z3 and the small IR models
remain trusted. See [scope and reproduction](docs/verified.md).

[Verified V1](docs/verified-v1.md) separately checks fixed four-byte arrays,
full-width `u32` indices, snapshot independence and short-circuit control flow.
Its bounded LLVM memory model tracks object origins and initialized bytes.
V0 sources remain frozen; both suites run independently in CI.

[Verified V2](docs/verified-v2.md) adds inductive proofs for symbolic-length
readonly search and sequential `i32` sum, including termination and the first
overflowing prefix. Supported LLVM loop forms are checked independently.

[Verified V3](docs/verified-v3.md) calibrates Alive2 on mandatory traps before
using LLVM refinement to validate generated/optimized IR pairs. Missed negative
controls produce `unsuitable`; unsupported or incomplete checks remain `unknown`.
It does not extend the V2 inductive or machine-code guarantees.

## TCP echo · первый сетевой срез 0.0.26

```sh
python -m liza build examples/apps/liza_echo.liza -O 2 -o build/liza-echo
./build/liza-echo --once
```

Сервер печатает выбранный loopback-порт, обслуживает одного клиента и закрывает
ресурсы после EOF. Без флага работает последовательно на `127.0.0.1:9000`.
Бинарные данные проходят через существующий `memory.Buffer<u8>` на 2048 байтов;
короткие записи обрабатывает приложение. [Контракт TCP](docs/tcp.md).

Сетевой runtime и машинный код не входят в гарантии Liza Verified V0–V4.

## TCP message server · срез 0.0.27

```sh
python -m liza build examples/apps/liza_message.liza -O 2 -o build/liza-message
./build/liza-message --once
```

Протокол: 4 байта unsigned big-endian длины, затем N бинарных байтов.
Сервер возвращает только полные кадры с телом не больше 65536 байтов.
Чистая библиотека на Liza обрабатывает фрагментацию и склейку кадров.
[Протокол, исходник и проверки](docs/message-server.md).

## TCP reactor · срез 0.0.28

```sh
python -m liza build examples/apps/liza_reactor.liza -O 2 -o build/liza-reactor
./build/liza-reactor --ephemeral
```

До восьми клиентов, один поток, тот же бинарный фрейминг. `net.Reactor`
владеет сокетами; приложение хранит состояния клиентов и один ожидающий ответ
на соединение. Буферы выделяются один раз и переиспользуются. Медленный клиент
не блокирует остальных. [Контракт, память и ограничения](docs/reactor.md).

## Message Router · срез 0.0.29

```sh
python -m liza build examples/apps/liza_router.liza -O 2 -o build/liza-router
./build/liza-router --ephemeral
```

Клиенты получают протокольные RouterId и отправляют сообщения адресату.
Очереди ограничены; `Accepted` подтверждает полную копию в очередь,
`Busy` и `Unavailable` не меняют очередь адресата. Старый ID не адресует
нового клиента после переиспользования слота. Логика реализована на Liza
поверх существующего reactor. [Wire-протокол и границы](docs/message-router.md).

## Bounded L4 TCP Proxy · срез 0.0.30

```sh
python -m liza build examples/apps/liza_proxy.liza -O 2 -o build/liza-proxy
./build/liza-proxy --ephemeral
```

До восьми пар, фиксированный upstream `127.0.0.1:9003`, два независимых
направления с half-close и 32 КиБ пользовательских буферов. Неблокирующий
connect явно проверяется перед передачей. [Контракт и отдельная модель relay](docs/tcp-proxy.md).

[Verified Relay R1](docs/verified-relay-r1.md) проверяет восемь чистых функций
`relay.direction` на полном пространстве входов через фактический Semantic IR:
16 обязательств и восемь воспроизводимых мутаций. Гарантия относится к
координатам очереди, не к сохранности байтов, runtime или машинному коду.
