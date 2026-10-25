"""Deterministic corpus and expected profile results, independent of timed code."""
import hashlib
import json
import random

SEED = 9183

def cases():
    good=[b'0',b'-12.34e+56',b'true',b'false',b'null',b'[]',b'{}',
          b'{"x":[true,null,0]}',b'"\\uD83D\\uDE80"',b'"\\u0000"',b'"\\uDBFF\\uDFFF"',
          b'"\\\"\\\\\\/\\b\\f\\n\\r\\t"','"Привет🚀"'.encode(),b'{"x":1,"x":2}',
          b'['*64+b'0'+b']'*64,b'"'+b'a'*20000+b'"',b'1'+b'0'*20000,b'1e'+b'9'*20000]
    bad=[(b'',6,0),(b' ',6,1),(b'[1,]',1,3),(b'{"a":1,}',1,7),
         (b'01',2,1),(b'1.',6,2),(b'1e+',6,3),(b'1e]',2,2),
         (b'"\\q"',3,2),(b'"\\u12x4"',3,5),(b'"\\uDC00"',4,1),
         (b'"\\uD800x"',4,1),(b'"\\uD800\\u0041"',4,1),
         (b'"\\uD800',4,1),(b'"\xed\xa0\x80"',5,1),(b'"\xf0\x9f',5,1),
         (b'"a\x00"',1,2),(b'\xef\xbb\xbf{}',1,0),(b'true false',1,5),
         (b'{"a" 0}',1,5),(b'[}',1,1),(b'NaN',1,0),(b'/*x*/null',1,0),
         (b'['*65+b'0'+b']'*65,7,64),(b'01'+b' '*10000,2,1)]
    rng=random.Random(SEED)
    for i in range(80):
        value={'id':i,'text':rng.choice(['é','🚀','a\n"\\', 'hello']),
               'values':[rng.randrange(-100000,100000), True, False, None]}
        good.append(json.dumps(value,ensure_ascii=bool(i%2)).encode())
    return [(d,0,len(d)) for d in good]+bad

def partitions(data):
    yield [data]
    if len(data)<=256:
        yield [bytes([b]) for b in data]
        for i in range(len(data)+1):yield [data[:i],b'',data[i:]]
    for chunk in (1,7,137,2048):
        yield [data[i:i+chunk] for i in range(0,len(data),chunk)] or [b'']
    rng=random.Random(SEED)
    result=[];i=0
    while i<len(data):
        n=rng.randrange(1,101);result.append(data[i:i+n]);i+=n
    yield result or [b'']

def workloads(size):
    def array(element):
        count=max(1,(size-2)//(len(element)+1))
        return b'['+b','.join([element]*count)+b']'
    return {
        'ascii':array(b'{"id":123,"enabled":true,"name":"liza"}'),
        'unicode':array('"Привет, Liza 🚀"'.encode()),
        'escaped':array(b'"\\uD83D\\uDE80\\n\\t\\u0041"'),
        'numbers':array(b'-123456789.0123456789e+123456789'),
        'long-string':b'"'+b'a'*size+b'"',
        'depth64':array(b'['*63+b'0'+b']'*63),
    }

def sha(data):return hashlib.sha256(data).hexdigest()
