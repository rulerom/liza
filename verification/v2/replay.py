"""Concrete replay of actual Semantic IR mutants, separate from SMT proofs.
Small fixtures only; repeated complete header states prove a concrete cycle.
The execution cap is a test limit and is never used in induction obligations.
"""
def run(fn,data,needle=0,limit=1000):
    blocks={b.name:b for b in fn.blocks};env={fn.params[0]['name']:tuple(data)}
    if len(fn.params)>1:env[fn.params[1]['name']]=needle
    label=fn.blocks[0].name;previous=None;seen=set();reads=[]
    for step in range(limit):
        block=blocks[label];old=dict(env)
        for op in block.operations:
            if op.op=='phi':env[op.result]=old[op.args[op.incoming_blocks.index(previous)]]
        # Complete interpreter environment, not just one merge phi, determines
        # the future. Include immutable input and predecessor as well.
        phis=tuple(env[o.result] for o in block.operations if o.op=='phi')
        if phis:
            state=(label,previous,tuple(sorted(env.items())))
            if state in seen:return {'kind':'Cycle','state':list(phis),'reads':reads}
            seen.add(state)
        for op in block.operations:
            if op.op=='phi':continue
            args=[env[a] for a in op.args] if op.op!='constant' else []
            if op.op=='constant':value=op.args[0]
            elif op.op=='sequence.length':value=len(args[0])
            elif op.op=='view.read':
                if not 0<=args[1]<len(args[0]):return {'kind':'Trap','reason':'bounds','reads':reads}
                reads.append(args[1]);value=args[0][args[1]]
            elif op.op in ('add','sub'):
                a,b=args;value=a+b if op.op=='add' else a-b
                lo,hi=(-(1<<31),(1<<31)-1) if op.type=='i32' else (0,(1<<32)-1)
                if op.overflow=='trap' and not lo<=value<=hi:return {'kind':'Trap','reason':'arithmetic','reads':reads}
                if op.overflow=='wrap':
                    value%=1<<32
                    if op.type=='i32' and value>=(1<<31):value-=1<<32
            elif op.op in ('ult','ule','ugt','uge','eq','ne'):
                a,b=args;value={'ult':lambda:a<b,'ule':lambda:a<=b,'ugt':lambda:a>b,'uge':lambda:a>=b,'eq':lambda:a==b,'ne':lambda:a!=b}[op.op]()
            else:raise ValueError('replay unsupported '+op.op)
            env[op.result]=value
        term=block.terminator
        if term.op=='return':return {'kind':'Return','value':env[term.args[0]],'reads':reads}
        previous=label
        label=term.args[0] if term.op=='jump' else term.args[1] if env[term.args[0]] else term.args[2]
    return {'kind':'ReplayLimit'}


def reference(name,data,needle=0):
    if name=='search':return {'kind':'Return','value':next((i for i,v in enumerate(data) if v==needle),len(data))}
    acc=0
    for i,value in enumerate(data):
        acc+=value
        if not -(1<<31)<=acc<(1<<31):return {'kind':'Trap','first_prefix':i+1}
    return {'kind':'Return','value':acc}


def differs(expected,actual):
    if expected['kind']!=actual['kind']:return True
    if expected['kind']=='Return':return expected['value']!=actual['value']
    return actual.get('reason')!='arithmetic' or expected.get('first_prefix')!=len(actual.get('reads',[]))
