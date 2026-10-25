"""Actual-IR lifecycle execution; no compiler dependency/effect summaries as axioms.

The finite table scans may be unfolded (eight slots). The event-loop backedge
is a cutpoint, never a bounded execution claim. Socket calls have explicit
logical ownership/phase contracts. Byte calls are handled by R2-B separately.
"""
import copy
import z3
from verification.relay_r1.semantic import Executor as DirectionExecutor
from verification.relay_r2b.semantic import group_returns
from verification.relay_r2b.fragment import Unsupported, require


def equal(a,b):
    if isinstance(a,dict):
        return z3.And(*[equal(a[k],b[k]) for k in a]) if isinstance(b,dict) and a.keys()==b.keys() else z3.BoolVal(False)
    if isinstance(a,(tuple,list)):
        return z3.And(*[equal(x,y) for x,y in zip(a,b)]) if isinstance(b,(tuple,list)) and len(a)==len(b) else z3.BoolVal(False)
    if isinstance(a,str) or isinstance(b,str): return z3.BoolVal(a==b)
    return a==b


def choose(c,a,b):
    if isinstance(a,dict): return {k:choose(c,a[k],b[k]) for k in a}
    if isinstance(a,tuple): return tuple(choose(c,x,y) for x,y in zip(a,b))
    if isinstance(a,str): require(a==b,'different structural alternatives');return a
    return z3.If(c,a,b)


