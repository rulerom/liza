"""Small, fail-closed symbolic interpreters for an acyclic scalar IR subset.

This code is part of the trusted base, not a verified LLVM implementation.
Reachable poison creation is conservatively rejected, including unused values.
"""
import re
import z3 as z


class Unsupported(ValueError):
    pass


def checked(op, a, b, signed):
    if op == 'add':
        safe = z.BVAddNoOverflow(a, b, signed)
        if signed: safe = z.And(safe, z.BVAddNoUnderflow(a, b))
        value = a+b
    elif op == 'sub':
        safe = z.BVSubNoUnderflow(a, b, signed)
        if signed: safe = z.And(safe, z.BVSubNoOverflow(a, b))
        value = a-b
    elif op == 'mul':
        safe = z.BVMulNoOverflow(a, b, signed)
        if signed: safe = z.And(safe, z.BVMulNoUnderflow(a, b))
        value = a*b
    else:
        raise Unsupported('arithmetic: '+op)
    return value, z.Not(safe)


def outcome(exits):
    return {
        'trap': z.Or(*[p for kind, p, v in exits if kind == 'trap']),
        'bad': z.Or(*[p for kind, p, v in exits if kind == 'bad']),
        'returns': [(p, v) for kind, p, v in exits if kind == 'return'],
        'covered': z.Or(*[p for kind, p, v in exits]),
    }


def semantic(fn, args):
    if fn.effect_contract != 'pure': raise Unsupported('effectful function')
    if len(fn.params) != len(args): raise Unsupported('parameter count')
    for p, a in zip(fn.params, args):
        if p['type'] not in ('u8', 'i8', 'bool'): raise Unsupported('parameter type')
        if (1 if p['type']=='bool' else 8) != a.size(): raise Unsupported('parameter width')
    blocks = {b.name: b for b in fn.blocks}
    exits = []

    def visit(label, env, path, seen, previous=None):
        if label in seen: raise Unsupported('loop')
        seen = seen | {label}
        env = dict(env)
        b = blocks[label]
        for v in b.operations:
            if v.effect_contract != 'pure': raise Unsupported('effectful operation')
            width = 1 if v.type == 'bool' else 8
            if v.type not in ('u8', 'i8', 'bool'): raise Unsupported('operation type')
            if v.op == 'constant':
                env[v.result] = z.BitVecVal(int(v.args[0]), width)
            elif v.op in ('add', 'sub', 'mul') and v.overflow == 'trap':
                result, trap = checked(v.op, env[v.args[0]], env[v.args[1]], v.type=='i8')
                exits.append(('trap', z.And(path, trap), None))
                path = z.And(path, z.Not(trap))
                env[v.result] = result
            elif v.op == 'phi':
                env[v.result] = env[v.args[v.incoming_blocks.index(previous)]]
            else: raise Unsupported('Semantic IR operation: '+v.op)
        t = b.terminator
        if t.op == 'return': exits.append(('return', path, env[t.args[0]]))
        elif t.op == 'jump': visit(t.args[0], env, path, seen, label)
        elif t.op == 'branch':
            condition = env[t.args[0]] == 1
            visit(t.args[1], env, z.And(path, condition), seen, label)
            visit(t.args[2], env, z.And(path, z.Not(condition)), seen, label)
        else: raise Unsupported('Semantic IR terminator: '+t.op)
    visit(fn.blocks[0].name, {p['name']:a for p,a in zip(fn.params,args)}, z.BoolVal(True), set())
    return outcome(exits)


def llvm_function(text, name):
    match = re.search(r'^define ([^\n]+) @liza_'+re.escape(name)+r'\(([^\n]*)\)([^\n]*) \{\n(.*?)^}', text, re.M|re.S)
    if not match: raise Unsupported('missing LLVM function: '+name)
    return match.groups()


