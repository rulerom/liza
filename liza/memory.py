"""Audited memory-library signatures; source calls retain normal argument order."""
from dataclasses import replace
import hashlib
from .frontend import Function, Token, CompileError, Enum
from .types import is_buffer, buffer_element

REGION = 'memory.Region'
ERROR = 'MemoryError'
OPERATIONS = {'create':'region.create', 'alloc':'region.alloc', 'set':'buffer.update',
              'view':'buffer.view', 'release':'buffer.release', 'close':'region.close',
              'len':'buffer.length'}


def error_declaration():
    return Enum(Token(ERROR,1,1),[(Token(n,1,1),None) for n in ('OutOfMemory','Exhausted','SizeOverflow')])


def signature(node, actuals, mono):
    operation = node.token.text.removeprefix('memory.')
    if operation not in OPERATIONS:
        raise CompileError(node.token, 'unknown memory operation')
    element = ''
    if operation == 'alloc':
        if len(node.type_args) != 1:
            raise CompileError(node.token, 'memory.alloc requires one explicit element type')
        element = mono.concrete_type(node.type_args[0], node.token)
        if not mono.structs.ensure(element)['copyable']:
            raise CompileError(node.token, 'region buffers require copyable elements')
    elif operation in ('set','view','release','len'):
        if not actuals or actuals[0] is None: return None
        if not is_buffer(actuals[0]):
            raise CompileError(node.token, 'expected memory.Buffer<T>')
        element = buffer_element(actuals[0])
    if operation != 'alloc' and node.type_args:
        raise CompileError(node.token, 'only memory.alloc accepts explicit type arguments')
    buffer = 'memory.Buffer<'+element+'>'
    parameters, result, borrowed, effect = {
        'create':(['u64'],'Result<memory.Region,MemoryError>',[],'alloc'),
        'alloc':([REGION,'u32',element],'Result<'+buffer+',MemoryError>',[0],'alloc'),
        'set':([buffer,'u32',element],buffer,[],'pure'),
        'view':([buffer],'View<'+element+'>',[0],'pure'),
        'len':([buffer],'u32',[0],'pure'),
        'release':([buffer],'u32',[],'pure'),
        'close':([REGION],'u32',[],'alloc'),
    }[operation]
    if len(actuals) != len(parameters):
        raise CompileError(node.token, 'wrong number of memory operation arguments')
    symbol='memory$'+operation+'$'+hashlib.sha256(element.encode()).hexdigest()
    fn=Function(replace(node.token,text=symbol),[(Token('p'+str(i),1,1),t) for i,t in enumerate(parameters)],[],result,effect,borrowed_params=borrowed)
    fn.memory_operation=OPERATIONS[operation]
    fn.memory_element=element
    mono.signatures[symbol]=fn
    mono.structs.ensure(result)
    return fn


def validate_element_layout(t, structs):
    """Bound native element layouts before LLVM's fixed-width size constants.

    Supported native targets use 64-bit pointers. Scalars/aggregates have at
    most 8-byte alignment; this does not choose a runtime allocation strategy.
    """
    from .types import INTEGER_TYPES, width, is_array, element_type, array_length
    def layout(name):
        if name in INTEGER_TYPES: size=width(name)//8;return size,size
        if name=='bool':return 1,1
        if name=='Text':return 16,8
        if is_array(name):
            size,alignment=layout(element_type(name));size*=array_length(name)
        else:
            if name in structs.variants:
                members=['u32']+[v for _,v in structs.variants[name].cases if v is not None]
            else:members=[v for _,v in structs[name].fields]
            size,alignment=0,1
            for member in members:
                member_size,member_alignment=layout(member)
                alignment=max(alignment,member_alignment)
                size=((size+member_alignment-1)//member_alignment)*member_alignment+member_size
            size=((size+alignment-1)//alignment)*alignment
        if size>9223372036854775807:
            raise ValueError('buffer element layout exceeds supported signed 64-bit size')
        return size,alignment
    layout(t)