class Executor:
    def __init__(self,module):
        require(module['version']==20,'IR version')
        self.functions={f['name']:f for f in module['functions']}
        self.structs={s['name']:[n for n,_ in s['fields']] for s in module['structures']}
        self.variants={s['name']:[n for n,_ in s['cases']] for s in module['variants']}
        self.pure=DirectionExecutor(module)
        self.serial=0
        self.helper_cache={}
        self.obligations=[]
        self.visited=set()
        self.budget=100000

    def fresh(self,name,boolean=False):
        self.serial+=1
        return (z3.Bool if boolean else z3.Int)(name+'_'+str(self.serial))

    def need(self,path,condition,label):
        self.obligations.append((label,z3.And(path,z3.Not(condition))))

    def runtime(self,callee,args,ghost,path):
        require(args and args[0]=='reactor','reactor identity')
        success=self.fresh('success',True);error=self.fresh('error') % 12
        domain=z3.And(0<=error,error<12)
        ghost=copy.deepcopy(ghost)
        name=callee.removeprefix('net.reactor_')
        if name=='poll':
            require(len(args)==2,'poll arity')
            self.need(path,z3.And(args[1]>=0,args[1]<=2147483647),'poll_timeout')
            yield success,('Ok',z3.IntVal(0)),ghost
        elif name=='accept':
            require(len(args)==1,'accept arity')
            yes=copy.deepcopy(ghost);yes['live'].add('new_client')
            yield success,('Ok','new_client'),yes
        elif name=='connect':
            require(len(args)==2,'connect arity')
            self.need(path,z3.And(args[1]>0,args[1]<=65535),'connect_port')
            yes=copy.deepcopy(ghost);yes['live'].add('new_upstream')
            yes['connected']=self.fresh('immediate_connect',True)
            yes['epoch']=ghost['epoch']+1
            yield success,('Ok','new_upstream'),yes
        elif name in ('ready','finish_connect','interest','disconnect'):
            require(len(args)==(3 if name=='interest' else 2),'socket call arity')
            peer=args[1]
            self.need(path,z3.BoolVal(peer in ghost['live']),'live_id:'+name)
            if name=='ready':
                flags=z3.BV2Int(z3.Int2BV(self.fresh('ready'),32))
                yield z3.And(success,0<=flags,flags<2**32),('Ok',flags),ghost
            elif name=='finish_connect':
                self.need(path,z3.BoolVal(peer==ghost['upstream']),'finish_upstream')
                done=z3.Or(ghost['connected'],self.fresh('connect_done',True))
                yes=copy.deepcopy(ghost);yes['connected']=done
                yield success,('Ok',done),yes
            elif name=='interest':
                self.need(path,z3.And(args[2]>=0,args[2]<=3),'interest_mask')
                yield success,('Ok',z3.IntVal(0)),ghost
            else:
                ghost['live'].discard(peer);ghost['closed'].append(peer)
                yield success,('Ok',z3.IntVal(0)),ghost
        else: raise Unsupported('lifecycle runtime: '+callee)
        # All declared ReactorError variants are represented. Retry policy is
        # interpreted from the real body, rather than classified here.
        failed_ghost=copy.deepcopy(ghost)
        if name=='interest':failed_ghost['failed']=z3.BoolVal(True)
        yield z3.And(z3.Not(success),domain),('Err',error),failed_ghost

    def helper(self,name,args):
        if name.startswith('relay.direction.'):
            key=(name,repr(args))
            if key not in self.helper_cache:self.helper_cache[key]=list(group_returns(self.pure.execute(name,args)))
            return self.helper_cache[key]
        require(name in ('liza_proxy.empty_pair','liza_proxy.retry'),'helper '+name)
        f=self.functions[name]
        out=self.execute(name,f['blocks'][0]['name'],None,dict(zip((p['name'] for p in f['params']),args)),{},None)
        returns=[(p,k,v) for p,k,v,g in out]
        if name=='liza_proxy.retry':
            # Merge the twelve real enum-switch returns into a single bool.
            good=[(p,v) for p,k,v in returns if k=='Return']
            require(len(good)==12,'closed retry enum')
            return [(z3.Or(*[p for p,_ in good]),'Return',z3.Or(*[z3.And(p,v) for p,v in good]))]
        return returns

    def execute(self,function,start,stop,env,ghost,previous=None,after_phi=False,stop_operation=None):
        blocks={b['name']:b for b in self.functions[function]['blocks']}
        exits=[]
        def walk(label,previous,env,ghost,path,position=0,skip_phi=False,depth=0):
            self.budget-=1
            require(self.budget>=0 and depth<300,'lifecycle execution budget / unsupported cycle')
            path=z3.simplify(path)
            if z3.is_false(path):return
            b=blocks[label];values=dict(env)
            if position==0:
                self.visited.add((function,label))
                if not skip_phi:
                    for o in b['operations']:
                        if o['op']=='phi':
                            require(o['incoming_blocks'].count(previous)==1,'phi predecessor')
                            values[o['result']]=env[o['args'][o['incoming_blocks'].index(previous)]]
                if label==stop or (isinstance(stop,set) and label in stop):
                    exits.append((path,'Cut',values,ghost));return
            for index in range(position,len(b['operations'])):
                o=b['operations'][index];op=o['op'];raw=o['args']
                if o['result']==stop_operation:
                    exits.append((path,'Cut',values,ghost));return
                if op=='phi':continue
                if op=='constant':
                    value=z3.BoolVal(raw[0]) if o['type']=='bool' else z3.IntVal(raw[0])
                else:
                    a=[values[v] for v in raw]
                    if op=='call':
                        if o['callee'].startswith('net.reactor_'):
                            outcomes=[(p,'Return',v,g) for p,v,g in self.runtime(o['callee'],a,ghost,path)]
                        else: outcomes=[(p,k,v,ghost) for p,k,v in self.helper(o['callee'],a)]
                        for guard,kind,value,newghost in outcomes:
                            if kind!='Return':exits.append((z3.And(path,guard),kind,None,newghost))
                            else:walk(label,previous,dict(values,**{o['result']:value}),newghost,z3.And(path,guard),index+1,depth=depth)
                        return
                    if op in ('copy','move'):value=a[0]
                    elif op=='struct.construct':value=dict(zip(self.structs[o['type']],a))
                    elif op=='struct.field':value=a[0][o['field_name']] if isinstance(a[0],dict) else a[0][self.structs[o['source_type']].index(o['field_name'])]
                    elif op=='struct.update':value=dict(a[0],**{o['field_name']:a[1]})
                    elif op=='variant.construct':value=(o['field_name'],*a)
                    elif op=='variant.payload':
                        require(a[0][0]==o['field_name'],'payload');value=a[0][1]
                    elif op=='variant.tag':
                        value=a[0] if o['source_type']=='ReactorError' else z3.IntVal(self.variants[o['source_type']].index(a[0][0]))
                    elif op=='array.repeat':
                        require(o['type']=='[liza_proxy.Pair;8]','table shape');value=[a[0]]*8
                    elif op in ('array.read','array.update'):
                        require(o['bounds_policy']=='trap','array bounds policy')
                        ix=z3.simplify(a[1]);require(z3.is_int_value(ix),'symbolic table index outside supported finite scan')
                        ix=ix.as_long()
                        if not 0<=ix<len(a[0]):exits.append((path,'Trap',None,ghost));return
                        if op=='array.read':value=a[0][ix]
                        else:value=list(a[0]);value[ix]=a[2]
                    elif op=='not':value=z3.Not(a[0])
                    elif op=='eq':value=equal(a[0],a[1])
                    elif op=='ne':value=z3.Not(equal(a[0],a[1]))
                    elif op=='ult':value=a[0]<a[1]
                    elif op=='or':
                        require(o['type']=='u32','bitwise type');value=z3.BV2Int(z3.Int2BV(a[0],32)|z3.Int2BV(a[1],32))
                    elif op=='add':
                        require(o['overflow']=='trap' and o['type']=='u32','arithmetic')
                        value=a[0]+a[1];safe=z3.And(value>=0,value<2**32)
                        exits.append((z3.And(path,z3.Not(safe)),'Trap',None,ghost));path=z3.And(path,safe)
                    else:raise Unsupported('lifecycle instruction '+op)
                values[o['result']]=value
            t=b['terminator'];a=t['args']
            if t['op']=='return':exits.append((path,'Return',values[a[0]],ghost))
            elif t['op']=='jump':walk(a[0],label,values,ghost,path,depth=depth+1)
            elif t['op']=='branch':
                walk(a[1],label,values,ghost,z3.And(path,values[a[0]]),depth=depth+1)
                walk(a[2],label,values,ghost,z3.And(path,z3.Not(values[a[0]])),depth=depth+1)
            elif t['op']=='switch':
                guards=[]
                for tag,target in a[2:]:
                    cond=values[a[0]]==tag;guards.append(cond)
                    walk(target,label,values,ghost,z3.And(path,cond),depth=depth+1)
                walk(a[1],label,values,ghost,z3.And(path,z3.Not(z3.Or(*guards))),depth=depth+1)
            elif t['op']=='unreachable':exits.append((path,'Undefined',None,ghost))
            else:raise Unsupported('terminator '+t['op'])
        walk(start,previous,env,ghost,z3.BoolVal(True),skip_phi=after_phi)
        return exits
