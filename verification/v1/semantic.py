"""Logical value interpreter. No objects, pointers, offsets or storage aliases."""
import z3 as z
from .common import Unsupported, bit, collect, scalar

WIDTHS={'bool':1,'u8':8,'u16':16,'u32':32}


def evaluate(fn,args):
    if fn.effect_contract!='pure':raise Unsupported('effectful function')
    if len(fn.params)!=len(args):raise Unsupported('parameter arity')
    env={p['name']:scalar(a,WIDTHS[p['type']]) for p,a in zip(fn.params,args)}
    blocks={b.name:b for b in fn.blocks};exits=[]

    def visit(label,env,path,seen,previous=None):
        if label in seen:raise Unsupported('Semantic loop')
        seen=seen|{label};env=dict(env)
        block=blocks[label]
        # Phi inputs are read simultaneously from the predecessor environment.
        old=dict(env)
        for op in block.operations:
            if op.effect_contract!='pure':raise Unsupported('Semantic effect')
            values=[env[a] for a in op.args] if op.op not in ('constant','phi') else []
            if op.op=='constant':value=z.BitVecVal(int(op.args[0]),WIDTHS[op.type])
            elif op.op=='array.construct' and op.type=='[u8;4]':
                if len(values)!=4:raise Unsupported('array length')
                value=tuple(scalar(v,8) for v in values)
            elif op.op=='copy' and op.type=='[u8;4]':value=tuple(values[0])
            elif op.op in ('array.read','array.update'):
                if op.bounds_policy!='trap':raise Unsupported('bounds policy')
                array,index=values[:2]
                if not isinstance(array,tuple) or len(array)!=4:raise Unsupported('array type')
                scalar(index,32)
                trap=z.UGE(index,4)
                exits.append(('Trap',z.And(path,trap),None));path=z.And(path,z.Not(trap))
                if op.op=='array.read':
                    value=array[0]
                    for j in range(1,4):value=z.If(index==j,array[j],value)
                else:
                    replacement=scalar(values[2],8)
                    value=tuple(z.If(index==j,replacement,array[j]) for j in range(4))
            elif op.op=='phi':
                value=old[op.args[op.incoming_blocks.index(previous)]]
            elif op.op in ('and','or'):
                a,b=values;value=a&b if op.op=='and' else a|b
            elif op.op=='eq':value=bit(values[0]==values[1])
            elif op.op=='convert.checked' and op.source_type=='u8' and op.type=='u16':
                value=z.ZeroExt(8,scalar(values[0],8))
            elif op.op=='shl' and op.shift_policy=='trap':
                a,count=values;trap=z.UGE(count,a.size())
                exits.append(('Trap',z.And(path,trap),None));path=z.And(path,z.Not(trap))
                value=a<<z.Extract(a.size()-1,0,count)
            else:raise Unsupported('Semantic operation '+op.op)
            if op.type in WIDTHS:scalar(value,WIDTHS[op.type])
            elif op.type!='[u8;4]':raise Unsupported('Semantic type '+op.type)
            env[op.result]=value
        term=block.terminator
        if term.op=='return':
            exits.append(('Return',path,scalar(env[term.args[0]],WIDTHS[fn.result_type])))
        elif term.op=='jump':visit(term.args[0],env,path,seen,label)
        elif term.op=='branch':
            c=scalar(env[term.args[0]],1)==1
            visit(term.args[1],env,z.And(path,c),seen,label)
            visit(term.args[2],env,z.And(path,z.Not(c)),seen,label)
        else:raise Unsupported('Semantic terminator '+term.op)
    visit(fn.blocks[0].name,env,z.BoolVal(True),set())
    return collect(exits)
