---
description: "Первая программа на Liza: проверка исходника, нативная сборка, запуск и знакомство с условиями и типами."
---

# Быстрый старт

Если вы впервые читаете Liza, откройте [основы языка](basics.md):
один документ про типы, функции, `if`, циклы, `match`, `Option` и `Result`.

## Требования

Нужны исходники Liza, Python 3.9+ и Clang в PATH. Сборка выполняется
на целевой системе; готовому бинарнику Python и Clang не нужны.

| Система | Проверенная архитектура | Инструменты |
| --- | --- | --- |
| Linux | x86-64 | Python, Clang и системный toolchain для линковки |
| macOS | ARM64 / Apple Silicon | Python и Xcode Command Line Tools с Clang |
| Windows | x86-64 | Python, Clang, MSVC Build Tools и Windows SDK; x64 Native Tools Command Prompt |

Все команды ниже выполняются из каталога с исходниками Liza.

### Явный выбор LLVM/Clang

Liza использует выбранный Clang и для определения target/ABI, и для сборки.
Можно выбрать LLVM 23 вместо системного Apple Clang без изменения исходника:

```sh
/opt/homebrew/opt/llvm/bin/clang --version
python3 -m liza build examples/hello.liza --clang /opt/homebrew/opt/llvm/bin/clang
```

Это путь Homebrew на Apple Silicon; проверьте фактическую версию установленного
пакета. Для тестов и benchmark runners, которые ищут `clang` в PATH:

```sh
PATH=/opt/homebrew/opt/llvm/bin:$PATH python3 -m unittest discover -s tests -v
```

Путь не закрепляет версию пакета навсегда. Для воспроизводимых измерений сохраняйте
полный вывод `clang --version` вместе с target, флагами и хешами артефактов.
Системные инструменты линковки и SDK по-прежнему необходимы. Закреплённые toolchains
отдельных экспериментов Verified имеют собственные контракты версий.

## Первая программа — Hello World

```liza
fn main() -> u32 : io {
    match console.println("Hello, Liza!") {
        Ok(written) => { return 0 }
        Err(error) => { return 1 }
    }
}
```

Исходник уже есть в `examples/hello.liza`. Linux/macOS:

```sh
python3 -m liza build examples/hello.liza
./build/hello
```

Windows, в **x64 Native Tools Command Prompt**:

```bat
python -m liza build examples/hello.liza
build\hello.exe
```

Программа печатает `Hello, Liza!` и возвращает 0 при успешном выводе.
Отказ вывода обрабатывается через `Result` и возвращает код 1.
[Контракт консоли](io-model.md).

`build` сохраняет исполняемый файл в `build/`. Путь можно задать явно:
`python3 -m liza build examples/hello.liza -o hello` или на Windows
`python -m liza build examples/hello.liza -o hello.exe`.

Для разового запуска используйте `python3 -m liza run examples/hello.liza`
(на Windows — `python` вместо `python3`). `run` создаёт временный бинарник,
запускает его и удаляет после завершения.

## Вычисление без вывода

```sh
python3 -m liza check examples/answer.liza
python3 -m liza run examples/answer.liza
echo $?  # 42
```

Этот пример возвращает 42 как код завершения, а не печатает его.
На POSIX оболочка видит младшие 8 бит результата `main`; на Windows
доступен 32-битный код завершения (`echo %ERRORLEVEL%` в cmd).

## Условия и логические значения

Пример `examples/conditions.liza` проверяет диапазон через функцию с результатом
`bool` и выбирает результат с помощью `if/else if/else`:

```sh
python3 -m liza check examples/conditions.liza
python3 -m liza run examples/conditions.liza
echo $?  # 42
```

Доступны `true`, `false`, отрицание `!`, сравнения `==`, `!=`, `<`, `<=`, `>`, `>=`,
а также `&&` и `||` с коротким замыканием.
Условие должно иметь тип `bool`; число вместо условия не допускается.
Подробнее: [спецификация ядра](core.md).

## Целые и битовые поля

Доступны `u8/u16/u32/u64` и `i8/i16/i32/i64`. Пример извлекает версию,
маркер и тип полезной нагрузки из двух переданных байтов заголовка RTP:

```sh
python3 -m liza run examples/rtp_fields.liza
echo $?  # 0: поля совпали с ожидаемыми
```

Здесь используются `u8`, маски и сдвиги. Более полный пример —
`examples/rtp_result.liza`: чтение через view, проверка заголовка
и типизированные ошибки разбора.

Пример деления позиции аудиосэмпла на целые секунды и остаток:

```sh
python3 -m liza run examples/division.liza
echo $?  # 0
```

`/` округляет частное к нулю, `%` возвращает остаток со знаком делимого.
Нулевой делитель вызывает trap; правила граничных случаев описаны
в [числовой модели](numeric-model.md).

## Преобразования и насыщение

`T(x)` проверяет диапазон, `T.wrap(x)` преобразует по модулю ширины T,
`T.saturate(x)` ограничивает значение границами T. Насыщаемая арифметика
записывается как `+|`, `-|`, `*|`.

