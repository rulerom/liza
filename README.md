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

Пока нет пользовательских ресурсных типов, задач, записи файлов,
автоматически растущих коллекций. Вызов `file.read` ограничен 2 КиБ; `file.read_chunk` позволяет читать файлы большего размера чанками.
Нет обещания оптимального исполнения на любой архитектуре. Есть только сборка
для хоста; кросс-компиляция и другие виды артефактов — следующие этапы.
Сейчас Clang связывает обычную host-программу с системным startup-кодом;
freestanding-сборка ещё не реализована.

- [Модель языка и открытые решения](docs/design.md)
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
