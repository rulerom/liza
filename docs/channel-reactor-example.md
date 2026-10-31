---
description: "Пример управляющего worker, scoped-канала и локального TCP reactor в Liza."
---

# Команды для worker с reactor

Пример [`examples/workers/channel_reactor.liza`](https://github.com/rulerom/liza/blob/main/examples/workers/channel_reactor.liza)
связывает два реализованных механизма: scoped SPSC-канал и reactor,
принадлежащий одному worker. Компилятор проверяет права producer и consumer;
через канал передаются только `u32`, без передачи сокетов и регионов.

Producer отправляет две команды по порядку. Consumer самостоятельно создаёт
reactor и loopback listener, затем:

1. По первой команде подключается через собственный reactor к своему listener,
   дожидается завершения connect и принимает настоящую TCP-пару.
2. Закрывает оба connection ID, а по второй команде прекращает приём новых
   соединений и проверяет, что порт listener больше недоступен через reactor.
3. Дожидается закрытия producer, проверяет последовательность команд и закрывает
   reactor. Основной поток получает отдельные результаты обеих функций через
   `Result<ChannelRun,ChannelError>` после join.

```sh
python3 -m liza run examples/workers/channel_reactor.liza -O 2
python3 -m unittest discover -s tests -p test_channel_reactor_example.py -v
```

Тест собирает пример на O0/O2, повторяет реальные loopback-подключения и
проверяет отдельный результат consumer для неверного порядка команд и ошибки
подключения. Порядок допускает отказ создания reactor или канала и явное
закрытие уже созданных ресурсов на штатных путях.

Это **не production-сервис и не proxy**: команды зашиты в пример, данные по TCP
не передаются, подключения других клиентов и внешнее управление отсутствуют.
Циклы `Full`/`Empty` используют повторные попытки; fairness, ограниченная общая
задержка и автоматический cleanup после trap не гарантируются. При ожидании
локального connect и accept используются ограниченное число попыток и `poll`,
но это не real-time deadline. Никакого network performance benchmark или новой
верификации runtime этот пример не добавляет.

[Контракт scoped-канала](scoped-channels.md) · [Модель и истории канала](scoped-channel-model.md) ·
[Модель reactor](reactor.md).
