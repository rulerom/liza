# Разработка Liza

Публичный сайт содержит документацию языка и его использования. Правила
сопровождения, CI и публикации храним вне `docs/`.
[Публикация документации](maintenance/documentation.md).

## Сквозное правило: семантика сопровождает реализацию

Каждая новая конструкция должна включать четыре результата:

1. Определённое поведение, включая ошибки, порядок вычисления и время жизни.
2. Представление в Liza IR, независимое от деталей LLVM.
3. Позитивные и негативные проверки, включая диагностику недопустимых программ.
4. Проверку одинакового наблюдаемого результата при `O0` и `O2`.

Изменение спецификации и реализации поставляется вместе. Проектные предложения
помечаются отдельно от работающих возможностей. Компилятор не должен расти
быстрее определённой модели языка.

Сравниваем не только возвращённое число, но и определённый отказ, порядок
наблюдаемых действий и отсутствие исполнения невыбранных ветвей.
Для арифметики проверяем границы каждого типа, знаковость, сужение,
переполнение, ноль, величины сдвига и короткое замыкание.
Для составных значений — границы, независимость копий, move и время жизни view.

### Числовая модель: проверка соответствия

- Для каждой ширины и знаковости покрыть MIN/MAX, соседние значения,
  деление на ноль, `MIN / -1`, `MIN % -1`, сдвиги 0/N−1/N и неправильные
  преобразования. Отделять ошибки исходника от runtime traps.
- Проверять полную ширину результата. Коды завершения POSIX не различают
  значения, отличающиеся только старшими битами; нужен harness с полным
  сравнением или другой канал наблюдения.
- При O0/O2 проверять ошибки с runtime-операндами, а не только сворачиваемыми
  литералами. Сохранять проверки невыбранных веток и порядка эффектов.
- Эталон рассчитывать по математическим правилам независимо от LLVM lowering,
  при необходимости с произвольной точностью в тестовом коде.
- Проверять выдаваемый IR на необоснованные `nsw`, `nuw`, `inbounds`, `exact`.
  Это не заменяет проверки UB для деления, остатка и сдвигов.
- Для межархитектурного прогона фиксировать архитектуру runner, target triple
  и версию toolchain. Linux/macOS без этих данных — только матрица ОС.

