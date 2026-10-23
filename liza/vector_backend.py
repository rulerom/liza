"""Native lowering of initialized-prefix operations; no allocation or relocation."""
from .types import product_args


def emit(op, args, refs, types, large, size, write, lines):
    name, ty, operation = op.result, types[op.type], op.op
    descriptor = '{ ptr, i32, i32 }'
    if operation in ('vec.len', 'vec.capacity'):
        index = 1 if operation == 'vec.len' else 2
        lines.append(f'  %{name} = extractvalue {descriptor} {args[0]}, {index}')
        return
    if operation == 'vec.view':
        lines.extend([f'  %{name}_ptr = extractvalue {descriptor} {args[0]}, 0',
                      f'  %{name}_len = extractvalue {descriptor} {args[0]}, 1',
                      f'  %{name}_base = insertvalue {{ ptr, i32 }} zeroinitializer, ptr %{name}_ptr, 0',
                      f'  %{name} = insertvalue {{ ptr, i32 }} %{name}_base, i32 %{name}_len, 1'])
        return
    if operation == 'vec.release':
        lines.append(f'  %{name} = add i32 0, 0')
        return
    # The result slot contains a descriptor and at most one independent T,
    # never the backing capacity. All tail reads are behind a length check.
    dest = refs[name] if large(op.type) else f'%{name}_scratch'
    lines.append(f'  call void @llvm.memset.p0.i64(ptr {dest}, i8 0, i64 {size(op.type)}, i1 false)')
    product = operation != 'vec.get'
    result_type = product_args(op.type)[1] if product else op.type
    result_llvm = types[result_type]
    if product:
        lines.extend([f'  %{name}_vector_slot = getelementptr {ty}, ptr {dest}, i32 0, i32 0',
                      f'  store {descriptor} {args[0]}, ptr %{name}_vector_slot',
                      f'  %{name}_result_slot = getelementptr {ty}, ptr {dest}, i32 0, i32 1'])
        status = f'%{name}_result_slot'
    else:
        status = dest
    lines.extend([f'  %{name}_ptr = extractvalue {descriptor} {args[0]}, 0',
                  f'  %{name}_len = extractvalue {descriptor} {args[0]}, 1'])
    if operation == 'vec.push':
        lines.extend([f'  %{name}_cap = extractvalue {descriptor} {args[0]}, 2',
                      f'  %{name}_bad = icmp uge i32 %{name}_len, %{name}_cap'])
        index = f'%{name}_len'
    elif operation == 'vec.pop':
        lines.extend([f'  %{name}_bad = icmp eq i32 %{name}_len, 0',
                      f'  %{name}_previous = sub i32 %{name}_len, 1'])
        index = f'%{name}_previous'
    else:
        lines.append(f'  %{name}_bad = icmp uge i32 {args[1]}, %{name}_len')
        index = args[1]
    lines.extend([f'  br i1 %{name}_bad, label %{name}_absent, label %{name}_present',
                  f'{name}_absent:', f'  store i32 1, ptr {status}'])
    if operation in ('vec.push', 'vec.set'):
        # Result.Err, with Full=0 or OutOfBounds=1.
        lines.extend([f'  %{name}_error_slot = getelementptr {result_llvm}, ptr {status}, i32 0, i32 2',
                      f'  store i32 {int(operation == "vec.set")}, ptr %{name}_error_slot'])
    lines.extend([f'  br label %{name}_done', f'{name}_present:',
                  f'  %{name}_offset = zext i32 {index} to i64',
                  f'  %{name}_element = getelementptr {types[op.source_type]}, ptr %{name}_ptr, i64 %{name}_offset'])
    if operation in ('vec.push', 'vec.set'):
        write(op.source_type, args[-1], f'%{name}_element')
    else:
        lines.append(f'  %{name}_item_slot = getelementptr {result_llvm}, ptr {status}, i32 0, i32 1')
        if large(op.source_type):
            value = f'%{name}_element'
        else:
            lines.append(f'  %{name}_item = load {types[op.source_type]}, ptr %{name}_element')
            value = f'%{name}_item'
        write(op.source_type, value, f'%{name}_item_slot')
    if operation in ('vec.push', 'vec.pop'):
        if operation == 'vec.push':
            lines.append(f'  %{name}_next_length = add i32 %{name}_len, 1')
            length = f'%{name}_next_length'
        else:
            length = index
        lines.extend([f'  %{name}_next = insertvalue {descriptor} {args[0]}, i32 {length}, 1',
                      f'  store {descriptor} %{name}_next, ptr %{name}_vector_slot'])
    lines.extend([f'  br label %{name}_done', f'{name}_done:'])
    if not large(op.type):
        lines.append(f'  %{name} = load {ty}, ptr {dest}')
