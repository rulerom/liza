"""Fail-closed, acyclic LLVM fragment with explicit physical local storage.

No general LLVM interpreter is claimed. See SUPPORTED and ASSUMPTIONS in the
report. Reached poison creation is conservatively Undefined in this model.
"""
import re
import z3 as z
from .common import Unsupported, bit, collect, scalar
from .memory import Memory, Pointer

TYPE=r'(?:i(?:1|8|16|32|64|128)|\[4 x i8\]|<4 x i8>)'
NAME=r'%[\w.]+'
SUPPORTED=['alloca (1..16 bytes)','getelementptr (i8 or [4 x i8]; inbounds, optionally nuw)' ,
           'load/store (byte integers, [4 x i8], <4 x i8>)','insertvalue/extractvalue ([4 x i8])',
           'insertelement/extractelement (<4 x i8>)','integer add/sub/and/or/xor/shl/lshr/ashr',
           'integer icmp','zext/sext/trunc','select','phi','br','ret','llvm.trap; unreachable',
           'bitcast (four bytes between i32, <4 x i8>)']
ASSUMPTIONS=['little endian; 64-bit address/index space; scalar widths 1,8,16,32,64,128',
             'successful distinct live local allocations of 1..16 bytes; no stack exhaustion',
             'pointer origin retained; byte offsets; alloca bytes initially uninitialized',
             'nuw GEP requires inbounds; negative nuw offsets conservatively rejected; base allocations do not wrap addresses',
             'alignment known from alloca (implicit byte-array alignment 1); stronger access alignment is unknown',
             'no pointer-index arithmetic wrap; inbounds also requires intermediate offsets in [0,size]',
             'reachable poison, uninitialized read, misaligned or out-of-bounds access are model Undefined',
             'no pointer escape, globals, heap, calls except trap, lifetime intrinsics or loops',
             'unknown instruction/attribute/layout yields unknown, never proved']


def width(ty):
    if not re.fullmatch(r'i(1|8|16|32|64|128)',ty):raise Unsupported('integer type '+ty)
    return int(ty[1:])


def size(ty):
    if ty in ('[4 x i8]','<4 x i8>'):return 4
    w=width(ty)
    if w==1:raise Unsupported('i1 storage')
    return w//8


def natural_align(ty):
    return 1 if ty=='[4 x i8]' else 4 if ty=='<4 x i8>' else size(ty)


def validate(ty,value):
    if ty in ('[4 x i8]','<4 x i8>'):
        if not isinstance(value,tuple) or len(value)!=4:raise Unsupported('aggregate operand type')
        for v in value:scalar(v,8)
        return value
    return scalar(value,width(ty))


def to_bytes(ty,value):
    validate(ty,value)
    if isinstance(value,tuple):return value
    return tuple(z.Extract(i*8+7,i*8,value) for i in range(size(ty)))


def from_bytes(ty,values):
    if ty in ('[4 x i8]','<4 x i8>'):return tuple(values)
    return values[0] if len(values)==1 else z.Concat(*reversed(values))


def function(text,name):
    m=re.search(r'^define ([^\n]+) @liza_'+re.escape(name)+r'\(([^\n]*)\)([^\n]*) \{\n(.*?)^}',text,re.M|re.S)
    if not m:raise Unsupported('missing LLVM function '+name)
    return m


