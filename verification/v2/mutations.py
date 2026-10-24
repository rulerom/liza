from dataclasses import asdict
import copy
from liza.frontend import Parser
from liza.ir import lower


def cases(module):
    functions={fn.name:fn for fn in module}
    def clone(name):return copy.deepcopy(functions[name])
    search=clone('search')
    next(o for b in search.blocks for o in b.operations if o.op=='ult').op='ule'
    yield 'off_by_one',search,[],1
    search=clone('search')
    search.blocks[0].operations[0].args=[1]
    yield 'skip_first',search,[7],7
    text='''fn search(data:View<u8>,needle:u8)->u32 {
      var i:u32=0;var last:u32=data.len
      while i<data.len {if data[i]==needle {last=i}i=i+1}return last
    }
    fn main()->u32{return 0}'''
    search=next(f for f in lower(Parser(text).parse()) if f.name=='search')
    yield 'last_instead_of_first',search,[7,7],7
    for label,increment in (('wrong_index',2),('no_progress',0)):
        search=clone('search')
        next(o for b in search.blocks for o in b.operations if o.op=='constant' and o.args==[1]).args=[increment]
        yield label,search,[0,7],7
    total=clone('sum')
    next(o for b in total.blocks for o in b.operations if o.op=='add' and o.type=='i32').overflow='wrap'
    yield 'removed_overflow',total,[(1<<31)-1,1,-1],0
    text='''fn sum(data:View<i32>)->i32 {var i:u32=0;var acc:i32=0
       while i<data.len {acc=acc+data[(data.len-1)-i];i=i+1}return acc
    }
    fn main()->u32{return 0}'''
    total=next(f for f in lower(Parser(text).parse()) if f.name=='sum')
    yield 'reordered_addends',total,[(1<<31)-1,1,-1],0
    total=clone('sum')
    phi=next(o for b in total.blocks for o in b.operations if o.op=='phi' and o.type=='i32')
    phi.args[1]=phi.result
    yield 'old_accumulator_phi',total,[1],0
