"""Two supported readonly LLVM loop forms, independently cut and checked.
Guarded i32 header (generated/O0), or i64 body header with latch exit (O2).
No reuse of Semantic IR control flow or results. No stores, frees or calls
other than overflow intrinsics/trap. One valid initialized readonly object.
"""
from dataclasses import dataclass
import re
import z3 as z
from .core import Unsupported,Exit,fits

@dataclass(frozen=True)
class Pointer:
    offset:object
    origin:str='view'

def sint(value,width):return z.If(value>=(1<<(width-1)),value-(1<<width),value)

class Engine:
    def __init__(self,text,name,ctx):
        self.ctx=ctx;self.name=name;self.observed=set()
        m=re.search(r'^define i32 @liza_'+name+r'\(([^\n]*)\)([^\n]*) \{\n(.*?)^}',text,re.M|re.S)
        if not m:raise Unsupported('LLVM function signature')
        params,attrs,body=m.groups()
        expected='{ ptr, i32 } %p0, i8 %p1' if name=='search' else '{ ptr, i32 } %p0'
        if params!=expected:raise Unsupported('LLVM view signature')
        if not re.fullmatch(r'(?: local_unnamed_addr)?(?: #\d+)?',attrs):raise Unsupported('LLVM function attributes')
        group=re.search(r'#(\d+)',attrs)
        if group:
            decl=re.search(r'^attributes #'+group[1]+r' = \{ (.*) \}',text,re.M)
            allowed=r'(?:nofree|norecurse|nosync|nounwind|memory\(read, inaccessiblemem: (?:none|write)\))'
            if not decl or not re.fullmatch(allowed+r'(?: '+allowed+r')*',decl[1]):raise Unsupported('LLVM attribute group')
        layout=re.search(r'^target datalayout = "(.*)"',text,re.M)
        triple=re.search(r'^target triple = "(.*)"',text,re.M)
        if layout and not layout[1].startswith('e-'):raise Unsupported('endianness')
        if layout:
            for field in layout[1].split('-'):
                if re.match(r'p(?:0)?:',field) and field not in ('p:64:64','p0:64:64'):raise Unsupported('pointer layout')
        if triple and not re.match(r'(x86_64|arm64|aarch64)-',triple[1]):raise Unsupported('target')
        self.blocks={};label=None
        for line in body.splitlines():
            line=line.split(';')[0].strip()
            if not line:continue
            if line.endswith(':'):
                label=line[:-1]
                if label in self.blocks:raise Unsupported('duplicate block')
                self.blocks[label]=[]
            elif label is None:raise Unsupported('unnamed entry')
            else:self.blocks[label].append(line)
        self.start=next(iter(self.blocks))
        visited=set();active=set();backtargets=set()
        def dfs(label):
            if label in active:backtargets.add(label);return
            if label in visited:return
            active.add(label)
            for target in re.findall(r'label %([\w.]+)',self.blocks[label][-1]):dfs(target)
            active.remove(label);visited.add(label)
        dfs(self.start)
        if len(backtargets)!=1:raise Unsupported('requires one natural-loop cutpoint')
        self.header=next(iter(backtargets));self.phis=[]
        for line in self.blocks[self.header]:
            pm=re.fullmatch(r'(%[\w.]+) = phi i(32|64) (.+)',line)
            if pm:self.phis.append((pm[1],int(pm[2]),pm[3]))
        if len(self.phis)!=(1 if name=='search' else 2):raise Unsupported('LLVM loop phi roles')
        self.index=self.phis[0][0];self.index_width=self.phis[0][1]
        self.acc=self.phis[1][0] if name=='sum' else None
        self.strict=any(' = load ' in line for line in self.blocks[self.header])
        if self.index_width!=(64 if self.strict else 32) or self.acc and self.phis[1][1]!=32:
            raise Unsupported('unsupported loop form')
        self.params={'%p0':(Pointer(z.IntVal(0)),ctx.length)}
        if name=='search':self.params['%p1']=ctx.needle
    def roles(self,env):return env[self.index],sint(env[self.acc],32) if self.acc else None
    def symbolic_header(self,seed):
        env=dict(seed);constraints=[]
        for name,width,_ in self.phis:
            env[name]=z.Int('header_'+name[1:]);constraints.append(fits(env[name],bits=width))
        return env,z.And(*constraints)
    def entry(self):return self.walk(self.start,self.params,False)
    def step(self,env):return self.walk(self.header,env,True)
    def value(self,text,width,env):
        if text.startswith('%'):return env[text]
        if width==1 and text in ('true','false','0','1'):return z.BoolVal(text in ('true','1'))
        if re.fullmatch(r'-?\d+',text):return z.IntVal(int(text)%(1<<width))
        raise Unsupported('LLVM operand '+text)
    def phi(self,entries,width,previous,env):
        items=re.findall(r'\[ ([^,]+), %([\w.]+) \]',entries)
        if ', '.join('[ '+v+', %'+b+' ]' for v,b in items)!=entries:raise Unsupported('phi syntax')
        values=[v for v,b in items if b==previous]
        if len(values)!=1:raise Unsupported('phi predecessor')
        return self.value(values[0],width,env)
    def walk(self,start,environment,skip_start_phi):
        exits=[]
        def visit(label,env,path,seen,previous=None,skip_phi=False):
            env=dict(env);old=dict(env)
            if label==self.header and not skip_phi:
                for name,width,entries in self.phis:env[name]=self.phi(entries,width,previous,old)
                exits.append(Exit('Back',path,env));return
            if label in seen:raise Unsupported('uncovered LLVM cycle')
            seen=seen|{label}
            def bad(condition,reason):exits.append(Exit('Undefined',z.And(path,condition),dict(env),reason=reason))
            instructions=self.blocks[label]
            for pos,line in enumerate(instructions):
                self.observed.add(line.split(' = ')[-1].split()[0])
                if re.fullmatch(r'(?:tail )?call void @llvm.trap\(\)(?: #\d+)?',line):
                    if instructions[pos+1:]!=['unreachable']:raise Unsupported('trap continuation')
                    exits.append(Exit('Trap',path,env));return
                if line=='unreachable':bad(z.BoolVal(True),'unreachable');return
                m=re.fullmatch(r'ret i32 (.+)',line)
                if m:
                    if pos!=len(instructions)-1:raise Unsupported('return terminator')
                    value=self.value(m[1],32,env)
                    exits.append(Exit('Return',path,env,sint(value,32) if self.name=='sum' else value));return
                m=re.fullmatch(r'br label %([\w.]+)',line)
                if m:
                    if pos!=len(instructions)-1:raise Unsupported('branch terminator')
                    visit(m[1],env,path,seen,label);return
                m=re.fullmatch(r'br i1 (.+), label %([\w.]+), label %([\w.]+)',line)
                if m:
                    if pos!=len(instructions)-1:raise Unsupported('branch terminator')
                    c=self.value(m[1],1,env)
                    visit(m[2],env,z.And(path,c),seen,label);visit(m[3],env,z.And(path,z.Not(c)),seen,label);return
                m=re.fullmatch(r'(%[\w.]+) = (.+)',line)
                if not m:raise Unsupported('LLVM instruction '+line)
                dest,expr=m.groups()
                m=re.fullmatch(r'phi i(32|64) (.+)',expr)
                if m:
                    if not skip_phi:env[dest]=self.phi(m[2],int(m[1]),previous,old)
                    continue
                m=re.fullmatch(r'extractvalue \{\s*ptr, i32\s*\} (%[\w.]+), ([01])',expr)
                if m:env[dest]=env[m[1]][int(m[2])];continue
                m=re.fullmatch(r'extractvalue \{\s*i32, i1\s*\} (%[\w.]+), ([01])',expr)
                if m:env[dest]=env[m[1]][int(m[2])];continue
                m=re.fullmatch(r'icmp (eq|ne|ult|ule|ugt|uge|slt|sle|sgt|sge) i(8|32|64) (.+), (.+)',expr)
                if m:
                    a,b=self.value(m[3],int(m[2]),env),self.value(m[4],int(m[2]),env)
                    if m[1].startswith('s'):a,b=sint(a,int(m[2])),sint(b,int(m[2]))
                    op=m[1][-2:] if m[1] not in ('eq','ne') else m[1]
                    env[dest]={'eq':lambda:a==b,'ne':lambda:a!=b,'lt':lambda:a<b,'le':lambda:a<=b,'gt':lambda:a>b,'ge':lambda:a>=b}[op]();continue
                m=re.fullmatch(r'(zext|trunc)((?: nneg| nuw)?) i(32|64) (.+) to i(32|64)',expr)
                if m:
                    op,flag,src,token,dst=m.groups();src,dst=int(src),int(dst);a=self.value(token,src,env)
                    if op=='zext' and dst>src:
                        if flag==' nneg':bad(a>=(1<<(src-1)),'zext nneg')
                        elif flag:raise Unsupported('zext flag')
                        env[dest]=a
                    elif op=='trunc' and dst<src:
                        if flag==' nuw':bad(a>=(1<<dst),'trunc nuw')
                        elif flag:raise Unsupported('trunc flag')
                        env[dest]=a%(1<<dst)
                    else:raise Unsupported('cast widths')
                    continue
                m=re.fullmatch(r'getelementptr( inbounds)? i(8|32), ptr (%[\w.]+), i64 (.+)',expr)
                if m:
                    base=env[m[3]]
                    if not isinstance(base,Pointer) or base.origin!='view':raise Unsupported('pointer origin')
                    offset=base.offset+sint(self.value(m[4],64,env),64)*(int(m[2])//8)
                    bad(z.Or(offset<-(1<<63),offset>=(1<<63)),'address-index wrap')
                    if m[1]:bad(z.Or(offset<0,offset>self.ctx.length*self.ctx.stride),'GEP inbounds')
                    env[dest]=Pointer(offset);continue
                m=re.fullmatch(r'load i(8|32), ptr (%[\w.]+)(?:, align (\d+))?',expr)
                if m:
                    p=env[m[2]];size=int(m[1])//8;align=int(m[3]) if m[3] else size
                    if not isinstance(p,Pointer) or p.origin!='view':raise Unsupported('load pointer origin')
                    if align not in (1,2,4) or align>self.ctx.stride:raise Unsupported('load alignment')
                    bad(z.Or(p.offset<0,p.offset+size>self.ctx.length*self.ctx.stride,p.offset%align!=0),'readonly object bounds/alignment')
                    env[dest]=sum(self.ctx.byte(p.offset+k)*(1<<(8*k)) for k in range(size));continue
                m=re.fullmatch(r'(?:tail )?call \{\s*i32, i1\s*\} @llvm\.([us])add\.with\.overflow\.i32\(i32 (.+), i32 (.+)\)',expr)
                if m:
                    a,b=self.value(m[2],32,env),self.value(m[3],32,env)
                    wide=(sint(a,32)+sint(b,32)) if m[1]=='s' else a+b
                    env[dest]=(wide%(1<<32),z.Not(fits(wide,m[1]=='s')));continue
                m=re.fullmatch(r'add((?: nuw| nsw)*) i(32|64) (.+), (.+)',expr)
                if m:
                    bits=int(m[2]);a,b=self.value(m[3],bits,env),self.value(m[4],bits,env)
                    if 'nuw' in m[1]:bad(z.Not(fits(a+b,bits=bits)),'add nuw')
                    if 'nsw' in m[1]:bad(z.Not(fits(sint(a,bits)+sint(b,bits),True,bits)),'add nsw')
                    env[dest]=(a+b)%(1<<bits);continue
                raise Unsupported('LLVM expression '+expr)
            raise Unsupported('missing terminator')
        visit(start,environment,z.BoolVal(True),set(),skip_phi=skip_start_phi)
        return exits