Для checked использовать overflow intrinsics; недопустимо сначала получить
poison через `nsw`, а затем пытаться обнаружить переполнение.
Подробности семантики инструкций:
[LLVM Language Reference](https://llvm.org/docs/LangRef.html).

## IR не наследует модель памяти LLVM

Логические значения, обновления привязок, состояния и права доступа различаются
в Liza IR. Backend вправе использовать `alloca`, `load`, `store`, `getelementptr`
и указатели, но не может определять через них семантику исходной программы.
Выбор представления должен сохранять контракт Liza и наблюдаемую стоимость.

Перед массивами необходимы правила copy/move/view; перед I/O — проект эффектов.
Локальный `var` не разрешает вводить изменяемую ссылку или разделяемый объект.

## Проверки и эталонные задачи

```sh
python3 -m unittest discover -s tests -v
.venv-docs/bin/python -m mkdocs build --strict
```

Три эталонные задачи описаны в [документации языка](docs/reference-programs.md).
Добавляем исполняемые версии по мере появления нужных конструкций, не выдавая
псевдокод за поддерживаемый синтаксис. Для RTP используем одинаковый набор
случаев с C-реализацией и отдельно измеряем копии/аллокации.

Эталонный интерпретатор IR для дифференциальной проверки — дальнейшее улучшение;
сейчас выполняются нативные программы при двух уровнях оптимизации.

## Проверка стоимости чтения через view

```sh
python3 tools/check_view_cost.py --output build/view-cost
```

Сохраняются исходный LLVM IR, O2 IR, ассемблер и выделенное тело `rtp_fields`.
Проверка ищет runtime-чтения и отсутствие записей, аллокаций и копирования
в выбранной функции. Тестовый LLVM bridge принимает данные от отдельно
компилируемого C harness; это не публичный FFI языка. Тесты проверяют разные
байты и короткие входы при O0/O2. CI сохраняет артефакты для x86_64 и ARM64.
Это проверка конкретного тракта, не доказательство zero-copy для всех программ.

Проверка выбранного RTP Result/match тракта: `python3 tools/check_result_cost.py`.
Артефакты `result-cost-*` содержат O2 IR, машинный код и отчёт; отсутствие
heap/bulk-copy не означает отсутствие ABI расходов возврата агрегатов.

Консольная runtime: `python3 tools/check_console_cost.py` сохраняет O2 IR и
машинный код в `build/console-cost`; CI публикует `console-cost-*`.
`tests/test_io.py` проверяет ошибки stdout/pipe, короткую запись, EINTR,
частичный результат, состояние сигналов и порядок эффектов при O0/O2.
Runtime использует POSIX write и временную маску SIGPIPE вызывающего потока.
Для ручной линковки консольного emit-llvm добавьте
`liza/runtime/console_posix.c -pthread`. Пользовательский FFI не предоставляется.

Windows acceptance: в x64 Native Tools Command Prompt выполните
`python -m unittest discover -s tests -p test_windows.py -v`.
Это frontend-проверки и отдельный нативный набор: все примеры при O0/O2,
CLI/.exe, коды возврата, traps, точные байты, Unicode-консоль и ошибки handles.
POSIX signal-тесты не подменяются Windows-проверками; их CI остаётся отдельно.
Стоимость runtime проверяет `python tools/check_console_cost.py` на каждой ОС.


Файловый срез: `python3 tools/check_file_cost.py` сохраняет исходный и O2 IR,
ассемблер и отчёт в `build/file-cost`; CI публикует `file-cost-*`.
Проверяется отсутствие stores/bulk-copy в отдельной функции
`file_parse_probe(FileBuffer)` между готовым буфером и вызовом RTP-парсера.
После изменения ABI LLVM может встроить `file.read` в `main`, поэтому граница
измерения больше не зависит от этого решения inliner. Полный `main` сохраняется
в IR/ассемблере артефакта: внутренние копии файлового чтения остаются видны. `tests/test_file.py` проверяет граничные
размеры, ошибки путей, UTF-8, частичное чтение/EINTR и приоритет ошибки закрытия.
Windows-набор включает файловые тесты, кроме POSIX fault injection.
Для ручной линковки файлового emit-llvm добавьте `liza/runtime/file_posix.c`
или `liza/runtime/file_windows.c`; при наличии консоли добавьте её runtime.


Ресурсы 0.0.14 проверяет `tests/test_resources.py`: линейные обязательства
на ветках/циклах, явная передача, запрет копирования и выхода с живым ресурсом;
чтение чанками при O0/O2, EOF, независимость буферов, порядок I/O, ошибки
чтения/закрытия и POSIX EINTR. Windows-набор включает переносимые проверки.
Semantic IR v14 записывает `parameter_modes` вызова и `mode` параметра,
а также отрицательные свойства копирования `File` и ресурсных вариантов.
Trusted library adapters проходят типизацию, но освобождены от линейного
анализа: только они обрабатывают недействительный raw handle ошибки открытия.
Новые адаптеры требуют отдельной проверки всех путей владения.


Обновления 0.0.15 проверяет `tests/test_updates.py`: вложенные пути, копии,
SSA/phi, лексические заимствования, перемещения, O0/O2 и runtime-индексы.
В IR v14 добавлены `struct.update(aggregate, value)` и
`array.update(aggregate, index, value)` с проверкой границ. До RHS путь
снижается через `struct.field`/`array.read`: последний read сохраняет раннюю
проверку границ, даже если его значение не используется. Повторную проверку
в `array.update` backend вправе устранить при оптимизации.

Небольшие структуры обновляются через `insertvalue`, массивы — через scratch
slot и load/store. Крупные значения используют отдельное хранилище и memmove;
исходное хранилище не изменяется. Это сохраняет независимость SSA-снимков,
копий и views. Подробности большого представления — ниже.
Для больших массивов возможны физические копии; O(1) здесь не обещается.
Существующие инструменты `check_view_cost.py`/`check_result_cost.py` проверяют,
что выбранный RTP read path по-прежнему обходится без копирования массива.


## Таблица соединений и крупные агрегаты

```sh
python3 -m unittest discover -s tests -p test_table.py -v
python3 tools/check_table_cost.py --output build/table-cost
# Отдельная конфигурация:
python3 tools/check_table_cost.py --capacity 4096 --output build/table-4096
```

`examples/connection_table.liza` — обычный исходник с вместимостью 64.
Генератор меняет только размер массива и список начальных значений для 4096;
алгоритмы не генерируются. `tests/fixtures/connection_table_cases.liza`
содержит сценарии reuse, invalid ID, retirement и заполнение таблицы.
Отдельный C harness передаёт scalar runtime-входы и проверяет коды результата;
он не реализует таблицу и не использует C ABI для агрегатов Liza.

Для обеих вместимостей инструмент компилирует O0/O2, прогоняет одинаковые
сценарии с двумя runtime seed, сохраняет Semantic IR v14, исходный/оптимизированный
LLVM IR, полный и выделенный машинный код четырёх операций и `report.json`.
Отчёт считает статические инструкции и сохраняет строки memcpy/memmove;
это не динамический объём трафика. Время относится ко всему сценарию приёмки,
а не к стоимости отдельного get/edit. Наличие символа memcpy в полном модуле
не доказывает копирование на каждом пути. `get` на O2 проверяется на отсутствие
store/alloca/bulk-copy; копии обычного `edit` отмечены отдельным флагом.
Этот обычный вариант нужен для сохранения наблюдаемого прежнего значения.
CI выполняет инструмент на Linux/macOS/Windows и публикует `table-cost-*`.
На Windows тестовый executable резервирует 32 МиБ стека: O0 хранит много
независимых агрегатов. Это условие теста, не новый default CLI и не гарантия
пригодности больших программ к стандартному стеку.

Backend выбирает memory representation при более чем 64 скалярных листьях
типа (эвристика, не ABI-размер и не свойство языка). Крупные аргументы передаются
внутренним `ptr` на неизменяемое хранилище без `byval`, результаты — через `sret`.
Обычные варианты функций не изменяют входное хранилище: конструкторы и updates получают
отдельные entry-block slots. Проекции создают GEP, чтение малого элемента — load,
копирование крупных значений — LLVM memmove с размером, вычисляемым target layout.
Пользовательский адрес или borrow-параметр в языке не появляется.

Большие phi реализуются параллельным переносом через edge blocks: сначала
снимки всех incoming values во временные slots, затем обновление phi slots.
Это обязательно для перестановок, циклов и сохранения значений предыдущей
итерации. Малые phi ссылаются на перенаправленные рёбра, включая блоки trap checks.
Регрессии проверяют swap, nested arrays, копирование view-элемента, Option<Big>,
break/continue и независимость snapshot. Физические копии на этих рёбрах пока
могут сохраняться; переиспользование хранилища требует отдельного доказательства.

Начальная реализация 0.0.15 материализовала массив в `get`, а O0-конфигурация
4096 породила более 100 МиБ промежуточного ассемблера. Причины локализованы в
передаче/материализации агрегатов, не в правилах идентификаторов. Новое представление
устраняет разворачивание больших агрегатов и копии в get. Обычный edit создаёт
независимое значение; ниже описан отдельно доказанный путь переиспользования.


### Переиспользование хранилища 0.0.16

`liza/storage.py` анализирует SSA liveness с phi-использованиями на рёбрах,
корни памяти копий, проекций и views. Source `move` не служит доказательством
уникальности. Кандидат — ациклическая функция с одним крупным параметром,
возвращающая его обновлённую версию первым полем структуры результата,
за которым следуют малые поля статуса. Несвязанные крупные конструкции,
ранние конкурирующие результаты и наблюдения старых версий исключают вариант.
Вложенная цепочка updates сворачивается только при доказанном совпадении пути
и отсутствии промежуточных наблюдений. Обычный вариант всегда сохраняется.

Backend создаёт `__liza_owned_*` и выбирает его только при отсутствии живых
наблюдателей исходного хранилища и заимствованных входных параметров. Вызов
использует один адрес для параметра и результата. Размер allocation резервируется
по максимальному target-layout размеру всех размещаемых результатов, включая
статус за таблицей. Phi не копирует incoming, если адрес уже совпадает с destination;
остальные переносы по-прежнему делаются через параллельные снимки.
Semantic IR v14 и синтаксис языка не меняются.

```sh
python3 tools/check_edit_cost.py --output build/edit-cost
```

Проверяются 64/4096/16384 записи, O0/O2, два runtime seed, миллион обновлений
за вызов. Liza-цикл генерирует индексы, вызывает get/edit, накапливает наблюдаемую
контрольную сумму. C вычисляет независимый эталон и проверяет неизменность входа.
Приватный LLVM test bridge создаёт вход по target layout, без C ABI агрегатов.
Он не реализует операции таблицы; подготовка не входит в замер. Время CPU clock
включает холодные phi-копии перед циклом; после прогрева сохраняются пять проб
для каждого seed. Числа сравнительные, порога времени в CI нет.

Gate проверяет отсутствие bulk-copy в owned edit и во всех циклических блоках
исходного и оптимизированного LLVM IR. Сохраняются полный LLVM IR, машинный код,
выделенный owned edit и JSON. В машинном коде owned edit проверяется отсутствие
вызовов memcpy/memmove; полный цикл доступен для проверки отсутствия развёрнутых
копий. CI публикует `edit-cost-*` для Linux/macOS/Windows.
Тесты включают живые copy/views, borrowed large view elements, snapshots между
итерациями, break/continue, competing results и runtime bounds trap O0/O2.


## Поддержка редактора

Tree-sitter-грамматика находится в `editors/tree-sitter-liza`, расширение Zed —
в `editors/zed`. Проверки редактора выполняются отдельным CI и не добавляют
Node.js к зависимостям компилятора. Для разработки нужны Node.js, npm и C compiler:

```sh
npm ci --prefix editors/tree-sitter-liza
npm run generate --prefix editors/tree-sitter-liza
python3 tools/check_editor.py
```

Если npm блокирует install scripts, разрешите install script только пакета
`tree-sitter-cli` (он загружает CLI с GitHub). Генератор закреплён на 0.25.10,
ABI 14. В репозитории хранится сгенерированный parser.c и заголовки.
Проверка охватывает корпус деревьев, все examples/fixtures, все SCM-запросы,
категории подсветки и восстановление Outline после незавершённого выражения.
После коммита грамматики обновите закреплённый SHA в `editors/zed/extension.toml`.
Редакторная грамматика допускает свободные переносы/незавершённый код; правила
корректности программы по-прежнему определяются frontend компилятора.


## Модули 0.0.17

`liza/modules.py` загружает файлы один раз, проверяет корень/регистр/циклы,
разрешает имена и публичные интерфейсы, затем объединяет AST. Номинальные имена
имеют вид `module.Type`; entry main сохраняет символ `main`. Semantic IR v15
добавляет `modules` и `declarations` (стабильный project-relative `id`, symbol,
module, public); операции вычислений не меняются. Type inference проверяет
приватность конструкторов и полей в контексте исходного модуля функции.

```sh
python3 -m unittest discover -s tests -p test_modules.py -v
python3 tools/check_edit_cost.py --modules --output build/module-edit-cost
```

Межмодульный cost probe использует настоящие `import`, публичные методы и
приватную таблицу. Test bridge лишь инициализирует вход по target layout; цикл
и edit написаны на Liza. Для 64/4096/16384 проверяются O0/O2, контрольная сумма,
неизменность входа и отсутствие bulk copies в owned edit и циклических блоках.
CI сохраняет `module-edit-cost-*` для Linux/macOS/Windows. Обычный baseline
по-прежнему строится из тех же алгоритмов: снимает pub/квалификацию и добавляет
внутренние acceptance fixtures, в том числе моделирование исчерпания поколений.
Потребители публичного API не получают доступа к служебным полям.

Реализация таблицы теперь находится в `examples/tables/connections.liza`;
`examples/connection_table.liza` и `examples/connection_lookup.liza` — её клиенты.

## Monomorphization (0.0.18)

`generics.py` caches instances by canonical declaration, concrete type arguments
and u32 capacities. Declaration-site module identity remains attached to clones.
Ordinary inference discovers calls; the lowerer checks every discovered function
before returning a ModuleIR. Failed compilations do not produce executable IR.
Semantic IR v16 adds `specializations` (declaration, arguments, kind, symbol);
counts can be derived by kind. Symbols use a deterministic SHA-256 encoding and
a `$` namespace unavailable to source identifiers.

`array.repeat` evaluates its operand once. Small values lower to insertvalue; large
arrays use a compact initialization loop. Its exit participates in LLVM phi labels.
Existing concrete table fixtures remain a historical cost baseline; the generic
module has one implementation for all T/N instances. Compare with:

```sh
python3 tools/check_edit_cost.py --generics --output build/generic-edit-cost
```

This runs the same runtime-index/checksum/independent-snapshot proof at capacities
64, 4096 and 16384, with O0/O2 LLVM and machine-code artifacts. Generic table
semantics additionally cover scalar and structure records and stale IDs.

## Storage dependencies (0.0.19)

`dependencies.py` runs after ordinary typing, ownership, lexical loans and
resource obligations. It tracks conditional provenance through variant payloads,
including pending results and evaluated call arguments. Function summaries map
parameter origins to results; factory calls freshen creation origins. Loop-carried
origins must be invariant, while fully discharged local regions may be recreated.
Ambiguous joins and recursive storage-bearing summaries are rejected.

Semantic IR v17 adds `storage_relation` to operations and `storage_contract` to
functions (preconditions, consumed parameters, provenance, transitive storage
effects and normal-exit/trap policy). Memory-library calls become explicit
region/buffer operations after all arguments have been evaluated.

The portable C runtime owns bounded byte storage. Allocation checks size,
alignment and capacity before committing its cursor. No individual reclamation
is performed. LLVM uses private pointers; the source language exposes none.

```sh
python3 tools/check_region_cost.py --output build/region-cost
```

The gate saves O0/O2 LLVM and assembly, rejects allocation or bulk-copy calls in
selected update/read functions, counts actual heap operations, injects creation
failure, and directly verifies alignment, overflow and failure atomicity.

Large `view.read` materializes an independent element snapshot before a mutable
region buffer can change or close its storage. This copies one element, never the
whole buffer. The storage-root analysis treats that snapshot as independent.
Borrowed resource arguments remain protected during evaluation of later arguments.

## Linear products and bounded Vec (0.0.20)

Semantic IR version 18 adds internal linear products and `vec.*` operations.
`unpack.consume` consumes the whole product; its two `unpack.component`
projections bind the components. These projections are compiler-generated,
not independent source-level field moves. Products carry component-wise
resource obligations and storage provenance, including conditional variants.
Public product constructors, annotations and aggregate storage remain forbidden.

The native vector descriptor contains storage, initialized length and capacity.
Only the initialized prefix is readable. `vec.create` reserves uninitialized
capacity using the bounded region runtime. Other vector operations never call
the allocator. Large `get/pop` results snapshot one element independently.

```sh
python3 -m unittest discover -s tests -p test_vectors.py -v
python3 tools/check_vec_cost.py --output build/vec-cost
```

The cost gate saves O0/O2 LLVM IR and assembly, checks the set/pop/push cycle
for allocation and bulk copying, and runs with runtime capacities/values.
A counted allocator checks one allocation per region, injected failure, and
untouched unused capacity. This is a selected-path guarantee, not a universal
constant-time claim for all element types or collection operations.

## Подсветка документации

Pygments-лексер Liza находится в `tools/pygments_liza` и подключается через
стандартный entry point `pygments.lexers`. Блоки `liza` используют подсветку
Material в обеих темах. Для обновления локальной сборки из корня репозитория:

```sh
.venv-docs/bin/python -m pip install -r requirements-docs.txt
.venv-docs/bin/python -m mkdocs build --strict
.venv-docs/bin/python tools/check_docs.py
```

После изменения лексера повторите установку: пакет устанавливается локальным
wheel, а не в editable-режиме. `check_docs.py` проверяет категории токенов,
все примеры и наличие подсветки в готовом HTML. Построчный разбор Vec включает
исходный файл через Snippets; проверка сравнивает отображённый код с файлом
и проверяет нумерацию строк. При изменении примера обновляйте пояснения к строкам.

## Explicit reserve (0.0.21)

Semantic IR version 19 adds `vec.reserve`. Its contract consumes vector argument
0, borrows region argument 1 and preserves the origin in product component 0.
Storage dependency analysis requires origin equality even for a no-op.
`returned_buffer_storage` becomes `may_relocate_within_origin` for functions
whose transitive storage effects include reserve.

The runtime reserves new capacity before copying the initialized prefix.
Failures leave the region cursor and the descriptor unchanged. Old allocations
are not reclaimed. No user syntax or descriptor representation changes.

```sh
python3 -m unittest discover -s tests -p test_vec_reserve.py -v
python3 tools/check_reserve_cost.py --output build/reserve-cost
```

The runtime-input cost harness counts heap allocations and copied bytes, checks
unused-tail sentinels, alignment, overflow, no-ops and retry after failure.
O0/O2 LLVM and assembly are preserved as CI artifacts. The previous bounded
vector cost gate still checks allocation-free set/pop/push paths.

## UTF-8 acceptance (0.0.22)

`liza/stdlib/utf8.liza` uses ordinary pure functions; Semantic IR remains v19.
`tests/test_utf8.py` compares runtime inputs against Python's strict decoder
at O0/O2, including every one/two-byte input and a stream of all Unicode scalars.
`python tools/check_utf8_cost.py --output build/utf8-cost` saves LLVM and assembly
and rejects heap calls and bulk copies in the generated library path.
The C/LLVM bridge is test infrastructure, not a public FFI.

## Streaming UTF-8 (0.0.23)

`utf8_stream.liza` uses existing value and visibility semantics; IR stays v19.
The stdlib loader assigns its private state and functions the same reserved
module identity. Boundary-counter tests alone construct trusted internal states.
`python tools/check_utf8_stream_cost.py --output build/utf8-stream-cost`
saves runtime-input LLVM/assembly checks at O0/O2. The C bridge is test-only.
