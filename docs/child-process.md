---
description: "Move-only process.Child: bounded argv/env, неблокирующий try_wait, reap, возврат владельца при ошибке close и минимальные файловые операции."
---

# Дочерний процесс

Первый Process API предназначен для управления одним нативным приложением из
цикла событий Liza. Он не реализует shell, worker pool, pipes, CAN, Recorder или
Storage. `process.Child` — непрозрачный move-only ресурс; PID и OS handles
пользовательскому коду не выдаются. Методы привязаны к native thread создателя.

## Создание и владение

| Операция | Результат и контракт |
| --- | --- |
| `process.command(inherit_environment)` | Копируемый `ProcessCommand` с приватными полями и пустыми argv/env overrides |
| `process.argument(command, bytes)` | `Result<ProcessCommand,ProcessError>`; один аргумент, включая пустой |
| `process.environment(command, name, value)` | `Result<ProcessCommand,ProcessError>`; запись только в окружение ребёнка |
| `process.spawn(executable, command)` | `Result<process.Child,ProcessError>`; абсолютный `Path`, без поиска PATH и shell; эффекты `io,alloc` |
| `process.try_wait(child)` | `Result<Option<ProcessExit>,ProcessError>`; `None` означает, что exit receipt ещё не получен |
| `process.wait(child)` | `Result<ProcessExit,ProcessError>`; блокирующее ожидание, не для активного Reactor-цикла |
| `process.terminate(child)` | `Result<ProcessDone,ProcessError>`; SIGTERM на POSIX, `Unsupported` на Windows |
| `process.kill(child)` | `Result<ProcessDone,ProcessError>`; принудительная остановка; всё равно нужен reap |
| `process.close(move child)` | `Result<ProcessDone,ProcessCloseFailure>`; освобождение после receipt |

`executable: Path` получается через `cli.path_arg`; он передаётся отдельно от
command, поэтому ограничение на хранение borrowed process paths в пользовательских
агрегатах сохраняется. Dynamic Path construction в этот срез не входит.
`ProcessExit` содержит `kind: ProcessExitKind` (`Exited` или `Signaled`) и `code: u32`.
POSIX signal number отличим от exit code; Windows возвращает полный DWORD exit code.

Wait/try_wait выполняют reap и кэшируют receipt. Повторный вызов возвращает тот
же статус. Terminate/kill уже reaped ребёнка не посылают сигнал новому процессу
с переиспользованным PID. `close` сам не ждёт и не делает неявный reap: без
receipt возвращает `Running`, даже если ребёнок уже успел завершиться в ОС.

Ошибка terminate, kill, wait или try_wait не потребляет владельца. При ошибке
`close` владелец возвращается внутри `ProcessCloseFailure`; его можно распаковать:

```liza
match process.close(move child) {
    Ok(done)=>{return 0}
    Err(failure)=>{
        (retained,error)=move failure
        // retained всё ещё нужно передать, reap/close или вернуть вызывающей стороне.
        return cleanup(move retained)
    }
}
```

