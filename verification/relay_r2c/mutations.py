"""Compiling source mutations in the real proxy lifecycle."""
MUTATIONS={
 'lost_persistence':('pairs[i]=copy pair','pairs[i]=copy pairs[i]'),
 'wrong_table_slot':('pairs[i]=copy pair','pairs[1]=copy pair'),
 'swapped_endpoints':('Pair(Some(client),Some(upstream),false,','Pair(Some(upstream),Some(client),false,'),
 'premature_connected':('Pair(Some(client),Some(upstream),false,','Pair(Some(client),Some(upstream),true,'),
 'retained_closed_pair':('pair=empty_pair()','pair=copy pair'),
 'one_fin_closes_pair':('if alive && pair.forward.fin && pair.reverse.fin','if alive && pair.forward.fin || pair.reverse.fin'),
 'disconnect_wrong_peer':('net.reactor_disconnect(reactor,upstream)','net.reactor_disconnect(reactor,client)'),
 'dirty_empty_pair':('Pair(None,None,false,','Pair(None,None,true,'),
}

def mutate(source,name):
    old,new=MUTATIONS[name]
    if source.count(old)!=1:raise ValueError('mutation anchor is not unique: '+name)
    return source.replace(old,new)
