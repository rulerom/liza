---
description: "Экспериментальный scoped SPSC канал u32 между двумя workers Liza."
---

# Экспериментальный scoped-канал u32

Первый срез создаёт один ограниченный канал и две функции в нативных потоках.
Endpoint не является значением Liza и не может покинуть группу. Сигнатуры
функций `producer()->u32` и `consumer()->u32` определяются во входном модуле;
компилятор закрепляет роли и проверяет транзитивный граф вызовов, включая
imports и generics. `channels.send` допустим только в producer,
`channels.receive` — только в consumer; из основного кода и противоположной
роли они отклоняются. Рекурсивный запуск `channels.run`, вложенные workers,
process-wide signal watcher и другой неаудированный runtime в ролях запрещены.
Роли могут использовать аудированные worker-local Region и Reactor по правилам
[workers](scoped-workers.md).

```liza
fn producer()->u32:io {
    var sent:u32=0
    while sent<10 {
        status=channels.send(sent)
        if status==0 {sent=sent+1}
        if status==2 {return 1}
    }
    return 0
}
fn consumer()->u32:io {
    var received:u32=0
    while received<10 {
        result=channels.receive()
        status=result>>32
        if status==2 {return 2}
        if status==0 {
            if u32.wrap(result)!=received {return 2}
            received=received+1
        }
    }
    return 0
}
fn main()->u32:io,alloc {
    match channels.run(8,1024) {
        Err(error)=>{return 1}
        Ok(result)=>{
            if result.producer!=0 || result.consumer!=0 || result.discarded!=0 {return 2}
            return 0
        }
    }
}
```

- `channels.run(capacity:u32, budget:u64)->Result<ChannelRun,ChannelError>`
  создаёт 1–65536 слотов, не превышая бюджет памяти канала, запускает оба потока
  и ожидает их. `Ok(ChannelRun)` содержит отдельные `producer:u32`,
  `consumer:u32` и `discarded:u32`. Значения функций доступны только после
  успешного запуска и join обоих workers; одинаковые ненулевые результаты не
  маскируют друг друга. `Err(ChannelError.InvalidCapacity)` означает неверную
  вместимость или бюджет; `Err(ChannelError.Unavailable)` — отказ выделения или
  запуска. Пользовательских результатов в `Err` нет. Группа и её нативные
  стеки не входят в бюджет канала. Счётчики отправленных и полученных сообщений
  в этом срезе не предоставляются.
- `channels.send(value:u32)->u32` возвращает 0 (`Ok`), 1 (`Full`) или 2
  (`Closed`). `Ok` означает публикацию, а не обработку получателем. `Full`
  не меняет очередь; оригинальное значение отправителя не потребляется.
- `channels.receive()->u64` возвращает в старших 32 битах 0 (`Ok`), 1 (`Empty`)
  или 2 (`Closed`). При `Ok` младшие 32 бита содержат значение.

Очередь FIFO; полная запись выполняется до публикации под mutex / SRW lock.
Операции не ждут освобождения слота или появления сообщения, но могут ждать
захвата lock. При нормальном возврате producer его сторона закрывается, и
consumer может дочитать очередь. Возврат consumer закрывает приём и учитывает
оставшиеся сообщения как отброшенные. Ресурсы канала освобождаются после join
обоих потоков. Ошибка создания неполной группы не запускает пользовательские
функции. Бесконечный worker задерживает `run`; trap не гарантирует cleanup.

Пока поддерживаются только два worker и одно скалярное сообщение `u32`.
Нет произвольных endpoints, блокирующего ожидания, fairness, каналов MPSC,
передачи ресурсов, общего состояния пользователя или стабильного API.
Пример намеренно использует повторные попытки и не является сетевым reactor.
Предположения, бюджет и критерии общего проекта описаны в
[контракте scoped channels](scoped-channels-contract.md).
[Ожидание с deadline](scoped-channel-wait-contract.md) пока описано как отдельный проект.