`cleanup` в этом фрагменте — функция приложения; пример её реализации есть в
[`examples/apps/process_child.liza`](https://github.com/rulerom/liza/blob/main/examples/apps/process_child.liza).
Компилятор отклоняет double-close, copy Child, use-after-move и потерю владельца,
в том числе на ветке ошибки close. Ошибки ОС не содержат argv/env или секретов.

Одновременно допустимо восемь Child на процесс, включая завершившиеся, но ещё
не закрытые. Admission освобождается после close или неуспешного spawn.
Тесты проверяют независимость этой ёмкости от числа последовательных запусков.

## Аргументы, окружение и платформы

- До 32 аргументов, каждый до 1024 UTF-8 байт, общий encoded budget 8192 байта.
  `argv[0]` — executable; пустые строки, пробелы, кавычки и trailing backslashes
  сохраняются. NUL и невалидный UTF-8 отклоняются. Shell metacharacters — обычные
  данные; executable должен сам понимать стандартный argv своей платформы.
- До 32 env overrides: ASCII name до 128 байт без `=`, value до 4096 UTF-8 байт,
  общий budget 8192. Повторные ключи отклоняются при spawn; на Windows сравнение
  ASCII-имён нечувствительно к регистру. Значения не передаются через argv.
- При `inherit_environment=false` окружение пустое до добавления overrides.
  При `true` копируется bounded snapshot родителя и затем применяются overrides.
  Snapshot вместе с копиями overrides ограничен 32768 байтами и 256 записями;
  превышение возвращает `TooLarge`, без обрезания. Глобальное окружение не меняется.
- POSIX использует `posix_spawn`, Linux требует glibc 2.34+ для close-from actions;
  macOS — `POSIX_SPAWN_CLOEXEC_DEFAULT`. Дескрипторы вне stdio не наследуются.
  Windows использует явный application path в `CreateProcessW`, UTF-16 command
  line и environment block, без общего наследования handles и без `cmd.exe`.
  Правила сериализации argv рассчитаны на обычный Microsoft CRT, а не на
  произвольный собственный parser command line дочерней программы.

На Windows нет универсального мягкого завершения произвольного дочернего
процесса. Поэтому `terminate` возвращает `Unsupported`, сохраняя Child; приложение
должно сначала применить свой штатный протокол остановки (например stop marker),
а принудительный `kill` выбирать явно. SIGTERM на POSIX тоже не обещает, что
приложение завершится или сохранит результат.

Платформенные основания: [POSIX spawn](https://man.openbsd.org/posix_spawn.3),
[CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw).

## Файлы для stop marker и проверки результата

`file.create_path`, `write_chunk`, `flush`, `close` уже предоставляют создание
marker. Добавлены три операции с `Path`, с эффектом `io`:

| Операция | Контракт |
| --- | --- |
| `file.stat(path)` | `Result<FileInfo,FsError>`; `kind` — Missing/Regular/Directory/Symlink/Other; `size:u64` для Regular, иначе 0 |
| `file.mkdir(path)` | Создаёт один каталог; существующий обычный каталог допустим; без рекурсивного создания родителей |
| `file.remove(path)` | Удаляет файл/файловую symlink; каталог не удаляет; отсутствие — `NotFound` |

Stat не следует последней symlink/reparse point; промежуточные компоненты пути
не являются sandbox boundary. Эти API не дают защиты от подмены путей другим
процессом. Предполагается контролируемый каталог приложения.
`FsError` отделён от старого FileError, чтобы сохранить существующие exhaustive
matches. Обход каталогов, recursive remove, seek и durable journal не добавлены.

## Запуск и приёмка

```sh
python3 -m liza build --project-root examples examples/apps/process_child.liza -o /tmp/liza-child
/tmp/liza-child /absolute/path/to/native-program
python3 -m unittest discover -s tests -p test_process.py -v
```

Пример без дополнительных аргументов ждёт ребёнка и возвращает его exit code;
тестовый fixture отдельно упражняет argv/env, stop marker и Reactor polling.
Native harness проверяет admission, wrong-thread ошибки, reap/отсутствие zombie
на POSIX и отсутствие роста handles на Windows после инициализации. Инъекции
ошибок terminate/kill и wait показывают сохранение владельца после отказа.
O0/O2 проверяются отдельно; платформенная матрица — Linux/macOS/Windows.

Область гарантий — прямой дочерний процесс и контролируемые выходы программы.
Автоматического destructor, управления деревом descendants и гарантированной
уборки при SIGKILL/crash родителя нет. Shutdown/deadline и политика эскалации
остаются в приложении; Child нельзя молча выбросить при истечении его срока.
Этот этап не доказывает готовность Recorder Agent или публикацию MP4 в Storage.
Локальный exit 0 и подтверждённая сервером финализация — разные результаты.
