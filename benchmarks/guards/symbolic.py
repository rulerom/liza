"""Independent, fail-closed pure/acyclic SIR and raw LLVM interpreters to SMT-LIB.

No optimizer certificate, may_trap summary or storage_contract is used as an axiom.
Supported integers are unsigned bitvectors; booleans and flat value structs only.
"""
from dataclasses import dataclass
import re

class Unsupported(ValueError):pass
@dataclass(frozen=True)
class S:
    text:str
    width:int # 0 means Bool

def constant(value,width):
    return S(('true' if value else 'false') if not width else f'(_ bv{int(value)%(1<<width)} {width})',width)

def conjunction(*args):return S('(and '+' '.join(x.text for x in args)+')',0) if args else constant(True,0)
def disjunction(args):return S('(or '+' '.join(x.text for x in args)+')',0) if args else constant(False,0)
def negate(x):return S('(not '+x.text+')',0)

class SMT:
    def __init__(self):self.lines=[];self.inputs=[]
    def var(self,name,width):
        sort='Bool' if not width else f'(_ BitVec {width})'
        self.lines.append(f'(declare-fun {name} () {sort})');self.inputs.append((name,width));return S(name,width)
    def bind(self,value):
        name='s'+str(len(self.lines));sort='Bool' if not value.width else f'(_ BitVec {value.width})'
        self.lines.append(f'(define-fun {name} () {sort} {value.text})');return S(name,value.width)
    def query(self,condition):return '(set-logic QF_BV)\n(set-option :timeout 15000)\n'+'\n'.join(self.lines)+f'\n(assert {condition.text})\n(check-sat)\n'

def width(t):
    if t in ('bool','i1'):return 0
    if re.fullmatch(r'[ui](8|16|32|64)',t):return int(t[1:])
    raise Unsupported('type '+t)

def binary(op,a,b):
    if a.width!=b.width:raise Unsupported('operand widths')
    if op in ('eq','ne','ult','ule','ugt','uge'):
        operator={'eq':'=','ne':'distinct','ult':'bvult','ule':'bvule','ugt':'bvugt','uge':'bvuge'}[op]
        return S(f'({operator} {a.text} {b.text})',0)
    operator={'add':'bvadd','sub':'bvsub','and':'bvand' if a.width else 'and','or':'bvor' if a.width else 'or','xor':'bvxor' if a.width else 'xor'}[op]
    return S(f'({operator} {a.text} {b.text})',a.width)

def equal(a,b):
    if isinstance(a,tuple):
        if not isinstance(b,tuple) or len(a)!=len(b):raise Unsupported('result shape')
        return conjunction(*(equal(x,y) for x,y in zip(a,b)))
    return binary('eq',a,b)

def choose(c,a,b):
    if isinstance(a,tuple):return tuple(choose(c,x,y) for x,y in zip(a,b))
    return S(f'(ite {c.text} {a.text} {b.text})',a.width)

def merge(values,guards):
    result=values[-1]
    for value,guard in reversed(list(zip(values[:-1],guards[:-1]))):result=choose(guard,value,result)
    return result

def order(blocks,edges):
    remaining=set(blocks);done=[]
    while remaining:
        ready=[b for b in blocks if b in remaining and all(p in done for p,targets in edges.items() if b in targets)]
        if not ready:raise Unsupported('cyclic CFG')
        done+=ready;remaining-=set(ready)
    return done

def inputs(smt,fn,structs):
    def value(t,prefix):
        if t in structs:return tuple(value(ft,prefix+'_'+n) for n,ft in structs[t])
        if t.startswith('i') and t!='bool':raise Unsupported('signed SIR input')
        return smt.var(prefix,width(t))
    return {p['name']:value(p['type'],p['name']) for p in fn['params']}

def semantic(smt,fn,args,structs):
    blocks={b['name']:b for b in fn['blocks']};edges={}
    for name,b in blocks.items():
        t=b['terminator'];op=t['op'];a=t['args']
        if op=='branch':edges[name]=a[1:]
        elif op=='jump':edges[name]=a
        elif op=='return':edges[name]=[]
        else:raise Unsupported('SIR terminator '+op)
    env=dict(args);paths={};returns=[];traps=[];entry=fn['blocks'][0]['name']
    for name in order(blocks,edges):
        active=constant(True,0) if name==entry else disjunction([v for (p,b),v in paths.items() if b==name])
        for o in blocks[name]['operations']:
            op=o['op'];a=o['args'];t=o['type']
            if op=='constant':v=constant(a[0],width(t))
            elif op=='struct.field':v=env[a[0]][[n for n,_ in structs[o['source_type']]].index(o['field_name'])]
            elif op=='struct.update':
                v=list(env[a[0]]);v[[n for n,_ in structs[t]].index(o['field_name'])]=env[a[1]];v=tuple(v)
            elif op=='phi':v=merge([env[x] for x in a],[paths.get((p,name),constant(False,0)) for p in o['incoming_blocks']])
            elif op in ('eq','ne','ult','ule','ugt','uge','add','sub','and','or','xor'):
                if t.startswith('i'):raise Unsupported('signed arithmetic')
                x,y=(env[z] for z in a);v=binary(op,x,y)
                if op in ('add','sub'):
                    if o['overflow']!='trap':raise Unsupported('arithmetic policy')
                    overflow=binary('ult',v,x) if op=='add' else binary('ult',x,y)
                    traps.append(conjunction(active,overflow));active=smt.bind(conjunction(active,negate(overflow)))
            elif op=='not':v=negate(env[a[0]])
            else:raise Unsupported('SIR operation '+op)
            env[o['result']]=smt.bind(v) if isinstance(v,S) else v
        term=blocks[name]['terminator'];op=term['op'];a=term['args']
        if op=='return':returns.append((active,env[a[0]]))
        elif op=='jump':paths[name,a[0]]=active
        else:
            paths[name,a[1]]=smt.bind(conjunction(active,env[a[0]]));paths[name,a[2]]=smt.bind(conjunction(active,negate(env[a[0]])))
    return {'trap':disjunction(traps),'returns':returns,'covered':disjunction(traps+[p for p,_ in returns])}


