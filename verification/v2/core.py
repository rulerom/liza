"""Inductive obligations, independent of either IR executor.

A proof is over one arbitrary traversal between cutpoints, not unrolling.
Prefix sums are mathematical ghosts: only true defining equations needed by
this step are instantiated. They are NOT assumptions about program variables.
"""
from dataclasses import dataclass
import z3 as z

U32=(1<<32)-1
MIN=-(1<<31)
MAX=(1<<31)-1

class Unsupported(ValueError):pass

def fits(value,signed=False,bits=32):
    return z.And(value>=(-(1<<(bits-1)) if signed else 0),value<=((1<<(bits-1))-1 if signed else (1<<bits)-1))

@dataclass
class Exit:
    kind:str
    path:object
    env:dict
    value:object=None
    reason:str=''

class Context:
    def __init__(self,name,physical=False):
        self.name=name;self.physical=physical
        self.length=z.Int('length');self.needle=z.Int('needle')
        self.data=z.Array('bytes' if physical else 'data',z.IntSort(),z.IntSort())
        self.prefix=z.Array('mathematical_prefix',z.IntSort(),z.IntSort())
        self.constraints=z.And(fits(self.length),fits(self.needle,bits=8))
    @property
    def stride(self):return 1 if self.name=='search' else 4
    def byte(self,offset):return z.Select(self.data,offset)%256
    def element(self,index):
        if not self.physical:
            unsigned=z.Select(self.data,index)%(256 if self.name=='search' else (1<<32))
        elif self.stride==1:unsigned=self.byte(index)
        else:unsigned=sum(self.byte(index*4+k)*(1<<(8*k)) for k in range(4))
        return z.If(unsigned>=(1<<31),unsigned-(1<<32),unsigned) if self.name=='sum' else unsigned
    def S(self,index):return z.Select(self.prefix,index)
    def history(self,index):
        j=z.Int('prefix_j')
        if self.name=='search':return z.ForAll(j,z.Implies(z.And(j>=0,j<index),self.element(j)!=self.needle))
        return z.ForAll(j,z.Implies(z.And(j>=0,j<=index),fits(self.S(j),True)))
    def invariant(self,index,acc=None,strict=False):
        terms=[index>=0,index<self.length if strict else index<=self.length,self.history(index)]
        if self.name=='sum':terms.append(acc==self.S(index))
        return z.And(*terms)
    def definitions(self,index=None):
        if self.name=='search':return z.BoolVal(True)
        definitions=[self.S(0)==0]
        if index is not None:
            definitions.append(z.Implies(z.And(index>=0,index<self.length),self.S(index+1)==self.S(index)+self.element(index)))
        return z.And(*definitions)
    def post(self,value):
        if self.name=='sum':return z.And(value==self.S(self.length),self.history(self.length))
        return z.Or(z.And(value==self.length,self.history(self.length)),
                    z.And(value>=0,value<self.length,self.element(value)==self.needle,self.history(value)))
    def expected_trap(self,index):
        return z.BoolVal(False) if self.name=='search' else z.And(index<self.length,z.Not(fits(self.S(index)+self.element(index),True)))


def obligations(engine,ctx):
    """All concrete entry edges, all back edges, all exits and termination.

engine returns actual CFG paths; it may cut ONLY at the declared loop header.
Any other cycle must be rejected. Every returned/trapping path is checked.
"""
    entry=engine.entry()
    cuts=[e for e in entry if e.kind=='Back']
    if len(cuts)!=1:raise Unsupported('requires one entry cutpoint path')
    seed=cuts[0].env
    initial_i,initial_acc=engine.roles(seed)
    initial=[]
    for e in entry:
        if e.kind=='Back':
            i,acc=engine.roles(e.env);condition=ctx.invariant(i,acc,engine.strict)
        elif e.kind=='Return':condition=ctx.post(e.value)
        else:condition=z.BoolVal(False)
        initial.append(z.Implies(e.path,condition))
    result=[('entry.coverage',ctx.constraints,z.Or(*[e.path for e in entry])),
            ('entry.invariant_and_exits',z.And(ctx.constraints,ctx.definitions()),z.And(*initial))]
    env,state_ranges=engine.symbolic_header(seed)
    i,acc=engine.roles(env)
    invariant=ctx.invariant(i,acc,engine.strict)
    assumptions=z.And(ctx.constraints,state_ranges,invariant,ctx.definitions(i))
    paths=engine.step(env)
    result.append(('step.coverage',assumptions,z.Or(*[e.path for e in paths])))
    result.append(('step.no_undefined',assumptions,z.Not(z.Or(*[e.path for e in paths if e.kind=='Undefined']))))
    if not ctx.physical:
        result.append(('step.no_bounds_trap',assumptions,z.Not(z.Or(*[e.path for e in paths if e.kind=='Trap' and e.reason=='bounds']))))
    result.append(('step.exact_first_trap',assumptions,
                   z.Or(*[e.path for e in paths if e.kind=='Trap'])==ctx.expected_trap(i)))
    backs=[e for e in paths if e.kind=='Back']
    returns=[e for e in paths if e.kind=='Return']
    preserve=[];progress=[];transition=[]
    for e in backs:
        next_i,next_acc=engine.roles(e.env)
        preserve.append(z.Implies(e.path,ctx.invariant(next_i,next_acc,engine.strict)))
        progress.append(z.Implies(e.path,z.And(ctx.length-i>=0,ctx.length-next_i>=0,ctx.length-next_i<ctx.length-i)))
        relation=next_i==i+1
        if ctx.name=='sum':relation=z.And(relation,next_acc==ctx.S(i+1))
        else:relation=z.And(relation,i<ctx.length,ctx.element(i)!=ctx.needle)
        transition.append(z.Implies(e.path,relation))
    result.extend([('backedge.invariant',assumptions,z.And(*preserve)),
                   ('backedge.strict_ranking',assumptions,z.And(*progress)),
                   ('backedge.prefix_transition',assumptions,z.And(*transition)),
                   ('exit.postcondition',assumptions,z.And(*[z.Implies(e.path,ctx.post(e.value)) for e in returns]))])
    return result
