"""Finite abstract notification protocol, independent of the C runtime."""
from dataclasses import dataclass, replace
from collections import deque


@dataclass(frozen=True)
class State:
    queue: tuple = ()
    published: tuple = ()
    received: tuple = ()
    closed: bool = False
    receiver: str = 'running'
    notification: str = 'idle'
    fault_observed: bool = False


def transitions(s, capacity, mutation=None):
    # One producer: it cannot publish or close again until its signal completes.
    if not s.closed and len(s.published) < 2 and len(s.queue) < capacity and s.notification != 'owed' and s.notification != 'fault':
        value = len(s.published)
        notification = 'signalled' if s.notification == 'signalled' else 'owed'
        yield 'publish', replace(s, queue=s.queue + (value,), published=s.published + (value,), notification=notification)
    if not s.closed and s.notification not in ('owed', 'fault'):
        yield 'close', replace(s, closed=True, notification='signalled' if s.notification == 'signalled' else 'owed')
    if s.notification == 'owed':
        yield 'signal_ok', replace(s, notification='idle' if mutation == 'lost_wake' else 'signalled')
        yield 'signal_fail', replace(s, notification='fault', fault_observed=mutation != 'hidden_fault')
    if s.receiver == 'running' and s.queue:
        yield 'receive', replace(s, queue=s.queue[1:], received=s.received + s.queue[:1])
    if s.receiver == 'running' and s.notification == 'signalled':
        # Reset happens while running; the next arm rechecks queue and close.
        yield 'reset', replace(s, notification='idle')
    if s.receiver == 'running' and (not s.queue or mutation == 'early_arm') and not s.closed and s.notification == 'idle':
        yield 'arm', replace(s, receiver='armed')
    if s.receiver == 'armed' and s.notification == 'signalled':
        yield 'wake', replace(s, receiver='running')
        if mutation == 'reset_race':
            yield 'bad_reset', replace(s, notification='idle')


def violation(s):
    if s.received + s.queue != s.published:
        return 'fifo/accounting'
    # An owed signal is in flight, not a durable notification. Progress of its
    # owner is an explicit assumption; model does not establish liveness.
    if s.receiver == 'armed' and (s.queue or s.closed) and s.notification not in ('owed', 'signalled') and not s.fault_observed:
        return 'sleeping with unobservable work or close'
    if s.notification == 'fault' and not s.fault_observed:
        return 'unobservable fault'
    return None


def explore(capacity, mutation=None):
    initial = State()
    seen = {initial}
    pending = deque([(initial, ())])
    while pending:
        state, trace = pending.popleft()
        bad = violation(state)
        if bad:
            return len(seen), trace, bad
        for action, new in transitions(state, capacity, mutation):
            if new not in seen:
                seen.add(new)
                pending.append((new, trace + (action,)))
    return len(seen), None, None
