"""V1 fixed contracts: logical arrays, no physical pointers or byte storage."""
import z3 as z

SUBJECTS = ('read','update','snapshot','short_and','short_or','branch','constant_read','choose')


def inputs(name):
    args = [z.BitVec(n,8) for n in ('a','b','c','d')]+[z.BitVec('index',32)]
    if name in ('update','snapshot'):
        args += [z.BitVec('value',8),z.BitVec('observe',32)]
    elif name in ('short_and','short_or','branch','choose'):
        args += [z.BitVec('take',1)]
    return args


def at(array,index):
    # Only selected under the independently stated validity condition.
    return z.If(index==0,array[0],z.If(index==1,array[1],z.If(index==2,array[2],array[3])))


def specification(name,args):
    a,b,c,d,index = args[:5]
    bad = z.UGE(index,4)
    read = at((a,b,c,d),index)
    if name=='read': return bad,read
    if name=='constant_read': return z.BoolVal(False),c
    if name in ('update','snapshot'):
        value,observe = args[5:]
        j = observe & 3
        original = at((a,b,c,d),j)
        updated = z.If(j==index,value,original)
        return bad, updated if name=='update' else z.Concat(updated,original)
    take = args[5]==1
    if name=='choose':return z.BoolVal(False),z.If(take,b,a)
    if name=='branch':return z.And(take,bad),z.If(take,read,a)
    equal = z.If(read==a,z.BitVecVal(1,1),z.BitVecVal(0,1))
    if name=='short_and': return z.And(take,bad),z.If(take,equal,z.BitVecVal(0,1))
    if name=='short_or': return z.And(z.Not(take),bad),z.If(take,z.BitVecVal(1,1),equal)
    raise ValueError(name)


def concrete(name,args):
    array,index = list(args[:4]),args[4]
    if name=='constant_read':return {'kind':'Return','value':array[2]}
    if name=='choose':return {'kind':'Return','value':array[1] if args[5] else array[0]}
    if name in ('short_and','branch') and not args[5]:
        return {'kind':'Return','value':0 if name=='short_and' else array[0]}
    if name=='short_or' and args[5]:return {'kind':'Return','value':1}
    if index>=4:return {'kind':'Trap'}
    if name in ('read','branch'):value=array[index]
    elif name in ('short_and','short_or'):value=int(array[index]==array[0])
    else:
        new,observe=args[5:];j=observe%4
        updated=list(array);updated[index]=new
        value=updated[j] if name=='update' else array[j]+256*updated[j]
    return {'kind':'Return','value':value}