Пример собирает 16-битное сетевое слово из двух байтов через явное расширение
и проверяет преобразования и насыщение:

```sh
python3 -m liza run examples/conversions.liza
echo $?  # 0
```

Литерал `u8(300)` отвергается при компиляции. Для переменной `x: i64 = 300`
операция `u8(x)` вызывает runtime trap; `u8.wrap(x)` возвращает 44,
`u8.saturate(x)` — 255.

## Локальная изменяемость

`var` разрешает повторное присваивание имени, сохраняя его тип:

```liza
var x: u8 = 10
snapshot = x
x = x + 1
// x == 11, snapshot == 10
```

Пример выбирает и корректирует локальное значение в ветках:

```sh
python3 -m liza run examples/mutable_locals.liza
echo $?  # 0
```

Без `var` повторное присваивание запрещено. Объявить `var` поверх видимого
имени тоже нельзя.

## Копирование и перемещение

`copy x` сохраняет доступность x, `move x` делает её недоступной для чтения.
Новое присваивание изменяемой `var` восстанавливает доступность. Для скаляров
обычное `y = x` по-прежнему означает неявное копирование.

```sh
python3 -m liza run examples/copy_move.liza
echo $?  # 0
```

Проверка действует и на путях ветвлений и циклов.
[Точные правила копирования и перемещения](core.md).

## Циклы

`while` проверяет условие перед каждой итерацией. `continue` повторяет проверку,
`break` выходит из ближайшего цикла. Пример вычисляет НОД и сумму нечётных чисел:

```sh
python3 -m liza run examples/loops.liza
echo $?  # 0
```

Изменяемые привязки сохраняют текущие значения между итерациями.
Локальные имена тела цикла за его пределами недоступны.

## Структуры-значения

```liza
struct Point { x: i32; y: i32 }

fn shifted(p: Point) -> Point {
    return Point(p.x + 1, p.y)
}
```

`Point(...)` создаёт значение, `p.x` читает поле. Присваивание `var` заменяет
всю структуру. Копии остаются независимыми, включая вложенные структуры.

Пример декодирует четыре переданных байта в `PacketInfo` с вложенным `RtpFields`,
копирует результат и вычисляет следующее значение номера последовательности:

```sh
python3 -m liza run examples/structures.liza
echo $?  # 0
```

## Массивы и readonly views

```liza
fn first(data: View<u8>) -> u8 {
    return data[0]
}
```

Массив `packet: [u8; 4] = [128, 96, 18, 52]` можно читать через
`header = view packet[0..4]`. Индексы и границы имеют тип `u32`;
нарушение границ вызывает trap. Пока view действует, владельца можно
копировать, но нельзя перемещать или переприсваивать.

```sh
python3 -m liza run examples/rtp_view.liza
echo $?  # 0
```

Пример читает первые четыре байта, но ещё не разбирает полный RTP-заголовок.
[Контракты массивов и времени жизни views](core.md).

## Посмотреть промежуточное представление

```sh
python3 -m liza emit-ir examples/answer.liza
python3 -m liza emit-llvm examples/answer.liza
```

`emit-ir` и `emit-llvm` принимают `-o PATH`; без него пишут в stdout.
`check` и `emit-*` не требуют Clang.

`build` принимает `-o PATH`, `-O 0` или `-O 2`, `--clang PATH`.
По умолчанию включена оптимизация `-O 2`, исполняемый файл записывается в `build/`.

## Проверки

```sh
python3 -m unittest discover -s tests -v
```

Нативные тесты пропускаются без Clang. Они проверяют исполнение при `O0` и `O2`,
включая переполнение. [Точная семантика ядра](core.md).


## Прочитать и разобрать RTP-файл

Из корня проекта:

```sh
python3 -m liza run examples/rtp_file.liza -O 2
# RTP sequence: 4660
```

На Windows используйте `python` вместо `python3`. Пример читает
`examples/data/rtp.bin`; путь относительно рабочей директории.
Первый файловый API ограничен 2 КиБ. [Ошибки и контракт чтения](io-model.md#0013).


## Чтение файла чанками

`examples/file_stream.liza` открывает файл, передаёт его байты в stdout
чанками по 2 КиБ и явно закрывает ресурс. Общий размер файла не ограничен
размером одного чанка. Для бинарного вывода используйте перенаправление:

```sh
python3 -m liza run examples/file_stream.liza > packet-copy.bin
```

Путь входного файла в примере — `examples/data/rtp.bin` относительно рабочей
директории. На Windows запустите через `python` в `cmd.exe`, чтобы перенаправление
сохранило бинарные байты. [Владение и закрытие](io-model.md#0014).

## Приложение с аргументами

`liza-text` проверяет UTF-8 файлов, считает байты и кодовые точки:

```sh
python3 -m liza run examples/apps/liza_text.liza -- info examples/data/utf8.txt
```

Аргументы после `--` передаются программе. Для независимого нативного
инструмента используйте `build` с `-o build/liza-text`.
[Команды, пути и коды ошибок](cli.md).
