# Выбор проверок CI

CI выбирает workflows нативными `paths` GitHub Actions. Отдельного диспетчера,
который подменяет результат тестов или решает, что считать успешным, нет.

## События и отмена

- PR запускает только workflows, чьи входы затронуты изменением.
- `push` запускает проверки только на `main`, с теми же path-фильтрами.
  Push feature-ветки не дублирует проверку её PR. Ветка без PR проверяется
  вручную через `workflow_dispatch`.
- Новый коммит PR отменяет предыдущий запуск того же workflow и PR.
  Разные PR и разные workflows не отменяют друг друга.
- Запущенные проверки `main` и ручные прогоны не прерываются новым PR.
  Concurrency GitHub может заменить устаревший ожидающий запуск более новым;
  это не журнал проверки каждого промежуточного commit.
- Публикация документации остаётся только на `main` и сохраняет отдельную
  сериализацию deployment. PR проверяет сборку, но ничего не публикует.

Состав существующих jobs, матрицы ОС, тесты, мутации, O0/O2, доказательные
обязательства и версии инструментария не сокращены. Меняется выбор запуска.

## Примеры маршрутизации

| Изменение | Автоматические workflows PR |
| --- | --- |
| `docs/basics.md`, тема, логотип, MkDocs | Documentation |
| Только README или maintenance-текст | Без тяжёлых проверок |
| `editors/**` | Editor support |
| `tests/test_proxy_lifecycle.py` | Compiler tests |
| `examples/apps/liza_proxy_ops.liza` или `proxy/config.liza` | Compiler tests, Editor support, Documentation |
| Baseline `liza_proxy.liza` | Те же + R2-B/R2-C |
| `relay/direction.liza` | Те же + R1/R2-B/R2-C |
| `liza/**`, включая runtime и stdlib | Compiler tests, V0–V4, pipeline harness, R1/R2-B/R2-C, aggregate/mutable agreement |
| Только модель R2-A | R2-A + pipeline harness |
| `verification/relay_r1/**` | R1, R2-B, R2-C + pipeline harness |
| `benchmarks/json/**` | JSON baseline, aggregate/mutable agreement, Compiler tests |
| Один workflow | Этот workflow + быстрая CI routing policy |

R2-A и самостоятельная relay-модель не зависят от компилятора: их правки или
изменение Z3 requirements запускают соответствующие модельные проверки.
V3 учитывает V0–V2 как замороженные зависимости. R2-C учитывает импортируемые
R1/R2-B. Общий benchmark corpus проверяется всеми его потребителями.
Смешанный PR получает объединение нужных workflows. Изменение собственного
YAML всегда запускает соответствующий workflow для приёмки новых настроек.

До изменения политики один docs-only commit открытого PR мог дать девять
запусков по push и десять по pull_request. Теперь он даёт один Documentation
по PR; после merge отдельно выполняется сборка и публикация на main.

## Проверка политики

```sh
python -m pip install -r requirements-ci.txt
python tools/check_ci.py
```

Лёгкий workflow CI routing policy выполняет эту проверку при изменении YAML
или самого проверяющего инструмента. Проверяются независимые наборы изменённых
путей, смешанные изменения, зависимости frozen baselines, отсутствие дублирующего
feature-push, ручные запуски, отмена устаревших PR и отрицательные контроли.
Это проверка конфигурации, не повторная реализация GitHub event delivery.
При добавлении нового входа workflow нужно обновить его path-фильтры и сценарии
в `tools/check_ci.py`. Для синтаксиса YAML и expressions дополнительно применим
`actionlint` (при этой правке использован 1.7.12).

## Ручной прогон независимо от paths

У каждого workflow есть `workflow_dispatch`, доступный через Actions → Run workflow:

```sh
gh workflow run test.yml --ref main
gh workflow run verified-relay-r2c.yml --ref main
# Дорогой полный pipeline V0–V4 на закреплённом proof toolchain:
gh workflow run verified-pipeline.yml --ref main -f full=true
```

Для широкого изменения или release-аудита можно запустить все проверки
(публикация документации намеренно остаётся отдельной операцией):

```sh
for workflow in .github/workflows/*.yml; do
    name="${workflow##*/}"
    if [ "$name" != docs.yml ]; then
        gh workflow run "$name" --ref main
    fi
done
```

Этот цикл запускает обычные наборы; full pipeline требует отдельного `full=true`.
Для воспроизводимой release-приёмки используйте фиксированный tag вместо
движущегося `main` и сверяйте SHA каждого запуска. Результат пропущенного workflow
не является новым свидетельством верификации текущего commit.

У [нативных path-фильтров GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#git-diff-comparisons)
есть ограничения на размер diff. Для больших массовых изменений проверяйте
фактически запущенные наборы и используйте ручной прогон.

Условный workflow не следует делать безусловно обязательным status check:
при пропуске по paths GitHub может оставить такой required check в Pending.
Если вводится branch protection, нужен отдельный всегда запускаемый итоговый
check с явным результатом «не требуется», а не фиктивный успех отсутствующего
теста. На момент изменения у main нет branch protection/rulesets; настройки
репозитория этой правкой не меняются.
