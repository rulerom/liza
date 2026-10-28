"""Narrow research transforms: no production compiler policy."""
import re


def boundary_alias(ir):
    old='define void @stream_feed(ptr %state, ptr %bytes, i32 %length) {'
    if ir.count(old)!=1:raise ValueError('unsupported benchmark boundary')
    return ir.replace(old,old.replace('ptr %state','ptr noalias %state'))


def scalarize(ir):
    """Split nonvolatile loads/stores of named structs with integer-only fields."""
    types={}
    for name,body in re.findall(r'(?m)^(%[\w.]+) = type \{ ([^\n]+) \}$',ir):
        fields=body.split(', ')
        if all(re.fullmatch(r'i(?:1|8|16|32|64)',f) for f in fields):types[name]=fields
    result=[];sites=0
    for line in ir.splitlines():
        load=re.fullmatch(r'\s*(%[\w.]+) = load (%[\w.]+), ptr (%[\w.]+)(?:, align \d+)?',line)
        store=re.fullmatch(r'\s*store (%[\w.]+) (%[\w.]+), ptr (%[\w.]+)(?:, align \d+)?',line)
        if load and load[2] in types:
            name,ty,ptr=load.groups();prefix=f'%s2_{sites}';fields=types[ty]
            previous='poison'
            for i,f in enumerate(fields):
                result.extend([f'  {prefix}_p{i} = getelementptr {ty}, ptr {ptr}, i32 0, i32 {i}',f'  {prefix}_v{i} = load {f}, ptr {prefix}_p{i}, align 1'])
                value=name if i==len(fields)-1 else f'{prefix}_a{i}'
                result.append(f'  {value} = insertvalue {ty} {previous}, {f} {prefix}_v{i}, {i}')
                previous=value
            sites+=1
        elif store and store[1] in types:
            ty,value,ptr=store.groups();prefix=f'%s2_{sites}'
            for i,f in enumerate(types[ty]):
                result.extend([f'  {prefix}_v{i} = extractvalue {ty} {value}, {i}',f'  {prefix}_p{i} = getelementptr {ty}, ptr {ptr}, i32 0, i32 {i}',f'  store {f} {prefix}_v{i}, ptr {prefix}_p{i}, align 1'])
            sites+=1
        else:result.append(line)
    return '\n'.join(result)+'\n',sites
