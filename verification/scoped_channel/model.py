"""Bounded independent FIFO spec, circular model and history linearizer.

No production sources or runtime data structures are imported. This checks
finite examples, not arbitrary executions or C/LLVM memory semantics.
"""
from dataclasses import dataclass, replace
from functools import lru_cache

@dataclass(frozen=True)
class State:
    queue: tuple = ()
    sender_closed: bool = False
    receiver_closed: bool = False
    published: int = 0
    received: int = 0
    discarded: int = 0


def step(s, capacity, op, arg=None):
    if op == 'send':
        if s.sender_closed or s.receiver_closed:return s, 'closed'
        if len(s.queue) == capacity:return s, 'full'
        return replace(s,queue=s.queue+(arg,),published=s.published+1), 'ok'
    if op == 'receive':
        if s.receiver_closed:return s, 'closed'
        if not s.queue:return s, 'closed' if s.sender_closed else 'empty'
        return replace(s,queue=s.queue[1:],received=s.received+1), 'ok:'+str(s.queue[0])
    if op == 'close_sender':return replace(s,sender_closed=True), 'ok'
    if op == 'close_receiver':
        n=len(s.queue)
        return replace(s,receiver_closed=True,queue=(),discarded=s.discarded+n), 'discard:'+str(n)
    raise ValueError('unknown operation '+op)

@dataclass(frozen=True)
class Ring:
    slots: tuple
    head: int = 0
    tail: int = 0
    count: int = 0
    sender_closed: bool = False
    receiver_closed: bool = False
    published: int = 0
    received: int = 0
    discarded: int = 0


def ring_step(s, op, arg=None, mutation=None):
    n=len(s.slots)
    if op == 'send':
        if mutation == 'closed_priority' and s.count == n:return s,'full'
        if s.sender_closed or s.receiver_closed:return s,'closed'
        if s.count == n:return s,'full'
        slots=list(s.slots);slots[s.tail]=arg ^ 1 if mutation=='publication' else arg
        return replace(s,slots=tuple(slots),tail=(s.tail+1)%n,count=s.count+1,published=s.published+1),'ok'
    if op == 'receive':
        if s.receiver_closed:return s,'closed'
        if not s.count:return s,'closed' if s.sender_closed else 'empty'
        index=(s.tail-1)%n if mutation=='fifo' else s.head
        value=s.slots[index]
        return replace(s,head=(s.head+1)%n,count=s.count if mutation=='release' else s.count-1,received=s.received+1),'ok:'+str(value)
    if op == 'close_sender':return replace(s,sender_closed=True),'ok'
    if op == 'close_receiver':return replace(s,receiver_closed=True,head=s.tail,count=0,discarded=s.discarded+s.count),'discard:'+str(s.count)
    raise ValueError(op)


def logical_queue(s):
    return tuple(s.slots[(s.head+i)%len(s.slots)] for i in range(s.count))


def linearize(history, capacity):
    """Return one sequential witness or None for complete recorded operations."""
    if capacity<1:raise ValueError('capacity')
    points=[]
    for h in history:
        if h['start']>=h['end']:raise ValueError('invalid interval')
        points.extend((h['start'],h['end']))
    if len(set(points))!=len(points):raise ValueError('duplicate event positions')
    predecessors=[]
    for h in history:
        mask=0
        for j,other in enumerate(history):
            if other['end']<h['start']:mask|=1<<j
        predecessors.append(mask)
    full=(1<<len(history))-1
    @lru_cache(None)
    def search(done,state):
        if done==full:return ()
        for i,h in enumerate(history):
            if done & (1<<i) or predecessors[i] & ~done:continue
            new,result=step(state,capacity,h['op'],h.get('arg'))
            if result==h['result']:
                rest=search(done | (1<<i),new)
                if rest is not None:return (i,)+rest
        return None
    return search(0,State())
