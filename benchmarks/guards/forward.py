"""Research-only forwarding of unchanged scalar fields to by-value roots."""
import copy
from dataclasses import replace


def forward(module, unsafe=False):
    result=copy.deepcopy(module);certificates=[]
    scalar={'bool',*[f'{s}{n}' for s in ('u','i') for n in (8,16,32,64)]}
    eligible={n for n,s in module.structs.items() if s.properties.get('copyable') and 0<len(s.fields)<=64 and all(t in scalar for _,t in s.fields)}
    for fn in result:
        if fn.effect_contract!='pure':continue
        definitions={o.result:o for b in fn.blocks for o in b.operations}
        params=[p for p in fn.params if p['type'] in eligible and p.get('mode','value')=='value']
        for b in fn.blocks:
            for op in b.operations:
                if op.op!='struct.field' or op.source_type not in eligible:continue
                for p in params:
                    if p['type']!=op.source_type or op.args[0]==p['name']:continue
                    visited=set();witness=[]
                    def unchanged(value):
                        if value==p['name']:return True
                        if value in visited:return False # cycles/unsupported values fail closed
                        d=definitions.get(value)
                        if d is None:return False
                        visited.add(value)
                        if d.op=='struct.update' and d.type==p['type']:
                            ok=(unsafe or d.field_name!=op.field_name) and unchanged(d.args[0])
                        elif d.op=='phi' and d.type==p['type']:
                            ok=bool(d.args) and all(unchanged(v) for v in d.args)
                        else:ok=False
                        visited.remove(value)
                        if ok:witness.append(value)
                        return ok
                    if unchanged(op.args[0]) and any(definitions[v].op=='phi' for v in witness):
                        certificates.append({'function':fn.name,'block':b.name,'result':op.result,'field':op.field_name,'source':op.args[0],'root':p['name'],'witness':sorted(set(witness))})
                        op.args=[p['name']];break
    return result,certificates
