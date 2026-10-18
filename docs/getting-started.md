---
description: "Первая программа на Liza: проверка исходника, нативная сборка, запуск и знакомство с условиями и типами."
---

# Быстрый старт

## Требования

Нужны Python 3.9+ и Clang в PATH. Прототип проверен локально на macOS ARM64
с Python 3.9.6 и Apple Clang 21. Команды выполняются из корня репозитория.

```sh
git clone https://github.com/rulerom/liza.git
cd liza
```

## Первая программа

```sh
python3 -m liza check examples/answer.liza
python3 -m liza build examples/answer.liza
./build/answer
echo $?  # 42
```

Программа возвращает 42 как код завершения, а не печатает текст.
На POSIX оболочка видит младшие 8 бит результата `main`.

Собрать и сразу запустить пример с циклическим переполнением:

```sh
python3 -m liza run examples/wrapping.liza
```

`run` возвращает код завершения программы.

## Условия и логические значения

Пример `examples/conditions.liza` проверяет диапазон через функцию с результатом
`bool` и выбирает результат с помощью `if/else if/else`:

```sh
python3 -m liza check examples/conditions.liza
python3 -m liza run examples/conditions.liza
echo $?  # 42
```

Доступны `true`, `false`, отрицание `!`, сравнения `==`, `!=`, `<`, `<=`, `>`, `>=`.
Условие должно иметь тип `bool`; число вместо условия не допускается.
Подробнее: [спецификация ядра, раздел «Ветвления и области видимости»](core.md).

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