def llvm(text, name, args):
    result, params, attrs, body = llvm_function(text, name)
    # Return range is a poison promise: check it on every return, not assume it.
    ranges = re.findall(r'range\(i8 (-?\d+), (-?\d+)\)', result)
    rest = re.sub(r'range\(i8 -?\d+, -?\d+\)\s*', '', result)
    if rest not in ('i8', 'noundef i8'): raise Unsupported('return attributes: '+result)
    ps = params.split(',') if params else []
    if len(ps) != len(args): raise Unsupported('LLVM parameter count')
    env = {}
    for p, a in zip(ps, args):
        m = re.fullmatch(r'i(1|8) (%[\w.]+)', p.strip())
        if not m or int(m[1]) != a.size(): raise Unsupported('LLVM parameter: '+p)
        env[m[2]] = a
    if not re.fullmatch(r'(?: local_unnamed_addr)?(?: #\d+)?', attrs):
        raise Unsupported('function attributes: '+attrs)
    # Group attributes may only describe the pure scalar subset or trap effects.
    group = re.search(r'#(\d+)', attrs)
    if group:
        decl = re.search(r'^attributes #'+group[1]+r' = \{ (.*) \}', text, re.M)
        if not decl: raise Unsupported('missing attributes')
        allowed = r'(?:nounwind|nofree|nosync|norecurse|mustprogress|willreturn|memory\(none\)|memory\(inaccessiblemem: write\))'
        if not re.fullmatch(allowed+r'(?: '+allowed+r')*', decl[1]):
            raise Unsupported('attribute group: '+decl[1])
    blocks = {}; current = None
    for line in body.splitlines():
        line = line.split(';')[0].strip()
        if not line: continue
        if line.endswith(':'):
            current = line[:-1]
            if current in blocks: raise Unsupported('duplicate block')
            blocks[current] = []
        elif current is None: raise Unsupported('unnamed entry block')
        else: blocks[current].append(line)
    exits = []

    def val(token, width, env):
        token = token.strip()
        if token.startswith('%'):
            v = env[token]
            if not z.is_bv(v) or v.size()!=width: raise Unsupported('operand type')
            return v
        if token in ('true','false'): return z.BitVecVal(int(token=='true'),width)
        if not re.fullmatch(r'-?\d+', token): raise Unsupported('operand: '+token)
        return z.BitVecVal(int(token),width)

    def visit(label, env, path, seen, previous=None):
        if label in seen: raise Unsupported('LLVM loop')
        seen = seen | {label}; env = dict(env)
        instructions = blocks[label]
        for pos, line in enumerate(instructions):
            if re.fullmatch(r'(?:tail )?call void @llvm.trap\(\)(?: #\d+)?', line):
                if instructions[pos+1:] != ['unreachable']: raise Unsupported('trap continuation')
                exits.append(('trap',path,None)); return
            if line == 'unreachable':
                exits.append(('bad',path,None)); return
            m = re.fullmatch(r'ret i8 (.+)', line)
            if m:
                value = val(m[1],8,env)
                for lo, hi in ranges:
                    lo, hi = int(lo)%256, int(hi)%256
                    inside = z.And(z.UGE(value,lo),z.ULT(value,hi)) if lo<hi else z.Or(z.UGE(value,lo),z.ULT(value,hi))
                    exits.append(('bad',z.And(path,z.Not(inside)),None))
                exits.append(('return',path,value))
                if pos != len(instructions)-1: raise Unsupported('instructions after return')
                return
            m = re.fullmatch(r'br label %([\w.]+)',line)
            if m:
                if pos != len(instructions)-1: raise Unsupported('instructions after branch')
                visit(m[1],env,path,seen,label);return
            m = re.fullmatch(r'br i1 (.+), label %([\w.]+), label %([\w.]+)',line)
            if m:
                if pos != len(instructions)-1: raise Unsupported('instructions after branch')
                c = val(m[1],1,env)==1
                visit(m[2],env,z.And(path,c),seen,label)
                visit(m[3],env,z.And(path,z.Not(c)),seen,label);return
            m = re.fullmatch(r'(%[\w.]+) = (.+)',line)
            if not m: raise Unsupported('LLVM instruction: '+line)
            dest, expr = m.groups()
            m = re.fullmatch(r'(?:tail )?call \{\s*i8, i1\s*\} @llvm\.([us])(add|sub|mul)\.with\.overflow\.i8\(i8 (.+), i8 (.+)\)',expr)
            if m:
                v, overflow = checked(m[2],val(m[3],8,env),val(m[4],8,env),m[1]=='s')
                env[dest] = (v,z.If(overflow,z.BitVecVal(1,1),z.BitVecVal(0,1)));continue
            m = re.fullmatch(r'extractvalue \{\s*i8, i1\s*\} (%[\w.]+), ([01])',expr)
            if m: env[dest] = env[m[1]][int(m[2])];continue
            m = re.fullmatch(r'(add|sub|mul)((?: nuw| nsw)*) i8 (.+), (.+)',expr)
            if m:
                a,b = val(m[3],8,env),val(m[4],8,env)
                v,_ = checked(m[1],a,b,False)
                for flag in m[2].split():
                    _,bad = checked(m[1],a,b,flag=='nsw')
                    exits.append(('bad',z.And(path,bad),None))
                env[dest] = v;continue
            m = re.fullmatch(r'phi i8 (.+)',expr)
            if m:
                entries = re.findall(r'\[ ([^,]+), %([\w.]+) \]',m[1])
                if ', '.join('[ '+v+', %'+b+' ]' for v,b in entries)!=m[1]: raise Unsupported('phi syntax')
                candidates = [v for v,b in entries if b==previous]
                if len(candidates)!=1: raise Unsupported('phi predecessor')
                env[dest] = val(candidates[0],8,env);continue
            m = re.fullmatch(r'icmp (eq|ne|ult|ule|ugt|uge|slt|sle|sgt|sge) i(1|8) (.+), (.+)',expr)
            if m:
                a,b = val(m[3],int(m[2]),env),val(m[4],int(m[2]),env)
                predicates={'eq':lambda:a==b,'ne':lambda:a!=b,'ult':lambda:z.ULT(a,b),'ule':lambda:z.ULE(a,b),'ugt':lambda:z.UGT(a,b),'uge':lambda:z.UGE(a,b),'slt':lambda:a<b,'sle':lambda:a<=b,'sgt':lambda:a>b,'sge':lambda:a>=b}
                env[dest]=z.If(predicates[m[1]](),z.BitVecVal(1,1),z.BitVecVal(0,1));continue
            raise Unsupported('LLVM expression: '+expr)
        raise Unsupported('missing terminator')
    visit(next(iter(blocks)),env,z.BoolVal(True),set())
    return outcome(exits)
