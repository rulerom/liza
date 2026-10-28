"""Untimed optimized-IR traffic counters. Physical state spans, not CPU traffic."""
import re


def instrument(ir, root, size):
    if not 0<size<=256: raise ValueError('unsupported state size')
    lines=[];function=None;pending=False;serial=0;sites={'load':0,'store':0,'branch':0,'overflow':0}
    for original in ir.splitlines():
        # Instrumentation adds global writes and temporarily records root addresses.
        original=re.sub(r', !(?:noalias|alias.scope) !\d+', '', original)
        line=re.sub(r'(?<!\S)(?:memory\([^)]*\)|captures\([^)]*\)|nocapture|noalias|readonly|readnone)(?=\s|[,}])','',original)
        if line.startswith('define '):
            function=re.search(r'@([^ (]+)',line)[1];pending=function=='stream_feed'
        elif pending and line.strip() and not line.lstrip().startswith(';') and not re.match(r'^[\w.]+:',line):
            if ' = phi ' in line:raise ValueError('unsupported entry phi')
            lines.append(f'  call void @s2_begin(ptr %{root}, i64 {size})');pending=False
        if function:
            # ptr operand appears after the type/value; aggregates may contain commas.
            load=re.search(r'= load (.+?), ptr ([%@][\w.$]+)(?:,|$)',line)
            store=re.match(r'\s*store (.+), ptr ([%@][\w.$]+)(?:,|$)',line)
            kind=0 if load else 1
            match=load or store
            if match:
                if load:ty=load[1]
                else:
                    # Recognize emitted scalar, vector, array and named aggregate stores.
                    m=re.match(r'(%[\w.]+|i\d+|ptr|<[^>]+>|\[[^]]+\]) ',store[1])
                    if not m:raise ValueError('unsupported store type: '+line)
                    ty=m[1]
                if 'volatile' in ty or 'atomic' in ty:raise ValueError('unsupported access')
                # LLVM computes the target allocation span, including struct padding.
                prefix=f'%s2sz{serial}';serial+=1
                lines.extend([f'  {prefix}_p = getelementptr {ty}, ptr null, i32 1',f'  {prefix} = ptrtoint ptr {prefix}_p to i64',f'  call void @s2_record(i32 {kind}, ptr {match[2]}, i64 {prefix})'])
                sites['load' if load else 'store']+=1
            if re.match(r'\s*(br i1|switch )',line):
                lines.append('  call void @s2_record(i32 2, ptr null, i64 0)');sites['branch']+=1
            if ' call ' in line and '.with.overflow.' in line:
                lines.append('  call void @s2_record(i32 3, ptr null, i64 0)');sites['overflow']+=1
            if function=='stream_feed' and re.match(r'\s*ret ',line):lines.append('  call void @s2_end()')
        lines.append(line)
        if line=='}':function=None
    lines.extend(['declare void @s2_begin(ptr, i64)','declare void @s2_end()','declare void @s2_record(i32, ptr, i64)'])
    return '\n'.join(lines)+'\n',sites