def evaluate(text,name,args):
    m=function(text,name);result,params,attrs,body=m.groups()
    layout=re.search(r'^target datalayout = "(.*)"',text,re.M)
    triple=re.search(r'^target triple = "(.*)"',text,re.M)
    if layout:
        if not layout[1].startswith('e-'):raise Unsupported('not little endian')
        for field in layout[1].split('-'):
            if re.match(r'p(?:0)?:',field) and field not in ('p:64:64','p0:64:64'):raise Unsupported('default pointer layout')
    if triple and not re.match(r'(x86_64|arm64|aarch64)-',triple[1]):raise Unsupported('target architecture')
    rm=re.fullmatch(r'(?:noundef )?(i(?:1|8|16|32|64|128))',result)
    if not rm:raise Unsupported('return type/attribute '+result)
    return_type=rm[1]
    if not re.fullmatch(r'(?: local_unnamed_addr)?(?: #\d+)?',attrs):raise Unsupported('function attributes '+attrs)
    group=re.search(r'#(\d+)',attrs)
    if group:
        decl=re.search(r'^attributes #'+group[1]+r' = \{ (.*) \}',text,re.M)
        allowed=r'(?:nounwind|nofree|nosync|norecurse|mustprogress|willreturn|memory\(none\)|memory\(inaccessiblemem: write\))'
        if not decl or not re.fullmatch(allowed+r'(?: '+allowed+r')*',decl[1]):raise Unsupported('attribute group')
    ps=params.split(',') if params else []
    if len(ps)!=len(args):raise Unsupported('LLVM arity')
    env={};returned=[]
    for p,a in zip(ps,args):
        pm=re.fullmatch('('+TYPE+') (returned )?('+NAME+')',p.strip())
        if not pm:raise Unsupported('parameter '+p)
        env[pm[3]]=validate(pm[1],a)
        if pm[2]:returned.append(a)
    blocks={};current=None
    for line in body.splitlines():
        line=line.split(';')[0].strip()
        if not line:continue
        if line.endswith(':'):
            current=line[:-1]
            if current in blocks:raise Unsupported('duplicate block')
            blocks[current]=[]
        elif current is None:raise Unsupported('unnamed entry')
        else:blocks[current].append(line)
    exits=[];violations=[];observed=set()

    def val(ty,token,env):
        token=token.strip()
        if token.startswith('%'):return validate(ty,env[token])
        if token=='zeroinitializer':return tuple(z.BitVecVal(0,8) for _ in range(4)) if ty.startswith(('[','<')) else z.BitVecVal(0,width(ty))
        if token in ('true','false'):return scalar(z.BitVecVal(int(token=='true'),1),width(ty))
        if re.fullmatch(r'-?\d+',token):return z.BitVecVal(int(token),width(ty))
        raise Unsupported('constant '+token)

    def visit(label,env,memory,path,seen,previous=None):
        if label in seen:raise Unsupported('LLVM loop')
        seen=seen|{label};env=dict(env);memory=memory.fork();old=dict(env)
        instructions=blocks[label]
        def undefined(condition,reason):
            bad=z.And(path,condition)
            exits.append(('Undefined',bad,None));violations.append((bad,reason))
        for pos,line in enumerate(instructions):
            expr=line.split(' = ',1)[-1]
            observed.add(expr.split()[0])
            if re.fullmatch(r'(?:tail )?call void @llvm.trap\(\)(?: #\d+)?',line):
                if instructions[pos+1:]!=['unreachable']:raise Unsupported('trap continuation')
                observed.add('llvm.trap');exits.append(('Trap',path,None));return
            if line=='unreachable':undefined(z.BoolVal(True),'unreachable without trap');return
            m=re.fullmatch('ret ('+TYPE+') (.+)',line)
            if m:
                if m[1]!=return_type or pos!=len(instructions)-1:raise Unsupported('return structure')
                value=val(m[1],m[2],env)
                for promised in returned:
                    scalar(promised,width(return_type))
                    undefined(value!=promised,'returned parameter promise violation')
                exits.append(('Return',path,value));return
            m=re.fullmatch(r'br label %([\w.]+)',line)
            if m:
                if pos!=len(instructions)-1:raise Unsupported('branch structure')
                visit(m[1],env,memory,path,seen,label);return
            m=re.fullmatch(r'br i1 (.+), label %([\w.]+), label %([\w.]+)',line)
            if m:
                if pos!=len(instructions)-1:raise Unsupported('branch structure')
                c=val('i1',m[1],env)==1
                visit(m[2],env,memory,z.And(path,c),seen,label)
                visit(m[3],env,memory,z.And(path,z.Not(c)),seen,label);return
            m=re.fullmatch('store ('+TYPE+') (.+), ptr ('+NAME+')(?:, align (\d+))?',line)
            if m:
                valid=memory.store(env[m[3]],to_bytes(m[1],val(m[1],m[2],env)),int(m[4]) if m[4] else natural_align(m[1]))
                undefined(z.Not(valid),'invalid store bounds/alignment');continue
            m=re.fullmatch('('+NAME+') = (.+)',line)
            if not m:raise Unsupported('LLVM instruction '+line)
            dest,expr=m.groups()
            m=re.fullmatch('alloca ('+TYPE+')(?:, align (\d+))?',expr)
            if m:
                env[dest]=memory.allocate(dest,size(m[1]),int(m[2]) if m[2] else natural_align(m[1]));continue
            m=re.fullmatch('load ('+TYPE+'), ptr ('+NAME+')(?:, align (\d+))?',expr)
            if m:
                values,valid,init=memory.load(env[m[2]],size(m[1]),int(m[3]) if m[3] else natural_align(m[1]))
                undefined(z.Not(valid),'invalid load bounds/alignment')
                undefined(z.And(valid,z.Not(init)),'uninitialized load')
                env[dest]=from_bytes(m[1],values);continue
            m=re.fullmatch(r'getelementptr((?: inbounds| nuw)*) (i8|\[4 x i8\]), ptr ('+NAME+r'), (.+)',expr)
            if m:
                indices=[]
                for field in m[4].split(', '):
                    im=re.fullmatch(r'(i32|i64) (.+)',field)
                    if not im:raise Unsupported('GEP index '+field)
                    indices.append(val(im[1],im[2],env))
                scales=[1] if m[2]=='i8' and len(indices)==1 else [4,1] if m[2]=='[4 x i8]' and len(indices)==2 else None
                if scales is None:raise Unsupported('GEP shape')
                pointer,valid=memory.gep(env[m[3]],indices,scales,m[1].split())
                undefined(z.Not(valid),'GEP offset/no-wrap/inbounds violation');env[dest]=pointer;continue
            m=re.fullmatch(r'insertvalue \[4 x i8\] (.+), i8 (.+), ([0-3])',expr)
            if m:
                values=list(val('[4 x i8]',m[1],env));values[int(m[3])]=val('i8',m[2],env)
                env[dest]=tuple(values);continue
            m=re.fullmatch(r'extractvalue \[4 x i8\] (.+), ([0-3])',expr)
            if m:env[dest]=val('[4 x i8]',m[1],env)[int(m[2])];continue
            m=re.fullmatch(r'(insert|extract)element <4 x i8> ([^,]+), (?:i8 ([^,]+), )?(i32|i64) (.+)',expr)
            if m:
                if (m[1]=='insert') != (m[3] is not None):raise Unsupported('vector instruction shape')
                values=val('<4 x i8>',m[2],env);index=val(m[4],m[5],env)
                undefined(z.UGE(index,4),'vector index out of bounds')
                if m[1]=='insert':env[dest]=tuple(z.If(index==j,val('i8',m[3],env),v) for j,v in enumerate(values))
                else:
                    selected=values[0]
                    for j in range(1,4):selected=z.If(index==j,values[j],selected)
                    env[dest]=selected
                continue
            m=re.fullmatch('(zext|sext|trunc)( nneg)? ('+TYPE+') (.+) to ('+TYPE+')',expr)
            if m:
                value=val(m[3],m[4],env);src=width(m[3]);dst=width(m[5])
                if m[2]:
                    if m[1]!='zext':raise Unsupported('nneg on non-zext')
                    undefined(value<0,'zext nneg violation')
                if m[1]=='trunc' and dst<src:env[dest]=z.Extract(dst-1,0,value)
                elif m[1] in ('zext','sext') and dst>src:env[dest]=(z.ZeroExt if m[1]=='zext' else z.SignExt)(dst-src,value)
                else:raise Unsupported('cast widths')
                continue
            m=re.fullmatch('bitcast ('+TYPE+') (.+) to ('+TYPE+')',expr)
            if m:
                if {m[1],m[3]}!={'i32','<4 x i8>'}:raise Unsupported('bitcast types')
                env[dest]=from_bytes(m[3],to_bytes(m[1],val(m[1],m[2],env)));continue
            m=re.fullmatch('(add|sub|and|or|xor|shl|lshr|ashr)((?: nuw| nsw| disjoint)*) ('+TYPE+') (.+), (.+)',expr)
            if m:
                op,flags,ty,a,b=m.groups();a=val(ty,a,env);b=val(ty,b,env);w=width(ty);flags=flags.split()
                allowed={'add':{'nuw','nsw'},'sub':{'nuw','nsw'},'shl':{'nuw','nsw'},'or':{'disjoint'}}.get(op,set())
                if not set(flags)<=allowed:raise Unsupported('integer flags')
                if op in ('shl','lshr','ashr'):undefined(z.UGE(b,w),'oversized LLVM shift')
                operations={'add':lambda:a+b,'sub':lambda:a-b,'and':lambda:a&b,'or':lambda:a|b,'xor':lambda:a^b,'shl':lambda:a<<b,'lshr':lambda:z.LShR(a,b),'ashr':lambda:a>>b}
                value=operations[op]()
                if 'disjoint' in flags:undefined((a&b)!=0,'or disjoint violation')
                if 'nuw' in flags:
                    safe=z.BVAddNoOverflow(a,b,False) if op=='add' else z.BVSubNoUnderflow(a,b,False) if op=='sub' else z.LShR(value,b)==a
                    undefined(z.Not(safe),'nuw violation')
                if 'nsw' in flags:
                    safe=z.And(z.BVAddNoOverflow(a,b,True),z.BVAddNoUnderflow(a,b)) if op=='add' else z.And(z.BVSubNoOverflow(a,b),z.BVSubNoUnderflow(a,b,True)) if op=='sub' else (value>>b)==a
                    undefined(z.Not(safe),'nsw violation')
                env[dest]=value;continue
            m=re.fullmatch('icmp (eq|ne|ult|ule|ugt|uge|slt|sle|sgt|sge) ('+TYPE+') (.+), (.+)',expr)
            if m:
                a,b=val(m[2],m[3],env),val(m[2],m[4],env)
                predicates={'eq':lambda:a==b,'ne':lambda:a!=b,'ult':lambda:z.ULT(a,b),'ule':lambda:z.ULE(a,b),'ugt':lambda:z.UGT(a,b),'uge':lambda:z.UGE(a,b),'slt':lambda:a<b,'sle':lambda:a<=b,'sgt':lambda:a>b,'sge':lambda:a>=b}
                env[dest]=bit(predicates[m[1]]());continue
            m=re.fullmatch('select i1 (.+), ('+TYPE+') (.+), ('+TYPE+') (.+)',expr)
            if m:
                if m[2]!=m[4]:raise Unsupported('select types')
                width(m[2]);env[dest]=z.If(val('i1',m[1],env)==1,val(m[2],m[3],env),val(m[4],m[5],env));continue
            m=re.fullmatch('phi ('+TYPE+') (.+)',expr)
            if m:
                entries=re.findall(r'\[ ([^,]+), %([\w.]+) \]',m[2])
                if ', '.join('[ '+v+', %'+b+' ]' for v,b in entries)!=m[2]:raise Unsupported('phi syntax')
                selected=[v for v,b in entries if b==previous]
                if len(selected)!=1:raise Unsupported('phi predecessor')
                env[dest]=val(m[1],selected[0],old);continue
            raise Unsupported('LLVM expression '+expr)
        raise Unsupported('missing terminator')
    visit(next(iter(blocks)),env,Memory(),z.BoolVal(True),set())
    result=collect(exits,violations);result['observed_instructions']=sorted(observed)
    return result