def llvm_function(ir,name):
    m=re.search(r'(?ms)^define [^\n]*@'+re.escape(name)+r'\([^\n]*\) \{\n(.*?)^}',ir)
    if not m:raise Unsupported('LLVM function shape '+name)
    blocks={};current=None
    for line in m[1].splitlines():
        if not line.strip() or line.lstrip().startswith(';'):continue
        label=re.fullmatch(r'([\w.]+):',line)
        if label:current=label[1];blocks[current]=[]
        elif current:blocks[current].append(line.strip())
        else:raise Unsupported('missing block label')
    return blocks


def llvm(smt,ir,name,args):
    blocks=llvm_function(ir,name);edges={}
    for n,lines in blocks.items():
        t=lines[-1]
        if t.startswith('br '):edges[n]=re.findall(r'label %([\w.]+)',t)
        elif t.startswith('ret ') or t=='unreachable':edges[n]=[]
        else:raise Unsupported('LLVM terminator '+t)
    env={'%'+k:v for k,v in args.items()};paths={};returns=[];traps=[];entry=next(iter(blocks))
    def atom(token,w=None):
        token=token.strip()
        if token.startswith('%'):return env[token]
        if token in ('true','false'):return constant(token=='true',0)
        if re.fullmatch(r'-?\d+',token) and w is not None:return constant(int(token),w)
        raise Unsupported('LLVM operand '+token)
    for name in order(blocks,edges):
        active=constant(True,0) if name==entry else disjunction([v for (p,b),v in paths.items() if b==name])
        for line in blocks[name][:-1]:
            if line=='call void @llvm.trap()':traps.append(active);active=constant(False,0);continue
            match=re.fullmatch(r'(%[\w.]+) = (.*)',line)
            if not match:raise Unsupported('LLVM instruction '+line)
            dest,expr=match.groups()
            if expr.startswith('extractvalue '):
                m=re.fullmatch(r'extractvalue .+ (%[\w.]+), (\d+)',expr)
                if not m:raise Unsupported(expr)
                v=env[m[1]][int(m[2])]
            elif expr.startswith('insertvalue '):
                m=re.fullmatch(r'insertvalue %[\w.]+ (%[\w.]+), (i\d+) ([^,]+), (\d+)',expr)
                if not m:raise Unsupported(expr)
                v=list(env[m[1]]);v[int(m[4])]=atom(m[3],width(m[2]));v=tuple(v)
            elif expr.startswith('phi '):
                ty=expr.split()[1];pairs=re.findall(r'\[\s*([^,\]]+),\s*%([\w.]+)\s*\]',expr)
                if not pairs:raise Unsupported(expr)
                w=None if ty.startswith('%') else width(ty)
                v=merge([atom(x,w) for x,_ in pairs],[paths.get((p,name),constant(False,0)) for _,p in pairs])
            elif expr.startswith('icmp '):
                m=re.fullmatch(r'icmp (eq|ne|ult|ule|ugt|uge) (i\d+) ([^,]+), (.+)',expr)
                if not m:raise Unsupported(expr)
                v=binary(m[1],atom(m[3],width(m[2])),atom(m[4],width(m[2])))
            elif expr.startswith('call '):
                m=re.fullmatch(r'call \{i(\d+), i1\} @llvm.u(add|sub).with.overflow.i\1\(i\1 ([^,]+), i\1 ([^)]+)\)',expr)
                if not m:raise Unsupported(expr)
                w=int(m[1]);x=atom(m[3],w);y=atom(m[4],w);value=binary(m[2],x,y)
                v=(value,binary('ult',value,x) if m[2]=='add' else binary('ult',x,y))
            else:
                m=re.fullmatch(r'(add|sub|xor|and|or) (i\d+) ([^,]+), (.+)',expr)
                if not m:raise Unsupported(expr)
                v=binary(m[1],atom(m[3],width(m[2])),atom(m[4],width(m[2])))
            env[dest]=smt.bind(v) if isinstance(v,S) else v
        term=blocks[name][-1]
        if term.startswith('ret '):
            m=re.fullmatch(r'ret (i\d+|%[\w.]+) (.+)',term)
            if not m:raise Unsupported(term)
            returns.append((active,atom(m[2],None if m[1].startswith('%') else width(m[1]))))
        elif term=='unreachable':
            # Any reachable undefined edge is included in comparison coverage.
            if active.text!='false':raise Unsupported('unmodeled unreachable')
        elif term.startswith('br label '):paths[name,edges[name][0]]=active
        else:
            m=re.fullmatch(r'br i1 ([^,]+), label %([\w.]+), label %([\w.]+)',term)
            if not m:raise Unsupported(term)
            c=atom(m[1],0);paths[name,m[2]]=smt.bind(conjunction(active,c));paths[name,m[3]]=smt.bind(conjunction(active,negate(c)))
    return {'trap':disjunction(traps),'returns':returns,'covered':disjunction(traps+[p for p,_ in returns])}


def mismatch(a,b):
    checks=[negate(a['covered']),negate(b['covered']),binary('ne',a['trap'],b['trap'])]
    for pa,va in a['returns']:
        for pb,vb in b['returns']:checks.append(conjunction(pa,pb,negate(equal(va,vb))))
    return disjunction(checks)
