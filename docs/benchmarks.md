---
description: "Каталог измерений Liza: текущие сетевые workloads, исторические baseline и стоимость преобразований."
---

# Измерения производительности

Выбирайте отчёт по задаче и конфигурации. Числа разных workloads и стендов
не составляют одну шкалу производительности языка. Артефакты, версии,
исходники, SHA-256 и ограничения находятся на странице конкретной серии.

## Сеть и RTP

| Отчёт | Что сравнивается | Где заканчивается вывод |
| --- | --- | --- |
| [SG4-A2: RTP Liza/C](sg4-a2-rtp-fanout.md) | Один сетевой owner, общий SG2 lifecycle, UDP fanout | Локальные Mac/VM серии; send success не равен наблюдаемой доставке |
| [Latency follow-up](sg4-a2-latency.md) | Длинные чередующиеся серии на сохранённых бинарниках | Паузы и конкуренция стенда не доказывают проблему компилятора |
| [Collector reliability](sg4-a2-collector.md) | File/memory collector и управляемая пауза | Механизм overflow воспроизведён; причина исторической паузы неизвестна |
| [SG4-B2: один/два owner](sg4-b2-dual-owners.md) | Две Liza-конфигурации, симметричная и асимметричная нагрузка | Вместе с CPU меняется число UDP queues; не физические NIC и не hard QoS |
| [Ранние TCP и NB1-C pilot](network-performance.md) | Однопоточные приложения и C-ориентиры | Исторический baseline, отличающийся от SG4 lifecycle |
| [Gateway R0 reproduction](gateway-reproduction.md) | Воспроизведение раннего TCP pilot | Методика и исходные ограничения сохранены |

Для текущего RTP результата начните с A2, затем прочитайте границы collector
и B2. Отчёт A2 не заменён результатом B2: различаются приложение и измерительная
конфигурация. Из single/dual сравнения нельзя вывести отношение Liza/C.

## Текст, LLVM и стоимость абстракций

- [JSON: результаты и исторический baseline](json-performance.md).
- [JSON ARM64 parity](performance-parity.md) и [mutable JSON](mutable-performance.md).
- [Bounded inlining](inlining-policy.md), [state/alias](state-alias-analysis.md),
  [guard/CFG](guard-cfg-investigation.md).
- [Field forwarding](field-forwarding.md) и [aggregate lowering](aggregate-lowering.md).

Для утверждений о корректности используйте [каталог проверок](research.md),
а для доступных API — [язык](basics.md) и [сеть/потоки](networking.md).
