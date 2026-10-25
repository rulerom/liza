"""Concrete whole-exchange replay, Python values only; no symbolic/Z3 imports.

A bounded witness is diagnostic, never the induction argument. Runtime tokens
are fresh per epoch. Byte histories and socket phases persist across the trace.
"""
import argparse
import json
from pathlib import Path
from verification.relay_r1.replay import run as direction_run


class Violation(Exception):pass


def run(module,epochs=2,budget=20000):
    functions={f['name']:f for f in module['functions']}
    structs={s['name']:[n for n,_ in s['fields']] for s in module['structures']}
    variants={s['name']:[n for n,_ in s['cases']] for s in module['variants']}
    trace=[];B=bytearray(32768);live=set();closed=set();phase={};histories={};epoch=0;completed=0
    attempts={};reads={};remaining=[budget]
    class Done(Exception):pass

    def direction_history(number,side):
        return histories.setdefault((number,side),dict(R=bytearray(),W=bytearray()))

    def table_check(table):
        for slot,pair in enumerate(table):
            if pair['client'][0]=='None':
                if pair['upstream'][0]!='None' or pair['connected'] or pair['forward']!=(0,0,False,False) or pair['reverse']!=(0,0,False,False):
                    raise Violation('inactive slot retains state')
                continue
            if pair['upstream'][0]!='Some':raise Violation('active slot without upstream')
            client=pair['client'][1];upstream=pair['upstream'][1]
            if client not in live or upstream not in live or client==upstream:raise Violation('stale or duplicate pair identity')
            number=int(client.split(':')[1])
            if client!='client:'+str(number) or upstream!='upstream:'+str(number):raise Violation('wrong pair endpoints')
            if pair['connected'] and not phase[upstream]:raise Violation('connected before completion')
            for side,base in [('forward',slot*4096),('reverse',slot*4096+2048)]:
                h,t,e,f=pair[side]
                if not(0<=h<=t<=2048) or (f and not(e and h==t)):raise Violation('invalid Direction')
                history=direction_history(number,side)
                if history['R']!=history['W']+B[base+h:base+t]:raise Violation('byte history / persisted Pair mismatch')

    def runtime(name,args):
        nonlocal epoch,completed
        trace.append(dict(call=name,args=args))
        if name in ('console.print_u64','console.write'):return ('Ok',0)
        if name=='net.reactor_port':return ('Ok',9004)
        if name=='net.reactor_poll':
            if completed>=epochs:raise Done()
            return ('Ok',1)
        if name=='net.reactor_accept':
            if live:return ('Err',('WouldBlock',))
            epoch+=1;client='client:'+str(epoch);live.add(client);return ('Ok',client)
        if name=='net.reactor_connect':
            upstream='upstream:'+str(epoch);live.add(upstream);phase[upstream]=False
            return ('Ok',upstream)
        if name=='net.reactor_close':live.clear();return ('Ok',0)
        if len(args)<2 or args[1] not in live:raise Violation('I/O using invalidated socket')
        peer=args[1];number=int(peer.split(':')[1])
        if name=='net.reactor_ready':return ('Ok',5)
        if name=='net.reactor_finish_connect':
            if not peer.startswith('upstream:'):raise Violation('finish_connect wrong endpoint')
            attempts[peer]=attempts.get(peer,0)+1
            phase[peer]=attempts[peer]>=2
            return ('Ok',phase[peer])
        if name=='net.reactor_interest':return ('Ok',0)
        if name=='net.reactor_disconnect':
            # A normal replay must not discard any pending byte history.
            for side in ('forward','reverse'):
                h=direction_history(number,side)
                if h['R']!=h['W']:raise Violation('disconnect discards pending bytes on normal path')
            live.remove(peer)
            if not live:completed+=1
            return ('Ok',0)
        if peer.startswith('upstream:') and not phase[peer]:raise Violation('I/O before connect completes')
        if name=='net.reactor_shutdown_write':
            if peer in closed:raise Violation('repeated FIN')
            side='forward' if peer.startswith('upstream:') else 'reverse'
            h=direction_history(number,side)
            if h['R']!=h['W']:raise Violation('FIN with pending bytes')
            closed.add(peer);return ('Ok',0)
        if name in ('net.reactor_read','net.reactor_write'):
            start,count=args[3:]
            if not 0<=start<start+count<=len(B):raise Violation('invalid runtime range')
            if name=='net.reactor_read':
                side='forward' if peer.startswith('client:') else 'reverse'
                data=(b'abc' if side=='forward' else b'XYZabcd') if not reads.get(peer) else b''
                reads[peer]=True;data=data[:count]
                B[start:start+len(data)]=data;direction_history(number,side)['R'].extend(data)
                return ('buffer',('Ok',len(data)))
            if peer in closed:raise Violation('write after FIN')
            side='forward' if peer.startswith('upstream:') else 'reverse'
            n=min(count,1);direction_history(number,side)['W'].extend(B[start:start+n]);return ('Ok',n)
        raise ValueError('unsupported concrete runtime '+name)

    def call(name,args):
        if name.startswith('relay.direction.'):
            result=direction_run(module,name,args)
            trace.append(dict(helper=name,arguments=args,result=result['value']))
            if result['outcome']!='Return':raise Violation('Direction trap')
            return result['value']
        f=functions[name];blocks={b['name']:b for b in f['blocks']}
        env=dict(zip((p['name'] for p in f['params']),args))
        label=f['blocks'][0]['name'];previous=None
        while True:
            remaining[0]-=1
            if remaining[0]<0:raise ValueError('replay budget exceeded')
            b=blocks[label];old=dict(env)
            trace.append(dict(function=name,block=label,previous=previous))
            for o in b['operations']:
                op=o['op'];raw=o['args']
                if op=='phi':value=old[raw[o['incoming_blocks'].index(previous)]]
                elif op in ('constant','text.literal'):value=raw[0]
                else:
                    a=[env[v] for v in raw]
                    if op=='call':
                        value=runtime(o['callee'],a) if o['callee'].startswith(('net.','console.')) else call(o['callee'],a)
                    elif op in ('copy','move','unpack.consume'):value=a[0]
                    elif op=='struct.construct':value=dict(zip(structs[o['type']],a))
                    elif op=='struct.field':value=a[0][o['field_name']] if isinstance(a[0],dict) else a[0][structs[o['source_type']].index(o['field_name'])]
                    elif op=='struct.update':value=dict(a[0],**{o['field_name']:a[1]})
                    elif op=='array.repeat':value=[a[0]]*8
                    elif op in ('array.read','array.update'):
                        if not 0<=a[1]<len(a[0]):raise Violation('table bounds trap')
                        if op=='array.read':value=a[0][a[1]]
                        else:
                            value=list(a[0]);value[a[1]]=a[2];table_check(value)
                    elif op=='variant.construct':value=(o['field_name'],*a)
                    elif op=='variant.tag':value=variants[o['source_type']].index(a[0][0])
                    elif op=='variant.payload':
                        if a[0][0]!=o['field_name']:raise ValueError('payload mismatch')
                        value=a[0][1]
                    elif op=='buffer.view':value='view'
                    elif op=='buffer.release':value=0
                    elif op=='unpack.component':value=a[0][int(o['field_name'])]
                    elif op=='convert.checked':value=a[0]
                    elif op=='not':value=not a[0]
                    elif op=='eq':value=a[0]==a[1]
                    elif op=='ne':value=a[0]!=a[1]
                    elif op=='ult':value=a[0]<a[1]
                    elif op=='and':value=a[0]&a[1]
                    elif op=='or':value=a[0]|a[1]
                    elif op in ('add','mul','sub'):
                        if o['overflow']!='trap':raise ValueError('unsupported arithmetic')
                        value=a[0]+a[1] if op=='add' else a[0]*a[1] if op=='mul' else a[0]-a[1]
                        if not 0<=value<2**32:raise Violation('checked arithmetic trap')
                    else:raise ValueError('concrete instruction '+op)
                env[o['result']]=value
            if name=='liza_proxy.exchange' and label=='b13':table_check(env['v33'])
            t=b['terminator'];a=t['args']
            if t['op']=='return':return env[a[0]]
            previous=label
            if t['op']=='jump':label=a[0]
            elif t['op']=='branch':label=a[1] if env[a[0]] else a[2]
            elif t['op']=='switch':label=next((target for tag,target in a[2:] if tag==env[a[0]]),a[1])
            elif t['op']=='unreachable':raise Violation('unreachable')
            else:raise ValueError('concrete terminator '+t['op'])
    try:
        call('liza_proxy.exchange',['reactor','buffer',9003,False])
        return dict(confirmed=False,reason='returned',trace=trace)
    except Done:
        return dict(confirmed=False,completed_epochs=completed,trace=trace)
    except Violation as error:
        return dict(confirmed=True,violation=str(error),epoch=epoch,trace=trace)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ir',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();result=run(json.loads(Path(args.ir).read_text()))
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='trace'}))
