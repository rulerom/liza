"""Actual Semantic IR acyclic segments cut at one externally selected header."""
import z3 as z
from .core import Unsupported,Exit,fits


def signed(value,bits=32):return z.If(value>=(1<<(bits-1)),value-(1<<bits),value)

class Engine:
    strict=False
    def __init__(self,fn,ctx):
        self.fn=fn;self.ctx=ctx;self.blocks={b.name:b for b in fn.blocks}
        visited=set();active=set();backtargets=set()
        def dfs(label):
            if label in active:backtargets.add(label);return
            if label in visited:return
            active.add(label);term=self.blocks[label].terminator
            targets=term.args[1:] if term.op=='branch' else term.args if term.op=='jump' else []
            for target in targets:dfs(target)
            active.remove(label);visited.add(label)
        dfs(fn.blocks[0].name)
        if len(backtargets)!=1:raise Unsupported('Semantic requires a single loop cutpoint')
        self.header=next(iter(backtargets))
        self.phis=[o for o in self.blocks[self.header].operations if o.op=='phi']
        if not self.phis:raise Unsupported('missing header phis')
        # External binding convention, verified by every entry/back/exit VC:
        # first phi = index; second phi = accumulator for sum.
        self.index=self.phis[0].result
        self.acc=self.phis[1].result if ctx.name=='sum' and len(self.phis)>1 else None
        if self.phis[0].type!='u32' or ctx.name=='sum' and (self.acc is None or self.phis[1].type!='i32'):
            raise Unsupported('Semantic loop role types')
        if fn.effect_contract!='pure':raise Unsupported('effects')
        if fn.result_type!=('u32' if ctx.name=='search' else 'i32'):raise Unsupported('result type')
        self.types={p['name']:p['type'] for p in fn.params}
        self.types.update({o.result:o.type for b in fn.blocks for o in b.operations})
        expected=['View<u8>','u8'] if ctx.name=='search' else ['View<i32>']
        if [p['type'] for p in fn.params]!=expected:raise Unsupported('Semantic signature')
        self.params={fn.params[0]['name']:'readonly_view'}
        if ctx.name=='search':self.params[fn.params[1]['name']]=ctx.needle
    def roles(self,env):return env[self.index],env[self.acc] if self.acc else None
    def symbolic_header(self,seed):
        env=dict(seed);ranges=[]
        for p in self.phis:
            if p.type not in ('u32','i32'):raise Unsupported('phi type')
            env[p.result]=z.Int('header_'+p.result)
            ranges.append(fits(env[p.result],p.type=='i32'))
        return env,z.And(*ranges)
    def entry(self):return self.walk(self.fn.blocks[0].name,self.params,False)
    def step(self,env):return self.walk(self.header,env,True)
    def walk(self,start,environment,skip_start_phi):
        exits=[]
        def visit(label,env,path,seen,previous=None,skip_phi=False):
            env=dict(env);block=self.blocks[label]
            if label==self.header and not skip_phi:
                old=dict(env)
                for phi in self.phis:
                    env[phi.result]=old[phi.args[phi.incoming_blocks.index(previous)]]
                exits.append(Exit('Back',path,env));return
            if label in seen:raise Unsupported('uncovered Semantic cycle')
            seen=seen|{label};old=dict(env)
            for op in block.operations:
                if op.op=='phi':
                    if skip_phi:continue
                    env[op.result]=old[op.args[op.incoming_blocks.index(previous)]]
                    continue
                if op.effect_contract!='pure':raise Unsupported('effectful operation')
                args=[env[a] for a in op.args] if op.op!='constant' else []
                if op.op=='constant':
                    if op.type not in ('bool','u32','i32'):raise Unsupported('constant type')
                    number=op.args[0]
                    if op.type=='bool':
                        if number not in (False,True):raise Unsupported('boolean constant')
                        value=z.BoolVal(bool(number))
                    else:
                        lo,hi=(-(1<<31),(1<<31)-1) if op.type=='i32' else (0,(1<<32)-1)
                        if not lo<=number<=hi:raise Unsupported('constant range')
                        value=z.IntVal(number)
                elif op.op=='sequence.length' and args==['readonly_view']:
                    if op.type!='u32' or op.source_type!=self.fn.params[0]['type']:raise Unsupported('length type')
                    value=self.ctx.length
                elif op.op=='view.read':
                    if args[0]!='readonly_view' or op.bounds_policy!='trap':raise Unsupported('view operation')
                    if op.type!=('u8' if self.ctx.name=='search' else 'i32') or op.source_type!=self.fn.params[0]['type'] or self.types[op.args[1]]!='u32':raise Unsupported('view types')
                    index=args[1];invalid=z.Or(index<0,index>=self.ctx.length)
                    exits.append(Exit('Trap',z.And(path,invalid),env,reason='bounds'))
                    path=z.And(path,z.Not(invalid));value=self.ctx.element(index)
                elif op.op in ('add','sub'):
                    if any(self.types[arg]!=op.type for arg in op.args):raise Unsupported('arithmetic operands')
                    a,b=args;wide=a+b if op.op=='add' else a-b
                    is_signed=op.type=='i32'
                    if op.type not in ('u32','i32'):raise Unsupported('arithmetic type')
                    if op.overflow=='trap':
                        invalid=z.Not(fits(wide,is_signed))
                        exits.append(Exit('Trap',z.And(path,invalid),env,reason='arithmetic'))
                        path=z.And(path,z.Not(invalid));value=wide
                    elif op.overflow=='wrap':value=signed(wide%(1<<32)) if is_signed else wide%(1<<32)
                    else:raise Unsupported('arithmetic policy')
                elif op.op in ('ult','ule','ugt','uge','eq','ne'):
                    if op.type!='bool' or self.types[op.args[0]]!=self.types[op.args[1]]:raise Unsupported('comparison types')
                    if op.op.startswith('u') and self.types[op.args[0]]!='u32':raise Unsupported('unsigned comparison operands')
                    a,b=args;value={'ult':lambda:a<b,'ule':lambda:a<=b,'ugt':lambda:a>b,'uge':lambda:a>=b,'eq':lambda:a==b,'ne':lambda:a!=b}[op.op]()
                else:raise Unsupported('Semantic operation '+op.op)
                env[op.result]=value
            term=block.terminator
            if term.op=='return':exits.append(Exit('Return',path,env,env[term.args[0]]))
            elif term.op=='jump':visit(term.args[0],env,path,seen,label)
            elif term.op=='branch':
                c=env[term.args[0]]
                visit(term.args[1],env,z.And(path,c),seen,label)
                visit(term.args[2],env,z.And(path,z.Not(c)),seen,label)
            else:raise Unsupported('Semantic terminator')
        visit(start,environment,z.BoolVal(True),set(),skip_phi=skip_start_phi)
        return exits
