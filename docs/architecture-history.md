---
description: "История MT0–SG4: завершённые этапы, ранние контракты и ссылки на текущий API."
---

# История архитектурных этапов

Это каталог обоснований и исследовательских этапов. Для новой программы
начните с [выбора сетевой модели](networking.md) и [scoped API](scoped-groups.md).
Номера MT/SG ниже — названия этапов, а не отдельные поддерживаемые версии API.
Ограничение раннего документа не означает ограничение нынешнего языка.

## Статус на сегодня

| Направление | Статус | Текущий результат |
| --- | --- | --- |
| Изолированные native workers | Реализованы | [`workers.run(1..8)`](scoped-workers.md), scalar boundary, start gate и joins |
| Scoped channel | Реализован экспериментальный срез | [`channels.run`](scoped-channels.md), bounded `u32` |
| SG2/SG3 | Реализованы | Runtime ownership и [языковые scoped-группы](scoped-groups.md) |
| SG4-A1/A2 | Завершены | UDP в scoped Reactor, Liza/C workload и расследование измерителя |
| SG4-B1 | Завершён | Две одновременно активные группы, отдельные join lanes |
| SG4-B2 | Завершён | Два независимых RTP owner, stop/fault и измерения single/dual |
| Физические NIC | Не входят в завершённый B2 | Нужна конкретная задача маршрутизации и hardware isolation |
| SG5 compute workers | Отложен | Начинается с измеренной тяжёлой операции; owned payload handoff ещё нет |

## Как развивалась модель

| Этап | Документ | Как его читать |
| --- | --- | --- |
| MT0-A | [План изолированных workers](mt0a-workers.md) | Исторический план dispatcher/Gateway; не текущая обязательная архитектура |
| Каналы | [Контракт](scoped-channels-contract.md), [модель](scoped-channel-model.md) | Источник модели FIFO и ограничений обмена |
| До unified wait | [Ожидание канала](scoped-channel-wait-contract.md), [пример retry-loop](channel-reactor-example.md) | Ранний пример; для новой программы используйте `groups.next` |
| Архитектурные схемы | [Многопоточность и сеть](concurrency-architecture.md) | История разделения owners, FIFO и notification |
| SG0 | [Supervisor/shutdown](sg0-lifecycle-contract.md) | Контракт и C-прототип наблюдения прогресса |
| SG1 | [Reactor worker](sg1-reactor-worker.md) | Первый интеграционный C-прототип |
| SG2 | [Ownership contract](sg2-scoped-runtime-ownership.md), [runtime runner](sg2-runtime-runner.md) | Joins, handback, бюджеты и process-fatal граница |
| SG3 | [Языковой API](sg3-scoped-reactor-group.md) | Первый producer/consumer с проверкой ролей; его single-group/TCP-only ограничения расширены позже |
| SG4-A | [Исходный аудит](sg4-a-udp-baseline.md) | Снимок плана до реализации; не список текущих недостающих функций |
| SG4-A1 | [Consumer-owned UDP](sg4-a1-udp.md) | Реализованное расширение Reactor |
| SG4-A2 | [Baseline](sg4-a2-rtp-fanout.md), [latency](sg4-a2-latency.md), [collector](sg4-a2-collector.md) | Измерения и ограничения стенда |
| SG4-B1 | [Multiple active groups](sg4-b1-multiple-groups.md) | Контракт и реализация двух групп |
| SG4-B2 | [Dual RTP owners](sg4-b2-dual-owners.md) | Прикладная проверка и данные Apple M4 |

Ранний [C/LLVM native worker probe #51](https://github.com/rulerom/liza/pull/51)
предшествовал языковому `workers.run`. Его закрытие как замещённого не означает,
что native threads ещё предстоит реализовать. Динамический compute pool — другая,
пока отложенная задача.
