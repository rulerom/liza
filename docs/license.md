# Лицензия

Liza распространяется по **Boost Software License 1.0**, SPDX: `BSL-1.0`.
Она применяется к собственному коду и документации проекта, включая компилятор,
runtime, стандартную библиотеку, примеры, проверки и инструменты редактора,
если для конкретного компонента не указано иное.

Основной текст находится в файле
[LICENSE в репозитории](https://github.com/rulerom/liza/blob/main/LICENSE).
Ниже включена его точная копия из того же файла.

```text
--8<-- "LICENSE"
```

## Сторонние компоненты

Сторонние зависимости и включённые компоненты сохраняют собственные лицензии.
BSL-1.0 проекта не заменяет условия LLVM/Clang, OpenSSL, Tree-sitter и других
внешних инструментов и библиотек.

В частности, заголовки `editors/tree-sitter-liza/src/tree_sitter/*.h` происходят
из Tree-sitter v0.25.10. Их
[MIT license и copyright notice](https://github.com/rulerom/liza/blob/main/editors/tree-sitter-liza/src/tree_sitter/LICENSE)
сохранены рядом с файлами. В метаданных npm-зависимости `tree-sitter-cli`
также сохраняется MIT.
