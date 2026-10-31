---
description: "Каталог исследований, измерений и проверок Liza с границами их применимости."
---

# Исследования и проверки

Здесь собраны экспериментальные отчёты, аудиты и проверки выбранных свойств
программ и компилятора. Они отделены от [документации языка](basics.md):
результат отдельного эксперимента не является общей гарантией для любой
программы Liza. Область покрытия, предположения и способы воспроизведения
описаны на соответствующих страницах.

Для знакомства с языком начните с [быстрого старта](getting-started.md)
и [модели вычислений, владения и доступа](design.md).

## Проверки и границы гарантий

- [Scoped channel: модель и истории](scoped-channel-model.md)

- [Verification pipeline](verification-pipeline.md)
- [Liza Verified V0](verified.md)
- [Liza Verified V1](verified-v1.md)
- [Liza Verified V2](verified-v2.md)
- [Liza Verified V3](verified-v3.md)
- [Liza Verified V4](verified-v4.md)
- [Verified Relay R1](verified-relay-r1.md)
- [Verified Relay R2](verified-relay-r2.md)
- [Verified Relay R2-B](verified-relay-r2b.md)
- [Verified Relay R2-C](verified-relay-r2c.md)

## Производительность и оптимизации

- [Сетевые бенчмарки Liza и C](network-performance.md)

- [M0: JSON performance](mutable-performance.md)
- [Performance Parity — JSON ARM64](performance-parity.md)
- [Performance Parity — bounded inlining](inlining-policy.md)
- [Performance Parity — state and aliasing](state-alias-analysis.md)
- [Performance Parity — guard and CFG](guard-cfg-investigation.md)
- [Production field forwarding](field-forwarding.md)
- [Производительность JSON: результаты и исторический baseline](json-performance.md)
- [Lowering составных значений](aggregate-lowering.md)

## Аудит модели доступа

- [M0: аудит доступа](mutable-audit.md)
