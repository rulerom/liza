---
description: "Общий bounded JSON reader/writer на Liza: owned document, приватные byte ranges, типы, Unicode, дубликаты и явные лимиты."
---

# Типизированный JSON Reader/Writer

Новый слой `json.*` читает значения из проверенного документа и формирует JSON
в переданном Buffer. Реализация находится в `liza/stdlib/json_reader.liza` и
`json_writer.liza`; это код Liza без нового C backend и скрытых аллокаций.
Существующие [потоковые validator и formatter](json.md) сохраняют свои API.
CAN-specific поля, сообщения и protocol state принадлежат будущему `can.*`.

## Документ и владение

`json.parse(move buffer, length, JsonLimits(document_bytes, depth, result_bytes))`
возвращает `JsonRead`: owned `JsonDocument` и `Result<JsonDone,JsonAccessError>`.
Даже ошибка возвращает владельца исходного Buffer; его нужно освободить или
получить обратно через `json.into_buffer(move document)`.

Сначала применяется существующий JSON-валидатор, затем проверяются заданная
глубина и дубликаты ключей. Успешный документ неизменяем; его поля и constructor
приватны. Для нескольких полей используется последовательный обход:

1. `json.field(move document, key)` выбирает значение поля текущего объекта.
2. `json.index(move document, index)` выбирает элемент текущего массива.
3. `json.root(move document)` возвращает фокус к корневому значению.

`field` и `index` возвращают `JsonRead`; при ошибке сохраняется прежний фокус.
Выбор хранится как приватный диапазон байтов в самом owner. API не выдаёт view,
ссылку или отдельный range handle. У диапазона нет независимого срока жизни:
Buffer перемещается вместе с документом. Readonly-операции наблюдают только
живой owner. Copy, повторный release, использование после `into_buffer` и закрытие
Region при живом документе отклоняются компилятором.

`json.release(move document)` освобождает Buffer. `into_buffer` завершает
документ и возвращает тот же Buffer для повторного использования; его новое
содержимое требует нового `parse`.

## Типизированное чтение

| Операция | Результат |
| --- | --- |
| `json.kind(document)` | `Result<JsonKind,JsonAccessError>`: Null, Bool, Number, String, Object, Array |
| `json.read_bool(document)` | `Result<bool,JsonAccessError>` |
| `json.read_u64(document)` / `read_i64(document)` | Целое с проверкой диапазона |
| `json.array_length(document)` | Число элементов текущего массива |
| `json.decode_string(move document, move output)` | `JsonDecoded`: document, owned output и Result длины UTF-8 |

Целые читаются из целочисленной лексемы: `1.0` и `1e0` дают `WrongType`.
`-0` читается как 0. Переполнение и отрицательное ненулевое значение для `u64`
дают `NumberOutOfRange`; Unix timestamps не сужаются до 32 бит.

Отсутствующее поле даёт `Missing`, присутствующий `null` — `JsonKind.Null`.
Неверный ожидаемый тип даёт `WrongType`. После ошибки `parse` доступ к значениям
даёт `InvalidDocument`; возврат или освобождение Buffer остаются доступны.

Строки декодируются с обработкой escapes, `\uXXXX` и surrogate pairs.
Декодированные ID можно хранить в отдельном owned Buffer после освобождения
сообщения. `decode_string` заранее проверяет длину результата и вместимость
output; при ошибке его содержимое не меняется. Неиспользованный суффикс output
не считается частью строки. Имена полей сравниваются после декодирования:
`"type"` и `"\u0074ype"` обозначают одно имя. Unicode normalization не выполняется.

## Дубликаты и лимиты

Новый reader отвергает **любые дубликаты в любом объекте**, включая вложенные
объекты и эквивалентные escaped keys. Нет неявного first/last-wins.
Старый validator продолжает проверять синтаксис без этой дополнительной политики.

`JsonLimits` задаёт максимальную длину документа, глубину контейнеров (1–64)
и максимальный размер декодированной строки. Фактическая длина также должна
помещаться в исходный Buffer. Выходной Buffer предоставляет caller.

Полного DOM и скрытого индекса нет. Выбор поля/элемента требует линейного обхода;
строгая проверка дубликатов и последовательная вставка ключей writer могут
требовать квадратичного времени в размере объекта. Это ограниченный по размеру
доступ для небольших управляющих сообщений. Лимит байтов не является deadline
или точным пределом RSS; учитываются также стеки вызовов и память runtime/ОС.

Ошибки: `Missing`, `WrongType`, `InvalidUnicode`, `TooLarge`, `Syntax`,
`DuplicateKey`, `NumberOutOfRange`, `InvalidDocument`, `IndexOutOfRange`.

## Writer

`json.writer(move buffer, max_output, max_depth)` возвращает `JsonWritten`:
owned `JsonWriter` и Result. Он начинает пустой документ. Каждая следующая
операция потребляет writer и возвращает его с Result:

| Операция | Назначение |
| --- | --- |
| `begin_object` / `end_object` | Открыть/закрыть объект |
| `begin_array` / `end_array` | Открыть/закрыть массив |
| `key(writer, utf8)` | Имя поля объекта |
| `write_string(writer, utf8)` | UTF-8 строка с JSON escaping |
| `write_bool`, `write_null` | Логическое значение и null |
| `write_u64`, `write_i64` | Целое, включая полные границы типов |

Во всех потребляющих вызовах writer передаётся через `move`. Кавычки,
backslash и управляющие символы экранируются; invalid UTF-8 отвергается.
Writer проверяет порядок ключей/значений, тип закрываемого контейнера,
дубликаты, глубину и размер **до записи**. Неуспешная операция сохраняет
предыдущий prefix и всё содержимое Buffer. Её Result нужно обработать;
можно повторить допустимую операцию на возвращённом writer.

`json.writer_length(writer)` наблюдает длину. `json.finish_writer(move writer)`
возвращает `JsonOutput`: Buffer, length и Result. Успех требует ровно одного
законченного корневого значения; пустой или незаконченный документ даёт `Syntax`.
На ошибке writer тоже завершён, а Buffer остаётся у вызывающей стороны.
Перед отправкой используются только `length` байтов после успешного Result.
Произвольного публичного raw-append для обхода этих проверок нет.

## Исполняемый пример

```sh
python3 -m liza run examples/json_access.liza -O 2
```

Пример выводит `Liza`, читает count как `u64` и возвращает 0. Имя name в JSON
записано с escape; lookup использует его декодированное написание.

```liza
--8<-- "examples/json_access.liza"
```

## Приёмка

```sh
python3 -m unittest discover -s tests -p 'test_json*.py' -v
```

O0/O2 проверяются на Linux/macOS/Windows. Сохранённый
[корпус VideoGrace](https://videograce.ru/doc/developer/protocol/can-examples.json)
в `tests/fixtures/can_examples.json` содержит 20 положительных примеров:
17 CAN-сообщений и 3 административных HTTP body. Приёмка проверяет общий JSON:
типы/значения всех полей и вложенных элементов, а также output writer.
Проверка CAN schema и обмен с настоящим сервером в этот этап не входят.

Отрицательные случаи: Missing/null, wrong types, invalid Unicode, escaped key
aliases, дубликаты, границы чисел, лимиты, порядок writer и неизменность storage
при ошибке. Случайный корпус сравнивается с независимыми Python-ожиданиями.
Три мутации библиотеки должны провалить приёмку: raw вместо decoded lookup,
отключение проверки дубликатов и отключение UTF-8 проверки writer.
