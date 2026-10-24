"""Understated return contracts; execution IR and analyzer observations stay intact."""
from . import fixtures

# Distinct origins matter: swapping parameters of TWO_BUFFERS alone would be
# conservative for that program because both buffers belong to one region.
DISTINCT = fixtures.TWO_BUFFERS.split('fn main', 1)[0] + fixtures.SAFE.replace(
    'released=memory.release(move buffer)', '''match memory.create(64) {
Err(e)=>{released=memory.release(move buffer)}
Ok(other)=>{
match memory.alloc<u8>(other,4,0) {
Err(e)=>{released=memory.release(move buffer)}
Ok(second)=>{next=choose(move buffer,move second)
released=memory.release(move next)}
}
closed_other=memory.close(move other)
}
}''')

CONTROLS = {
    'summary_empty_direct': (fixtures.CALL, 'empty_direct'),
    'summary_missing_returns': (fixtures.CALL, 'missing_returns'),
    'summary_missing_ok': (fixtures.RESULT_CALL, 'missing_ok'),
    'summary_empty_constructed_ok': (fixtures.WRAP, 'empty_ok'),
    'summary_wrong_variant': (fixtures.WRAP, 'wrong_variant'),
    'summary_wrong_parameter': (DISTINCT, 'wrong_parameter'),
    'summary_hidden_factory_region': (fixtures.FACTORY, 'hidden_region'),
    'summary_wrong_payload_origin': (fixtures.RESULT_CALL, 'wrong_payload_origin'),
}


def understate(module, mutation):
    helper = next(fn for fn in module if fn.name != 'main')
    contract = helper.storage_contract
    returns = contract['returns']
    if mutation == 'empty_direct': returns['depends_on'] = []
    elif mutation == 'missing_returns': del contract['returns']
    elif mutation == 'missing_ok': del returns['variants']['Ok']
    elif mutation == 'empty_ok': returns['variants']['Ok']['depends_on'] = []
    elif mutation == 'wrong_variant':
        returns['variants']['Err'] = returns['variants'].pop('Ok')
    elif mutation == 'wrong_parameter': returns['depends_on'] = ["('parameter', '0')"]
    elif mutation == 'hidden_region': returns['variants']['Ok']['regions'] = []
    elif mutation == 'wrong_payload_origin':
        returns['variants']['Ok']['depends_on'] = ["('parameter', '0', 'Err')"]
    else: raise ValueError(mutation)
    return helper.name
