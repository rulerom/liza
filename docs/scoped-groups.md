---
description: "Текущий groups API: один или два сетевых consumer, сообщения u32, TCP/UDP, shutdown и результаты после join."
---

# Scoped-группы: текущий API

Scoped-группа связывает два статических callback: producer публикует команды
`u32`, consumer единолично управляет своим Reactor и TCP либо UDP endpoint.
Runtime владеет FIFO, data/control wake sources, supervisor и средствами join.
Возврат runner означает подтверждённые joins, handback и cleanup ресурсов группы.
API экспериментальный; произвольных callbacks и динамического spawn нет.
`workers.run` и `channels.run` нельзя вызывать в той же программе, что и
`groups.run/run_pair`; отдельный compute handoff пока не реализован.

## Одна группа

`groups.run(config)` использует `fn producer()->u32` и `fn consumer()->u32`
из входного модуля и возвращает `Result<GroupRun,GroupError>`. Подготовьте
consumer-owned endpoint через `groups.listen` или `groups.udp_bind`, затем
вызывайте `groups.next` для команд, сетевой готовности и shutdown.

| Операция | Кто вызывает | Что означает |
| --- | --- | --- |
| `groups.send(u32)` | Producer | `Published`, `NotPublished` или `PublishedFault` |
| `groups.listen`, `groups.udp_bind` | Consumer | Создание скрытого Reactor/endpoint |
| `groups.next` | Consumer | `Command`, `Network`, `Closed`, `Stopping`, `NotificationFault` |
| TCP read/write и `groups.udp_receive/send` | Consumer | I/O с сохранением владения buffer/view |
| `groups.stop` | Участник своей группы | Stop intent; не уничтожение ресурсов |
| `groups.busy` | Участник своей группы | Новое ограниченное обязательство; не бесконечный heartbeat |
| `groups.stopping` | Участник своей группы | Наблюдение опубликованного shutdown |

[Рабочий UDP-пример](https://github.com/rulerom/liza/blob/main/examples/workers/udp_group.liza)
показывает приём/отправку с возвратом owned buffer. Для TCP используйте
[Reactor group](https://github.com/rulerom/liza/blob/main/examples/workers/reactor_group.liza).
`Closed` сообщает закрытие producer один раз; consumer может продолжать сеть.
При shutdown принятая команда проверяется перед `Stopping`; дальнейшая сеть
может уступить остановке. `WouldBlock` при UDP send учитывает приложение,
автоматической retry queue нет.

<a id="two-groups"></a>

## Две группы

`groups.run_pair(config_a,config_b)` использует четыре функции входного модуля:
`producer_a`, `consumer_a`, `producer_b`, `consumer_b`, каждая `()->u32`.
`GroupPairRun.first` и `.second` — отдельные `Result<GroupRun,GroupError>`.
Runner возвращается после завершения обеих групп. Ресурсы завершившейся B
могут быть освобождены раньше A, но промежуточного результата B owner не получает.

Полный пример ниже использует общий helper двух consumer и разные результаты.
Это тот же исходник, который собирается и запускается при O0/O2 в B1 tests.

```liza
--8<-- "examples/workers/udp_groups.liza"
```

Статические роли проверяются после generic specialization по графу вызовов.
Общий helper обязан быть допустим для каждой вызывающей роли; producer не
получает сетевые полномочия через импорт или generic. Callback нельзя вызвать
как обычную функцию. `groups.*` адресуется TLS-контекстом конкретной группы;
числовые descriptors, mutex и thread handles пользователю не выдаются.

## Лимиты и ошибки

- Максимум две одновременно активные группы и один pair runner. Admission
  не ждёт свободного слота: исчерпание возвращает `Busy`.
- Канал bounded и допускает одно in-flight `u32`. RTP payload между группами
  не передаётся. UDP endpoint и TCP listener в текущем срезе взаимоисключающие.
- `operation_ms` ограничивает конкретное обязательство; `shutdown_ms` задаёт
  один deadline при остановке. Законный `Idle` не ограничивает срок жизни группы.
- Service stack фиксируется при инициализации join lane. Для предсказуемого reuse
  задавайте одинаковый service stack всем группам.
- Managed budget FIFO/метаданных, Region, Reactor, native stacks и OS socket
  buffers — разные ресурсы. Один размер FIFO не ограничивает RSS процесса.

`PublishedFault` сохраняет состоявшуюся публикацию. `Faulted(GroupRun)` можно
получить после контролируемого завершения отвечающих участников. Если join или
безопасный shutdown не подтверждён к deadline, runtime использует process-fatal
эскалацию; она не возвращает обычный `Err` и не обещает деструкторы.
Timeout не даёт права освободить ресурсы живого участника.

## Основания контракта

[SG2](sg2-runtime-runner.md) описывает ownership и join, [SG3](sg3-scoped-reactor-group.md)
— языковые роли, [SG4-A1](sg4-a1-udp.md) — UDP, [B1](sg4-b1-multiple-groups.md)
— две группы и независимые join lanes. [B2](sg4-b2-dual-owners.md) проверяет
применение к RTP fanout. Эти исследования не являются полным доказательством
всех межпоточных исполнений C/runtime/ОС.
